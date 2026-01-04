#!/usr/bin/env python3
"""
Transcribe Spanish audio files from Duolinguo/radios directory.
Uses OpenAI Whisper for high-quality Spanish transcription.
Includes grammar correction and story splitting.
"""

import os
import sys
import re
from pathlib import Path
import whisper
import language_tool_python

def proofread_spanish(text, tool):
    """
    Proofread Spanish text using LanguageTool.
    """
    if tool is None:
        return text
    
    try:
        matches = tool.check(text)
        corrected_text = text
        
        # Apply corrections in reverse order to maintain correct positions
        for match in reversed(matches):
            if match.replacements:
                start = match.offset
                end = match.offset + match.errorLength
                corrected_text = corrected_text[:start] + match.replacements[0] + corrected_text[end:]
        
        return corrected_text
    except Exception as e:
        print(f"   ⚠️  Warning: Grammar check failed: {str(e)}")
        return text

def detect_english_hints(text):
    """
    Detect English hint words that might indicate section/radio numbers.
    Returns list of tuples: (position, hint_text)
    """
    hints = []
    
    # Patterns for English hints: section, radio, part, number, etc.
    patterns = [
        r'\b(section|Section|SECTION)\s*(\d+)',
        r'\b(radio|Radio|RADIO)\s*(\d+)',
        r'\b(part|Part|PART)\s*(\d+)',
        r'\b(story|Story|STORY)\s*(\d+)',
        r'\b(number|Number|NUMBER)\s*(\d+)',
        r'\b(segment|Segment|SEGMENT)\s*(\d+)',
    ]
    
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            hints.append((match.start(), match.group(0)))
    
    # Also look for standalone numbers that might be section markers
    # (numbers at the start of lines or after clear breaks)
    number_pattern = r'(?:^|\n\n)\s*(\d+)\s*(?:\.|:|\n)'
    for match in re.finditer(number_pattern, text):
        hints.append((match.start(), match.group(1)))
    
    return sorted(hints, key=lambda x: x[0])

def split_by_english_hints(text, hints):
    """
    Split text based on English hint words.
    Each hint marks the start of a new story section.
    """
    if not hints:
        return []
    
    stories = []
    
    # If first hint is not at the start, include text before it as first story
    if hints[0][0] > 0:
        first_story = text[0:hints[0][0]].strip()
        if first_story:
            stories.append(first_story)
    
    # Split at each hint position
    for i in range(len(hints)):
        start_pos = hints[i][0]
        # Find the end position (next hint or end of text)
        if i + 1 < len(hints):
            end_pos = hints[i + 1][0]
        else:
            end_pos = len(text)
        
        story_text = text[start_pos:end_pos].strip()
        if story_text:
            stories.append(story_text)
    
    return stories if stories else [text]

def split_by_content(text):
    """
    Split transcript into multiple stories based on content markers.
    Looks for program introductions and clear breaks.
    """
    stories = []
    
    # Common Spanish radio program introduction patterns
    intro_patterns = [
        r'Hola, te doy la bienvenida a',
        r'¡Pu-pu-pu! Hola, te doy la bienvenida a',
        r'Te doy la bienvenida a',
        r'¿Te doy la bienvenida a',
        r'Hola, les doy la bienvenida a',
        r'Hola, esto es',
        r'¡Hola! Esto es',
        r'Soy \w+ y (hoy|si)',
    ]
    
    # Find all introduction points
    split_points = [0]
    
    for pattern in intro_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            # Only add if it's not at the very beginning
            if match.start() > 50:  # At least 50 chars from start
                split_points.append(match.start())
    
    # Remove duplicates and sort
    split_points = sorted(set(split_points))
    
    # Split the text
    for i in range(len(split_points)):
        start = split_points[i]
        end = split_points[i + 1] if i + 1 < len(split_points) else len(text)
        story = text[start:end].strip()
        
        # Only add if story is substantial (at least 100 characters)
        if len(story) > 100:
            stories.append(story)
    
    # If no splits found, return the whole text as one story
    if not stories:
        stories = [text]
    
    return stories

def format_transcript(text):
    """
    Format transcript text to be more readable.
    - Add proper spacing
    - Capitalize sentences
    - Add line breaks for better readability
    """
    # Split by periods and format
    sentences = text.split('.')
    formatted_sentences = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence:
            # Capitalize first letter
            sentence = sentence[0].upper() + sentence[1:] if len(sentence) > 1 else sentence.upper()
            formatted_sentences.append(sentence)
    
    # Join with periods and newlines for readability
    formatted_text = '.\n\n'.join(formatted_sentences)
    if formatted_text and not formatted_text.endswith('.'):
        formatted_text += '.'
    
    return formatted_text

def check_existing_transcripts(audio_path, output_dir):
    """
    Check if transcripts already exist for this audio file.
    Returns list of existing transcript file paths if found, None otherwise.
    """
    prefix = audio_path.stem
    pattern = f"transcript_{prefix}_*.txt"
    existing_files = sorted(output_dir.glob(pattern))
    
    if existing_files:
        return existing_files
    return None

def read_existing_transcripts(transcript_files):
    """
    Read and combine existing transcript files into a single text.
    Handles both old single-file format and new split-file format.
    """
    combined_text = ""
    for file_path in transcript_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Remove header lines
            lines = content.split('\n')
            transcript_start = 0
            # Find where the actual transcript starts (after header and separator)
            for i, line in enumerate(lines):
                if line.startswith('=' * 10) or (line.startswith('Story') and i < 5):
                    transcript_start = i + 1
                    break
                # Also check for old format: "Transcript from:"
                if line.startswith('Transcript from:') and i < 3:
                    transcript_start = i + 2  # Skip header and separator
                    break
            
            # Get the actual transcript text
            transcript_text = '\n'.join(lines[transcript_start:]).strip()
            # Remove extra formatting (double newlines between sentences)
            # But keep the content
            combined_text += transcript_text + "\n\n"
    
    return combined_text.strip()

def transcribe_audio_file(audio_path, model, output_dir, grammar_tool):
    """
    Transcribe a single audio file, proofread, split into stories, and save.
    Checks for existing transcripts first.
    """
    print(f"\n📻 Processing: {audio_path.name}")
    
    try:
        # Check if transcripts already exist
        existing_transcripts = check_existing_transcripts(audio_path, output_dir)
        
        if existing_transcripts:
            print(f"   📄 Found {len(existing_transcripts)} existing transcript file(s)")
            print("   Reading existing transcripts...")
            transcript = read_existing_transcripts(existing_transcripts)
            print("   ✅ Using existing transcripts (skipping transcription)")
        else:
            # Transcribe the audio
            if model is None:
                print("   ❌ Error: No model provided and no existing transcripts found")
                return False
            print("   Transcribing...")
            result = model.transcribe(str(audio_path), language="es")
            transcript = result["text"]
        
        # Proofread the transcript
        print("   Proofreading...")
        corrected_transcript = proofread_spanish(transcript, grammar_tool)
        
        # Detect English hints
        print("   Detecting story boundaries...")
        hints = detect_english_hints(corrected_transcript)
        
        # Split into stories
        if hints:
            print(f"   Found {len(hints)} English hint(s), splitting by hints...")
            stories = split_by_english_hints(corrected_transcript, hints)
        else:
            print("   No English hints found, splitting by content...")
            stories = split_by_content(corrected_transcript)
        
        print(f"   Split into {len(stories)} story/stories")
        
        # Extract prefix from audio filename (remove extension)
        prefix = audio_path.stem
        
        # Save each story
        saved_files = []
        first_story_preview = None
        for i, story in enumerate(stories, 1):
            # Format the story
            formatted_story = format_transcript(story)
            
            # Store first story for preview
            if i == 1:
                first_story_preview = formatted_story
            
            # Create output filename: transcript_{prefix}_{number}.txt
            output_filename = f"transcript_{prefix}_{i}.txt"
            output_path = output_dir / output_filename
            
            # Save story
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"Story {i} from: {audio_path.name}\n")
                f.write("=" * 60 + "\n\n")
                f.write(formatted_story)
                f.write("\n")
            
            saved_files.append(output_path)
            print(f"   ✅ Saved story {i}: {output_path.name}")
        
        if first_story_preview:
            print(f"   📝 Preview of story 1:\n{first_story_preview[:200]}...\n")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error processing {audio_path.name}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    # Set up paths
    script_dir = Path(__file__).parent
    radios_dir = script_dir / "Duolinguo" / "radios"
    
    if not radios_dir.exists():
        print(f"❌ Directory not found: {radios_dir}")
        sys.exit(1)
    
    # Find all m4a files
    audio_files = list(radios_dir.glob("*.m4a"))
    
    if not audio_files:
        print(f"❌ No .m4a files found in {radios_dir}")
        sys.exit(1)
    
    print(f"🎯 Found {len(audio_files)} audio file(s)")
    
    # Check which files need transcription
    files_needing_transcription = []
    for audio_file in audio_files:
        existing = check_existing_transcripts(audio_file, radios_dir)
        if not existing:
            files_needing_transcription.append(audio_file)
    
    # Load Whisper model only if transcription is needed
    model = None
    if files_needing_transcription:
        print(f"   {len(files_needing_transcription)} file(s) need transcription")
        print("\n📥 Loading Whisper model (this may take a moment on first run)...")
        model = whisper.load_model("base")
        print("✅ Model loaded")
    else:
        print("   ✅ All files already have transcripts (skipping transcription)")
    
    # Initialize grammar checker for Spanish
    print("\n📥 Loading Spanish grammar checker...")
    try:
        grammar_tool = language_tool_python.LanguageTool('es-ES')
        print("✅ Grammar checker loaded\n")
    except Exception as e:
        print(f"⚠️  Warning: Could not load grammar checker: {str(e)}")
        print("   Continuing without grammar correction...\n")
        grammar_tool = None
    
    # Process each audio file (save transcripts in same folder as audio files)
    success_count = 0
    for audio_file in audio_files:
        if transcribe_audio_file(audio_file, model, radios_dir, grammar_tool):
            success_count += 1
    
    print(f"\n{'='*60}")
    print(f"✨ Transcription complete!")
    print(f"   Processed: {success_count}/{len(audio_files)} files")
    print(f"   Transcripts saved in: {radios_dir}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()

