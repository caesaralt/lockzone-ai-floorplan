#!/usr/bin/env bash
set -o errexit

echo "Installing system dependencies..."
apt-get update
apt-get install -y poppler-utils libgl1-mesa-glx libglib2.0-0

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Creating required directories..."
mkdir -p uploads outputs data

echo "Build complete!"
