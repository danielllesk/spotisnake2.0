#!/bin/bash

# DiscogSnake Environment Setup Script
# This script helps you set up environment variables for development

echo "🎵 DiscogSnake Environment Setup"
echo "================================"

# Check if .env file exists
if [ -f ".env" ]; then
    echo "⚠️  .env file already exists. Backing up to .env.backup"
    cp .env .env.backup
fi

# Create .env file
echo "Creating .env file..."

cat > .env << EOF
# DiscogSnake Environment Variables
# Copy this file to .env.local for local development

# Discogs API Configuration
# Get your personal access token from: https://www.discogs.com/settings/developers
DISCOGS_TOKEN=your_discogs_token_here

# Backend Configuration (for deployment)
DISCOGSNAKE_BACKEND_URL=https://spotisnake2-0.onrender.com

# Flask Configuration (for backend)
FLASK_SECRET_KEY=your_secret_key_here
FLASK_ENV=development

# Optional: Override backend URL for local development
# DISCOGSNAKE_BACKEND_URL=http://localhost:5000
EOF

echo "✅ .env file created successfully!"
echo ""
echo "📝 Next steps:"
echo "1. Edit .env file and add your Discogs API token"
echo "2. Get your token from: https://www.discogs.com/settings/developers"
echo "3. For local development, copy .env to .env.local"
echo ""
echo "🔒 Security note: .env files are already in .gitignore"
echo "   Your API keys will not be committed to the repository"
