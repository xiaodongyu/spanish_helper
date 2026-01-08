# Step-by-Step Setup Guide: Hybrid Option (HuggingFace + OpenAI)

This guide will help you set up both HuggingFace (free speaker diarization) and OpenAI API (better transcription) for the hybrid approach.

---

## Part 1: HuggingFace Setup (Free Speaker Diarization)

### Step 1: Create HuggingFace Account

1. Go to: https://huggingface.co/join
2. Sign up (free account)
3. Verify your email if needed

### Step 2: Get Your Access Token

1. Go to: https://huggingface.co/settings/tokens
2. Click **"New token"**
3. Name it: `spanish_helper_diarization` (or any name you like)
4. Select **"Read"** access (that's all you need)
5. Click **"Generate token"**
6. **COPY THE TOKEN** - you'll need it in a moment!
   - It looks like: `hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - ⚠️ **Important**: You can only see it once! Copy it now.

### Step 3: Accept Model Terms (Required)

HuggingFace requires you to accept terms for the models we use. You need to accept terms for **2 models**:

#### Model 1: pyannote/speaker-diarization-3.1
1. Go to: https://huggingface.co/pyannote/speaker-diarization-3.1
2. Click **"Agree and access repository"** button
3. Accept the terms

#### Model 2: pyannote/segmentation-3.0
1. Go to: https://huggingface.co/pyannote/segmentation-3.0
2. Click **"Agree and access repository"** button
3. Accept the terms

✅ **Done with HuggingFace!** Now let's set up OpenAI.

---

## Part 2: OpenAI API Setup (Better Transcription)

### Step 1: Create OpenAI Account

1. Go to: https://platform.openai.com/signup
2. Sign up (or log in if you have an account)
3. Verify your email/phone if needed

### Step 2: Add Payment Method (Required)

⚠️ **Note**: OpenAI API is paid, but very affordable:
- ~$0.006-0.06 per minute of audio
- ~$0.15-0.60 per hour of audio

1. Go to: https://platform.openai.com/account/billing
2. Click **"Add payment method"**
3. Add your credit card
4. Set a usage limit if you want (optional, recommended: $5-10)

### Step 3: Get Your API Key

1. Go to: https://platform.openai.com/api-keys
2. Click **"Create new secret key"**
3. Name it: `spanish_helper` (or any name)
4. Click **"Create secret key"**
5. **COPY THE KEY** - you'll need it now!
   - It looks like: `sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - ⚠️ **Important**: You can only see it once! Copy it now.

✅ **Done with OpenAI!** Now let's configure everything.

---

## Part 3: Configure Environment Variables

You need to set both tokens as environment variables. Choose one method:

### Option A: Temporary (Current Session Only)

Run these commands in your terminal:

```bash
export HUGGINGFACE_TOKEN=hf_your_token_here
export OPENAI_API_KEY=sk-your_key_here
```

⚠️ **Note**: These will be lost when you close the terminal.

### Option B: Permanent (Recommended)

Add to your shell configuration file so they persist:

**For Bash** (most Linux systems):
```bash
echo 'export HUGGINGFACE_TOKEN=hf_your_token_here' >> ~/.bashrc
echo 'export OPENAI_API_KEY=sk-your_key_here' >> ~/.bashrc
source ~/.bashrc
```

**For Zsh** (if you use zsh):
```bash
echo 'export HUGGINGFACE_TOKEN=hf_your_token_here' >> ~/.zshrc
echo 'export OPENAI_API_KEY=sk-your_key_here' >> ~/.zshrc
source ~/.zshrc
```

**Replace**:
- `hf_your_token_here` with your actual HuggingFace token
- `sk-your_key_here` with your actual OpenAI API key

---

## Part 4: Verify Setup

Let's test that everything is configured correctly:

```bash
# Check if tokens are set
echo "HuggingFace token: ${HUGGINGFACE_TOKEN:0:10}..."  # Shows first 10 chars
echo "OpenAI key: ${OPENAI_API_KEY:0:10}..."  # Shows first 10 chars
```

If you see your tokens (first 10 characters), you're good to go! ✅

---

## Part 5: Test the Script

Now run the transcription script:

```bash
python transcribe_audio.py
```

You should see:
- ✅ OpenAI API key detected
- ✅ HuggingFace token detected
- The script will use OpenAI for transcription and HuggingFace for speaker diarization

---

## Troubleshooting

### "HuggingFace token not found"
- Make sure you exported the token: `export HUGGINGFACE_TOKEN=...`
- Check spelling: `HUGGINGFACE_TOKEN` (not `HUGGING_FACE_TOKEN`)
- Restart your terminal or run `source ~/.bashrc`

### "OpenAI API key not found"
- Make sure you exported the key: `export OPENAI_API_KEY=...`
- Check spelling: `OPENAI_API_KEY` (not `OPENAI_KEY`)
- Restart your terminal or run `source ~/.bashrc`

### "Model access denied" (HuggingFace)
- Make sure you accepted terms for both models:
  - https://huggingface.co/pyannote/speaker-diarization-3.1
  - https://huggingface.co/pyannote/segmentation-3.0

### "OpenAI API error: insufficient_quota"
- Check your billing: https://platform.openai.com/account/billing
- Make sure you added a payment method
- Check if you hit your usage limit

### "Module not found: pyannote" or "Module not found: openai"
- Install dependencies: `pip install -r requirements.txt`

---

## What Happens Next?

Once set up, the script will:
1. **Use OpenAI API** for transcription (better quality text)
2. **Use HuggingFace** for speaker diarization (free speaker identification)
3. **Combine both** for best results!

---

## Cost Estimate

For typical usage (10 episodes, ~10 minutes each = 100 minutes total):
- **HuggingFace**: $0 (free!)
- **OpenAI**: ~$0.60-6.00 (depending on model)
- **Total**: ~$0.60-6.00 for 100 minutes of audio

Very affordable for learning Spanish! 🎉
