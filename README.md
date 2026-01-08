# Spanish Helper - Duolinguo Radio Transcription

A Python tool to transcribe Spanish audio files from Duolinguo radio episodes, with automatic speaker identification, proofreading, and story splitting capabilities.

## Features

- 🎙️ **Audio Transcription**: Uses OpenAI Whisper for high-quality Spanish transcription
- 👥 **Advanced Speaker Identification**: Combines audio-based and text-based methods for high accuracy
  - **Audio-based diarization**: Uses pyannote.audio (HuggingFace) to identify speakers from voice characteristics
  - **OpenAI API support**: Can use OpenAI API for transcription (more accurate), then apply diarization
  - **Text-based patterns**: Detects speaker names from dialogue (e.g., "Soy María", "Me llamo Carlos")
  - **Hybrid approach**: Combines both methods for best results
  - **Episode structure awareness**: Uses fixed episode patterns to refine identification
  - **Question detection**: Identifies when someone is being questioned (e.g., "Mateo, ¿por qué...")
  - **Gender detection**: Uses gender information when available
- ✍️ **Grammar Correction**: Automatic proofreading using LanguageTool (requires Java)
- 📚 **Smart Episode Splitting**: Automatically splits transcripts into episodes
  - **Pattern-based splitting**: Uses fixed episode patterns (intro, word review, dialog, closing) to detect boundaries
  - Detects English hint words (section/radio numbers) as fallback
  - Falls back to content-based splitting using program introductions
- 💾 **Smart Processing**: Skips transcription if transcripts already exist
- 📝 **Formatted Output**: Clean, readable transcripts with proper capitalization and spacing

## Requirements

- Python 3.8+
- ffmpeg (for audio processing)
- Java (optional, for grammar checking with LanguageTool)
- **API Key for Audio Diarization** (choose one):
  - **Option 1 (Recommended)**: OpenAI API key
    - Get from: https://platform.openai.com/api-keys
    - Set: `export OPENAI_API_KEY=your_key_here`
    - Provides high-quality transcription + can combine with diarization
  - **Option 2**: HuggingFace token (free)
    - Get from: https://huggingface.co/settings/tokens
    - Set: `export HUGGINGFACE_TOKEN=your_token_here`
    - Requires accepting model terms (see setup guide)

## Installation

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Install ffmpeg

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html) or use:
```bash
choco install ffmpeg
```

**Using Conda:**
```bash
conda install -c conda-forge ffmpeg
```

### 3. Set up API Key for Audio Diarization (optional, but recommended)

Choose **ONE** of the following options:

#### Option A: OpenAI API (Easiest Setup)

**Note**: OpenAI API provides high-quality transcription but **not speaker diarization**. 
For speaker diarization, you'll still need HuggingFace (Option B) or rely on text-based identification.

1. Get your OpenAI API key:
   - Go to: https://platform.openai.com/api-keys
   - Click "Create new secret key"
   - Copy the key (starts with `sk-...`)

2. Set the environment variable:
   ```bash
   export OPENAI_API_KEY=sk-your_key_here
   ```

3. **That's it!** No model terms to accept.

**Note**: 
- OpenAI API has usage costs (~$0.006 per minute). Check pricing: https://openai.com/pricing
- For best speaker identification, combine with HuggingFace token (Option B)

#### Option B: HuggingFace (Free, but requires setup)

For improved speaker identification accuracy, you can enable audio-based speaker diarization:

1. Create a HuggingFace account: https://huggingface.co/join
2. Get your access token: https://huggingface.co/settings/tokens
3. Accept the terms for pyannote models:
   - https://huggingface.co/pyannote/speaker-diarization-3.1 (click "Agree and access repository")
   - https://huggingface.co/pyannote/segmentation-3.0 (click "Agree and access repository")
4. Set the token as an environment variable:
   ```bash
   export HUGGINGFACE_TOKEN=your_token_here
   ```
   Or add to your `~/.bashrc` or `~/.zshrc` for persistence.

**Note**: Audio diarization will automatically be used if the token is available. Without it, the script falls back to text-based identification only.

### 4. Install Java (optional, for grammar checking)

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install default-jdk
```

**macOS:**
```bash
brew install openjdk
```

**Windows:**
Download from [Adoptium](https://adoptium.net/) or use:
```bash
choco install openjdk
```

## Usage

1. Place your `.m4a` audio files in the `Duolinguo/radios/` directory

2. Run the transcription script:
```bash
python transcribe_audio.py
```

3. Transcripts will be saved in the `Duolinguo/radios/transcript/` folder with the format:
   - `transcript_{audio_filename}_{story_number}.txt`

## How It Works

1. **Transcription**: Uses Whisper's base model to transcribe Spanish audio
2. **Episode Detection**: 
   - **Primary method**: Uses fixed episode patterns to detect boundaries:
     - Introduction: Main speaker says hello and introduces theme/guest
     - Word review: "Pero primero, estas son algunas palabras..." (marks start of dialog)
     - Closing: "Gracias por escuchar... Hasta pronto." (marks end of episode)
   - **Fallback methods**: 
     - Detects English hint words (e.g., "section 1", "radio 2")
     - Splits based on program introduction patterns
3. **Speaker Identification** (Hybrid Approach):
   - **Audio-based diarization** (if HuggingFace token provided):
     - Uses pyannote.audio to separate speakers by voice characteristics
     - Aligns speaker segments with transcript using word-level timestamps
     - Provides accurate speaker identification even when text patterns are unclear
   - **OpenAI API transcription** (if OpenAI API key provided):
     - Uses OpenAI's Whisper API for high-quality transcription
     - More accurate than local Whisper model
     - Still uses text-based or HuggingFace diarization for speaker identification
   - **Text-based identification** (always used, primary method if no audio diarization):
     - Uses episode structure to identify speakers:
       - All text before word review = main speaker
       - Word review section = main speaker
       - Dialog section = alternates between main speaker and guest
       - Closing = main speaker
     - Detects questions directed at someone (e.g., "Mateo, ¿por qué..." → Mateo is NOT speaking)
     - Uses gender information when available
   - **Combined approach**: Merges audio and text results for best accuracy
   - Labels sentences with speaker names (e.g., "[Sari]: Hola, ¿cómo estás?")
4. **Proofreading**: Applies grammar corrections using LanguageTool (if Java is installed)
5. **Output**: Saves each episode/story as a separate, formatted text file with speaker labels

## Project Structure

```
spanish_helper/
├── Duolinguo/
│   └── radios/          # Place your .m4a files here
│       └── transcript/  # Transcripts are saved here
├── transcribe_audio.py   # Main transcription script
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Notes

- The script automatically checks for existing transcripts and skips transcription if found
- Whisper model is only loaded when transcription is needed
- If Java is not installed, the script will continue without grammar correction
- Transcripts are formatted with proper sentence capitalization and spacing

## Troubleshooting

**"No such file or directory: 'ffmpeg'"**
- Install ffmpeg using the instructions above

**"No java install detected"**
- Install Java for grammar checking, or the script will continue without it

**"pyannote.audio not available"**
- Install with: `pip install pyannote.audio pyannote.core`
- Note: Requires HuggingFace token for model access

**"Speaker diarization failed"**
- Check that your HuggingFace token is set correctly: `echo $HUGGINGFACE_TOKEN`
- Verify you've accepted the terms for pyannote models on HuggingFace
- The script will fall back to text-based identification if diarization fails

**Model download is slow**
- The Whisper model (~139MB) downloads on first use. Subsequent runs are faster.

## License

MIT License - feel free to use and modify as needed.
