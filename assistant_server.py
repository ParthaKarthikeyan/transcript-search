#!/usr/bin/env python3
"""
Transcript Assistant Server
Flask backend that connects to RunPod for AI-powered transcript analysis.
"""

import os
import json
import time
import requests
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='.')
CORS(app)

# RunPod Configuration - Set these environment variables in Render
ENDPOINT_ID = os.environ.get('RUNPOD_ENDPOINT_ID', '')
RUNPOD_API_KEY = os.environ.get('RUNPOD_API_KEY', '')
RUNPOD_URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/run"
RUNPOD_STATUS_URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/status"
RUNPOD_HEADERS = {
    "Authorization": f"Bearer {RUNPOD_API_KEY}",
    "Content-Type": "application/json",
}

# Processing parameters
MAX_TOKENS = 32768
MAX_CONTEXT_CHARS = 20000  # Increased - batch limit now 32768 tokens
MAX_WAIT_TIME = 300  # 5 minutes
CHECK_INTERVAL = 2  # Check every 2 seconds

# Load transcripts
TRANSCRIPT_DIR = Path(__file__).parent / "formatted"
TRANSCRIPTS = []

def load_transcripts():
    """Load all transcripts into memory."""
    global TRANSCRIPTS
    TRANSCRIPTS = []
    
    if not TRANSCRIPT_DIR.exists():
        print(f"Warning: Transcript directory not found: {TRANSCRIPT_DIR}")
        return
    
    import re
    pattern = r'^((?:Agent|Customer|Speaker \d+))\s*\[starttime:\s*(\d+:\d+)\s*-\s*endtime:\s*(\d+:\d+)\]:\s*(.*)$'
    
    for filepath in sorted(TRANSCRIPT_DIR.glob("*.txt")):
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            filename = filepath.stem
            display_name = re.sub(r'^audio_Call1-', '', filename)
            display_name = re.sub(r'\.MP3$', '', display_name, flags=re.IGNORECASE)
            
            utterances = []
            for line in content.split('\n'):
                line = line.strip()
                if not line:
                    continue
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    utterances.append({
                        'speaker': match.group(1),
                        'text': match.group(4).strip()
                    })
            
            if utterances:
                # Create condensed text for context
                condensed = "\n".join([f"{u['speaker']}: {u['text']}" for u in utterances])
                TRANSCRIPTS.append({
                    'id': filename,
                    'name': display_name,
                    'utterances': utterances,
                    'text': condensed,
                    'char_count': len(condensed)
                })
        except Exception as e:
            print(f"Error loading {filepath.name}: {e}")
    
    print(f"Loaded {len(TRANSCRIPTS)} transcripts")

def find_relevant_transcripts(question: str, max_chars: int = MAX_CONTEXT_CHARS) -> list:
    """
    Find transcripts relevant to the question.
    For aggregate questions, sample across all transcripts.
    For specific questions, use keyword matching.
    """
    question_lower = question.lower()
    
    # Check if this is an aggregate question
    aggregate_keywords = ['main', 'common', 'most', 'overall', 'general', 'typical', 
                         'usually', 'often', 'frequently', 'issues', 'problems',
                         'painpoints', 'pain points', 'challenges', 'complaints',
                         'summarize', 'summary', 'patterns', 'trends']
    
    is_aggregate = any(kw in question_lower for kw in aggregate_keywords)
    
    if is_aggregate:
        # For aggregate questions, sample transcripts evenly
        # to get a representative view
        selected = []
        total_chars = 0
        step = max(1, len(TRANSCRIPTS) // 30)  # Aim for ~30 transcripts
        
        for i in range(0, len(TRANSCRIPTS), step):
            t = TRANSCRIPTS[i]
            if total_chars + t['char_count'] > max_chars:
                break
            selected.append(t)
            total_chars += t['char_count']
        
        return selected
    else:
        # For specific questions, use keyword matching
        keywords = [w for w in question_lower.split() if len(w) > 3]
        
        scored = []
        for t in TRANSCRIPTS:
            text_lower = t['text'].lower()
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scored.append((score, t))
        
        # Sort by score descending
        scored.sort(key=lambda x: -x[0])
        
        selected = []
        total_chars = 0
        for score, t in scored:
            if total_chars + t['char_count'] > max_chars:
                break
            selected.append(t)
            total_chars += t['char_count']
        
        # If no matches, fall back to sampling
        if not selected:
            return find_relevant_transcripts("summarize main issues", max_chars)
        
        return selected

def build_context(transcripts: list, question: str) -> str:
    """Build the context string for the LLM."""
    context_parts = []
    
    for i, t in enumerate(transcripts, 1):
        context_parts.append(f"=== Transcript {i} (ID: {t['name']}) ===\n{t['text']}\n")
    
    return "\n".join(context_parts)

def create_prompt(question: str, context: str, num_transcripts: int, total_transcripts: int) -> str:
    """Create the full prompt for the LLM."""
    system_prompt = f"""You are reviewing {num_transcripts} customer service transcripts. Answer the question directly.

{context}

Question: {question}

Answer directly. Cite transcript IDs when giving examples."""

    return system_prompt

def extract_text_from_output(output) -> str:
    """Extract the actual text response from various RunPod output formats."""
    if isinstance(output, str):
        return output
    
    if isinstance(output, dict):
        # Try common keys
        for key in ['text', 'response', 'generated_text', 'content']:
            if key in output:
                return extract_text_from_output(output[key])
        
        # Check for choices array (OpenAI format)
        if 'choices' in output and isinstance(output['choices'], list):
            choices = output['choices']
            if choices:
                choice = choices[0]
                if isinstance(choice, dict):
                    # Check for message content
                    if 'message' in choice and 'content' in choice['message']:
                        return choice['message']['content']
                    # Check for text
                    if 'text' in choice:
                        return choice['text']
                    # Check for tokens
                    if 'tokens' in choice and isinstance(choice['tokens'], list):
                        return ''.join(choice['tokens'])
        
        # Return string representation as fallback
        return str(output)
    
    if isinstance(output, list):
        # Try to join if it's a list of strings/tokens
        if all(isinstance(item, str) for item in output):
            return ''.join(output)
        # Check if it's a choices-like structure
        if output and isinstance(output[0], dict):
            return extract_text_from_output(output[0])
        return str(output)
    
    return str(output)

def call_runpod(prompt: str) -> str:
    """Submit job to RunPod and wait for response."""
    # vLLM on RunPod - parameters go in sampling_params
    payload = {
        "input": {
            "prompt": prompt,
            "sampling_params": {
                "max_tokens": 4096,
                "temperature": 0.3,
                "top_p": 0.95,
            }
        }
    }
    
    # Submit job
    try:
        response = requests.post(RUNPOD_URL, headers=RUNPOD_HEADERS, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
    except Exception as e:
        return f"Error submitting to RunPod: {str(e)}"
    
    job_id = result.get('id')
    if not job_id:
        return f"Error: No job ID returned. Response: {result}"
    
    # Poll for result
    status_url = f"{RUNPOD_STATUS_URL}/{job_id}"
    start_time = time.time()
    
    while time.time() - start_time < MAX_WAIT_TIME:
        try:
            response = requests.get(status_url, headers=RUNPOD_HEADERS, timeout=30)
            response.raise_for_status()
            result = response.json()
        except Exception as e:
            return f"Error checking status: {str(e)}"
        
        status = result.get('status')
        
        if status == 'COMPLETED':
            output = result.get('output', {})
            text = extract_text_from_output(output)
            # Clean up common artifacts
            text = text.strip()
            # Remove any leading instruction artifacts
            if text.startswith("Focus on details"):
                text = text.split("\n\n", 1)[-1] if "\n\n" in text else text
            return text
        elif status == 'FAILED':
            return f"Job failed: {result.get('error', 'Unknown error')}"
        elif status in ['IN_QUEUE', 'IN_PROGRESS']:
            time.sleep(CHECK_INTERVAL)
        else:
            return f"Unknown status: {status}"
    
    return "Error: Request timed out"

@app.route('/')
def serve_index():
    """Serve the search.html file."""
    return send_from_directory('.', 'search.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files."""
    return send_from_directory('.', filename)

def format_response(raw_response: str) -> str:
    """Format the LLM response into clean HTML."""
    import re
    
    text = raw_response.strip()
    
    # Remove thinking tags and content before them
    if '</think>' in text:
        text = text.split('</think>')[-1].strip()
    if '<think>' in text:
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    
    # Remove chain-of-thought reasoning patterns
    cot_patterns = [
        r"^Answer with just text.*?\.\s*",
        r"^Okay,?\s*so I need to.*?carefully\.\s*",
        r"^Let me go through.*?\.\s*",
        r"^Looking at the.*?:\s*",
        r"^I see that.*?\.\s*",
    ]
    for pattern in cot_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove common instruction leaks at start
    prefixes_to_remove = [
        r"^Now,?\s*Answer.*?:\s*",
        r"^Based on the transcripts.*?:\s*",
        r"^Here is my analysis:?\s*",
        r"^Format as per example.*?\.\s*",
        r"^Avoid unnecessary details\.?\s*",
        r"^\([^)]*\)\s*",  # Remove (e.g., ...) at start
        r"^Use bold.*?\.\s*",  # Remove "Use bold to differentiate..."
        r"^Note:.*?\.\s*",  # Remove "Note: ..." at start
        r"^The example.*?\.\s*",  # Remove "The example provided..."
        r"^I'll.*?\.\s*",  # Remove "I'll use..." type responses
        r"^Okay,?\s*",  # Remove "Okay, " at start
    ]
    for pattern in prefixes_to_remove:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)
    
    # Clean up markdown artifacts
    text = re.sub(r'\*\*\\', '', text)  # Remove **\ patterns
    text = re.sub(r'\\+"', '"', text)    # Fix escaped quotes
    text = text.replace('---', '')       # Remove horizontal rules
    
    # If it looks like JSON, try to extract meaningful content
    if text.strip().startswith('{'):
        try:
            # Find complete JSON if possible
            first_brace = text.find('{')
            brace_count = 0
            end_pos = first_brace
            for i, c in enumerate(text[first_brace:], first_brace):
                if c == '{':
                    brace_count += 1
                elif c == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = i
                        break
            
            json_str = text[first_brace:end_pos + 1]
            data = json.loads(json_str)
            
            # Format JSON as HTML
            html_parts = []
            
            if 'summary' in data:
                html_parts.append(f"<p><strong>{data['summary']}</strong></p>")
            
            if 'key_findings' in data:
                html_parts.append("<div class='findings'>")
                for i, finding in enumerate(data['key_findings'], 1):
                    title = finding.get('title', f'Finding {i}')
                    desc = finding.get('description', '')
                    html_parts.append(f"<div class='finding'>")
                    html_parts.append(f"<div class='finding-title'>{i}. {title}</div>")
                    html_parts.append(f"<div class='finding-desc'>{desc}</div>")
                    html_parts.append("</div>")
                html_parts.append("</div>")
            
            if 'recommendations' in data:
                html_parts.append("<div class='recommendations'>")
                html_parts.append("<div class='rec-title'>💡 Recommendations</div>")
                for rec in data['recommendations']:
                    html_parts.append(f"<div class='rec-item'>• {rec}</div>")
                html_parts.append("</div>")
            
            if html_parts:
                return ''.join(html_parts)
        except (json.JSONDecodeError, ValueError):
            pass  # Fall through to text formatting
    
    # Format plain text response nicely
    # First, highlight transcript references
    text = re.sub(r'Transcript\s*(\d+)', r'<span class="transcript-ref">Transcript \1</span>', text)
    text = re.sub(r'\(ID:\s*([a-f0-9-]+)\)', r'<span class="transcript-ref">\1</span>', text)
    
    # Split into sentences for better formatting
    # Break up long paragraphs into readable chunks
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    if len(sentences) <= 3:
        # Short response - just format nicely
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        return f"<div class='response-content'><p>{text}</p></div>"
    
    # Group sentences into logical paragraphs (2-3 sentences each)
    html_parts = ["<div class='response-content'>"]
    current_para = []
    step_count = 0
    
    for i, sentence in enumerate(sentences):
        sentence = sentence.strip()
        if not sentence:
            continue
            
        # Apply inline bold
        sentence = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', sentence)
        
        # Check if this looks like a step/process
        if re.match(r'^(First|Second|Third|Then|Next|Finally|Once|After|If)', sentence, re.IGNORECASE):
            # Output previous paragraph if any
            if current_para:
                html_parts.append(f"<p>{' '.join(current_para)}</p>")
                current_para = []
            
            step_count += 1
            html_parts.append(f"<div class='step-item'><div class='step-number'>{step_count}</div><div class='step-content'>{sentence}</div></div>")
        # Check for "For example" or specific examples
        elif re.match(r'^For example|^In Transcript|^As seen in', sentence, re.IGNORECASE):
            if current_para:
                html_parts.append(f"<p>{' '.join(current_para)}</p>")
                current_para = []
            html_parts.append(f"<div class='finding'><div class='finding-desc'>{sentence}</div></div>")
        else:
            current_para.append(sentence)
            # Group 2-3 sentences per paragraph
            if len(current_para) >= 2:
                html_parts.append(f"<p>{' '.join(current_para)}</p>")
                current_para = []
    
    # Output remaining sentences
    if current_para:
        html_parts.append(f"<p>{' '.join(current_para)}</p>")
    
    html_parts.append("</div>")
    return ''.join(html_parts)

@app.route('/api/ask', methods=['POST'])
def ask_question():
    """Handle question from the chat interface."""
    data = request.json
    question = data.get('question', '').strip()
    
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    
    if not TRANSCRIPTS:
        return jsonify({'error': 'No transcripts loaded'}), 500
    
    # Find relevant transcripts
    relevant = find_relevant_transcripts(question)
    
    if not relevant:
        return jsonify({'error': 'Could not find relevant transcripts'}), 500
    
    # Build context and prompt
    context = build_context(relevant, question)
    prompt = create_prompt(question, context, len(relevant), len(TRANSCRIPTS))
    
    # Call RunPod
    raw_answer = call_runpod(prompt)
    
    # Log raw output for debugging
    print("\n" + "="*60)
    print("RAW RUNPOD OUTPUT:")
    print("="*60)
    print(raw_answer)
    print("="*60 + "\n")
    
    # Format the response
    formatted_answer = format_response(raw_answer)
    
    return jsonify({
        'answer': formatted_answer,
        'raw_output': raw_answer,  # Include raw output for debugging
        'transcripts_analyzed': len(relevant),
        'total_transcripts': len(TRANSCRIPTS)
    })

@app.route('/api/status', methods=['GET'])
def get_status():
    """Return server status and transcript count."""
    return jsonify({
        'status': 'ok',
        'transcripts_loaded': len(TRANSCRIPTS)
    })

# Load transcripts at module level for gunicorn
print("Loading transcripts...")
load_transcripts()
print(f"Loaded {len(TRANSCRIPTS)} transcripts")

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get('PORT', 5000))
    print(f"\nStarting server on http://localhost:{port}")
    print(f"Open http://localhost:{port} in your browser")
    print("Press Ctrl+C to stop\n")
    app.run(host='0.0.0.0', port=port, debug=False)

