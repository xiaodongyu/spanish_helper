# Module Context: transcribe_audio.py - Quick Reference

**Module:** `transcribe_audio.py`  
**Created:** 2026-01-08  
**Purpose:** Quick reference for transcription module - for future conversations and development

---

## What This Module Does

Transcribes Spanish Duolingo radio audio files (.m4a) with:
- ✅ High-quality transcription (OpenAI Whisper or OpenAI API)
- ✅ Automatic speaker identification (hybrid: audio + text)
- ✅ Grammar correction (LanguageTool, optional)
- ✅ Smart episode/story splitting (pattern-based)
- ✅ Organized output files (`transcript_{prefix}_{number}.txt`)

---

## Current Project State

### Files & Structure
```
spanish_helper/
├── Duolinguo/radios/
│   ├── *.m4a                          # Input audio
│   └── transcript/                    # Output transcripts
├── transcribe_audio.py                # This module (866 lines)
├── requirements.txt                   # Dependencies (includes transcription deps)
├── notes/
│   ├── transcribe_audio_CHAT_HISTORY.md  # Full chat history (41,831 lines)
│   ├── transcribe_audio_SUMMARY.md       # Detailed summary (this module)
│   └── transcribe_audio_CONTEXT.md       # Quick reference (this file)
├── README.md                           # Project-level documentation
├── SETUP_GUIDE.md                      # Setup instructions
├── API_COMPARISON.md                   # HuggingFace vs OpenAI comparison
└── setup_tokens.sh                     # Token setup helper
```

### Current Status
- ✅ **Dependencies:** Installed (whisper, torch, pyannote, openai, language-tool)
- ✅ **ffmpeg:** Installed (v4.4.2)
- ⚠️ **Java:** v11 installed, but LanguageTool requires >= 17 (grammar checking disabled)
- ❌ **API Keys:** Not set (using local Whisper only, text-based speaker ID)

### Script Capabilities
- ✅ Transcribes Spanish audio
- ✅ Splits into stories/episodes
- ✅ Uses existing transcripts (skips re-transcription)
- ⚠️ Speaker identification: Text-based only (no audio diarization without API keys)
- ❌ Grammar checking: Disabled (Java 11, needs 17+)

---

## Key Features & Implementation

### 1. Transcription Backends (Priority Order)
1. **OpenAI API** (if `OPENAI_API_KEY` set) - Best accuracy, paid
2. **Local Whisper** (default) - Good accuracy, free, slower

### 2. Speaker Identification (Hybrid Approach)
- **Audio-based:** Requires `HUGGINGFACE_TOKEN` (free) or `OPENAI_API_KEY` (paid)
- **Text-based:** Always used, detects patterns like "Soy María", "Me llamo Carlos"
- **Episode structure:** Uses intro/word review/dialog/closing patterns
- **Question detection:** "Mateo, ¿por qué..." → Mateo is NOT speaking

### 3. Episode/Story Splitting
- **Primary:** Pattern-based (fixed episode structures)
- **Fallback 1:** English hint words ("section 1", "radio 2")
- **Fallback 2:** Content-based (program introductions)

### 4. Smart Processing
- Checks for existing transcripts before transcribing
- Reuses existing files to skip transcription
- Lazy loading: Only loads Whisper model when needed

---

## Quick Setup Checklist

### Required
- [x] Python 3.8+
- [x] ffmpeg (for audio processing)
- [x] Dependencies installed (`pip install -r requirements.txt`)

### Optional (but recommended)
- [ ] Java >= 17 (for grammar checking with LanguageTool)
- [ ] `OPENAI_API_KEY` (for better transcription)
- [ ] `HUGGINGFACE_TOKEN` (for free speaker diarization)

### To Enable Grammar Checking
```bash
sudo apt install openjdk-17-jdk  # Upgrade from Java 11 to 17+
```

### To Enable Hybrid Approach
```bash
export OPENAI_API_KEY=sk-...          # Get from platform.openai.com/api-keys
export HUGGINGFACE_TOKEN=hf_...       # Get from huggingface.co/settings/tokens
# Add to ~/.bashrc for persistence
```

---

## Common Tasks

### Run Transcription
```bash
python3 transcribe_audio.py
```

### Check Token Setup
```bash
./setup_tokens.sh
```

### Verify Setup
```bash
python3 -c "import whisper; import openai; import pyannote.audio; print('✅ OK')"
ffmpeg -version
java -version  # Should be >= 17 for grammar checking
echo $OPENAI_API_KEY  # Check if set
echo $HUGGINGFACE_TOKEN  # Check if set
```

---

## Key Functions Reference

### Main Functions
- `transcribe_audio_file()` - Main processing (checks existing, transcribes, splits, labels)
- `split_by_episode_patterns()` - Pattern-based episode detection
- `identify_speakers_with_audio()` - Audio diarization wrapper
- `identify_speakers_text_based()` - Text pattern identification
- `format_transcript_with_speakers()` - Format output with speaker labels

### Helper Functions
- `check_existing_transcripts()` - Find existing files
- `read_existing_transcripts()` - Read and combine existing files
- `proofread_spanish()` - Grammar correction
- `extract_speaker_names()` - Extract names from dialogue

---

## Important Design Decisions

1. **Separate transcript folder** - Keeps outputs organized
2. **Numbered files** - Easy sequential processing (`transcript_prefix_1.txt`, `_2.txt`, etc.)
3. **Existing file reuse** - Skips redundant transcription
4. **Graceful degradation** - Works without optional components (Java, API keys)
5. **Hybrid speaker ID** - Combines audio + text for best accuracy

---

## Known Issues

1. **Java version mismatch** - Java 11 installed, LanguageTool needs >= 17
   - **Impact:** Grammar checking disabled
   - **Fix:** Upgrade to Java 17+ (`sudo apt install openjdk-17-jdk`)

2. **torchcodec warnings** - Non-critical, script still works
   - **Impact:** Warning messages about torchcodec compatibility
   - **Fix:** None needed (fallback works)

3. **No API keys set** - Only text-based speaker identification active
   - **Impact:** Lower speaker identification accuracy (no audio diarization)
   - **Fix:** Set `HUGGINGFACE_TOKEN` (free) or `OPENAI_API_KEY` (paid)

---

## Recent Development

### From Chat History (41,831 lines)
1. Initial basic transcription → Enhanced formatting
2. Added grammar checking → Story splitting
3. Added speaker identification → Audio diarization support
4. Added OpenAI API support → Hybrid approach
5. Added smart processing → Existing file reuse
6. Added comprehensive documentation → Setup guides

### Current Implementation
- **File size:** transcribe_audio.py is 866 lines (complex, feature-rich)
- **Dependencies:** All major features implemented
- **Documentation:** Comprehensive (README, SETUP_GUIDE, API_COMPARISON)

---

## Next Steps / Potential Enhancements

1. **Upgrade Java to 17+** - Enable grammar checking
2. **Set up API keys** - Enable hybrid approach for better accuracy
3. **Test with multiple audio files** - Verify batch processing
4. **Consider enhancements:**
   - Subtitle export (SRT, VTT)
   - Episode metadata extraction
   - Batch processing improvements
   - Configuration file support

---

## Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| "ffmpeg not found" | `sudo apt install ffmpeg` |
| "Java too old" | `sudo apt install openjdk-17-jdk` |
| "No API keys" | Set `OPENAI_API_KEY` and/or `HUGGINGFACE_TOKEN` |
| "torchcodec warning" | Ignore (non-critical) |
| "Grammar check failed" | Install Java 17+ |
| "Speaker ID not working" | Set `HUGGINGFACE_TOKEN` (free) |

---

**Last Updated:** 2026-01-08  
**Use Case:** Personal Spanish learning tool for Duolingo radio transcripts
