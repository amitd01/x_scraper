#!/bin/bash
set -e

# Activate virtual environment
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please run ./setup.sh first."
    exit 1
fi

source venv/bin/activate

echo "Running X Scraper..."
python scraper.py
