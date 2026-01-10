# Module Summary: transcribe_audio.py - Duolingo Radio Transcription

**Module:** `transcribe_audio.py`  
**Date Created:** 2026-01-08  
**Source:** Chat history from previous development session  
**Purpose:** Comprehensive summary of transcription module features, decisions, and implementation details

---

## Project Overview

A Python tool for transcribing Spanish audio files from Duolingo radio episodes with advanced features including:
- High-quality Spanish transcription using OpenAI Whisper
- Automatic speaker identification (hybrid audio + text-based)
- Grammar correction and proofreading
- Smart episode/story splitting
- Support for multiple API backends (OpenAI, HuggingFace)

---

## Key Features & Evolution

### Phase 1: Basic Transcription (Initial Implementation)
- **Goal:** Transcribe Spanish .m4a audio files to readable text
- **Technology:** OpenAI Whisper (base model)
- **Output:** Single transcript file per audio file
- **File naming:** `transcript_{audio_filename}.txt`

### Phase 2: Enhanced Formatting & Proofreading
- **Added:** Grammar correction using LanguageTool (Spanish)
- **Requirements:** Java >= 17 (optional, script continues without it)
- **Features:**
  - Automatic proofreading of Spanish text
  - Proper sentence capitalization
  - Improved formatting with proper spacing

### Phase 3: Story/Episode Splitting
- **Added:** Automatic splitting of long transcripts into multiple stories
- **Methods:**
  1. **Primary:** Pattern-based detection using fixed episode structures
     - Introduction patterns
     - Word review sections ("Pero primero, estas son algunas palabras...")
     - Closing patterns ("Gracias por escuchar... Hasta pronto.")
  2. **Fallback:** English hint words detection (e.g., "section 1", "radio 2")
  3. **Secondary:** Content-based splitting using program introductions
- **Output format:** `transcript_{prefix}_{number}.txt` (e.g., `transcript_audio_1.txt`, `transcript_audio_2.txt`)

### Phase 4: Speaker Identification (Hybrid Approach)
- **Text-based identification:**
  - Episode structure awareness (before word review = main speaker, etc.)
  - Pattern detection ("Soy María", "Me llamo Carlos")
  - Question detection ("Mateo, ¿por qué..." → Mateo is NOT speaking)
  - Gender information usage
- **Audio-based diarization:**
  - **HuggingFace/pyannote.audio** (free option)
    - Uses voice characteristics to separate speakers
    - Requires: HuggingFace token + accepting model terms
    - Models: pyannote/speaker-diarization-3.1, pyannote/segmentation-3.0
  - **OpenAI API** (paid, higher accuracy)
    - Better transcription quality
    - Can combine with diarization
    - Costs: ~$0.006-0.06 per minute
- **Hybrid approach:** Combines both audio and text methods for best accuracy
- **Output format:** Labels sentences with speaker names (e.g., "[Sari]: Hola, ¿cómo estás?")

### Phase 5: Smart Processing & Optimization
- **Existing transcript detection:**
  - Checks for existing transcripts before transcribing
  - Reads and combines existing files if found
  - Skips time-consuming transcription step
- **Lazy model loading:**
  - Whisper model only loaded when transcription is needed
  - Saves memory and startup time
- **Transcript directory:**
  - Output saved to `Duolinguo/radios/transcript/` subfolder
  - Organized file structure

---

## Technical Architecture

### Dependencies
```
openai-whisper>=20231117  # Local Whisper transcription
torch>=2.0.0              # PyTorch backend
language-tool-python>=2.7.1  # Grammar checking (requires Java >= 17)
pyannote.audio>=3.1.0     # Speaker diarization (optional, requires HuggingFace token)
pyannote.core>=5.0.0      # Core utilities for pyannote
openai>=1.0.0             # OpenAI API client (optional)
```

### System Requirements
- **Python:** 3.8+
- **ffmpeg:** Required for audio processing
- **Java:** >= 17 (optional, for grammar checking)
- **API Keys (optional):**
  - `OPENAI_API_KEY` - For OpenAI transcription/diarization
  - `HUGGINGFACE_TOKEN` - For free speaker diarization

### Project Structure
```
spanish_helper/
├── Duolinguo/
│   └── radios/
│       ├── *.m4a                    # Input audio files
│       └── transcript/              # Output transcripts
│           └── transcript_{prefix}_{number}.txt
├── notes/
│   ├── transcribe_audio_CHAT_HISTORY.md  # Full chat history
│   ├── transcribe_audio_SUMMARY.md       # This file (detailed summary)
│   └── transcribe_audio_CONTEXT.md       # Quick reference
├── transcribe_audio.py              # Main script
├── requirements.txt                 # Python dependencies
├── setup_tokens.sh                  # Token setup helper
├── README.md                        # User documentation
├── SETUP_GUIDE.md                   # Detailed setup instructions
├── API_COMPARISON.md                # HuggingFace vs OpenAI comparison
└── LICENSE                          # MIT License
```

---

## Key Design Decisions

### 1. Transcription Backend Priority
- **Priority order:** OpenAI API > Local Whisper > Error
- **Reasoning:** OpenAI provides better accuracy, local Whisper is fallback

### 2. Speaker Identification Strategy
- **Hybrid approach:** Combines audio-based (pyannote/OpenAI) + text-based patterns
- **Fallback chain:** Audio diarization → Text patterns → Generic labels
- **Reasoning:** Each method has strengths; combining provides best accuracy

### 3. Episode Splitting Methodology
- **Primary:** Pattern-based (fixed episode structures)
- **Fallback:** English hint words
- **Secondary:** Content-based splitting
- **Reasoning:** Duolingo radio has consistent structure; patterns are most reliable

### 4. File Organization
- **Separate transcript folder:** Keeps outputs organized
- **Numbered files:** Easy to identify and process sequentially
- **Naming convention:** `transcript_{audio_prefix}_{story_number}.txt`

### 5. Error Handling & User Experience
- **Graceful degradation:** Script continues without optional components (Java, API keys)
- **Clear messaging:** Informative warnings and tips for setup
- **Existing file handling:** Reuses transcripts to avoid redundant work

---

## API Setup Details

### HuggingFace Setup (Free Speaker Diarization)
1. Create account at https://huggingface.co/join
2. Get token from https://huggingface.co/settings/tokens (Read access)
3. Accept model terms:
   - https://huggingface.co/pyannote/speaker-diarization-3.1
   - https://huggingface.co/pyannote/segmentation-3.0
4. Set environment variable: `export HUGGINGFACE_TOKEN=hf_...`

### OpenAI API Setup (Better Transcription)
1. Create account at https://platform.openai.com/signup
2. Add payment method at https://platform.openai.com/account/billing
3. Get API key from https://platform.openai.com/api-keys
4. Set environment variable: `export OPENAI_API_KEY=sk-...`
5. **Cost:** ~$0.006-0.06 per minute (~$0.15-0.60 per hour)

### Hybrid Approach Benefits
- **Best of both worlds:**
  - OpenAI for high-quality transcription
  - HuggingFace for free speaker diarization
- **Cost effective:** Only pay for transcription, not diarization
- **Privacy:** Speaker identification happens locally

---

## Workflow Summary

### Standard Processing Flow
1. **Check existing transcripts** → If found, read and skip transcription
2. **Load Whisper model** (only if transcription needed)
3. **Transcribe audio** (if needed) using Whisper or OpenAI API
4. **Proofread transcript** using LanguageTool (if Java available)
5. **Detect episode boundaries** using pattern-based approach
6. **Split into stories** based on patterns/hints/content
7. **Identify speakers** using hybrid approach (audio + text)
8. **Format and label** transcripts with speaker names
9. **Save numbered files** to transcript folder

### Error Handling & Warnings
- Missing Java → Continues without grammar checking
- Missing API keys → Uses text-based speaker identification only
- Missing ffmpeg → Script will fail (required for audio processing)
- Model download issues → Clear error messages

---

## Performance Characteristics

### Processing Times (Estimated)
- **Transcription:** 1-5 minutes per 10-minute audio (depends on model/hardware)
- **Speaker diarization (HuggingFace):** 2-5 minutes per 10-minute audio
- **Speaker diarization (OpenAI):** 30-60 seconds per 10-minute audio
- **Grammar checking:** Minimal overhead (seconds)
- **Episode splitting:** Near-instant

### Accuracy Estimates
- **Transcription (Local Whisper):** 90-95%
- **Transcription (OpenAI):** 95-99%
- **Speaker ID (Text-based):** 70-85%
- **Speaker ID (Audio-based):** 85-95%
- **Speaker ID (Hybrid):** 90-98%

---

## Key Functions & Methods

### Core Functions
- `transcribe_audio_file()` - Main processing function
- `split_by_episode_patterns()` - Pattern-based episode detection
- `split_by_english_hints()` - English hint word detection
- `split_by_content()` - Content-based fallback splitting
- `identify_speakers_with_audio()` - Audio-based diarization wrapper
- `identify_speakers_text_based()` - Text pattern-based identification
- `extract_speaker_names()` - Extract names from dialogue
- `format_transcript_with_speakers()` - Format output with labels
- `proofread_spanish()` - Grammar correction
- `check_existing_transcripts()` - Find existing transcript files
- `read_existing_transcripts()` - Read and combine existing files

### Helper Functions
- `detect_english_hints()` - Find English section markers
- `format_transcript()` - Basic text formatting
- `detect_episode_intro()` - Detect episode introductions

---

## Development History

### Major Milestones
1. **Initial implementation** - Basic Whisper transcription
2. **Formatting improvements** - Better text formatting and capitalization
3. **Grammar checking** - LanguageTool integration
4. **Story splitting** - Multi-file output support
5. **Speaker identification** - Text-based patterns
6. **Audio diarization** - HuggingFace/pyannote.audio integration
7. **OpenAI API support** - Cloud-based transcription option
8. **Hybrid approach** - Combining multiple methods
9. **Smart processing** - Existing file detection and reuse
10. **Documentation** - Comprehensive guides and setup instructions

### Known Issues & Limitations
- Java 11 installed but LanguageTool requires Java >= 17
- torchcodec warnings (non-critical, script still works)
- Some speaker identification edge cases with rapid dialogue

---

## Future Enhancement Ideas

### Potential Improvements
1. **Better speaker name extraction** - More robust pattern matching
2. **Episode metadata** - Extract and save episode numbers, titles
3. **Transcript merging** - Combine multiple audio files into single transcript
4. **Export formats** - Support for SRT, VTT subtitle formats
5. **Batch processing** - Process multiple files more efficiently
6. **Configuration file** - YAML/JSON config for settings
7. **Progress indicators** - Better progress bars for long operations
8. **Error recovery** - Resume interrupted transcriptions

---

## Usage Examples

### Basic Usage
```bash
# Place audio files in Duolinguo/radios/
python3 transcribe_audio.py
```

### With API Keys (Hybrid)
```bash
export OPENAI_API_KEY=sk-...
export HUGGINGFACE_TOKEN=hf_...
python3 transcribe_audio.py
```

### Check Token Setup
```bash
./setup_tokens.sh
```

---

## Important Notes

1. **Privacy:** Audio files processed locally (unless using OpenAI API)
2. **Costs:** Only OpenAI API has costs; HuggingFace is completely free
3. **Requirements:** ffmpeg is mandatory; Java and API keys are optional
4. **File naming:** Script automatically handles naming; don't manually rename output files
5. **Existing transcripts:** Script will reuse existing transcripts; delete them to re-transcribe

---

## References

- **Full Chat History:** `notes/transcribe_audio_CHAT_HISTORY.md` (41,831 lines)
- **Quick Reference:** `notes/transcribe_audio_CONTEXT.md`
- **Setup Guide:** `SETUP_GUIDE.md`
- **API Comparison:** `API_COMPARISON.md`
- **User Documentation:** `README.md`
- **Original Chat:** Exported from Cursor on 2026-01-08

---

**Last Updated:** 2026-01-08  
**Maintainer:** Project owner  
**Status:** Active development / Production ready
