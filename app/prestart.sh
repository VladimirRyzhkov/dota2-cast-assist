#!/bin/bash

# Installing dependencies
echo "[in progress] Installing POETRY dependencies..."

if ! poetry install --only main --no-interaction --no-ansi; then
  echo "[error] Service pre-starter: Failed to install dependencies"
  exit 1
fi

echo "[done] POETRY dependencies are successfully installed"


# Running Live Matches Crawler as a background process in the Docker container
echo ""
echo "[in progress] Live Matches Crawler..."
poetry run python /live_matches_crawler/crawler.py &
