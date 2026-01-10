# Token Backup and Recovery Guide

This guide explains how to securely backup your API tokens for recovery purposes.

---

## Current Token Storage

Your tokens are currently stored in:
- **Location:** `~/.bashrc` (your home directory)
- **Status:** Active in terminal sessions (after `source ~/.bashrc`)
- **Security:** Safe from being pushed to GitHub (outside project directory)

---

## Should You Backup Tokens?

**✅ YES - Recommended!** Backing up tokens is useful for:
- Recovering if you accidentally delete `~/.bashrc`
- Setting up on a new machine/laptop
- Recovering if you lose access to your account temporarily
- Quick reference without logging into accounts

---

## Secure Backup Options

### Option 1: Encrypted Local File (Recommended)

Create a secure, encrypted backup file:

```bash
# Create a secure backup file (encrypted)
cd ~/Documents  # or wherever you keep backups
nano tokens_backup.txt

# Add your tokens (encrypted with a password):
HUGGINGFACE_TOKEN=hf_your_token_here
OPENAI_API_KEY=sk-your_key_here

# Encrypt the file
gpg -c tokens_backup.txt
# Enter a strong password when prompted

# Remove unencrypted version
rm tokens_backup.txt

# Now you have: tokens_backup.txt.gpg (encrypted)
```

**To decrypt later:**
```bash
gpg -d tokens_backup.txt.gpg > tokens_backup.txt
```

### Option 2: Password Manager (Best Practice)

Store tokens in a password manager:
- **1Password**, **LastPass**, **Bitwarden**, **KeePass**
- Create entries:
  - "Spanish Helper - HuggingFace Token"
  - "Spanish Helper - OpenAI API Key"
- Tags: `api-keys`, `spanish-helper`, `development`

**Benefits:**
- ✅ Encrypted by default
- ✅ Sync across devices (if using cloud service)
- ✅ Easy to retrieve
- ✅ Can generate secure passwords too

### Option 3: Secure Notes File (Simple)

Create a simple encrypted notes file:

```bash
# Using a password-protected archive
zip -e ~/Documents/spanish_helper_tokens.zip ~/.bashrc
# Enter password when prompted

# Or use 7zip with encryption
7z a -p ~/Documents/spanish_helper_tokens.7z ~/.bashrc
```

### Option 4: Print/Save to Secure Location (Physical)

If you prefer non-digital backup:
- Print tokens and store in a locked drawer/safe
- Write in a password-protected notebook
- Store in a secure location at home

**⚠️ Warning:** Physical backups are less secure if lost/stolen

---

## What Information to Backup

### Essential Information:

```
HUGGINGFACE_TOKEN=hf_your_token_here
OPENAI_API_KEY=sk-your_key_here

# Additional helpful info:
- Where to regenerate tokens:
  - HuggingFace: https://huggingface.co/settings/tokens
  - OpenAI: https://platform.openai.com/api-keys
- Account emails/username
- Creation dates
- Purpose: Spanish Helper project
```

---

## Recovery Methods

### Method 1: From Backup File

If you have an encrypted backup:
```bash
# Decrypt backup
gpg -d tokens_backup.txt.gpg > tokens_backup.txt

# Read tokens and add to ~/.bashrc
cat tokens_backup.txt >> ~/.bashrc

# Remove unencrypted file
rm tokens_backup.txt

# Reload bashrc
source ~/.bashrc
```

### Method 2: From Password Manager

1. Open your password manager
2. Search for "Spanish Helper" or "API Keys"
3. Copy tokens
4. Add to `~/.bashrc` or use as environment variables

### Method 3: Regenerate (If Lost)

If you can't recover tokens, regenerate them:

**HuggingFace:**
1. Go to: https://huggingface.co/settings/tokens
2. Delete old token (if needed)
3. Create new token
4. Accept model terms again (if needed)

**OpenAI:**
1. Go to: https://platform.openai.com/api-keys
2. Revoke old key (if needed for security)
3. Create new key
4. Update `~/.bashrc`

---

## Quick Backup Script

You can create a simple backup script:

```bash
#!/bin/bash
# Backup tokens from ~/.bashrc

BACKUP_DIR="$HOME/Documents/backups"
mkdir -p "$BACKUP_DIR"

# Extract tokens from ~/.bashrc
grep -E "(HUGGINGFACE_TOKEN|OPENAI_API_KEY)" ~/.bashrc > "$BACKUP_DIR/tokens_$(date +%Y%m%d).txt"

# Encrypt backup (requires GPG)
if command -v gpg &> /dev/null; then
    gpg -c "$BACKUP_DIR/tokens_$(date +%Y%m%d).txt"
    rm "$BACKUP_DIR/tokens_$(date +%Y%m%d).txt"
    echo "✅ Encrypted backup created: $BACKUP_DIR/tokens_$(date +%Y%m%d).txt.gpg"
else
    echo "⚠️  GPG not installed. Unencrypted backup created: $BACKUP_DIR/tokens_$(date +%Y%m%d).txt"
    echo "   Consider installing GPG: sudo apt install gnupg"
fi
```

---

## Security Best Practices

### ✅ DO:
- Store backups in encrypted format
- Use strong passwords for encrypted backups
- Store backups in secure location (home directory, password manager)
- Regularly update backups if you regenerate tokens
- Use password manager for convenience

### ❌ DON'T:
- Store unencrypted backups in cloud storage (unless encrypted)
- Email tokens to yourself
- Commit tokens to git repositories
- Share backup files with others
- Store on public/shared computers without encryption

---

## Current Backup Status

Your tokens are currently in:
- `~/.bashrc` - **Primary location (active)**

**Recommended backup locations:**
- [ ] Password manager entry
- [ ] Encrypted file (`.gpg` or `.zip` with password)
- [ ] Secure notes file (encrypted)

---

## Quick Reference: Where to Get Tokens Again

If you need to regenerate:

**HuggingFace Token:**
- URL: https://huggingface.co/settings/tokens
- Steps: Settings → Access Tokens → New token
- Models to accept:
  - https://huggingface.co/pyannote/speaker-diarization-3.1
  - https://huggingface.co/pyannote/segmentation-3.0

**OpenAI API Key:**
- URL: https://platform.openai.com/api-keys
- Steps: API Keys → Create new secret key
- Requires: Payment method on file

---

**Last Updated:** 2026-01-09  
**Security Note:** This guide contains your actual tokens - keep it secure!
