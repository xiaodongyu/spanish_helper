# Token Reuse Guide: Using API Tokens Across Modules

This guide explains how to reuse your HuggingFace and OpenAI API tokens across multiple modules in the Spanish Helper project.

---

## Quick Answer

**✅ YES - You can reuse the same tokens in all modules!**

Since tokens are stored as **environment variables** in `~/.bashrc`, they're available globally to all Python scripts and modules in your project.

---

## How It Works

### Environment Variables Are Global

When you set tokens in `~/.bashrc`:
```bash
export HUGGINGFACE_TOKEN=hf_...
export OPENAI_API_KEY=sk-...
```

These become **environment variables** that are available to:
- ✅ All Python scripts
- ✅ All modules in your project
- ✅ Any terminal session (after sourcing ~/.bashrc)
- ✅ Any subprocess or script you run

---

## How to Access Tokens in Any Module

### Method 1: Using `os.environ.get()` (Recommended)

This is the standard way to access environment variables in Python:

```python
import os

# Get HuggingFace token
hf_token = os.environ.get('HUGGINGFACE_TOKEN')
# or with fallback
hf_token = os.environ.get('HUGGINGFACE_TOKEN') or os.environ.get('HF_TOKEN')

# Get OpenAI API key
openai_key = os.environ.get('OPENAI_API_KEY')

# Check if tokens are available
if hf_token:
    print("✅ HuggingFace token found")
    # Use the token
else:
    print("❌ HuggingFace token not set")

if openai_key:
    print("✅ OpenAI API key found")
    # Use the key
else:
    print("❌ OpenAI API key not set")
```

### Method 2: Direct Access (with error handling)

```python
import os

try:
    hf_token = os.environ['HUGGINGFACE_TOKEN']
except KeyError:
    print("HUGGINGFACE_TOKEN not set")
    hf_token = None
```

### Method 3: Using `os.getenv()` (Alternative)

```python
import os

hf_token = os.getenv('HUGGINGFACE_TOKEN')
openai_key = os.getenv('OPENAI_API_KEY')
```

---

## Example: New Module Using Tokens

Here's how you'd use tokens in a new module (e.g., `vocabulary_extractor.py`):

```python
#!/usr/bin/env python3
"""
Vocabulary extractor module - extracts Spanish vocabulary from transcripts.
Uses OpenAI API for advanced processing if available.
"""

import os
from pathlib import Path

# Get API tokens (reused from ~/.bashrc)
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
HUGGINGFACE_TOKEN = os.environ.get('HUGGINGFACE_TOKEN')

def extract_vocabulary(transcript_path):
    """Extract vocabulary from transcript."""
    
    # Check if OpenAI API is available
    if OPENAI_API_KEY:
        print("✅ Using OpenAI API for advanced vocabulary extraction")
        # Use OpenAI API for processing
        # ... your code here ...
    else:
        print("⚠️  OpenAI API key not set, using local processing")
        # Fallback to local processing
        # ... your code here ...
    
    # Check if HuggingFace token is available
    if HUGGINGFACE_TOKEN:
        print("✅ HuggingFace token available for additional features")
        # Use HuggingFace models if needed
        # ... your code here ...

def main():
    # Tokens are automatically available from environment
    print(f"OpenAI key set: {OPENAI_API_KEY is not None}")
    print(f"HuggingFace token set: {HUGGINGFACE_TOKEN is not None}")
    
    # Your module logic here
    # ...

if __name__ == "__main__":
    main()
```

---

## Current Implementation (transcribe_audio.py)

Looking at how `transcribe_audio.py` accesses tokens:

```python
# From transcribe_audio.py (lines 1150-1151)
openai_api_key = os.environ.get('OPENAI_API_KEY')
hf_token = os.environ.get('HUGGINGFACE_TOKEN') or os.environ.get('HF_TOKEN')
```

**You can use the exact same pattern in any module!**

---

## Best Practices for Token Reuse

### ✅ DO:

1. **Use `os.environ.get()` with fallback:**
   ```python
   hf_token = os.environ.get('HUGGINGFACE_TOKEN') or os.environ.get('HF_TOKEN')
   ```

2. **Check if tokens exist before using:**
   ```python
   if openai_key:
       # Use OpenAI API
   else:
       # Fallback to local processing
   ```

3. **Provide helpful messages:**
   ```python
   if not hf_token:
       print("💡 Tip: Set HUGGINGFACE_TOKEN for enhanced features")
   ```

4. **Use consistent variable names:**
   - `HUGGINGFACE_TOKEN` or `HF_TOKEN` for HuggingFace
   - `OPENAI_API_KEY` for OpenAI

### ❌ DON'T:

1. **Don't hardcode tokens in code:**
   ```python
   # ❌ BAD
   hf_token = "hf_your_token_here"
   ```

2. **Don't commit tokens to git:**
   - Always use environment variables
   - Never put real tokens in code files

3. **Don't assume tokens are always set:**
   ```python
   # ❌ BAD - will crash if token not set
   hf_token = os.environ['HUGGINGFACE_TOKEN']
   
   # ✅ GOOD - handles missing token gracefully
   hf_token = os.environ.get('HUGGINGFACE_TOKEN')
   ```

---

## Token Availability Across Modules

### Module 1: transcribe_audio.py
```python
hf_token = os.environ.get('HUGGINGFACE_TOKEN')
openai_key = os.environ.get('OPENAI_API_KEY')
# ✅ Tokens available
```

### Module 2: vocabulary_extractor.py (future)
```python
hf_token = os.environ.get('HUGGINGFACE_TOKEN')
openai_key = os.environ.get('OPENAI_API_KEY')
# ✅ Same tokens available (reused!)
```

### Module 3: quiz_generator.py (future)
```python
hf_token = os.environ.get('HUGGINGFACE_TOKEN')
openai_key = os.environ.get('OPENAI_API_KEY')
# ✅ Same tokens available (reused!)
```

**All modules share the same tokens from `~/.bashrc`!**

---

## Verification: Check Token Availability

You can verify tokens are available in any module:

```python
import os

print("Token Status:")
print(f"  HUGGINGFACE_TOKEN: {'✅ Set' if os.environ.get('HUGGINGFACE_TOKEN') else '❌ Not set'}")
print(f"  OPENAI_API_KEY: {'✅ Set' if os.environ.get('OPENAI_API_KEY') else '❌ Not set'}")
```

Or use the existing helper script:
```bash
./setup_tokens.sh
```

---

## Common Use Cases

### Use Case 1: OpenAI API in Multiple Modules

**transcribe_audio.py:**
```python
openai_key = os.environ.get('OPENAI_API_KEY')
# Uses OpenAI for transcription
```

**vocabulary_extractor.py:**
```python
openai_key = os.environ.get('OPENAI_API_KEY')
# Uses OpenAI for vocabulary analysis
```

**Same token, different modules!**

### Use Case 2: HuggingFace Token for Different Models

**transcribe_audio.py:**
```python
hf_token = os.environ.get('HUGGINGFACE_TOKEN')
# Uses pyannote models for speaker diarization
```

**word_frequency.py (future):**
```python
hf_token = os.environ.get('HUGGINGFACE_TOKEN')
# Uses different HuggingFace models for word analysis
```

**Same token, different models!**

---

## Token Sharing Benefits

1. **Single Setup:** Set tokens once in `~/.bashrc`, use everywhere
2. **Consistency:** All modules use the same tokens
3. **Easy Management:** Update tokens in one place (`~/.bashrc`)
4. **No Duplication:** Don't need separate tokens per module
5. **Security:** Tokens stay in environment variables (not in code)

---

## Troubleshooting

### "Token not found in new module"

**Problem:** Module can't access tokens

**Solution:**
1. Verify tokens are in `~/.bashrc`:
   ```bash
   grep HUGGINGFACE_TOKEN ~/.bashrc
   grep OPENAI_API_KEY ~/.bashrc
   ```

2. Source bashrc in your terminal:
   ```bash
   source ~/.bashrc
   ```

3. Check in Python:
   ```python
   import os
   print(os.environ.get('HUGGINGFACE_TOKEN'))
   ```

### "Token works in one module but not another"

**Problem:** Inconsistent token access

**Solution:**
- Make sure you're using `os.environ.get()` in both modules
- Verify both modules are run in the same terminal session
- Check for typos in environment variable names

---

## Summary

**✅ YES - Reuse tokens across all modules!**

- Tokens in `~/.bashrc` are available globally
- Use `os.environ.get('TOKEN_NAME')` in any module
- Same tokens work for all modules
- No need to set tokens per module
- Single source of truth: `~/.bashrc`

**Example pattern for any module:**
```python
import os

# Get tokens (reused from ~/.bashrc)
hf_token = os.environ.get('HUGGINGFACE_TOKEN')
openai_key = os.environ.get('OPENAI_API_KEY')

# Use tokens in your module
if hf_token:
    # Use HuggingFace
    pass

if openai_key:
    # Use OpenAI
    pass
```

---

**Last Updated:** 2026-01-09
