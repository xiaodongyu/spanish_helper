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

def split_by_episode_patterns(text):
    """
    Split transcript into episodes based on fixed patterns in Duolinguo radio episodes.
    Each episode has:
    1. Introduction: Main speaker says hello and introduces theme/guest
    2. Word review: "Pero primero, estas son algunas palabras..." (before dialog)
    3. Dialog: Conversation between main speaker and guest
    4. Closing: "Gracias por escuchar... Hasta pronto."
    
    Returns:
        List of episode texts
    """
    episodes = []
    
    # Pattern for episode closing (marks end of episode)
    closing_patterns = [
        r'Gracias por escuchar[^.]*\.\s*Hasta (pronto|la próxima)\.',
        r'Gracias por acompañarme[^.]*\.\s*Hasta (pronto|la próxima)\.',
        r'Y así termina[^.]*\.\s*Recuerda[^.]*\.\s*Hasta pronto\.',
        r'¡Ah! Gracias por escuchar[^.]*\.\s*Nos vemos pronto\.',
    ]
    
    # Find all closing markers
    split_points = [0]  # Start with beginning
    
    for pattern in closing_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            # Find the end of the closing sentence
            end_pos = match.end()
            # Look for next sentence start or new episode intro
            next_text = text[end_pos:end_pos+200]
            # Check if there's a new episode intro nearby
            if re.search(r'Hola.*bienvenida|Te doy.*bienvenida|Soy \w+ y', next_text, re.IGNORECASE):
                split_points.append(end_pos)
            else:
                # Also split at closing if it's followed by substantial text
                if len(text[end_pos:].strip()) > 100:
                    split_points.append(end_pos)
    
    # Also look for episode introductions (new episode starts)
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
            # Only add if it's not at the very beginning and not already a split point
            if pos > 50:
                # Check if this is far enough from existing split points
                is_new_split = True
                for existing_split in split_points:
                    if abs(pos - existing_split) < 100:
                        is_new_split = False
                        break
                if is_new_split:
                    split_points.append(pos)
    
    # Remove duplicates and sort
    split_points = sorted(set(split_points))
    
    # Split the text into episodes
    for i in range(len(split_points)):
        start = split_points[i]
        end = split_points[i + 1] if i + 1 < len(split_points) else len(text)
        episode = text[start:end].strip()
        
        # Only add if episode is substantial (at least 100 characters)
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
    Uses gpt-4o-transcribe-diarize model which provides both transcription and speaker labels.
    
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
            try:
                transcript = client.audio.transcriptions.create(
                    model="gpt-4o-transcribe-diarize",
                    file=audio_file,
                    language="es",
                    response_format="verbose_json"
                )
            except Exception as e:
                # Fallback to whisper-1 if gpt-4o-transcribe-diarize not available
                print(f"   ⚠️  gpt-4o-transcribe-diarize not available, using whisper-1: {str(e)}")
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
        
        if hasattr(transcript, 'segments'):
            for segment in transcript.segments:
                start = segment.get('start', 0)
                end = segment.get('end', 0)
                text = segment.get('text', '').strip()
                speaker = segment.get('speaker', None)  # Available in gpt-4o-transcribe-diarize
                
                if text:
                    full_text += text + " "
                    labeled_segments.append((start, end, speaker, text))
        elif hasattr(transcript, 'text'):
            # Fallback: just text, no segments
            full_text = transcript.text
        
        return full_text.strip(), labeled_segments
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
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=hf_token
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

def identify_speakers(text, speaker_names):
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
    
    # Process sentences with structure-aware logic
    last_speaker = None
    
    for i, sentence in enumerate(sentences):
        sentence = sentence.strip()
        if not sentence:
            continue
        
        speaker_found = None
        
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

def format_transcript_with_speakers(text, speaker_names=None, pre_labeled_sentences=None, audio_path=None, whisper_model=None, hf_token=None):
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
    """
    # Use pre-labeled sentences if provided, otherwise identify speakers
    if pre_labeled_sentences:
        labeled_sentences = pre_labeled_sentences
    elif speaker_names:
        # Use combined audio + text identification if audio is available
        if audio_path and whisper_model:
            labeled_sentences = identify_speakers_with_audio(text, speaker_names, audio_path, whisper_model, hf_token)
        else:
            labeled_sentences = identify_speakers(text, speaker_names)
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
    
    try:
        # Check if transcripts already exist
        existing_transcripts = check_existing_transcripts(audio_path, transcript_dir)
        has_audio_for_diarization = False
        
        if existing_transcripts:
            print(f"   📄 Found {len(existing_transcripts)} existing transcript file(s)")
            print("   Reading existing transcripts...")
            transcript = read_existing_transcripts(existing_transcripts)
            print("   ✅ Using existing transcripts (skipping transcription)")
            # Audio file still available for diarization even if transcript exists
            has_audio_for_diarization = audio_path.exists() and model is not None
        else:
            # Transcribe the audio
            if model is None:
                print("   ❌ Error: No model provided and no existing transcripts found")
                return False
            print("   Transcribing...")
            result = model.transcribe(str(audio_path), language="es")
            transcript = result["text"]
            has_audio_for_diarization = True
        
        # Proofread the transcript
        print("   Proofreading...")
        corrected_transcript = proofread_spanish(transcript, grammar_tool)
        
        # Split into episodes using pattern-based approach (not speaker-based)
        print("   Detecting episode boundaries using patterns...")
        episodes = split_by_episode_patterns(corrected_transcript)
        if episodes:
            print(f"   ✅ Split into {len(episodes)} episode(s) based on episode patterns")
        else:
            # Fallback to content-based splitting
            print("   Pattern-based splitting not applicable, using content-based splitting...")
            episodes = split_by_content(corrected_transcript)
        
        # Extract speaker names from each episode for better identification
        print("   Identifying speakers in each episode...")
        all_speaker_names = extract_speaker_names(corrected_transcript)
        if all_speaker_names:
            print(f"   ✅ Detected {len(all_speaker_names)} speaker(s) overall: {', '.join(all_speaker_names[:5])}{'...' if len(all_speaker_names) > 5 else ''}")
        else:
            print("   ⚠️  No speaker names detected, using generic labels")
        
        # Perform audio-based speaker diarization on full transcript (once)
        full_transcript_labeled = None
        if has_audio_for_diarization:
            # Try OpenAI API first (if available), then HuggingFace, then text-only
            full_transcript_labeled = identify_speakers_with_audio(
                corrected_transcript, 
                all_speaker_names, 
                audio_path, 
                model, 
                hf_token,
                openai_api_key
            )
            if full_transcript_labeled:
                print("   ✅ Audio diarization completed, will be combined with text-based identification")
            # If OpenAI was used, update transcript
            if openai_api_key and OPENAI_API_AVAILABLE:
                # Check if OpenAI provided a better transcript
                openai_transcript, _ = perform_speaker_diarization_openai(audio_path, openai_api_key)
                if openai_transcript:
                    corrected_transcript = proofread_spanish(openai_transcript, grammar_tool)
        
        # Process each episode: identify speakers and format
        stories = []
        for episode in episodes:
            # Extract speaker names for this specific episode
            episode_speaker_names = extract_speaker_names(episode)
            if not episode_speaker_names:
                episode_speaker_names = all_speaker_names  # Use global names if episode-specific not found
            
            # Check if episode needs further splitting (e.g., multiple stories in one episode)
            hints = detect_english_hints(episode)
            if hints:
                # Split episode by hints
                episode_stories = split_by_english_hints(episode, hints)
                stories.extend(episode_stories)
            else:
                # Keep episode as single story
                stories.append(episode)
        
        print(f"   Final split: {len(stories)} story/stories")
        
        # Extract prefix from audio filename (remove extension)
        prefix = audio_path.stem
        
        # If we have full transcript labels from audio, extract relevant sentences for each story
        # Create a mapping from full transcript to story segments
        full_sentences = re.split(r'[.!?]+\s+', corrected_transcript)
        
        # Save each story
        saved_files = []
        first_story_preview = None
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
            
            # Format the story with speaker labels
            formatted_story = format_transcript_with_speakers(
                story, 
                story_speaker_names,
                pre_labeled_sentences=story_labeled_sentences
            )
            
            # Store first story for preview
            if i == 1:
                first_story_preview = formatted_story
            
            # Create output filename: transcript_{prefix}_{number}.txt
            output_filename = f"transcript_{prefix}_{i}.txt"
            output_path = transcript_dir / output_filename
            
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

