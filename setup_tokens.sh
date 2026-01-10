#!/bin/bash
# Helper script to set up API tokens for Spanish Helper

echo "🔧 Spanish Helper - Token Setup"
echo "================================"
echo ""

# Check if tokens are already set
if [ -n "$HUGGINGFACE_TOKEN" ]; then
    echo "✅ HUGGINGFACE_TOKEN is already set"
else
    echo "❌ HUGGINGFACE_TOKEN not set"
fi

if [ -n "$OPENAI_API_KEY" ]; then
    echo "✅ OPENAI_API_KEY is already set"
else
    echo "❌ OPENAI_API_KEY not set"
fi

echo ""
echo "To set tokens, run:"
echo ""
echo "  export HUGGINGFACE_TOKEN=hf_your_token_here"
echo "  export OPENAI_API_KEY=sk-your_key_here"
echo ""
echo "Or to make them permanent, add to ~/.bashrc:"
echo ""
echo "  echo 'export HUGGINGFACE_TOKEN=hf_your_token_here' >> ~/.bashrc"
echo "  echo 'export OPENAI_API_KEY=sk-your_key_here' >> ~/.bashrc"
echo "  source ~/.bashrc"
echo ""


