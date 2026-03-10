#!/bin/bash
set -e

echo "Setting up X Scraper environment..."

# Check if python3 is installed
if ! command -v python3 &> /dev/null
then
    echo "Python 3 could not be found. Please install Python 3."
    exit 1
fi

# Create a virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install playwright anthropic

# Install playwright browsers
echo "Installing Playwright browsers..."
playwright install chromium

echo "=========================================="
echo "✅ Setup Complete!"
echo "To run the scraper, simply execute:"
echo "./run.sh"
echo "=========================================="
