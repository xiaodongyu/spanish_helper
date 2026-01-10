# Spanish Helper

A Python toolkit for processing and learning from Spanish Duolingo radio episodes. Multiple modules work together to provide transcription, vocabulary extraction, and language learning features.

## Overview

Spanish Helper consists of multiple independent modules that can be used together or separately:

- 🎙️ **transcribe_audio.py** - Transcribe Spanish audio files with speaker identification
- 📚 *(More modules coming soon...)*

Each module is self-contained and can be used independently or combined with others.

---

## Modules

### 🎙️ transcribe_audio.py - Audio Transcription

**Purpose:** Transcribe Spanish audio files from Duolingo radio episodes with automatic speaker identification, proofreading, and story splitting.

**Key Features:**
- High-quality Spanish transcription using OpenAI Whisper
- Advanced speaker identification (audio-based + text-based hybrid approach)
- Automatic grammar correction using LanguageTool
- Smart episode/story splitting
- Skips re-transcription if transcripts already exist

**Quick Start:**
```bash
python transcribe_audio.py
```

**Documentation:**
- **Quick Reference:** [notes/transcribe_audio_CONTEXT.md](notes/transcribe_audio_CONTEXT.md)
- **Detailed Summary:** [notes/transcribe_audio_SUMMARY.md](notes/transcribe_audio_SUMMARY.md)
- **Development History:** [notes/transcribe_audio_CHAT_HISTORY.md](notes/transcribe_audio_CHAT_HISTORY.md)

**Requirements:**
- Python 3.8+
- ffmpeg (for audio processing)
- Java >= 17 (optional, for grammar checking)
- OpenAI API key or HuggingFace token (optional, for speaker diarization)

---

## Project Requirements

### Core Requirements (All Modules)
- **Python:** 3.8+
- **ffmpeg:** For audio processing (required by transcription module)

### Optional Requirements (Module-Specific)
- **Java >= 17:** For grammar checking (transcription module)
- **API Keys:** 
  - `OPENAI_API_KEY` - For OpenAI transcription/diarization (transcription module)
  - `HUGGINGFACE_TOKEN` - For free speaker diarization (transcription module)

### Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install ffmpeg:**
   ```bash
   # Linux (Ubuntu/Debian)
   sudo apt-get install ffmpeg
   
   # macOS
   brew install ffmpeg
   
   # Windows
   choco install ffmpeg
   ```

3. **Set up API keys (optional):**
   See [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed instructions.

4. **Install Java >= 17 (optional, for grammar checking):**
   ```bash
   # Linux (Ubuntu/Debian)
   sudo apt-get install openjdk-17-jdk
   
   # macOS
   brew install openjdk
   ```

---

## Project Structure

```
spanish_helper/
├── Duolinguo/
│   └── radios/                  # Audio files directory
│       └── transcript/          # Generated transcripts
├── notes/                       # Module documentation
│   ├── README.md               # Documentation organization guide
│   ├── WORKFLOW_GUIDE.md       # Development workflow guide
│   ├── {module}_SUMMARY.md     # Module summaries
│   ├── {module}_CONTEXT.md     # Module quick references
│   └── {module}_CHAT_HISTORY.md # Module development histories
├── transcribe_audio.py          # Transcription module
├── requirements.txt             # Python dependencies
├── setup_tokens.sh              # Token setup helper
├── README.md                    # This file (project overview)
├── SETUP_GUIDE.md               # Setup instructions
├── API_COMPARISON.md            # API comparison guide
└── LICENSE                      # MIT License
```

---

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   sudo apt-get install ffmpeg  # or equivalent for your OS
   ```

2. **Set up API keys (optional but recommended):**
   ```bash
   # See SETUP_GUIDE.md for detailed instructions
   export OPENAI_API_KEY=sk-...
   export HUGGINGFACE_TOKEN=hf_...
   ```

3. **Use a module:**
   ```bash
   # Transcription module
   python transcribe_audio.py
   ```

---

## Documentation

### Project-Level Documentation
- **[README.md](README.md)** - Project overview (this file)
- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Detailed setup instructions
- **[API_COMPARISON.md](API_COMPARISON.md)** - HuggingFace vs OpenAI comparison
- **[notes/README.md](notes/README.md)** - Module documentation organization
- **[notes/WORKFLOW_GUIDE.md](notes/WORKFLOW_GUIDE.md)** - Development workflow guide

### Module-Specific Documentation
Each module has its own documentation in the `notes/` directory:
- `{module}_SUMMARY.md` - Comprehensive module summary
- `{module}_CONTEXT.md` - Quick reference guide
- `{module}_CHAT_HISTORY.md` - Development history

**Current Modules:**
- **transcribe_audio:** See [notes/transcribe_audio_CONTEXT.md](notes/transcribe_audio_CONTEXT.md)

---

## Adding New Modules

When adding a new module to this project:

1. **Start a new chat session** for the module (keeps histories separate)
2. **Create module file** (e.g., `new_module.py`)
3. **Develop module** in focused chat session
4. **Export chat history** as `notes/{module}_CHAT_HISTORY.md`
5. **Generate documentation:**
   - `notes/{module}_SUMMARY.md` - Detailed summary
   - `notes/{module}_CONTEXT.md` - Quick reference
6. **Update this README.md** - Add module to "Modules" section
7. **Update `notes/README.md`** - Add module to documentation list

See [notes/WORKFLOW_GUIDE.md](notes/WORKFLOW_GUIDE.md) for detailed workflow instructions.

---

## Troubleshooting

### Common Issues

**"No such file or directory: 'ffmpeg'"**
- Install ffmpeg using the installation instructions above

**"Java too old for LanguageTool"**
- Install Java >= 17: `sudo apt-get install openjdk-17-jdk`

**"API key not found"**
- Check environment variables: `echo $OPENAI_API_KEY`, `echo $HUGGINGFACE_TOKEN`
- See [SETUP_GUIDE.md](SETUP_GUIDE.md) for setup instructions

**Module-specific issues:**
- Check module-specific documentation in `notes/{module}_CONTEXT.md`
- See module troubleshooting sections

---

## Contributing

This is a personal learning project. However, suggestions and improvements are welcome!

### Development Workflow

1. Each module should be developed in its own chat session
2. Export chat history regularly during development
3. Generate SUMMARY and CONTEXT files from chat history
4. Update documentation when adding features

See [notes/WORKFLOW_GUIDE.md](notes/WORKFLOW_GUIDE.md) for detailed guidelines.

---

## License

MIT License - feel free to use and modify as needed.

---

## Project Status

**Current Version:** Multi-module architecture (WIP)

**Modules:**
- ✅ `transcribe_audio.py` - Stable and feature-complete
- 🔜 More modules coming soon...

**Future Modules (Ideas):**
- Vocabulary extractor from transcripts
- Quiz generator from vocabulary
- Word frequency analysis
- Grammar pattern extraction

---

**Last Updated:** 2026-01-09
