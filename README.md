# Spanish Helper - Duolinguo Radio Transcription

A Python tool to transcribe Spanish audio files from Duolinguo radio episodes, with automatic proofreading and story splitting capabilities.

## Features

- 🎙️ **Audio Transcription**: Uses OpenAI Whisper for high-quality Spanish transcription
- ✍️ **Grammar Correction**: Automatic proofreading using LanguageTool (requires Java)
- 📚 **Story Splitting**: Automatically splits transcripts into multiple stories
  - Detects English hint words (section/radio numbers) to split by
  - Falls back to content-based splitting using program introductions
- 💾 **Smart Processing**: Skips transcription if transcripts already exist
- 📝 **Formatted Output**: Clean, readable transcripts with proper capitalization and spacing

## Requirements

- Python 3.8+
- ffmpeg (for audio processing)
- Java (optional, for grammar checking with LanguageTool)

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

### 3. Install Java (optional, for grammar checking)

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

3. Transcripts will be saved in the same folder with the format:
   - `transcript_{audio_filename}_{story_number}.txt`

## How It Works

1. **Transcription**: Uses Whisper's base model to transcribe Spanish audio
2. **Proofreading**: Applies grammar corrections using LanguageTool (if Java is installed)
3. **Story Detection**: 
   - First tries to find English hint words (e.g., "section 1", "radio 2")
   - If none found, splits based on program introduction patterns
4. **Output**: Saves each story as a separate, formatted text file

## Project Structure

```
spanish_helper/
├── Duolinguo/
│   └── radios/          # Place your .m4a files here
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

**Model download is slow**
- The Whisper model (~139MB) downloads on first use. Subsequent runs are faster.

## License

MIT License - feel free to use and modify as needed.
