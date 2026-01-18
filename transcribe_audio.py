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

# Force CPU mode to avoid CUDA compatibility issues
# This must be set before importing torch/whisper
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

import whisper
import language_tool_python
import subprocess

# Audio-based speaker diarization (optional)
try:
    from pyannote.audio import Pipeline
    from pyannote.core import Segment
    DIARIZATION_AVAILABLE = True
except ImportError:
    DIARIZATION_AVAILABLE = False

# OpenAI API for speaker diarization (optional)
try:
    from openai import OpenAI
    OPENAI_API_AVAILABLE = True
except ImportError:
    OPENAI_API_AVAILABLE = False

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
                # Handle both old (errorLength) and new (error_length) attribute names
                error_length = getattr(match, 'error_length', getattr(match, 'errorLength', 0))
                end = match.offset + error_length
                corrected_text = corrected_text[:start] + match.replacements[0] + corrected_text[end:]
        
        return corrected_text
    except Exception as e:
        print(f"   ⚠️  Warning: Grammar check failed: {str(e)}")
        return text

def transcribe_english_narrator(audio_path, model, start_time=0, duration=10):
    """
    Transcribe the beginning of audio in English to capture narrator's section/unit/radio numbers.
    Returns English transcript of the narrator portion.
    """
    try:
        # Use ffmpeg to extract the first few seconds
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.m4a', delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Extract first N seconds using ffmpeg
        subprocess.run(
            ['ffmpeg', '-i', str(audio_path), '-t', str(duration), 
             '-acodec', 'copy', '-y', temp_path],
            capture_output=True,
            timeout=30
        )
        
        # Transcribe in English
        result = model.transcribe(temp_path, language="en")
        english_text = result["text"].strip()
        
        # Clean up temp file
        os.unlink(temp_path)
        
        return english_text
    except Exception as e:
        print(f"   ⚠️  Warning: Could not transcribe English narrator: {str(e)}")
        return None

def detect_english_narrator_in_text(text):
    """
    Detect English narrator text in transcript (already transcribed, possibly in Spanish).
    Returns tuple: (english_narrator_text, spanish_text_without_narrator)
    """
    # Common English patterns that indicate narrator
    english_patterns = [
        r'(?:Section|section|SECTION)\s+\d+',
        r'(?:Unit|unit|UNIT)\s+\d+',
        r'(?:Radio|radio|RADIO)\s+\d+',
        r'(?:Section|section|SECTION)\s+\d+\s+(?:Unit|unit|UNIT)\s+\d+',
        r'(?:Section|section|SECTION)\s+\d+\s+(?:Unit|unit|UNIT)\s+\d+\s+(?:Radio|radio|RADIO)\s+\d+',
        r'(?:Section|section|SECTION)\s+\d+\s+(?:Radio|radio|RADIO)\s+\d+',
        r'\d+\s*(?:st|nd|rd|th)\s+(?:radio|section|unit|part)',
    ]
    
    # Split into sentences
    sentences = re.split(r'[.!?]+\s+', text)
    english_sentences = []
    spanish_sentences = []
    found_english = False
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        # Check if sentence contains English narrator patterns
        is_english_narrator = False
        
        # Check for English patterns
        for pattern in english_patterns:
            if re.search(pattern, sentence, re.IGNORECASE):
                is_english_narrator = True
                found_english = True
                break
        
        # Additional check: if sentence is mostly English indicator words
        if not is_english_narrator:
            english_words = ['section', 'unit', 'radio', 'part', 'number', 'segment', 
                           'first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth']
            words = re.findall(r'\b\w+\b', sentence.lower())
            if words:
                english_word_count = sum(1 for w in words if w in english_words)
                # If more than 30% are English indicator words, likely English narrator
                if english_word_count / len(words) > 0.3:
                    is_english_narrator = True
                    found_english = True
        
        # Only capture English narrator at the beginning (first few sentences)
        # Once we see clear Spanish content, stop capturing English
        if is_english_narrator and len(english_sentences) < 3:
            english_sentences.append(sentence)
        else:
            # If we've found English and now see Spanish, stop checking
            if found_english and not is_english_narrator:
                spanish_sentences.append(sentence)
            elif not found_english:
                # Haven't found English yet, keep all sentences
                spanish_sentences.append(sentence)
            else:
                # Found English but this might still be English, add to Spanish for now
                spanish_sentences.append(sentence)
    
    english_text = '. '.join(english_sentences) if english_sentences else None
    spanish_text = '. '.join(spanish_sentences) if spanish_sentences else text
    
    if spanish_text and not spanish_text.endswith('.'):
        spanish_text += '.'
    
    return english_text, spanish_text

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

def get_audio_duration(audio_path):
    """
    Get audio duration in seconds using ffprobe.
    Returns duration in seconds, or None if unavailable.
    """
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
             '-of', 'default=noprint_wrappers=1:nokey=1', str(audio_path)],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return float(result.stdout.strip())
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, ValueError, FileNotFoundError):
        pass
    return None

def split_by_episode_patterns(text, audio_path=None, speaker_segments=None, audio_duration=None):
    """
    Split transcript into episodes based on multiple heuristics:
    1. Pattern-based: Fixed patterns in Duolinguo radio episodes (intros/closings)
    2. Duration-based: Each episode is roughly 2.5-3 minutes (150-180 seconds)
    3. Speaker-based: Adjacent episodes have different speaker sets
    
    Args:
        text: Full transcript text
        audio_path: Path to audio file (for duration calculation)
        speaker_segments: List of (start_time, end_time, speaker_id, text) tuples from audio diarization
        audio_duration: Audio duration in seconds (if known)
    
    Returns:
        List of episode texts
    """
    episodes = []
    
    # Get audio duration if not provided
    if audio_duration is None and audio_path and audio_path.exists():
        audio_duration = get_audio_duration(audio_path)
    
    # Calculate expected episode duration (2.5-3 minutes = 150-180 seconds)
    MIN_EPISODE_DURATION = 120  # 2 minutes - minimum expected (merge if shorter)
    TARGET_EPISODE_DURATION = 165  # ~2.75 minutes - target
    MAX_EPISODE_DURATION = 210  # 3.5 minutes - maximum acceptable before splitting
    SPLIT_EPISODE_DURATION = 240  # 4 minutes - definitely split if longer
    
    # If we have audio duration, calculate text-to-time ratio
    # Estimate: average speaking rate ~150 words per minute, ~10 chars per word = ~1500 chars/min
    chars_per_second = None
    if audio_duration and len(text) > 0:
        chars_per_second = len(text) / audio_duration
        # Estimate duration for each character position
        estimated_chars_per_episode = int(TARGET_EPISODE_DURATION * chars_per_second)
        min_chars_per_episode = int(MIN_EPISODE_DURATION * chars_per_second)
        max_chars_per_episode = int(MAX_EPISODE_DURATION * chars_per_second)
        split_chars_per_episode = int(SPLIT_EPISODE_DURATION * chars_per_second)
    else:
        # Fallback: use rough estimates based on typical transcript length
        estimated_chars_per_episode = 2000  # Rough estimate for 2.5-3 min episode
        min_chars_per_episode = 1500
        max_chars_per_episode = 3000
        split_chars_per_episode = 3500
        chars_per_second = None  # Not available for time-based calculations
    
    # Step 1: Find initial split points using patterns
    split_points = [0]  # Start with beginning
    
    # PRIORITY 1: English narrator patterns (strong signal - always indicates new episode)
    # English narrator typically says "Section X Unit Y Radio Z" or similar
    # These patterns work even if English was transcribed in Spanish (e.g., "Sección" instead of "Section")
    english_narrator_patterns = [
        # English patterns
        r'(?:Section|section|SECTION)\s+\d+[^.]*\.',
        r'(?:Section|section|SECTION)\s+\d+\s+(?:Unit|unit|UNIT)\s+\d+[^.]*\.',
        r'(?:Section|section|SECTION)\s+\d+\s+(?:Unit|unit|UNIT)\s+\d+\s+(?:Radio|radio|RADIO)\s+\d+[^.]*\.',
        r'(?:Section|section|SECTION)\s+\d+\s+(?:Radio|radio|RADIO)\s+\d+[^.]*\.',
        r'\d+\s*(?:st|nd|rd|th)\s+(?:radio|section|unit|part)[^.]*\.',
        # Spanish transcription of English (common when Whisper transcribes English in Spanish mode)
        r'(?:Sección|sección|SECCIÓN)\s+\d+[^.]*\.',
        r'(?:Sección|sección|SECCIÓN)\s+\d+\s+(?:Unió|unió|UNIÓ|Unidad|unidad|UNIDAD)\s+\d+[^.]*\.',
        r'(?:Sección|sección|SECCIÓN)\s+\d+\s+(?:Unió|unió|UNIÓ|Unidad|unidad|UNIDAD)\s+\d+\s+(?:Radio|radio|RADIO)\s+\d+[^.]*\.',
        r'(?:Sección|sección|SECCIÓN)\s+\d+\s+(?:Radio|radio|RADIO)\s+\d+[^.]*\.',
    ]
    
    for pattern in english_narrator_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            pos = match.start()
            # English narrator is a strong signal - always add as split point (except at position 0)
            # Look backwards to find the actual start of the English narrator sentence
            # English narrator usually appears at the start of a sentence
            sentence_start = pos
            # Look for sentence boundary before this position
            for i in range(max(0, pos - 200), pos):
                if text[i] in '.!?':
                    sentence_start = i + 1
                    # Skip whitespace
                    while sentence_start < pos and text[sentence_start].isspace():
                        sentence_start += 1
                    break
            
            if sentence_start > 0:
                is_new_split = True
                for existing_split in split_points:
                    if abs(sentence_start - existing_split) < 50:  # Allow closer splits for English narrator
                        is_new_split = False
                        break
                if is_new_split:
                    split_points.append(sentence_start)
    
    # Pattern for episode closing (marks end of episode)
    closing_patterns = [
        r'Gracias por escuchar[^.]*\.\s*Hasta (pronto|la próxima)\.',
        r'Gracias por acompañarme[^.]*\.\s*Hasta (pronto|la próxima)\.',
        r'Y así termina[^.]*\.\s*Recuerda[^.]*\.\s*Hasta pronto\.',
        r'¡Ah! Gracias por escuchar[^.]*\.\s*Nos vemos pronto\.',
    ]
    
    for pattern in closing_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            end_pos = match.end()
            next_text = text[end_pos:end_pos+200]
            if re.search(r'Hola.*bienvenida|Te doy.*bienvenida|Soy \w+ y', next_text, re.IGNORECASE):
                split_points.append(end_pos)
            elif len(text[end_pos:].strip()) > 100:
                split_points.append(end_pos)
    
    # Pattern for episode introductions (new episode starts)
    intro_patterns = [
        r'Hola, te doy la bienvenida a',
        r'¡Pu-pu-pu! Hola, te doy la bienvenida a',
        r'Te doy la bienvenida a',
        r'¿Te doy la bienvenida a',
        r'Hola, les doy la bienvenida a',
        r'Hola, esto es',
        r'¡Hola! Esto es',
    ]
    
    for pattern in intro_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            pos = match.start()
            if pos > 50:
                is_new_split = True
                for existing_split in split_points:
                    if abs(pos - existing_split) < 100:
                        is_new_split = False
                        break
                if is_new_split:
                    split_points.append(pos)
    
    # Remove duplicates and sort
    split_points = sorted(set(split_points))
    
    # Step 2: Extract speakers for each potential episode segment
    # Use speaker segments if available to identify speaker changes
    episode_speaker_sets = []
    for i in range(len(split_points)):
        start = split_points[i]
        end = split_points[i + 1] if i + 1 < len(split_points) else len(text)
        episode_text = text[start:end]
        
        # Extract speaker names from this episode
        episode_speakers = set(extract_speaker_names(episode_text))
        episode_speaker_sets.append(episode_speakers)
        
        # If we have audio-based speaker segments, use them too
        if speaker_segments:
            # Estimate time range for this text segment
            if chars_per_second:
                start_time = start / chars_per_second
                end_time = end / chars_per_second
                # Find speakers in this time range
                segment_speakers = set()
                for seg_start, seg_end, speaker_id, seg_text in speaker_segments:
                    if speaker_id and (start_time <= (seg_start + seg_end) / 2 <= end_time):
                        segment_speakers.add(speaker_id)
                if segment_speakers:
                    episode_speakers.update(segment_speakers)
    
    # Step 3: Refine splits based on duration and speaker changes
    # First pass: merge too-short segments
    refined_splits = [split_points[0]]  # Start with first split (usually 0)
    
    i = 1
    while i < len(split_points):
        prev_start = refined_splits[-1]
        current_start = split_points[i]
        current_end = split_points[i + 1] if i + 1 < len(split_points) else len(text)
        
        # Calculate length of segment from previous split to current
        segment_length = current_start - prev_start
        
        # If segment is too short, check if we should merge with next
        if segment_length < min_chars_per_episode:
            # Check next segment
            if i + 1 < len(split_points):
                next_start = split_points[i + 1]
                next_segment_length = next_start - current_start
                # Calculate combined length of current segment + next segment only
                # (not including the segment after next)
                combined_length = next_start - prev_start
                
                # Get speakers for both segments
                current_seg = text[prev_start:current_start]
                next_seg = text[current_start:next_start]
                current_speakers = set(extract_speaker_names(current_seg))
                next_speakers = set(extract_speaker_names(next_seg))
                speakers_overlap = len(current_speakers & next_speakers) > 0
                
                # Merge if: (1) speakers overlap (same episode split incorrectly), 
                # or (2) combined length is still reasonable
                if speakers_overlap or combined_length < max_chars_per_episode:
                    # Skip current split, merge segments
                    i += 1
                    continue
        
        # Segment length is reasonable or shouldn't be merged, keep the split
        refined_splits.append(current_start)
        i += 1
    
    # Second pass: split too-long segments
    final_splits = [refined_splits[0]]
    i = 1
    while i < len(refined_splits):
        prev_start = final_splits[-1]
        current_start = refined_splits[i]
        current_end = refined_splits[i + 1] if i + 1 < len(refined_splits) else len(text)
        
        segment_length = current_end - prev_start
        
        # If segment is too long, try to find a good split point
        # Use split_threshold for definitely splitting (4 minutes)
        if segment_length > max_chars_per_episode:
            segment_text = text[prev_start:current_end]
            
            # Determine how many splits we need (for very long episodes, split multiple times)
            num_splits_needed = max(1, int(segment_length / max_chars_per_episode))
            
            # For very long episodes, be more aggressive in finding split points
            best_split = None
            best_score = 0
            
            # Determine search window based on segment length
            # For very long episodes (>4 min), search a wider area
            if segment_length > split_chars_per_episode:
                # Very long episode - search broader area, focus on closing+intro patterns
                search_start = prev_start + min_chars_per_episode
                search_end = current_end - min_chars_per_episode
                
                # Priority 1: Look for closing pattern followed by intro pattern (clear episode boundary)
                # This is the strongest indicator of two episodes mixed together
                for closing_pattern in closing_patterns:
                    for closing_match in re.finditer(closing_pattern, segment_text, re.IGNORECASE):
                        closing_end = prev_start + closing_match.end()
                        
                        # Look for intro pattern within 500 chars after closing (new episode starts)
                        next_text = text[closing_end:min(closing_end + 500, current_end)]
                        for intro_pattern in intro_patterns:
                            intro_match = re.search(intro_pattern, next_text, re.IGNORECASE)
                            if intro_match:
                                candidate = closing_end + intro_match.start()
                                before_text = text[prev_start:candidate]
                                after_text = text[candidate:current_end]
                                
                                before_speakers = set(extract_speaker_names(before_text))
                                after_speakers = set(extract_speaker_names(after_text))
                                speaker_diff = len(before_speakers & after_speakers) == 0
                                
                                before_len = len(before_text)
                                after_len = len(after_text)
                                len_ok = (min_chars_per_episode <= before_len <= max_chars_per_episode * 1.5 and
                                         min_chars_per_episode <= after_len <= max_chars_per_episode * 1.5)
                                
                                # Very high score for closing+intro pattern (strongest indicator)
                                score = (5 if True else 0) + (2 if speaker_diff else 0) + (2 if len_ok else 0)
                                if score > best_score:
                                    best_score = score
                                    best_split = candidate
                                    break
                            if best_split:
                                break
                        if best_split:
                            break
                    if best_split:
                        break
                
                # Priority 2: If no closing+intro found, look for intro patterns at target intervals
                if not best_split:
                    for split_idx in range(1, num_splits_needed + 1):
                        ideal_split_pos = prev_start + int(split_idx * estimated_chars_per_episode)
                        if ideal_split_pos >= current_end - min_chars_per_episode:
                            break
                        
                        # Search around ideal position
                        search_start_local = max(prev_start + min_chars_per_episode, ideal_split_pos - 800)
                        search_end_local = min(current_end - min_chars_per_episode, ideal_split_pos + 800)
                        
                        # Check intro patterns first (higher priority)
                        for pattern in intro_patterns:
                            for match in re.finditer(pattern, text[search_start_local:search_end_local], re.IGNORECASE):
                                candidate = search_start_local + match.start()
                                before_text = text[prev_start:candidate]
                                after_text = text[candidate:current_end]
                                
                                before_speakers = set(extract_speaker_names(before_text))
                                after_speakers = set(extract_speaker_names(after_text))
                                speaker_diff = len(before_speakers & after_speakers) == 0
                                
                                before_len = len(before_text)
                                after_len = len(after_text)
                                len_ok = (min_chars_per_episode <= before_len <= max_chars_per_episode * 1.4 and
                                         min_chars_per_episode <= after_len <= max_chars_per_episode * 1.4)
                                
                                # Bonus for being close to ideal position
                                pos_bonus = 1 if abs(candidate - ideal_split_pos) < 400 else 0
                                score = (3 if speaker_diff else 0) + (2 if len_ok else 0) + pos_bonus
                                if score > best_score:
                                    best_score = score
                                    best_split = candidate
                                    break
                            if best_split:
                                break
                        if best_split:
                            break
                
                # Priority 3: Look for closing patterns followed by substantial new content
                if not best_split:
                    for pattern in closing_patterns:
                        for match in re.finditer(pattern, segment_text, re.IGNORECASE):
                            candidate = prev_start + match.end()
                            # Check if there's substantial new content after closing
                            after_text = text[candidate:current_end]
                            if len(after_text.strip()) > min_chars_per_episode * 0.8:  # At least 80% of min length
                                before_text = text[prev_start:candidate]
                                before_len = len(before_text)
                                after_len = len(after_text)
                                
                                # Check if lengths are reasonable
                                if (min_chars_per_episode <= before_len <= max_chars_per_episode * 1.5 and
                                    min_chars_per_episode <= after_len <= max_chars_per_episode * 1.5):
                                    before_speakers = set(extract_speaker_names(before_text))
                                    after_speakers = set(extract_speaker_names(after_text))
                                    speaker_diff = len(before_speakers & after_speakers) == 0
                                    
                                    len_ok_local = (min_chars_per_episode <= before_len <= max_chars_per_episode * 1.5 and
                                                   min_chars_per_episode <= after_len <= max_chars_per_episode * 1.5)
                                    score = (4 if True else 0) + (2 if speaker_diff else 0) + (1 if len_ok_local else 0)
                                    if score > best_score:
                                        best_score = score
                                        best_split = candidate
            else:
                # Moderately long episode - look around midpoint
                mid_point = prev_start + segment_length // 2
                search_start = max(prev_start + min_chars_per_episode, mid_point - 1000)
                search_end = min(current_end - min_chars_per_episode, mid_point + 1000)
                
                # Priority 1: Closing + intro pattern
                for closing_pattern in closing_patterns:
                    for closing_match in re.finditer(closing_pattern, text[search_start:search_end], re.IGNORECASE):
                        closing_end = search_start + closing_match.end()
                        next_text = text[closing_end:min(closing_end + 500, search_end)]
                        for intro_pattern in intro_patterns:
                            intro_match = re.search(intro_pattern, next_text, re.IGNORECASE)
                            if intro_match:
                                candidate = closing_end + intro_match.start()
                                before_text = text[prev_start:candidate]
                                after_text = text[candidate:current_end]
                                
                                before_speakers = set(extract_speaker_names(before_text))
                                after_speakers = set(extract_speaker_names(after_text))
                                speaker_diff = len(before_speakers & after_speakers) == 0
                                
                                before_len = len(before_text)
                                after_len = len(after_text)
                                len_ok = (min_chars_per_episode <= before_len <= max_chars_per_episode * 1.3 and
                                         min_chars_per_episode <= after_len <= max_chars_per_episode * 1.3)
                                
                                score = (5 if True else 0) + (2 if speaker_diff else 0) + (2 if len_ok else 0)
                                if score > best_score:
                                    best_score = score
                                    best_split = candidate
                                    break
                            if best_split:
                                break
                        if best_split:
                            break
                    if best_split:
                        break
                
                # Priority 2: Intro patterns
                if not best_split:
                    for pattern in intro_patterns:
                        for match in re.finditer(pattern, text[search_start:search_end], re.IGNORECASE):
                            candidate = search_start + match.start()
                            before_text = text[prev_start:candidate]
                            after_text = text[candidate:current_end]
                            
                            before_speakers = set(extract_speaker_names(before_text))
                            after_speakers = set(extract_speaker_names(after_text))
                            speaker_diff = len(before_speakers & after_speakers) == 0
                            
                            before_len = len(before_text)
                            after_len = len(after_text)
                            len_ok = (min_chars_per_episode <= before_len <= max_chars_per_episode * 1.2 and
                                     min_chars_per_episode <= after_len <= max_chars_per_episode * 1.2)
                            
                            score = (3 if speaker_diff else 0) + (1 if len_ok else 0)
                            if score > best_score:
                                best_score = score
                                best_split = candidate
                
                # Priority 3: Closing patterns
                if not best_split:
                    for pattern in closing_patterns:
                        for match in re.finditer(pattern, text[search_start:search_end], re.IGNORECASE):
                            candidate = search_start + match.end()
                            before_text = text[prev_start:candidate]
                            after_text = text[candidate:current_end]
                            
                            before_speakers = set(extract_speaker_names(before_text))
                            after_speakers = set(extract_speaker_names(after_text))
                            speaker_diff = len(before_speakers & after_speakers) == 0
                            
                            before_len = len(before_text)
                            after_len = len(after_text)
                            len_ok = (min_chars_per_episode <= before_len <= max_chars_per_episode * 1.2 and
                                     min_chars_per_episode <= after_len <= max_chars_per_episode * 1.2)
                            
                            score = (2 if speaker_diff else 0) + (1 if len_ok else 0)
                            if score > best_score:
                                best_score = score
                                best_split = candidate
            
            # For very long episodes (>5 minutes), if no pattern found, force split at midpoint
            # Lower threshold: if episode is >5 minutes (split_chars_per_episode * 1.25) and no pattern found
            if not best_split and segment_length > split_chars_per_episode * 1.25:
                # Episode is extremely long (>5 minutes), force split at midpoint
                # Look for any intro or closing pattern in the middle 40% (wider search)
                mid_point = prev_start + segment_length // 2
                search_start = max(prev_start + min_chars_per_episode, mid_point - int(segment_length * 0.2))
                search_end = min(current_end - min_chars_per_episode, mid_point + int(segment_length * 0.2))
                
                # Try to find ANY intro pattern in this wider search area
                for pattern in intro_patterns:
                    for match in re.finditer(pattern, text[search_start:search_end], re.IGNORECASE):
                        candidate = search_start + match.start()
                        before_len = candidate - prev_start
                        after_len = current_end - candidate
                        
                        # Accept split if both parts are at least minimum length
                        # For very long episodes, be more lenient - allow splits even if one part is slightly shorter
                        min_required = int(min_chars_per_episode * 0.8)  # Allow 80% of minimum
                        if before_len >= min_required and after_len >= min_required:
                            best_split = candidate
                            best_score = 3  # Moderate score for forced split
                            break
                    if best_split:
                        break
                
                # If still no pattern, split at exact midpoint as last resort
                if not best_split:
                    mid_point = prev_start + segment_length // 2
                    before_len = mid_point - prev_start
                    after_len = current_end - mid_point
                    # Only force split if both parts are reasonable
                    # For very long episodes, be more lenient
                    min_required = int(min_chars_per_episode * 0.75)  # Allow 75% of minimum for forced splits
                    if before_len >= min_required and after_len >= min_required:
                                    # Find sentence boundary near midpoint
                                    # Look for period, exclamation, or question mark near midpoint
                                    for offset in range(-300, 301, 50):  # Check in 50-char increments, wider range
                                        check_pos = mid_point + offset
                                        if prev_start + min_required <= check_pos <= current_end - min_required:
                                            # Find next sentence boundary after this position
                                            text_around = text[max(check_pos - 150, prev_start):min(check_pos + 400, current_end)]
                                            boundary_match = re.search(r'[.!?]+\s+', text_around)
                                            if boundary_match:
                                                candidate = max(check_pos - 150, prev_start) + boundary_match.end()
                                                if prev_start + min_required <= candidate <= current_end - min_required:
                                                    best_split = candidate
                                                    best_score = 2  # Low score, but acceptable for forced split
                                                    break
                                            else:
                                                # Find any punctuation or whitespace boundary
                                                whitespace_match = re.search(r'\s{2,}|\n', text_around)
                                                if whitespace_match:
                                                    candidate = max(check_pos - 150, prev_start) + whitespace_match.end()
                                                    if prev_start + min_required <= candidate <= current_end - min_required:
                                                        best_split = candidate
                                                        best_score = 1
                                                        break
                                                else:
                                                    # Use the position itself if no boundary found (last resort)
                                                    candidate = check_pos
                                                    if prev_start + min_required <= candidate <= current_end - min_required:
                                                        best_split = candidate
                                                        best_score = 1
                                                        break
                                        if best_split:
                                            break
            
            if best_split:
                # Insert new split in refined_splits and restart processing from there
                refined_splits.insert(i, best_split)
                # Recalculate speaker sets (will be recalculated in next iteration)
                # Continue from beginning of this loop to reprocess
                i = 1
                final_splits = [refined_splits[0]]
                continue
        
        # Segment length is reasonable, keep the split
        final_splits.append(current_start)
        i += 1
    
    # Add final split point at text end
    if final_splits[-1] != len(text):
        final_splits.append(len(text))
    
    # Final pass: filter out splits that are too close
    filtered_splits = [final_splits[0]]
    for split in final_splits[1:]:
        min_gap = min_chars_per_episode * 0.4  # At least 40% of min episode length
        if split - filtered_splits[-1] >= min_gap:
            filtered_splits.append(split)
        elif split == len(text):
            # Always include final split
            if filtered_splits[-1] != len(text):
                filtered_splits.append(len(text))
        else:
            # Merge: replace last split
            filtered_splits[-1] = split
    
    # Ensure we end at text end
    if filtered_splits[-1] != len(text):
        filtered_splits.append(len(text))
    
    # Create episodes from final splits
    for i in range(len(filtered_splits) - 1):
        start = filtered_splits[i]
        end = filtered_splits[i + 1]
        episode = text[start:end].strip()
        
        if len(episode) > 100:
            episodes.append(episode)
    
    # If no splits found, return the whole text as one episode
    if not episodes:
        episodes = [text]
    
    return episodes

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

def extract_speaker_names(text):
    """
    Extract speaker names from dialogue using common Spanish patterns.
    Returns a list of detected names.
    """
    names = set()
    
    # Common words that might be mistaken for names
    common_words = {'Hola', 'Gracias', 'Bienvenida', 'Bienvenido', 'Soy', 'Llamo', 'Nombre', 
                    'Pero', 'Por', 'Los', 'Las', 'Nos', 'Todo', 'Tal', 'Eso', 'Eso', 'Cada',
                    'Muy', 'Ahora', 'Antes', 'Hasta', 'Voy', 'Hace', 'Siempre', 'Entonces',
                    'Algunos', 'Bueno', 'Ideas', 'Recuerda', 'Pintar', 'Visite', 'Alegre',
                    'Carros', 'Colombia'}
    
    # Common patterns for name introduction in Spanish
    patterns = [
        r'(?:Soy|soy)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',  # "Soy María" or "Soy María José"
        r'(?:Me llamo|me llamo)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',  # "Me llamo Carlos"
        r'(?:Mi nombre es|mi nombre es)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',  # "Mi nombre es Ana"
        r'(?:Hola|hola),?\s+([A-Z][a-z]+)',  # "Hola, Juan" (when addressing someone)
        r'(?:Hola|hola)\s+([A-Z][a-z]+)',  # "Hola Juan"
        r'([A-Z][a-z]+),?\s+(?:gracias|Gracias)',  # "María, gracias"
        r'([A-Z][a-z]+),?\s+(?:cuéntanos|cuéntame)',  # "María, cuéntanos"
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            name = match.group(1).strip()
            # Filter out common words that might be mistaken for names
            if name and name not in common_words and len(name) > 2:
                names.add(name)
    
    # Also look for capitalized words that appear multiple times (likely names)
    # But be more selective - only consider words that appear in name introduction patterns
    words = re.findall(r'\b([A-Z][a-z]{2,})\b', text)
    word_counts = {}
    for word in words:
        if word not in common_words:
            word_counts[word] = word_counts.get(word, 0) + 1
    
    # Add words that appear 3+ times and are capitalized (likely names)
    # This is more conservative to avoid false positives
    for word, count in word_counts.items():
        if count >= 3:
            names.add(word)
    
    return sorted(list(names))

def perform_speaker_diarization_openai(audio_path, openai_api_key=None):
    """
    Perform transcription and speaker diarization using OpenAI API.
    Uses gpt-4o-transcribe-diarize-api-ev3 model which provides both transcription and speaker labels.
    
    Returns tuple: (transcript_text, labeled_segments)
    where labeled_segments is list of (start_time, end_time, speaker_id, text)
    """
    if not OPENAI_API_AVAILABLE:
        return None, None
    
    try:
        client = OpenAI(api_key=openai_api_key)
        
        # Open audio file
        with open(audio_path, 'rb') as audio_file:
            # Try to use gpt-4o-transcribe-diarize model (if available)
            # This model provides both transcription and speaker diarization
            try:
                transcript = client.audio.transcriptions.create(
                    model="gpt-4o-transcribe-diarize",
                    file=audio_file,
                    language="es",
                    response_format="json",  # Use 'json' for gpt-4o-transcribe-diarize
                    chunking_strategy="auto"  # Required for diarization models
                )
            except Exception as e:
                # Fallback to whisper-1 if gpt-4o-transcribe-diarize not available
                print(f"   ⚠️  gpt-4o-transcribe-diarize not available, using whisper-1: {str(e)}")
                # Reset file pointer to beginning before second attempt
                audio_file.seek(0)
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="es",
                    response_format="verbose_json",
                    timestamp_granularities=["segment", "word"]
                )
        
        # Extract transcript text and segments with speaker labels
        full_text = ""
        labeled_segments = []
        
        # Handle different response formats
        if hasattr(transcript, 'segments') and transcript.segments:
            # verbose_json format (whisper-1)
            for segment in transcript.segments:
                # Handle both dict-like and object-like segments
                if isinstance(segment, dict):
                    start = segment.get('start', 0)
                    end = segment.get('end', 0)
                    text = segment.get('text', '').strip()
                    speaker = segment.get('speaker', None)
                else:
                    # Object with attributes
                    start = getattr(segment, 'start', 0)
                    end = getattr(segment, 'end', 0)
                    text = getattr(segment, 'text', '').strip()
                    speaker = getattr(segment, 'speaker', None)
                
                if text:
                    full_text += text + " "
                    labeled_segments.append((start, end, speaker, text))
        elif hasattr(transcript, 'text'):
            # Simple text format
            full_text = transcript.text if isinstance(transcript.text, str) else getattr(transcript, 'text', '')
        elif isinstance(transcript, dict):
            # Dictionary response (json format)
            full_text = transcript.get('text', '')
            if 'segments' in transcript:
                for segment in transcript['segments']:
                    start = segment.get('start', 0)
                    end = segment.get('end', 0)
                    text = segment.get('text', '').strip()
                    speaker = segment.get('speaker', None)
                    if text:
                        full_text += text + " "
                        labeled_segments.append((start, end, speaker, text))
        
        return full_text.strip(), labeled_segments if labeled_segments else None
    except Exception as e:
        print(f"   ⚠️  OpenAI API transcription failed: {str(e)}")
        return None, None

def perform_speaker_diarization(audio_path, hf_token=None):
    """
    Perform speaker diarization on audio file using pyannote.audio.
    Returns list of tuples: (start_time, end_time, speaker_id)
    """
    if not DIARIZATION_AVAILABLE:
        return None
    
    try:
        # Load the pre-trained speaker diarization pipeline
        # Using pyannote/speaker-diarization-3.1 model
        if hf_token:
            # Use 'token' parameter (current API)
            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                token=hf_token
            )
        else:
            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1"
            )
        
        # Run diarization
        diarization = pipeline(str(audio_path))
        
        # Extract segments with speaker labels
        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append((turn.start, turn.end, speaker))
        
        return segments
    except Exception as e:
        print(f"   ⚠️  Speaker diarization failed: {str(e)}")
        return None

def get_word_timestamps(audio_path, model):
    """
    Get word-level timestamps from Whisper transcription.
    Returns list of tuples: (word, start_time, end_time)
    """
    try:
        result = model.transcribe(
            str(audio_path), 
            language="es",
            word_timestamps=True
        )
        
        words_with_timestamps = []
        for segment in result.get("segments", []):
            for word_info in segment.get("words", []):
                word = word_info.get("word", "").strip()
                start = word_info.get("start", 0)
                end = word_info.get("end", 0)
                if word:
                    words_with_timestamps.append((word, start, end))
        
        return words_with_timestamps
    except Exception as e:
        print(f"   ⚠️  Word timestamp extraction failed: {str(e)}")
        return None

def align_speakers_with_text(sentences, words_with_timestamps, diarization_segments):
    """
    Align speaker diarization segments with transcript sentences.
    Returns list of tuples: (sentence, speaker_id_from_audio)
    """
    if not words_with_timestamps or not diarization_segments:
        return None
    
    # Create a mapping: time -> speaker (more efficient lookup)
    speaker_segments = []  # List of (start, end, speaker)
    for start, end, speaker in diarization_segments:
        speaker_segments.append((start, end, speaker))
    speaker_segments.sort(key=lambda x: x[0])  # Sort by start time
    
    def get_speaker_at_time(time):
        """Get speaker at a given time."""
        for start, end, speaker in speaker_segments:
            if start <= time <= end:
                return speaker
        return None
    
    # Align sentences with speakers by finding word timestamps
    sentence_speakers = []
    word_idx = 0
    
    for sentence in sentences:
        if not sentence.strip():
            sentence_speakers.append((sentence, None))
            continue
        
        # Find words in this sentence (normalized)
        sentence_words = [w.lower().strip('.,!?;:') for w in re.findall(r'\b\w+\b', sentence)]
        if not sentence_words:
            sentence_speakers.append((sentence, None))
            continue
        
        # Find matching words in timestamp list
        sentence_start = None
        sentence_end = None
        matched_words = 0
        
        # Look for sentence words in the word timestamp list
        for i in range(word_idx, len(words_with_timestamps)):
            word, start, end = words_with_timestamps[i]
            word_clean = word.strip().lower().rstrip('.,!?;:')
            
            # Check if this word matches any word in the sentence
            if word_clean in sentence_words:
                if sentence_start is None:
                    sentence_start = start
                sentence_end = end
                matched_words += 1
                
                # If we've matched enough words, we found the sentence
                if matched_words >= min(3, len(sentence_words)):  # Match at least 3 words or all if less
                    word_idx = i + 1
                    break
        
        # Determine speaker for this sentence
        speaker_id = None
        if sentence_start is not None and sentence_end is not None:
            # Use the middle point of the sentence
            mid_time = (sentence_start + sentence_end) / 2
            speaker_id = get_speaker_at_time(mid_time)
            
            # If no speaker at mid point, try start and end
            if not speaker_id:
                speaker_id = get_speaker_at_time(sentence_start) or get_speaker_at_time(sentence_end)
        
        sentence_speakers.append((sentence, speaker_id))
    
    return sentence_speakers

def identify_speakers_with_audio(text, speaker_names, audio_path=None, whisper_model=None, hf_token=None, openai_api_key=None):
    """
    Identify speakers using both audio diarization and text-based methods.
    Supports both OpenAI API and HuggingFace (pyannote) approaches.
    Combines both approaches for better accuracy.
    """
    # First, try OpenAI API (if available and preferred)
    audio_speakers = None
    openai_transcript = None
    
    if audio_path and openai_api_key and OPENAI_API_AVAILABLE:
        print("   🎤 Using OpenAI API for transcription with speaker diarization...")
        openai_transcript, openai_segments = perform_speaker_diarization_openai(audio_path, openai_api_key)
        if openai_transcript and openai_segments:
            print("   ✅ OpenAI API transcription with speaker diarization successful")
            # OpenAI gpt-4o-transcribe-diarize provides speaker labels directly
            # Map segments to sentences
            sentences = re.split(r'[.!?]+\s+', openai_transcript)
            audio_speakers = []
            
            # Create mapping from time to speaker
            time_to_speaker = {}
            for seg_start, seg_end, seg_speaker, seg_text in openai_segments:
                if seg_speaker:
                    # Map time range to speaker
                    mid_time = (seg_start + seg_end) / 2
                    time_to_speaker[mid_time] = seg_speaker
            
            # Assign speakers to sentences based on segments
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                # Find matching segment
                speaker_id = None
                for seg_start, seg_end, seg_speaker, seg_text in openai_segments:
                    if sentence.lower() in seg_text.lower() or any(w in seg_text.lower() for w in sentence.split()[:3]):
                        speaker_id = seg_speaker
                        break
                
                audio_speakers.append((sentence, speaker_id))
            
            if audio_speakers:
                print(f"   ✅ OpenAI API diarization: {len(set(s for _, s in audio_speakers if s))} speaker(s) detected")
                text = openai_transcript
        elif openai_transcript:
            print("   ✅ OpenAI API transcription successful (no speaker labels)")
            text = openai_transcript
    
    # Fallback to HuggingFace/pyannote if OpenAI not available or failed
    if not audio_speakers and audio_path and whisper_model and DIARIZATION_AVAILABLE:
        print("   🎤 Performing audio-based speaker diarization (HuggingFace)...")
        diarization_segments = perform_speaker_diarization(audio_path, hf_token)
        if diarization_segments:
            words_with_timestamps = get_word_timestamps(audio_path, whisper_model)
            if words_with_timestamps:
                sentences = re.split(r'[.!?]+\s+', text)
                audio_speakers = align_speakers_with_text(sentences, words_with_timestamps, diarization_segments)
                if audio_speakers:
                    print(f"   ✅ Audio diarization successful: {len(set(s for _, s in audio_speakers if s))} speaker(s) detected")
    
    # Get text-based speaker identification
    text_speakers = identify_speakers(text, speaker_names)
    
    # Combine both methods
    if audio_speakers and len(audio_speakers) == len(text_speakers):
        # Map audio speaker IDs to names
        # Audio gives us speaker IDs (SPEAKER_00, SPEAKER_01, etc.)
        # We need to map them to actual names
        
        # Count occurrences of each audio speaker
        audio_speaker_counts = {}
        for sentence, audio_speaker in audio_speakers:
            if audio_speaker:
                audio_speaker_counts[audio_speaker] = audio_speaker_counts.get(audio_speaker, 0) + 1
        
        # Map audio speakers to text speakers based on patterns
        # Use text-based identification as primary, audio as validation/refinement
        combined_speakers = []
        audio_speaker_to_name = {}
        
        # Try to map audio speakers to detected names
        if len(audio_speaker_counts) == len(speaker_names) and len(speaker_names) == 2:
            # Simple case: 2 speakers, map based on frequency and patterns
            sorted_audio = sorted(audio_speaker_counts.items(), key=lambda x: x[1], reverse=True)
            # Assume main speaker speaks more in intro/closing
            main_speaker_name = None
            for name in speaker_names:
                # Check if this name appears in intro section
                intro_text = ' '.join([s for s, _ in text_speakers[:5]])
                if name.lower() in intro_text.lower():
                    main_speaker_name = name
                    break
            
            if main_speaker_name:
                audio_speaker_to_name[sorted_audio[0][0]] = main_speaker_name
                other_name = [n for n in speaker_names if n != main_speaker_name][0]
                if len(sorted_audio) > 1:
                    audio_speaker_to_name[sorted_audio[1][0]] = other_name
        
        # Combine: prefer audio when available and confident, otherwise use text
        for i, (sentence, text_speaker) in enumerate(text_speakers):
            if i < len(audio_speakers):
                _, audio_speaker = audio_speakers[i]
                if audio_speaker and audio_speaker in audio_speaker_to_name:
                    # Use audio-based identification
                    combined_speakers.append((sentence, audio_speaker_to_name[audio_speaker]))
                else:
                    # Use text-based identification
                    combined_speakers.append((sentence, text_speaker))
            else:
                combined_speakers.append((sentence, text_speaker))
        
        return combined_speakers
    
    # Fallback to text-based only
    return text_speakers

def detect_gender(name):
    """
    Detect gender from Spanish name endings.
    Returns 'M' for male, 'F' for female, or None if unknown.
    """
    # Common Spanish name endings
    female_endings = ['a', 'ia', 'ina', 'ela', 'ela', 'ela']
    male_endings = ['o', 'io', 'in', 'el', 'er', 'an', 'en']
    
    name_lower = name.lower()
    
    # Check for common female endings
    for ending in female_endings:
        if name_lower.endswith(ending) and len(name_lower) > len(ending):
            return 'F'
    
    # Check for common male endings
    for ending in male_endings:
        if name_lower.endswith(ending) and len(name_lower) > len(ending):
            return 'M'
    
    # Known names database (common Spanish names)
    known_female = {'maria', 'mariana', 'ana', 'carla', 'laura', 'sofia', 'elena', 
                    'fernanda', 'vea', 'sari', 'claudia'}
    known_male = {'carlos', 'juan', 'pedro', 'miguel', 'mateo', 'felipe', 'antonio',
                  'daniel', 'jose', 'luis', 'junior', 'ector', 'vicram'}
    
    if name_lower in known_female:
        return 'F'
    if name_lower in known_male:
        return 'M'
    
    return None

def identify_speakers(text, speaker_names, is_episode_start=False):
    """
    Identify which speaker is talking for each sentence using episode structure patterns.
    
    Episode structure:
    1. Introduction: Main speaker says hello and introduces theme/guest (all before word review)
    2. Word review: "Pero primero, estas son algunas palabras..." (usually main speaker)
    3. Dialog: Conversation between main speaker and guest (alternates)
    4. Closing: "Gracias por escuchar... Hasta pronto." (usually main speaker)
    
    Refinements:
    - If a sentence contains a question directed at someone by name, that person is NOT the speaker
    - Uses gender information to help identify speakers when available
    - First four words of an episode are spoken by a third person (narrator), not the main speakers
    
    Args:
        text: The transcript text
        speaker_names: List of detected speaker names
        is_episode_start: Whether this is the start of a new episode (for narrator detection)
    
    Returns list of tuples: (sentence, speaker_label)
    """
    if not speaker_names:
        # If no names detected, use generic labels
        sentences = re.split(r'[.!?]+\s+', text)
        return [(s.strip(), "Speaker 1" if i % 2 == 0 else "Speaker 2") 
                for i, s in enumerate(sentences) if s.strip()]
    
    # Split into sentences
    sentences = re.split(r'[.!?]+\s+', text)
    labeled_sentences = []
    
    # Find the word review marker ("Pero primero, estas son algunas palabras...")
    word_review_marker = None
    for i, sentence in enumerate(sentences):
        if re.search(r'Pero primero.*palabras|estas son algunas palabras', sentence, re.IGNORECASE):
            word_review_marker = i
            break
    
    # Identify main speaker (usually the one who introduces themselves first)
    main_speaker = None
    guest_speaker = None
    
    # Look for self-introduction patterns in the introduction section
    intro_section = sentences[:word_review_marker] if word_review_marker else sentences[:5]
    for sentence in intro_section:
        for name in speaker_names:
            if re.search(rf'(?:Soy|soy|Me llamo|me llamo|Mi nombre es|mi nombre es)\s+{name}\b', sentence, re.IGNORECASE):
                main_speaker = name
                # Guest is the other speaker
                guest_speaker = [n for n in speaker_names if n != name]
                if guest_speaker:
                    guest_speaker = guest_speaker[0]
                break
        if main_speaker:
            break
    
    # If no clear main speaker found, use first detected name as main
    if not main_speaker:
        main_speaker = speaker_names[0]
        if len(speaker_names) > 1:
            guest_speaker = speaker_names[1]
    
    # Detect genders for speakers (if we have male and female, use this to refine)
    main_gender = detect_gender(main_speaker) if main_speaker else None
    guest_gender = detect_gender(guest_speaker) if guest_speaker else None
    has_gender_info = main_gender and guest_gender and main_gender != guest_gender
    
    # Track words for narrator detection (first four words of episode)
    word_count = 0
    narrator_words_complete = False
    
    # Process sentences with structure-aware logic
    last_speaker = None
    
    for i, sentence in enumerate(sentences):
        sentence = sentence.strip()
        if not sentence:
            continue
        
        speaker_found = None
        
        # Check if first four words are spoken by narrator (third person)
        if is_episode_start and not narrator_words_complete:
            words_in_sentence = len(re.findall(r'\b\w+\b', sentence))
            if word_count + words_in_sentence <= 4:
                # First four words are narrator
                speaker_found = "Narrator"
                word_count += words_in_sentence
                if word_count >= 4:
                    narrator_words_complete = True
            elif word_count < 4:
                # Partial sentence: first part is narrator, rest is not
                # Count how many words we need from this sentence
                words_needed = 4 - word_count
                # For simplicity, if we need most of the sentence, label as narrator
                if words_needed >= words_in_sentence * 0.5:
                    speaker_found = "Narrator"
                    word_count += words_in_sentence
                    narrator_words_complete = True
                else:
                    # Only first few words are narrator, rest is main speaker
                    # For simplicity, label entire sentence as narrator if we still need words
                    speaker_found = "Narrator"
                    word_count += words_in_sentence
                    narrator_words_complete = True
        
        # If narrator detection is complete or not applicable, proceed with normal logic
        if not speaker_found:
            # Phase 1: Introduction (before word review) - all main speaker
            if word_review_marker and i < word_review_marker:
                speaker_found = main_speaker
            
            # Phase 2: Word review section - usually main speaker
            elif word_review_marker and i == word_review_marker:
                speaker_found = main_speaker
            
            # Phase 3: Dialog section (after word review, before closing)
            elif word_review_marker and i > word_review_marker:
                # Check if this is closing
                if re.search(r'Gracias por escuchar|Gracias por acompañarme|Y así termina|Hasta pronto|Hasta la próxima', sentence, re.IGNORECASE):
                    speaker_found = main_speaker
                # Check for self-introduction
                elif re.search(rf'(?:Soy|soy|Me llamo|me llamo|Mi nombre es|mi nombre es)\s+(\w+)\b', sentence, re.IGNORECASE):
                    match = re.search(rf'(?:Soy|soy|Me llamo|me llamo|Mi nombre es|mi nombre es)\s+(\w+)\b', sentence, re.IGNORECASE)
                    intro_name = match.group(1) if match else None
                    if intro_name in speaker_names:
                        speaker_found = intro_name
                    else:
                        # Alternate from last speaker
                        speaker_found = guest_speaker if last_speaker == main_speaker else main_speaker
                # IMPORTANT: Check if sentence contains a question directed at someone by name
                # Pattern: "Name, ¿question" or "Name, question word" - the person being asked is NOT the speaker
                # Look for: Name followed by comma and question mark/question word (at start or early in sentence)
                elif any(re.search(rf'(?:^|\s){name},?\s*¿(?:por qué|qué|cómo|cuándo|dónde|cuál|quién)', sentence, re.IGNORECASE) or
                         re.search(rf'(?:^|\s){name},?\s*¿', sentence, re.IGNORECASE) or
                         re.search(rf'(?:^|\s){name},?\s*\?', sentence, re.IGNORECASE) or
                         re.search(rf'(?:^|\s){name},?\s+por qué', sentence, re.IGNORECASE)
                         for name in speaker_names):
                    # Find which name is being questioned
                    questioned_name = None
                    for name in speaker_names:
                        if (re.search(rf'(?:^|\s){name},?\s*¿(?:por qué|qué|cómo|cuándo|dónde|cuál|quién)', sentence, re.IGNORECASE) or
                            re.search(rf'(?:^|\s){name},?\s*¿', sentence, re.IGNORECASE) or
                            re.search(rf'(?:^|\s){name},?\s*\?', sentence, re.IGNORECASE) or
                            re.search(rf'(?:^|\s){name},?\s+por qué', sentence, re.IGNORECASE)):
                            questioned_name = name
                            break
                    # The person being questioned is NOT the speaker - the other person is speaking
                    if questioned_name:
                        speaker_found = guest_speaker if questioned_name == main_speaker else main_speaker
                    else:
                        speaker_found = guest_speaker if last_speaker == main_speaker else main_speaker
                # Check if addressing someone by name (without question mark)
                elif re.search(rf'(\w+),?\s+(?:cuéntanos|cuéntame|gracias|por qué|porque)', sentence, re.IGNORECASE):
                    # The person being addressed is NOT the speaker
                    match = re.search(rf'(\w+),?\s+(?:cuéntanos|cuéntame|gracias|por qué|porque)', sentence, re.IGNORECASE)
                    addressed_name = match.group(1) if match else None
                    if addressed_name in speaker_names:
                        # Other person is speaking
                        speaker_found = guest_speaker if addressed_name == main_speaker else main_speaker
                    else:
                        # Alternate
                        speaker_found = guest_speaker if last_speaker == main_speaker else main_speaker
                else:
                    # Use gender information if available to refine alternation
                    if has_gender_info and last_speaker:
                        # Check if sentence contains gender-specific words that might help
                        # (This is a simple heuristic - could be expanded)
                        current_gender = detect_gender(last_speaker)
                        # Alternate to the other speaker
                        if last_speaker == main_speaker:
                            speaker_found = guest_speaker if guest_speaker else main_speaker
                        else:
                            speaker_found = main_speaker
                    else:
                        # Alternate between main and guest
                        if last_speaker == main_speaker:
                            speaker_found = guest_speaker if guest_speaker else main_speaker
                        else:
                            speaker_found = main_speaker
        
        # Fallback: If no word review marker, use alternation
        else:
            # Check for self-introduction
            for name in speaker_names:
                if re.search(rf'(?:Soy|soy|Me llamo|me llamo|Mi nombre es|mi nombre es)\s+{name}\b', sentence, re.IGNORECASE):
                    speaker_found = name
                    break
            
            if not speaker_found:
                # Alternate
                if last_speaker:
                    other_speakers = [n for n in speaker_names if n != last_speaker]
                    speaker_found = other_speakers[0] if other_speakers else last_speaker
                else:
                    speaker_found = main_speaker
        
        # Update tracking
        last_speaker = speaker_found
        labeled_sentences.append((sentence, speaker_found))
    
    return labeled_sentences

def format_transcript_with_speakers(text, speaker_names=None, pre_labeled_sentences=None, audio_path=None, whisper_model=None, hf_token=None, is_episode_start=False):
    """
    Format transcript text with speaker identification.
    - Add proper spacing
    - Capitalize sentences
    - Add speaker labels
    - Add line breaks for better readability
    
    Args:
        text: The transcript text
        speaker_names: List of detected speaker names
        pre_labeled_sentences: Optional pre-labeled sentences (sentence, speaker) tuples
        audio_path: Optional path to audio file for audio-based diarization
        whisper_model: Optional Whisper model for word timestamps
        hf_token: Optional HuggingFace token for pyannote models
        is_episode_start: Whether this is the start of a new episode (for narrator detection)
    """
    # Use pre-labeled sentences if provided, otherwise identify speakers
    if pre_labeled_sentences:
        labeled_sentences = pre_labeled_sentences
    elif speaker_names:
        # Use combined audio + text identification if audio is available
        if audio_path and whisper_model:
            labeled_sentences = identify_speakers_with_audio(text, speaker_names, audio_path, whisper_model, hf_token)
            # Apply narrator detection to pre-labeled sentences if this is episode start
            if is_episode_start and labeled_sentences:
                word_count = 0
                narrator_words_complete = False
                updated_labeled_sentences = []
                for sentence, speaker in labeled_sentences:
                    if not narrator_words_complete:
                        words_in_sentence = len(re.findall(r'\b\w+\b', sentence))
                        if word_count + words_in_sentence <= 4:
                            updated_labeled_sentences.append((sentence, "Narrator"))
                            word_count += words_in_sentence
                            if word_count >= 4:
                                narrator_words_complete = True
                        elif word_count < 4:
                            words_needed = 4 - word_count
                            if words_needed >= words_in_sentence * 0.5:
                                updated_labeled_sentences.append((sentence, "Narrator"))
                                word_count += words_in_sentence
                                narrator_words_complete = True
                            else:
                                updated_labeled_sentences.append((sentence, speaker))
                                narrator_words_complete = True
                    else:
                        updated_labeled_sentences.append((sentence, speaker))
                labeled_sentences = updated_labeled_sentences
        else:
            labeled_sentences = identify_speakers(text, speaker_names, is_episode_start=is_episode_start)
    else:
        labeled_sentences = None
    
    if labeled_sentences:
        formatted_sentences = []
        
        for sentence, speaker in labeled_sentences:
            sentence = sentence.strip()
            if sentence:
                # Capitalize first letter
                sentence = sentence[0].upper() + sentence[1:] if len(sentence) > 1 else sentence.upper()
                # Add speaker label
                formatted_sentences.append(f"[{speaker}]: {sentence}")
        
        # Join with periods and newlines
        formatted_text = '.\n\n'.join(formatted_sentences)
        if formatted_text and not formatted_text.endswith('.'):
            formatted_text += '.'
    else:
        # Fallback to original formatting
        sentences = text.split('.')
        formatted_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                sentence = sentence[0].upper() + sentence[1:] if len(sentence) > 1 else sentence.upper()
                formatted_sentences.append(sentence)
        
        formatted_text = '.\n\n'.join(formatted_sentences)
        if formatted_text and not formatted_text.endswith('.'):
            formatted_text += '.'
    
    return formatted_text

def format_transcript(text):
    """
    Format transcript text to be more readable (without speaker labels).
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
    Check if transcript already exists for this audio file.
    Returns the transcript file path if found, None otherwise.
    """
    prefix = audio_path.stem
    transcript_filename = f"{prefix}_transcript.txt"
    transcript_path = output_dir / transcript_filename
    
    if transcript_path.exists():
        return transcript_path
    return None

def read_existing_transcript(transcript_path):
    """
    Read existing transcript file.
    Returns the transcript text content.
    """
    with open(transcript_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    return content

def transcribe_audio_file(audio_path, model, transcript_dir, grammar_tool, hf_token=None, openai_api_key=None):
    """
    Transcribe a single audio file, proofread, split into stories, and save.
    Checks for existing transcripts first.
    Uses both audio-based and text-based speaker identification for better accuracy.
    
    Supports:
    - OpenAI API (if openai_api_key provided) - preferred method
    - HuggingFace/pyannote (if hf_token provided) - fallback
    - Text-based only (if neither provided)
    """
    print(f"\n📻 Processing: {audio_path.name}")
    
    # Initialize variables
    english_narrator = None
    has_audio_for_diarization = False
    
    try:
        # Check if transcript already exists
        existing_transcript_path = check_existing_transcripts(audio_path, transcript_dir)
        
        if existing_transcript_path:
            print(f"   📄 Found existing transcript: {existing_transcript_path.name}")
            print("   ✅ Skipping - transcript already exists")
            return True
        else:
            # Transcribe the audio
            if model is None:
                print("   ❌ Error: No model provided and no existing transcripts found")
                return False
            
            # First, transcribe the beginning in English to capture narrator
            print("   Transcribing English narrator (beginning)...")
            english_narrator = transcribe_english_narrator(audio_path, model, start_time=0, duration=10)
            if english_narrator:
                print(f"   ✅ English narrator: {english_narrator[:100]}...")
            
            # Then transcribe the full audio in Spanish
            print("   Transcribing Spanish content...")
            result = model.transcribe(str(audio_path), language="es")
            transcript = result["text"]
            has_audio_for_diarization = True
        
        # Proofread the transcript (only Spanish parts)
        print("   Proofreading...")
        # Split transcript to proofread only Spanish parts
        if english_narrator or (transcript and re.search(r'(?:Section|Unit|Radio)\s+\d+', transcript, re.IGNORECASE)):
            # Extract English narrator and Spanish parts
            parts = re.split(r'((?:Section|Unit|Radio)\s+\d+[^.]*\.)', transcript, maxsplit=1, flags=re.IGNORECASE)
            if len(parts) >= 3:
                english_part = parts[0] + parts[1] if parts[0] or parts[1] else ""
                spanish_part = ''.join(parts[2:]) if len(parts) > 2 else transcript
                corrected_transcript = english_part + " " + proofread_spanish(spanish_part, grammar_tool)
            else:
                corrected_transcript = proofread_spanish(transcript, grammar_tool)
        else:
            corrected_transcript = proofread_spanish(transcript, grammar_tool)
        
        # Extract speaker names from transcript for better identification
        print("   Identifying speakers in transcript...")
        all_speaker_names = extract_speaker_names(corrected_transcript)
        if all_speaker_names:
            print(f"   ✅ Detected {len(all_speaker_names)} speaker(s) overall: {', '.join(all_speaker_names[:5])}{'...' if len(all_speaker_names) > 5 else ''}")
        else:
            print("   ⚠️  No speaker names detected, using generic labels")
        
        # Perform audio-based speaker diarization on full transcript FIRST (before splitting)
        # This provides speaker segments that help with episode boundary detection
        speaker_segments = None
        audio_duration = None
        full_transcript_labeled = None
        
        if has_audio_for_diarization:
            # Get audio duration
            audio_duration = get_audio_duration(audio_path)
            if audio_duration:
                print(f"   🎵 Audio duration: {audio_duration:.1f} seconds ({audio_duration/60:.1f} minutes)")
            
            # Try OpenAI API first (if available), then HuggingFace, then text-only
            openai_transcript, openai_segments = None, None
            if openai_api_key and OPENAI_API_AVAILABLE:
                print("   🎤 Using OpenAI API for transcription with speaker diarization...")
                openai_transcript, openai_segments = perform_speaker_diarization_openai(audio_path, openai_api_key)
                if openai_transcript and openai_segments:
                    print("   ✅ OpenAI API transcription with speaker diarization successful")
                    print(f"   ✅ OpenAI API diarization: {len(set(s[2] for s in openai_segments if s[2]))} speaker(s) detected")
                    speaker_segments = openai_segments
                    # Detect and preserve English narrator in OpenAI transcript
                    detected_english, spanish_part = detect_english_narrator_in_text(openai_transcript)
                    if detected_english:
                        openai_transcript = detected_english + " " + spanish_part
                    corrected_transcript = proofread_spanish(openai_transcript, grammar_tool)
                elif openai_transcript:
                    print("   ✅ OpenAI API transcription successful (no speaker labels)")
                    # Detect and preserve English narrator in OpenAI transcript
                    detected_english, spanish_part = detect_english_narrator_in_text(openai_transcript)
                    if detected_english:
                        openai_transcript = detected_english + " " + spanish_part
                    corrected_transcript = proofread_spanish(openai_transcript, grammar_tool)
            
            # Fallback to HuggingFace/pyannote if OpenAI didn't provide segments
            if not speaker_segments and hf_token and DIARIZATION_AVAILABLE and model:
                print("   🎤 Performing audio-based speaker diarization (HuggingFace)...")
                diarization_segments = perform_speaker_diarization(audio_path, hf_token)
                if diarization_segments:
                    # Convert to (start, end, speaker_id, text) format
                    speaker_segments = [(start, end, speaker, None) for start, end, speaker in diarization_segments]
                    print(f"   ✅ Audio diarization successful: {len(set(s[2] for s in speaker_segments if s[2]))} speaker(s) detected")
            
            # Get full transcript labels for later use
            if all_speaker_names:
                full_transcript_labeled = identify_speakers_with_audio(
                    corrected_transcript, 
                    all_speaker_names, 
                    audio_path, 
                    model, 
                    hf_token,
                    openai_api_key
                )
                if full_transcript_labeled:
                    print("   ✅ Full transcript labeled with speakers")
        
        # Split into episodes using improved heuristic-based approach
        # Uses pattern-based, duration-based, and speaker-based heuristics
        print("   Detecting episode boundaries using patterns, duration, and speaker changes...")
        episodes = split_by_episode_patterns(
            corrected_transcript,
            audio_path=audio_path if has_audio_for_diarization else None,
            speaker_segments=speaker_segments,
            audio_duration=audio_duration
        )
        if episodes:
            print(f"   ✅ Split into {len(episodes)} episode(s) using improved heuristics")
            
            # Report estimated durations if available
            if audio_duration:
                chars_per_second_calc = len(corrected_transcript) / audio_duration
                for i, episode in enumerate(episodes, 1):
                    ep_duration = len(episode) / chars_per_second_calc
                    print(f"      Episode {i}: ~{ep_duration:.1f} seconds ({ep_duration/60:.1f} minutes)")
        else:
            # Fallback to content-based splitting
            print("   Pattern-based splitting not applicable, using content-based splitting...")
            episodes = split_by_content(corrected_transcript)
        
        # Process each episode: identify speakers and format
        stories = []
        for episode_idx, episode in enumerate(episodes):
            # For each episode, transcribe English narrator at the beginning
            episode_english_narrator = None
            if has_audio_for_diarization and model:
                # Transcribe first few seconds in English for narrator
                try:
                    # Get episode start time (approximate)
                    if audio_duration:
                        chars_per_second = len(corrected_transcript) / audio_duration
                        # Find where this episode starts in the full transcript
                        episode_start_char = corrected_transcript.find(episode[:100])
                        if episode_start_char >= 0:
                            episode_start_time = episode_start_char / chars_per_second
                            # Transcribe 5-10 seconds in English
                            episode_english_narrator = transcribe_english_narrator(
                                audio_path, model, start_time=episode_start_time, duration=8
                            )
                except Exception as e:
                    pass  # If English transcription fails, continue without it
            
            # Also try to detect English narrator in the episode text
            detected_english, spanish_episode = detect_english_narrator_in_text(episode)
            
            # Use separately transcribed English if available, otherwise use detected
            if episode_english_narrator:
                # Clean up the English narrator text
                episode_english_narrator = episode_english_narrator.strip()
                if episode_english_narrator and not episode_english_narrator.endswith('.'):
                    episode_english_narrator += '.'
            elif detected_english:
                episode_english_narrator = detected_english
                episode = spanish_episode
            
            # Extract speaker names for this specific episode
            episode_speaker_names = extract_speaker_names(episode)
            if not episode_speaker_names:
                episode_speaker_names = all_speaker_names  # Use global names if episode-specific not found
            
            # Check if episode needs further splitting (e.g., multiple stories in one episode)
            hints = detect_english_hints(episode)
            if hints:
                # Split episode by hints
                episode_stories = split_by_english_hints(episode, hints)
                # Add English narrator to first story only
                if episode_english_narrator and episode_stories:
                    episode_stories[0] = episode_english_narrator + " " + episode_stories[0]
                stories.extend(episode_stories)
            else:
                # Keep episode as single story, prepend English narrator if available
                if episode_english_narrator:
                    episode = episode_english_narrator + " " + episode
                stories.append(episode)
        
        print(f"   Final split: {len(stories)} episode(s)")
        
        # Extract prefix from audio filename (remove extension)
        prefix = audio_path.stem
        
        # If we have full transcript labels from audio, extract relevant sentences for each story
        # Create a mapping from full transcript to story segments
        full_sentences = re.split(r'[.!?]+\s+', corrected_transcript)
        
        # Prepare content for single transcript file
        transcript_content_parts = []
        separator = "=" * 80  # 80 '=' characters as separator
        first_episode_preview = None
        
        for i, story in enumerate(stories, 1):
            # Extract speaker names for this story
            story_speaker_names = extract_speaker_names(story)
            if not story_speaker_names:
                story_speaker_names = all_speaker_names  # Use global names if story-specific not found
            
            # If we have audio-based labels, extract the relevant portion for this story
            story_labeled_sentences = None
            if full_transcript_labeled:
                # Find which sentences from full transcript belong to this story
                story_sentences = re.split(r'[.!?]+\s+', story)
                story_labeled_sentences = []
                story_sentence_idx = 0
                
                for full_sentence, full_speaker in full_transcript_labeled:
                    if story_sentence_idx < len(story_sentences):
                        story_sentence = story_sentences[story_sentence_idx].strip()
                        full_sentence_clean = full_sentence.strip()
                        # Check if this full sentence matches the story sentence
                        if story_sentence and full_sentence_clean and story_sentence.lower() in full_sentence_clean.lower():
                            story_labeled_sentences.append((story_sentence, full_speaker))
                            story_sentence_idx += 1
                        elif not story_sentence:
                            story_sentence_idx += 1
                
                # If alignment didn't work perfectly, fall back to text-based
                if len(story_labeled_sentences) < len(story_sentences) * 0.5:
                    story_labeled_sentences = None
            
            # Check if story starts with English narrator
            english_narrator_text = None
            spanish_story = story
            
            # Detect English narrator at the beginning
            detected_english, spanish_part = detect_english_narrator_in_text(story)
            if detected_english:
                english_narrator_text = detected_english
                spanish_story = spanish_part
            
            # Format the Spanish story with speaker labels
            # Pass is_episode_start=True for each episode to detect narrator (first four words)
            formatted_story = format_transcript_with_speakers(
                spanish_story, 
                story_speaker_names,
                pre_labeled_sentences=story_labeled_sentences,
                is_episode_start=True  # Each episode starts with narrator (first four words)
            )
            
            # Prepend English narrator if found
            if english_narrator_text:
                # Format English narrator with [Narrator] label
                english_narrator_formatted = f"[Narrator]: {english_narrator_text.strip()}"
                formatted_story = english_narrator_formatted + "\n\n" + formatted_story
            
            # Store first episode for preview
            if i == 1:
                first_episode_preview = formatted_story
            
            # Add episode separator and content
            if i > 1:
                # Add separator before episode (except first one)
                transcript_content_parts.append(separator)
            transcript_content_parts.append(formatted_story)
        
        # Save single transcript file with all episodes
        # File naming: {audio_filename}_transcript.txt
        transcript_filename = f"{prefix}_transcript.txt"
        transcript_path = transcript_dir / transcript_filename
        
        with open(transcript_path, 'w', encoding='utf-8') as f:
            # Write all episodes with separators
            f.write('\n\n'.join(transcript_content_parts))
            f.write('\n')
        
        print(f"   ✅ Saved transcript: {transcript_filename}")
        print(f"      Total episodes: {len(stories)}")
        
        if first_episode_preview:
            print(f"   📝 Preview of episode 1:\n{first_episode_preview[:200]}...\n")
        
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
    transcript_dir = radios_dir / "transcript"
    
    if not radios_dir.exists():
        print(f"❌ Directory not found: {radios_dir}")
        sys.exit(1)
    
    # Create transcript directory if it doesn't exist
    transcript_dir.mkdir(exist_ok=True)
    
    # Find all m4a files
    audio_files = list(radios_dir.glob("*.m4a"))
    
    if not audio_files:
        print(f"❌ No .m4a files found in {radios_dir}")
        sys.exit(1)
    
    print(f"🎯 Found {len(audio_files)} audio file(s)")
    
    # Check which files need transcription
    files_needing_transcription = []
    for audio_file in audio_files:
        existing = check_existing_transcripts(audio_file, transcript_dir)
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
    
    # Get API keys for speaker diarization (optional)
    # Priority: OpenAI API > HuggingFace > Text-only
    openai_api_key = os.environ.get('OPENAI_API_KEY')
    hf_token = os.environ.get('HUGGINGFACE_TOKEN') or os.environ.get('HF_TOKEN')
    
    # Inform user about available options
    if openai_api_key and OPENAI_API_AVAILABLE:
        print("\n✅ OpenAI API key detected - will use OpenAI for speaker diarization")
    elif hf_token and DIARIZATION_AVAILABLE:
        print("\n✅ HuggingFace token detected - will use pyannote.audio for speaker diarization")
    elif not openai_api_key and not hf_token:
        print("\n💡 Tip: Set API key for audio-based speaker diarization:")
        print("   Option 1 (Recommended): Set OPENAI_API_KEY for OpenAI API")
        print("      Get key from: https://platform.openai.com/api-keys")
        print("   Option 2: Set HUGGINGFACE_TOKEN for HuggingFace (free)")
        print("      Get token from: https://huggingface.co/settings/tokens")
        print("   Audio diarization will be disabled without API key\n")
    
    # Process each audio file (save transcripts in transcript subfolder)
    success_count = 0
    for audio_file in audio_files:
        if transcribe_audio_file(audio_file, model, transcript_dir, grammar_tool, hf_token, openai_api_key):
            success_count += 1
    
    print(f"\n{'='*60}")
    print(f"✨ Transcription complete!")
    print(f"   Processed: {success_count}/{len(audio_files)} files")
    print(f"   Transcripts saved in: {transcript_dir}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()

