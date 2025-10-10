#!/usr/bin/env bash
# Build script for Render deployment
set -o errexit

echo "🔧 Installing system dependencies..."
apt-get update
apt-get install -y poppler-utils libsm6 libxext6 libxrender-dev libgomp1 libglib2.0-0

echo "📦 Upgrading pip..."
pip install --upgrade pip

echo "📚 Installing Python dependencies..."
pip install -r requirements.txt

echo "✅ Build complete!"
