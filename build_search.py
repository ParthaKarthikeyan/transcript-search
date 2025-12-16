#!/usr/bin/env python3
"""
Transcript Search Tool Builder
Parses all transcripts and generates a standalone HTML search application.
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime

# Configuration
TRANSCRIPT_DIR = Path(__file__).parent / "formatted"
OUTPUT_FILE = Path(__file__).parent / "search.html"

def parse_transcript(filepath: Path) -> dict:
    """Parse a single transcript file into structured data."""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Extract filename without extension for display
    filename = filepath.stem
    # Clean up the filename for display (remove audio_Call1- prefix)
    display_name = re.sub(r'^audio_Call1-', '', filename)
    display_name = re.sub(r'\.MP3$', '', display_name, flags=re.IGNORECASE)
    
    # Parse individual utterances
    # Pattern: Speaker [starttime: MM:SS - endtime: MM:SS]: Text
    pattern = r'^((?:Agent|Customer|Speaker \d+))\s*\[starttime:\s*(\d+:\d+)\s*-\s*endtime:\s*(\d+:\d+)\]:\s*(.*)$'
    
    utterances = []
    full_text_parts = []
    
    for line in content.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        match = re.match(pattern, line, re.IGNORECASE)
        if match:
            speaker = match.group(1)
            start_time = match.group(2)
            end_time = match.group(3)
            text = match.group(4).strip()
            
            # Normalize speaker names
            if speaker.lower() == 'agent' or speaker.lower() == 'speaker 2':
                speaker_type = 'agent'
            else:
                speaker_type = 'customer'
            
            utterances.append({
                'speaker': speaker,
                'speaker_type': speaker_type,
                'start': start_time,
                'end': end_time,
                'text': text
            })
            full_text_parts.append(f"{speaker}: {text}")
    
    return {
        'id': filename,
        'name': display_name,
        'filename': filepath.name,
        'utterances': utterances,
        'full_text': '\n'.join(full_text_parts),
        'utterance_count': len(utterances)
    }

def load_all_transcripts() -> list:
    """Load and parse all transcripts from the directory."""
    transcripts = []
    
    if not TRANSCRIPT_DIR.exists():
        print(f"Error: Transcript directory not found: {TRANSCRIPT_DIR}")
        return transcripts
    
    txt_files = list(TRANSCRIPT_DIR.glob("*.txt"))
    print(f"Found {len(txt_files)} transcript files")
    
    for filepath in sorted(txt_files):
        try:
            transcript = parse_transcript(filepath)
            transcripts.append(transcript)
        except Exception as e:
            print(f"Error parsing {filepath.name}: {e}")
    
    return transcripts

def generate_html(transcripts: list) -> str:
    """Generate the complete HTML search application."""
    
    # Convert transcripts to JSON for embedding
    transcripts_json = json.dumps(transcripts, ensure_ascii=False)
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Transcript Search</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: #f8fafc;
            --bg-secondary: #ffffff;
            --bg-tertiary: #f1f5f9;
            --bg-card: #ffffff;
            --border-color: #e2e8f0;
            --border-hover: #cbd5e1;
            --text-primary: #0f172a;
            --text-secondary: #475569;
            --text-muted: #94a3b8;
            --accent-primary: #3b82f6;
            --accent-primary-light: #eff6ff;
            --accent-secondary: #8b5cf6;
            --agent-color: #059669;
            --agent-bg: #ecfdf5;
            --customer-color: #d97706;
            --customer-bg: #fffbeb;
            --highlight-bg: #fef08a;
            --highlight-text: #854d0e;
            --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.07), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -4px rgba(0, 0, 0, 0.05);
            --radius-sm: 6px;
            --radius-md: 8px;
            --radius-lg: 12px;
            --transition-fast: 150ms ease;
            --transition-smooth: 250ms ease;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        html {{
            font-size: 16px;
            scroll-behavior: smooth;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            line-height: 1.6;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}

        /* Header - Hidden, using sidebar for context */
        .header {{
            display: none;
        }}

        /* Search Box */
        .search-container {{
            position: sticky;
            top: 0;
            z-index: 100;
            background: linear-gradient(180deg, var(--bg-primary) 0%, var(--bg-primary) 85%, transparent 100%);
            padding: 2rem 0 1.5rem;
            margin-bottom: 0.5rem;
        }}

        .search-box {{
            max-width: 720px;
            margin: 0 auto;
        }}

        .search-input-wrapper {{
            position: relative;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            transition: all var(--transition-fast);
            box-shadow: var(--shadow-sm);
        }}

        .search-input-wrapper:focus-within {{
            border-color: var(--accent-primary);
            box-shadow: 0 0 0 3px var(--accent-primary-light), var(--shadow-md);
        }}

        .search-icon {{
            position: absolute;
            left: 1rem;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-muted);
            transition: color var(--transition-fast);
            pointer-events: none;
        }}

        .search-input-wrapper:focus-within .search-icon {{
            color: var(--accent-primary);
        }}

        #searchInput {{
            width: 100%;
            padding: 1rem 1rem 1rem 3rem;
            font-family: inherit;
            font-size: 1rem;
            background: transparent;
            border: none;
            color: var(--text-primary);
            outline: none;
        }}

        #searchInput::placeholder {{
            color: var(--text-muted);
        }}

        /* Syntax Help */
        .syntax-help {{
            display: flex;
            justify-content: center;
            gap: 1.5rem;
            margin-top: 0.75rem;
            font-size: 0.8125rem;
            color: var(--text-muted);
        }}

        .syntax-item {{
            display: flex;
            align-items: center;
            gap: 0.375rem;
        }}

        .syntax-item code {{
            background: var(--bg-tertiary);
            padding: 0.125rem 0.375rem;
            border-radius: 4px;
            font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
            font-size: 0.75rem;
            color: var(--text-secondary);
        }}

        /* Controls */
        .controls {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.75rem;
            justify-content: center;
            align-items: center;
            margin-top: 1rem;
        }}

        .control-group {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .toggle-btn {{
            display: flex;
            align-items: center;
            gap: 0.375rem;
            padding: 0.5rem 0.875rem;
            font-family: inherit;
            font-size: 0.8125rem;
            font-weight: 500;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            color: var(--text-secondary);
            cursor: pointer;
            transition: all var(--transition-fast);
        }}

        .toggle-btn:hover {{
            border-color: var(--border-hover);
            background: var(--bg-tertiary);
        }}

        .toggle-btn.active {{
            background: var(--accent-primary-light);
            border-color: var(--accent-primary);
            color: var(--accent-primary);
        }}

        .toggle-btn svg {{
            width: 14px;
            height: 14px;
        }}

        .filter-select {{
            padding: 0.5rem 2rem 0.5rem 0.875rem;
            font-family: inherit;
            font-size: 0.8125rem;
            font-weight: 500;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            color: var(--text-secondary);
            cursor: pointer;
            appearance: none;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: right 0.625rem center;
            transition: all var(--transition-fast);
        }}

        .filter-select:hover {{
            border-color: var(--border-hover);
        }}

        .filter-select:focus {{
            outline: none;
            border-color: var(--accent-primary);
            box-shadow: 0 0 0 3px var(--accent-primary-light);
        }}

        /* Stats Bar */
        .stats-bar {{
            display: flex;
            justify-content: center;
            gap: 2rem;
            margin-top: 1.25rem;
            padding: 0.875rem 1.5rem;
            background: var(--bg-secondary);
            border-radius: var(--radius-md);
            border: 1px solid var(--border-color);
            max-width: 720px;
            margin-left: auto;
            margin-right: auto;
        }}

        .stat-item {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.8125rem;
            color: var(--text-muted);
        }}

        .stat-value {{
            color: var(--accent-primary);
            font-weight: 600;
        }}

        .stat-item.search-time .stat-value {{
            color: var(--accent-secondary);
        }}

        /* Results */
        .results-container {{
            margin-top: 1.5rem;
        }}

        /* Transcript Cards */
        .transcript-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            margin-bottom: 0.75rem;
            overflow: hidden;
            transition: all var(--transition-fast);
            box-shadow: var(--shadow-sm);
        }}

        .transcript-card:hover {{
            border-color: var(--border-hover);
            box-shadow: var(--shadow-md);
        }}

        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem 1.25rem;
            cursor: pointer;
            transition: background var(--transition-fast);
        }}

        .card-header:hover {{
            background: var(--bg-tertiary);
        }}

        .card-title {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}

        .card-icon {{
            width: 36px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--accent-primary-light);
            border-radius: var(--radius-md);
            color: var(--accent-primary);
        }}

        .card-name {{
            font-size: 0.9375rem;
            font-weight: 500;
            color: var(--text-primary);
            font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
        }}

        .card-meta {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}

        .match-count {{
            font-size: 0.75rem;
            font-weight: 600;
            padding: 0.25rem 0.625rem;
            background: var(--accent-primary-light);
            border-radius: 20px;
            color: var(--accent-primary);
        }}

        .expand-icon {{
            color: var(--text-muted);
            transition: transform var(--transition-smooth);
        }}

        .transcript-card.expanded .expand-icon {{
            transform: rotate(180deg);
        }}

        .card-content {{
            max-height: 0;
            overflow: hidden;
            transition: max-height var(--transition-smooth);
        }}

        .transcript-card.expanded .card-content {{
            max-height: 3000px;
        }}

        .utterances-list {{
            padding: 0 1.25rem 1.25rem;
            border-top: 1px solid var(--border-color);
        }}

        .utterance {{
            display: flex;
            gap: 1rem;
            padding: 1rem 0;
            border-bottom: 1px solid var(--bg-tertiary);
        }}

        .utterance:last-child {{
            border-bottom: none;
        }}

        .utterance-speaker {{
            flex-shrink: 0;
            width: 85px;
        }}

        .speaker-badge {{
            display: inline-flex;
            align-items: center;
            font-size: 0.6875rem;
            font-weight: 600;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            text-transform: uppercase;
            letter-spacing: 0.025em;
        }}

        .speaker-badge.agent {{
            background: var(--agent-bg);
            color: var(--agent-color);
        }}

        .speaker-badge.customer {{
            background: var(--customer-bg);
            color: var(--customer-color);
        }}

        .utterance-content {{
            flex: 1;
            min-width: 0;
        }}

        .utterance-time {{
            font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
            font-size: 0.6875rem;
            color: var(--text-muted);
            margin-bottom: 0.25rem;
        }}

        .utterance-text {{
            font-size: 0.9375rem;
            line-height: 1.7;
            color: var(--text-secondary);
            word-wrap: break-word;
        }}

        .highlight {{
            background: var(--highlight-bg);
            color: var(--highlight-text);
            padding: 0.125rem 0.25rem;
            border-radius: 3px;
            font-weight: 500;
        }}

        /* Context indicator */
        .context-indicator {{
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 0.5rem;
            color: var(--text-muted);
        }}

        .context-dots {{
            display: flex;
            gap: 0.25rem;
        }}

        .context-dots span {{
            width: 4px;
            height: 4px;
            background: var(--border-color);
            border-radius: 50%;
        }}

        /* Empty State */
        .empty-state {{
            text-align: center;
            padding: 4rem 2rem;
            color: var(--text-muted);
        }}

        .empty-state svg {{
            width: 56px;
            height: 56px;
            margin-bottom: 1.25rem;
            color: var(--border-color);
        }}

        .empty-state h3 {{
            font-size: 1.125rem;
            font-weight: 600;
            color: var(--text-secondary);
            margin-bottom: 0.5rem;
        }}

        .empty-state p {{
            font-size: 0.9375rem;
            max-width: 400px;
            margin: 0 auto;
            color: var(--text-muted);
        }}

        /* Scrollbar */
        ::-webkit-scrollbar {{
            width: 8px;
            height: 8px;
        }}

        ::-webkit-scrollbar-track {{
            background: var(--bg-primary);
        }}

        ::-webkit-scrollbar-thumb {{
            background: var(--border-color);
            border-radius: 4px;
        }}

        ::-webkit-scrollbar-thumb:hover {{
            background: var(--border-hover);
        }}

        /* Responsive */
        @media (max-width: 768px) {{
            .container {{
                padding: 1rem;
            }}

            .header h1 {{
                font-size: 1.5rem;
            }}

            .syntax-help {{
                flex-direction: column;
                gap: 0.5rem;
            }}

            .controls {{
                flex-direction: column;
                gap: 0.5rem;
            }}

            .stats-bar {{
                flex-direction: column;
                gap: 0.5rem;
                text-align: center;
            }}

            .card-meta {{
                flex-direction: column;
                align-items: flex-end;
                gap: 0.5rem;
            }}

            .utterance {{
                flex-direction: column;
                gap: 0.5rem;
            }}

            .utterance-speaker {{
                width: auto;
            }}
        }}

        /* Animations */
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(8px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .transcript-card {{
            animation: fadeIn 0.25s ease-out;
            animation-fill-mode: both;
        }}

        .transcript-card:nth-child(1) {{ animation-delay: 0ms; }}
        .transcript-card:nth-child(2) {{ animation-delay: 30ms; }}
        .transcript-card:nth-child(3) {{ animation-delay: 60ms; }}
        .transcript-card:nth-child(4) {{ animation-delay: 90ms; }}
        .transcript-card:nth-child(5) {{ animation-delay: 120ms; }}

        /* View Full Button */
        .view-full-btn {{
            display: flex;
            align-items: center;
            gap: 0.375rem;
            padding: 0.375rem 0.75rem;
            font-family: inherit;
            font-size: 0.75rem;
            font-weight: 500;
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-sm);
            color: var(--text-secondary);
            cursor: pointer;
            transition: all var(--transition-fast);
        }}

        .view-full-btn:hover {{
            background: var(--accent-primary-light);
            border-color: var(--accent-primary);
            color: var(--accent-primary);
        }}

        .view-full-btn svg {{
            width: 14px;
            height: 14px;
        }}

        /* Modal */
        .modal-overlay {{
            position: fixed;
            inset: 0;
            background: rgba(15, 23, 42, 0.6);
            backdrop-filter: blur(4px);
            z-index: 1000;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 2rem;
            opacity: 0;
            visibility: hidden;
            transition: all var(--transition-smooth);
        }}

        .modal-overlay.active {{
            opacity: 1;
            visibility: visible;
        }}

        .modal-container {{
            background: var(--bg-secondary);
            border-radius: var(--radius-lg);
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
            max-width: 900px;
            width: 100%;
            max-height: 90vh;
            display: flex;
            flex-direction: column;
            transform: scale(0.95) translateY(10px);
            transition: transform var(--transition-smooth);
        }}

        .modal-overlay.active .modal-container {{
            transform: scale(1) translateY(0);
        }}

        .modal-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            padding: 1.5rem;
            border-bottom: 1px solid var(--border-color);
        }}

        .modal-title {{
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }}

        .modal-title h2 {{
            font-size: 1.125rem;
            font-weight: 600;
            color: var(--text-primary);
            font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
        }}

        .modal-title .modal-subtitle {{
            font-size: 0.8125rem;
            color: var(--text-muted);
        }}

        .modal-close {{
            display: flex;
            align-items: center;
            justify-content: center;
            width: 36px;
            height: 36px;
            background: transparent;
            border: none;
            border-radius: var(--radius-md);
            color: var(--text-muted);
            cursor: pointer;
            transition: all var(--transition-fast);
        }}

        .modal-close:hover {{
            background: var(--bg-tertiary);
            color: var(--text-primary);
        }}

        .modal-body {{
            flex: 1;
            overflow-y: auto;
            padding: 1.5rem;
        }}

        .modal-utterance {{
            display: flex;
            gap: 1rem;
            padding: 0.875rem 0;
            border-bottom: 1px solid var(--bg-tertiary);
        }}

        .modal-utterance:last-child {{
            border-bottom: none;
        }}

        .modal-speaker {{
            flex-shrink: 0;
            width: 85px;
        }}

        .modal-content {{
            flex: 1;
            min-width: 0;
        }}

        .modal-time {{
            font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
            font-size: 0.6875rem;
            color: var(--text-muted);
            margin-bottom: 0.25rem;
        }}

        .modal-text {{
            font-size: 0.9375rem;
            line-height: 1.7;
            color: var(--text-secondary);
        }}

        /* Modal responsive */
        @media (max-width: 768px) {{
            .modal-overlay {{
                padding: 1rem;
            }}

            .modal-container {{
                max-height: 95vh;
            }}

            .modal-utterance {{
                flex-direction: column;
                gap: 0.5rem;
            }}

            .modal-speaker {{
                width: auto;
            }}
        }}

        /* Chat Assistant */
        .chat-fab {{
            position: fixed;
            bottom: 1.5rem;
            right: 1.5rem;
            width: 56px;
            height: 56px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            transition: all var(--transition-smooth);
            z-index: 900;
        }}

        .chat-fab:hover {{
            transform: scale(1.05);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
        }}

        .chat-fab svg {{
            width: 24px;
            height: 24px;
            color: white;
        }}

        .chat-fab.active {{
            transform: rotate(45deg);
        }}

        .chat-panel {{
            position: fixed;
            bottom: 5.5rem;
            right: 1.5rem;
            width: 420px;
            max-width: calc(100vw - 3rem);
            height: 520px;
            max-height: calc(100vh - 8rem);
            background: var(--bg-secondary);
            border-radius: var(--radius-lg);
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
            display: flex;
            flex-direction: column;
            z-index: 901;
            opacity: 0;
            visibility: hidden;
            transform: translateY(20px) scale(0.95);
            transition: all var(--transition-smooth);
        }}

        .chat-panel.active {{
            opacity: 1;
            visibility: visible;
            transform: translateY(0) scale(1);
        }}

        .chat-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 1rem 1.25rem;
            border-bottom: 1px solid var(--border-color);
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: var(--radius-lg) var(--radius-lg) 0 0;
        }}

        .chat-header-title {{
            display: flex;
            align-items: center;
            gap: 0.625rem;
        }}

        .chat-header-title svg {{
            width: 20px;
            height: 20px;
            color: white;
        }}

        .chat-header-title span {{
            font-size: 0.9375rem;
            font-weight: 600;
            color: white;
        }}

        .chat-status {{
            font-size: 0.6875rem;
            padding: 0.25rem 0.5rem;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 20px;
            color: white;
        }}

        .chat-messages {{
            flex: 1;
            overflow-y: auto;
            padding: 1rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }}

        .chat-message {{
            max-width: 85%;
            padding: 0.75rem 1rem;
            border-radius: var(--radius-md);
            font-size: 0.875rem;
            line-height: 1.6;
        }}

        .chat-message.user {{
            align-self: flex-end;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-bottom-right-radius: 4px;
        }}

        .chat-message.assistant {{
            align-self: flex-start;
            background: var(--bg-tertiary);
            color: var(--text-primary);
            border-bottom-left-radius: 4px;
        }}

        .chat-message.assistant.thinking {{
            color: var(--text-muted);
            font-style: italic;
        }}

        .chat-message.assistant .meta {{
            margin-top: 0.5rem;
            padding-top: 0.5rem;
            border-top: 1px solid var(--border-color);
            font-size: 0.75rem;
            color: var(--text-muted);
        }}

        .chat-welcome {{
            text-align: center;
            padding: 2rem 1rem;
            color: var(--text-muted);
        }}

        .chat-welcome svg {{
            width: 48px;
            height: 48px;
            margin-bottom: 1rem;
            color: var(--border-color);
        }}

        .chat-welcome h4 {{
            font-size: 1rem;
            font-weight: 600;
            color: var(--text-secondary);
            margin-bottom: 0.5rem;
        }}

        .chat-welcome p {{
            font-size: 0.8125rem;
            margin-bottom: 1rem;
        }}

        .chat-suggestions {{
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }}

        .chat-suggestion {{
            padding: 0.5rem 0.75rem;
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            font-size: 0.75rem;
            color: var(--text-secondary);
            cursor: pointer;
            transition: all var(--transition-fast);
            text-align: left;
        }}

        .chat-suggestion:hover {{
            background: var(--accent-primary-light);
            border-color: var(--accent-primary);
            color: var(--accent-primary);
        }}

        .chat-input-area {{
            padding: 1rem;
            border-top: 1px solid var(--border-color);
        }}

        .chat-input-wrapper {{
            display: flex;
            gap: 0.5rem;
        }}

        .chat-input {{
            flex: 1;
            padding: 0.75rem 1rem;
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            font-family: inherit;
            font-size: 0.875rem;
            background: var(--bg-primary);
            color: var(--text-primary);
            outline: none;
            transition: all var(--transition-fast);
        }}

        .chat-input:focus {{
            border-color: var(--accent-primary);
            box-shadow: 0 0 0 3px var(--accent-primary-light);
        }}

        .chat-input::placeholder {{
            color: var(--text-muted);
        }}

        .chat-send {{
            width: 42px;
            height: 42px;
            border: none;
            border-radius: var(--radius-md);
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all var(--transition-fast);
        }}

        .chat-send:hover {{
            transform: scale(1.05);
        }}

        .chat-send:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }}

        .chat-send svg {{
            width: 18px;
            height: 18px;
        }}

        .chat-error {{
            background: #fef2f2;
            border: 1px solid #fecaca;
            color: #dc2626;
            padding: 0.75rem 1rem;
            border-radius: var(--radius-md);
            font-size: 0.8125rem;
            margin: 0.5rem 1rem;
        }}

        /* Structured response styles */
        .chat-message.assistant .findings {{
            margin-top: 0.75rem;
        }}

        .chat-message.assistant .finding {{
            margin-bottom: 0.75rem;
            padding: 0.5rem;
            background: rgba(0,0,0,0.03);
            border-radius: 6px;
        }}

        .chat-message.assistant .finding-title {{
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 0.25rem;
        }}

        .chat-message.assistant .finding-desc {{
            font-size: 0.8125rem;
            line-height: 1.5;
        }}

        .chat-message.assistant .finding-refs {{
            font-size: 0.6875rem;
            color: var(--text-muted);
            margin-top: 0.375rem;
            font-family: 'SF Mono', Monaco, monospace;
        }}

        .chat-message.assistant .recommendations {{
            margin-top: 0.75rem;
            padding-top: 0.75rem;
            border-top: 1px solid var(--border-color);
        }}

        .chat-message.assistant .rec-title {{
            font-weight: 600;
            color: var(--accent-primary);
            margin-bottom: 0.375rem;
        }}

        .chat-message.assistant .rec-item {{
            font-size: 0.8125rem;
            margin-bottom: 0.25rem;
            padding-left: 0.25rem;
        }}

        /* Better response formatting */
        .chat-message.assistant .response-content {{
            font-size: 0.875rem;
            line-height: 1.7;
        }}

        .chat-message.assistant .response-content p {{
            margin-bottom: 0.75rem;
        }}

        .chat-message.assistant .response-content p:last-child {{
            margin-bottom: 0;
        }}

        .chat-message.assistant .response-content strong {{
            color: var(--text-primary);
            font-weight: 600;
        }}

        .chat-message.assistant .response-content ul,
        .chat-message.assistant .response-content ol {{
            margin: 0.75rem 0;
            padding-left: 1.25rem;
        }}

        .chat-message.assistant .response-content li {{
            margin-bottom: 0.5rem;
            padding-left: 0.25rem;
        }}

        .chat-message.assistant .response-content li::marker {{
            color: var(--accent-primary);
        }}

        .chat-message.assistant .step-item {{
            display: flex;
            gap: 0.75rem;
            margin-bottom: 0.75rem;
            padding: 0.5rem 0;
        }}

        .chat-message.assistant .step-number {{
            flex-shrink: 0;
            width: 24px;
            height: 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.75rem;
            font-weight: 600;
        }}

        .chat-message.assistant .step-content {{
            flex: 1;
            padding-top: 0.125rem;
        }}

        .chat-message.assistant .transcript-ref {{
            display: inline;
            padding: 0.125rem 0.375rem;
            background: var(--accent-primary-light);
            color: var(--accent-primary);
            border-radius: 3px;
            font-size: 0.75rem;
            font-weight: 500;
            font-family: 'SF Mono', Monaco, monospace;
        }}

        /* Typing indicator */
        .typing-indicator {{
            display: flex;
            gap: 4px;
            padding: 0.75rem 1rem;
        }}

        .typing-indicator span {{
            width: 8px;
            height: 8px;
            background: var(--text-muted);
            border-radius: 50%;
            animation: typing 1.4s infinite ease-in-out;
        }}

        .typing-indicator span:nth-child(1) {{ animation-delay: 0ms; }}
        .typing-indicator span:nth-child(2) {{ animation-delay: 200ms; }}
        .typing-indicator span:nth-child(3) {{ animation-delay: 400ms; }}

        @keyframes typing {{
            0%, 60%, 100% {{ transform: translateY(0); opacity: 0.4; }}
            30% {{ transform: translateY(-4px); opacity: 1; }}
        }}

        /* Chat responsive */
        @media (max-width: 480px) {{
            .chat-panel {{
                bottom: 0;
                right: 0;
                width: 100%;
                max-width: 100%;
                height: 100%;
                max-height: 100%;
                border-radius: 0;
            }}

            .chat-fab {{
                bottom: 1rem;
                right: 1rem;
            }}
        }}

        /* Sidebar Styles */
        .app-layout {{
            display: flex;
            min-height: 100vh;
        }}

        .sidebar {{
            width: 280px;
            background: var(--bg-secondary);
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            transition: all var(--transition-smooth);
            flex-shrink: 0;
        }}

        .sidebar.collapsed {{
            width: 0;
            overflow: hidden;
            border-right: none;
        }}

        .sidebar-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 1rem 1.25rem;
            border-bottom: 1px solid var(--border-color);
        }}

        .sidebar-brand {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .sidebar-brand-icon {{
            display: flex;
            align-items: center;
            justify-content: center;
            width: 28px;
            height: 28px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 8px;
            color: white;
        }}

        .sidebar-brand-icon svg {{
            width: 14px;
            height: 14px;
        }}

        .sidebar-brand-text {{
            font-weight: 600;
            font-size: 0.875rem;
            color: var(--text-primary);
            letter-spacing: -0.01em;
        }}

        .sidebar-toggle {{
            display: flex;
            align-items: center;
            justify-content: center;
            width: 32px;
            height: 32px;
            background: transparent;
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            color: var(--text-muted);
            cursor: pointer;
            transition: all var(--transition-fast);
        }}

        .sidebar-toggle:hover {{
            background: var(--bg-tertiary);
            color: var(--text-primary);
            border-color: var(--border-hover);
        }}

        .sidebar-content {{
            flex: 1;
            padding: 1.25rem;
            overflow-y: auto;
        }}

        .filter-section {{
            margin-bottom: 1.25rem;
        }}

        .filter-section:last-child {{
            margin-bottom: 0;
        }}

        .filter-label {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.6875rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--text-muted);
            margin-bottom: 0.375rem;
            padding-left: 0.125rem;
        }}

        .filter-label svg {{
            width: 12px;
            height: 12px;
            opacity: 0.6;
        }}

        .filter-dropdown {{
            width: 100%;
            padding: 0.5rem 0.75rem;
            font-family: inherit;
            font-size: 0.8125rem;
            font-weight: 500;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            color: var(--text-primary);
            cursor: pointer;
            appearance: none;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2.5'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: right 0.625rem center;
            transition: all var(--transition-fast);
            box-shadow: var(--shadow-sm);
        }}

        .filter-dropdown:hover {{
            border-color: var(--border-hover);
        }}

        .filter-dropdown:focus {{
            outline: none;
            border-color: var(--accent-primary);
            box-shadow: 0 0 0 3px var(--accent-primary-light);
        }}

        .sidebar-footer {{
            padding: 0.875rem 1.25rem;
            border-top: 1px solid var(--border-color);
            background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        }}

        .sidebar-footer-info {{
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        .sidebar-footer-label {{
            font-size: 0.6875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            font-weight: 500;
        }}

        .sidebar-footer-value {{
            font-size: 0.75rem;
            font-weight: 600;
            color: #667eea;
            background: rgba(102, 126, 234, 0.1);
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
        }}

        .main-content {{
            flex: 1;
            min-width: 0;
            display: flex;
            flex-direction: column;
        }}

        .sidebar-toggle-float {{
            position: fixed;
            top: 1rem;
            left: 1rem;
            z-index: 200;
            display: none;
            align-items: center;
            justify-content: center;
            width: 40px;
            height: 40px;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            color: var(--text-secondary);
            cursor: pointer;
            box-shadow: var(--shadow-md);
            transition: all var(--transition-fast);
        }}

        .sidebar-toggle-float:hover {{
            background: var(--bg-tertiary);
            color: var(--text-primary);
        }}

        .sidebar.collapsed ~ .main-content .sidebar-toggle-float {{
            display: flex;
        }}

        /* Sidebar responsive */
        @media (max-width: 900px) {{
            .sidebar {{
                position: fixed;
                left: 0;
                top: 0;
                height: 100%;
                z-index: 300;
                box-shadow: var(--shadow-lg);
            }}

            .sidebar.collapsed {{
                transform: translateX(-100%);
                width: 280px;
            }}

            .sidebar-overlay {{
                display: none;
                position: fixed;
                inset: 0;
                background: rgba(0, 0, 0, 0.3);
                z-index: 299;
            }}

            .sidebar:not(.collapsed) ~ .sidebar-overlay {{
                display: block;
            }}

            .sidebar-toggle-float {{
                display: flex;
            }}

            .sidebar.collapsed ~ .main-content .sidebar-toggle-float {{
                display: flex;
            }}
        }}
    </style>
</head>
<body>
    <div class="app-layout">
        <!-- Sidebar -->
        <aside class="sidebar" id="sidebar">
            <div class="sidebar-header">
                <div class="sidebar-brand">
                    <div class="sidebar-brand-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                            <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon>
                        </svg>
                    </div>
                    <span class="sidebar-brand-text">Filters</span>
                </div>
                <button class="sidebar-toggle" onclick="toggleSidebar()" title="Collapse sidebar">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M15 18l-6-6 6-6"></path>
                    </svg>
                </button>
            </div>
            <div class="sidebar-content">
                <div class="filter-section">
                    <label class="filter-label">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M3 21h18M3 10h18M3 3h18M9 21v-6M9 10V3M15 21v-6M15 10V3"></path>
                        </svg>
                        Company
                    </label>
                    <select class="filter-dropdown" id="companyFilter">
                        <option value="TP" selected>TP</option>
                    </select>
                </div>
                <div class="filter-section">
                    <label class="filter-label">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                            <circle cx="9" cy="7" r="4"></circle>
                            <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"></path>
                        </svg>
                        Organization
                    </label>
                    <select class="filter-dropdown" id="organizationFilter">
                        <option value="IT HELPDESK" selected>IT HELPDESK</option>
                    </select>
                </div>
                <div class="filter-section">
                    <label class="filter-label">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                            <polyline points="22 4 12 14.01 9 11.01"></polyline>
                        </svg>
                        Program
                    </label>
                    <select class="filter-dropdown" id="programFilter">
                        <option value="CTSS HA" selected>CTSS HA</option>
                    </select>
                </div>
                <div class="filter-section">
                    <label class="filter-label">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                            <line x1="16" y1="2" x2="16" y2="6"></line>
                            <line x1="8" y1="2" x2="8" y2="6"></line>
                            <line x1="3" y1="10" x2="21" y2="10"></line>
                        </svg>
                        Date
                    </label>
                    <select class="filter-dropdown" id="dateFilter">
                        <option value="2025-12-14" selected>2025-12-14</option>
                    </select>
                </div>
            </div>
            <div class="sidebar-footer">
                <div class="sidebar-footer-info">
                    <span class="sidebar-footer-label">Total Transcripts</span>
                    <span class="sidebar-footer-value">{len(transcripts)} records</span>
                </div>
            </div>
        </aside>
        <div class="sidebar-overlay" onclick="toggleSidebar()"></div>

        <!-- Main Content -->
        <main class="main-content">
            <button class="sidebar-toggle-float" onclick="toggleSidebar()" title="Show filters">
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M3 6h18M3 12h18M3 18h18"></path>
                </svg>
            </button>
            <div class="container">
                <header class="header">
                    <div class="header-content">
                        <h1>Transcript Search</h1>
                        <div class="count-badge">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                <polyline points="14 2 14 8 20 8"></polyline>
                                <line x1="16" y1="13" x2="8" y2="13"></line>
                                <line x1="16" y1="17" x2="8" y2="17"></line>
                            </svg>
                            <span>{len(transcripts)}</span> transcripts
                        </div>
                    </div>
                </header>

                <div class="search-container">
                    <div class="search-box">
                        <div class="search-input-wrapper">
                            <svg class="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <circle cx="11" cy="11" r="8"></circle>
                                <path d="m21 21-4.35-4.35"></path>
                            </svg>
                            <input type="text" id="searchInput" placeholder="Search transcripts..." autocomplete="off" spellcheck="false">
                        </div>

                        <div class="syntax-help">
                            <div class="syntax-item">
                                <code>"exact phrase"</code>
                                <span>phrase match</span>
                            </div>
                            <div class="syntax-item">
                                <code>word1;word2</code>
                                <span>must contain both</span>
                            </div>
                        </div>

                        <div class="controls">
                            <div class="control-group">
                                <button class="toggle-btn" id="caseToggle" title="Case sensitive search">
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M3 15h6"></path>
                                        <path d="M6 9v12"></path>
                                        <path d="M13 9h8"></path>
                                        <path d="M17 9v12"></path>
                                    </svg>
                                    Case Sensitive
                                </button>
                            </div>
                            <div class="control-group">
                                <select class="filter-select" id="speakerFilter">
                                    <option value="all">All Speakers</option>
                                    <option value="agent">Agent Only</option>
                                    <option value="customer">Customer Only</option>
                                </select>
                            </div>
                        </div>

                        <div class="stats-bar">
                            <div class="stat-item">
                                <span>Transcripts:</span>
                                <span class="stat-value" id="resultCount">-</span>
                            </div>
                            <div class="stat-item">
                                <span>Matches:</span>
                                <span class="stat-value" id="matchCount">-</span>
                            </div>
                            <div class="stat-item search-time">
                                <span>Time:</span>
                                <span class="stat-value" id="searchTime">-</span>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="results-container" id="results">
                    <div class="empty-state">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <circle cx="11" cy="11" r="8"></circle>
                            <path d="m21 21-4.35-4.35"></path>
                        </svg>
                        <h3>Start typing to search</h3>
                        <p>Search through {len(transcripts)} transcripts. Use quotes for exact phrases and semicolons for multiple terms.</p>
                    </div>
                </div>
            </div>
        </main>
    </div>

    <!-- Modal for full transcript view -->
    <div class="modal-overlay" id="transcriptModal" onclick="closeModalOnBackdrop(event)">
        <div class="modal-container">
            <div class="modal-header">
                <div class="modal-title">
                    <h2 id="modalTitle">Transcript</h2>
                    <span class="modal-subtitle" id="modalSubtitle"></span>
                </div>
                <button class="modal-close" onclick="closeModal()" title="Close (Esc)">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M18 6L6 18M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
            <div class="modal-body" id="modalBody"></div>
        </div>
    </div>

    <!-- Chat Assistant -->
    <button class="chat-fab" id="chatFab" onclick="toggleChat()" title="Ask AI Assistant">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
    </button>

    <div class="chat-panel" id="chatPanel">
        <div class="chat-header">
            <div class="chat-header-title">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8z"></path>
                    <path d="M12 6v6l4 2"></path>
                </svg>
                <span>Transcript Assistant</span>
            </div>
            <span class="chat-status" id="chatStatus">{len(transcripts)} transcripts</span>
        </div>
        <div class="chat-messages" id="chatMessages">
            <div class="chat-welcome">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
                </svg>
                <h4>Ask me anything</h4>
                <p>I can analyze all {len(transcripts)} transcripts to answer your questions.</p>
                <div class="chat-suggestions">
                    <button class="chat-suggestion" onclick="askSuggestion('What are the main issues faced by customers?')">
                        What are the main issues faced by customers?
                    </button>
                    <button class="chat-suggestion" onclick="askSuggestion('What are the common pain points?')">
                        What are the common pain points?
                    </button>
                    <button class="chat-suggestion" onclick="askSuggestion('How do agents typically handle password resets?')">
                        How do agents typically handle password resets?
                    </button>
                </div>
            </div>
        </div>
        <div class="chat-input-area">
            <div class="chat-input-wrapper">
                <input type="text" class="chat-input" id="chatInput" placeholder="Ask about the transcripts..." onkeydown="handleChatKeydown(event)">
                <button class="chat-send" id="chatSend" onclick="sendChatMessage()">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"></path>
                    </svg>
                </button>
            </div>
        </div>
    </div>

    <script>
        // Embedded transcript data
        const TRANSCRIPTS = {transcripts_json};

        // State
        let caseSensitive = false;
        let speakerFilter = 'all';
        let debounceTimer = null;

        // Sidebar toggle
        function toggleSidebar() {{
            const sidebar = document.getElementById('sidebar');
            sidebar.classList.toggle('collapsed');
        }}

        // DOM Elements
        const searchInput = document.getElementById('searchInput');
        const caseToggle = document.getElementById('caseToggle');
        const speakerFilterEl = document.getElementById('speakerFilter');
        const resultsContainer = document.getElementById('results');
        const resultCountEl = document.getElementById('resultCount');
        const matchCountEl = document.getElementById('matchCount');
        const searchTimeEl = document.getElementById('searchTime');

        // Initialize
        document.addEventListener('DOMContentLoaded', () => {{
            searchInput.focus();

            document.addEventListener('keydown', (e) => {{
                if (e.key === '/' && document.activeElement !== searchInput) {{
                    e.preventDefault();
                    searchInput.focus();
                }}
                if (e.key === 'Escape') {{
                    searchInput.value = '';
                    searchInput.blur();
                    showEmptyState();
                }}
            }});

            searchInput.addEventListener('input', () => {{
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(performSearch, 50);
            }});

            caseToggle.addEventListener('click', () => {{
                caseSensitive = !caseSensitive;
                caseToggle.classList.toggle('active', caseSensitive);
                performSearch();
            }});

            speakerFilterEl.addEventListener('change', (e) => {{
                speakerFilter = e.target.value;
                performSearch();
            }});
        }});

        /**
         * Parse the search query into terms
         * - Quoted strings become exact phrase matches
         * - Semicolons separate AND terms
         */
        function parseSearchQuery(query) {{
            const terms = [];
            let remaining = query;
            
            // Extract quoted phrases first
            const quoteRegex = /"([^"]+)"/g;
            let match;
            while ((match = quoteRegex.exec(query)) !== null) {{
                terms.push({{ type: 'phrase', value: match[1] }});
                remaining = remaining.replace(match[0], '');
            }}
            
            // Split remaining by semicolons for AND terms
            const parts = remaining.split(';').map(s => s.trim()).filter(s => s.length > 0);
            for (const part of parts) {{
                if (part.length > 0) {{
                    terms.push({{ type: 'keyword', value: part }});
                }}
            }}
            
            return terms;
        }}

        /**
         * Check if text matches all search terms (AND logic)
         */
        function matchesAllTerms(text, terms, isCaseSensitive) {{
            const searchText = isCaseSensitive ? text : text.toLowerCase();
            
            for (const term of terms) {{
                const searchValue = isCaseSensitive ? term.value : term.value.toLowerCase();
                if (!searchText.includes(searchValue)) {{
                    return false;
                }}
            }}
            return true;
        }}

        /**
         * Create a regex that matches any of the terms for highlighting
         */
        function createHighlightRegex(terms, isCaseSensitive) {{
            const patterns = terms.map(term => {{
                return term.value.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&');
            }});
            const flags = isCaseSensitive ? 'g' : 'gi';
            return new RegExp('(' + patterns.join('|') + ')', flags);
        }}

        /**
         * Count total matches across all terms
         */
        function countMatches(text, terms, isCaseSensitive) {{
            let count = 0;
            const searchText = isCaseSensitive ? text : text.toLowerCase();
            
            for (const term of terms) {{
                const searchValue = isCaseSensitive ? term.value : term.value.toLowerCase();
                let pos = 0;
                while ((pos = searchText.indexOf(searchValue, pos)) !== -1) {{
                    count++;
                    pos += searchValue.length;
                }}
            }}
            return count;
        }}

        function performSearch() {{
            const query = searchInput.value.trim();
            
            if (!query) {{
                showEmptyState();
                return;
            }}

            const startTime = performance.now();
            
            // Parse the query
            const terms = parseSearchQuery(query);
            
            if (terms.length === 0) {{
                showEmptyState();
                return;
            }}

            const results = [];
            let totalMatches = 0;

            for (const transcript of TRANSCRIPTS) {{
                const matchingUtterances = [];
                let transcriptMatches = 0;

                for (let i = 0; i < transcript.utterances.length; i++) {{
                    const utterance = transcript.utterances[i];
                    
                    // Apply speaker filter
                    if (speakerFilter !== 'all' && utterance.speaker_type !== speakerFilter) {{
                        continue;
                    }}

                    // Check if utterance matches ALL terms
                    if (matchesAllTerms(utterance.text, terms, caseSensitive)) {{
                        const matchCount = countMatches(utterance.text, terms, caseSensitive);
                        transcriptMatches += matchCount;
                        matchingUtterances.push({{
                            ...utterance,
                            index: i,
                            matchCount: matchCount
                        }});
                    }}
                }}

                if (matchingUtterances.length > 0) {{
                    results.push({{
                        transcript,
                        matchingUtterances,
                        totalMatches: transcriptMatches
                    }});
                    totalMatches += transcriptMatches;
                }}
            }}

            const endTime = performance.now();
            const searchTime = (endTime - startTime).toFixed(1);

            resultCountEl.textContent = results.length;
            matchCountEl.textContent = totalMatches;
            searchTimeEl.textContent = searchTime + 'ms';

            renderResults(results, terms);
        }}

        function renderResults(results, terms) {{
            if (results.length === 0) {{
                resultsContainer.innerHTML = `
                    <div class="empty-state">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <circle cx="12" cy="12" r="10"></circle>
                            <path d="M8 15s1.5-2 4-2 4 2 4 2"></path>
                            <line x1="9" y1="9" x2="9.01" y2="9"></line>
                            <line x1="15" y1="9" x2="15.01" y2="9"></line>
                        </svg>
                        <h3>No matches found</h3>
                        <p>Try different keywords or adjust your filters.</p>
                    </div>
                `;
                return;
            }}

            const highlightRegex = createHighlightRegex(terms, caseSensitive);
            let html = '';

            for (const result of results) {{
                const {{ transcript, matchingUtterances, totalMatches }} = result;
                
                html += `
                    <div class="transcript-card" data-id="${{transcript.id}}">
                        <div class="card-header" onclick="toggleCard(this)">
                            <div class="card-title">
                                <div class="card-icon">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                                    </svg>
                                </div>
                                <span class="card-name">${{transcript.name}}</span>
                            </div>
                            <div class="card-meta">
                                <button class="view-full-btn" onclick="event.stopPropagation(); openTranscriptModal('${{transcript.id}}')">
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                        <polyline points="14 2 14 8 20 8"></polyline>
                                        <line x1="16" y1="13" x2="8" y2="13"></line>
                                        <line x1="16" y1="17" x2="8" y2="17"></line>
                                        <polyline points="10 9 9 9 8 9"></polyline>
                                    </svg>
                                    View Full
                                </button>
                                <span class="match-count">${{totalMatches}} match${{totalMatches !== 1 ? 'es' : ''}}</span>
                                <svg class="expand-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <polyline points="6 9 12 15 18 9"></polyline>
                                </svg>
                            </div>
                        </div>
                        <div class="card-content">
                            <div class="utterances-list">
                                ${{renderUtterances(transcript, matchingUtterances, highlightRegex)}}
                            </div>
                        </div>
                    </div>
                `;
            }}

            resultsContainer.innerHTML = html;
        }}

        function renderUtterances(transcript, matchingUtterances, highlightRegex) {{
            let html = '';
            let prevIndex = -2;

            for (const utterance of matchingUtterances) {{
                if (utterance.index > prevIndex + 1 && prevIndex >= 0) {{
                    html += `
                        <div class="context-indicator">
                            <div class="context-dots">
                                <span></span><span></span><span></span>
                            </div>
                        </div>
                    `;
                }}

                const highlightedText = utterance.text.replace(highlightRegex, '<mark class="highlight">$1</mark>');

                html += `
                    <div class="utterance">
                        <div class="utterance-speaker">
                            <span class="speaker-badge ${{utterance.speaker_type}}">${{utterance.speaker_type === 'agent' ? 'Agent' : 'Customer'}}</span>
                        </div>
                        <div class="utterance-content">
                            <div class="utterance-time">${{utterance.start}} - ${{utterance.end}}</div>
                            <div class="utterance-text">${{highlightedText}}</div>
                        </div>
                    </div>
                `;

                prevIndex = utterance.index;
            }}

            return html;
        }}

        function toggleCard(header) {{
            const card = header.closest('.transcript-card');
            card.classList.toggle('expanded');
        }}

        function showEmptyState() {{
            resultCountEl.textContent = '-';
            matchCountEl.textContent = '-';
            searchTimeEl.textContent = '-';
            
            resultsContainer.innerHTML = `
                <div class="empty-state">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <circle cx="11" cy="11" r="8"></circle>
                        <path d="m21 21-4.35-4.35"></path>
                    </svg>
                    <h3>Start typing to search</h3>
                    <p>Search through ${{TRANSCRIPTS.length}} transcripts. Use quotes for exact phrases and semicolons for multiple terms.</p>
                </div>
            `;
        }}

        // Modal functionality
        const modalOverlay = document.getElementById('transcriptModal');
        const modalTitle = document.getElementById('modalTitle');
        const modalSubtitle = document.getElementById('modalSubtitle');
        const modalBody = document.getElementById('modalBody');

        function highlightTextInModal(text, searchTerms) {{
            if (!searchTerms || searchTerms.length === 0) return text;
            
            let result = text;
            for (const term of searchTerms) {{
                if (!term) continue;
                // Escape special regex characters
                const escaped = term.replace(/[.*+?^${{}}()|[\]\\\\]/g, '\\\\$&');
                const regex = new RegExp(`(${{escaped}})`, caseSensitive ? 'g' : 'gi');
                result = result.replace(regex, '<mark class="highlight">$1</mark>');
            }}
            return result;
        }}

        function openTranscriptModal(transcriptId) {{
            const transcript = TRANSCRIPTS.find(t => t.id === transcriptId);
            if (!transcript) return;

            // Get current search terms for highlighting
            const currentQuery = searchInput.value.trim();
            let searchTerms = [];
            
            if (currentQuery) {{
                // Parse search terms (same logic as search)
                const phraseMatches = currentQuery.match(/"[^"]+"/g) || [];
                const phrases = phraseMatches.map(p => p.slice(1, -1));
                
                let remaining = currentQuery;
                phraseMatches.forEach(p => {{ remaining = remaining.replace(p, ''); }});
                
                const parts = remaining.split(';').map(p => p.trim()).filter(p => p);
                searchTerms = [...phrases, ...parts];
            }}

            modalTitle.textContent = transcript.name;
            const matchInfo = searchTerms.length > 0 ? ` • Searching: "${{searchTerms.join('", "')}}"` : '';
            modalSubtitle.textContent = `${{transcript.utterances.length}} utterances${{matchInfo}}`;

            let html = '';
            for (const utterance of transcript.utterances) {{
                const highlightedText = highlightTextInModal(utterance.text, searchTerms);
                html += `
                    <div class="modal-utterance">
                        <div class="modal-speaker">
                            <span class="speaker-badge ${{utterance.speaker_type}}">${{utterance.speaker_type === 'agent' ? 'Agent' : 'Customer'}}</span>
                        </div>
                        <div class="modal-content">
                            <div class="modal-time">${{utterance.start}} - ${{utterance.end}}</div>
                            <div class="modal-text">${{highlightedText}}</div>
                        </div>
                    </div>
                `;
            }}

            modalBody.innerHTML = html;
            modalOverlay.classList.add('active');
            document.body.style.overflow = 'hidden';
        }}

        function closeModal() {{
            modalOverlay.classList.remove('active');
            document.body.style.overflow = '';
        }}

        function closeModalOnBackdrop(event) {{
            if (event.target === modalOverlay) {{
                closeModal();
            }}
        }}

        // Close modal on Escape key
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape' && modalOverlay.classList.contains('active')) {{
                closeModal();
            }}
        }});

        // Chat Assistant functionality
        const chatFab = document.getElementById('chatFab');
        const chatPanel = document.getElementById('chatPanel');
        const chatMessages = document.getElementById('chatMessages');
        const chatInput = document.getElementById('chatInput');
        const chatSend = document.getElementById('chatSend');
        const chatStatus = document.getElementById('chatStatus');

        let chatOpen = false;
        let isAsking = false;

        function toggleChat() {{
            chatOpen = !chatOpen;
            chatFab.classList.toggle('active', chatOpen);
            chatPanel.classList.toggle('active', chatOpen);
            if (chatOpen) {{
                chatInput.focus();
            }}
        }}

        function handleChatKeydown(event) {{
            if (event.key === 'Enter' && !event.shiftKey) {{
                event.preventDefault();
                sendChatMessage();
            }}
        }}

        function askSuggestion(question) {{
            chatInput.value = question;
            sendChatMessage();
        }}

        function addMessage(content, type, meta = null) {{
            // Remove welcome message if present
            const welcome = chatMessages.querySelector('.chat-welcome');
            if (welcome) welcome.remove();

            const msg = document.createElement('div');
            msg.className = `chat-message ${{type}}`;
            
            let html = content;
            if (meta) {{
                html += `<div class="meta">${{meta}}</div>`;
            }}
            msg.innerHTML = html;
            
            chatMessages.appendChild(msg);
            chatMessages.scrollTop = chatMessages.scrollHeight;
            
            return msg;
        }}

        function addTypingIndicator() {{
            const typing = document.createElement('div');
            typing.className = 'chat-message assistant thinking';
            typing.id = 'typingIndicator';
            typing.innerHTML = `
                <div class="typing-indicator">
                    <span></span><span></span><span></span>
                </div>
                Analyzing transcripts...
            `;
            chatMessages.appendChild(typing);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }}

        function removeTypingIndicator() {{
            const typing = document.getElementById('typingIndicator');
            if (typing) typing.remove();
        }}

        function showError(message) {{
            const error = document.createElement('div');
            error.className = 'chat-error';
            error.textContent = message;
            chatMessages.appendChild(error);
            chatMessages.scrollTop = chatMessages.scrollHeight;
            
            setTimeout(() => error.remove(), 5000);
        }}

        async function sendChatMessage() {{
            const question = chatInput.value.trim();
            if (!question || isAsking) return;

            isAsking = true;
            chatSend.disabled = true;
            chatInput.value = '';

            // Add user message
            addMessage(question, 'user');
            
            // Show typing indicator
            addTypingIndicator();
            chatStatus.textContent = 'Thinking...';

            try {{
                const response = await fetch('/api/ask', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                    }},
                    body: JSON.stringify({{ question }}),
                }});

                removeTypingIndicator();

                if (!response.ok) {{
                    throw new Error(`Server error: ${{response.status}}`);
                }}

                const data = await response.json();
                
                if (data.error) {{
                    showError(data.error);
                }} else {{
                    const meta = `Analyzed ${{data.transcripts_analyzed}} of ${{data.total_transcripts}} transcripts`;
                    addMessage(data.answer, 'assistant', meta);
                }}

                chatStatus.textContent = `${{TRANSCRIPTS.length}} transcripts`;

            }} catch (error) {{
                removeTypingIndicator();
                
                if (error.message.includes('Failed to fetch')) {{
                    showError('Cannot connect to server. Make sure assistant_server.py is running.');
                }} else {{
                    showError(`Error: ${{error.message}}`);
                }}
                
                chatStatus.textContent = `${{TRANSCRIPTS.length}} transcripts`;
            }}

            isAsking = false;
            chatSend.disabled = false;
            chatInput.focus();
        }}
    </script>
</body>
</html>'''

    return html

def main():
    """Main entry point."""
    print("=" * 60)
    print("Transcript Search Tool Builder")
    print("=" * 60)
    
    # Load transcripts
    print("\nLoading transcripts...")
    transcripts = load_all_transcripts()
    
    if not transcripts:
        print("No transcripts found. Exiting.")
        return
    
    # Calculate stats
    total_utterances = sum(t['utterance_count'] for t in transcripts)
    print(f"Loaded {len(transcripts)} transcripts with {total_utterances} total utterances")
    
    # Generate HTML
    print("\nGenerating search.html...")
    html_content = generate_html(transcripts)
    
    # Write output
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    file_size = os.path.getsize(OUTPUT_FILE) / 1024
    print(f"Generated: {OUTPUT_FILE}")
    print(f"File size: {file_size:.1f} KB")
    
    print("\n" + "=" * 60)
    print("Done! Double-click search.html to start searching.")
    print("=" * 60)

if __name__ == "__main__":
    main()
