#!/bin/bash

# Installing dependencies
if ! poetry install --only main --no-interaction --no-ansi; then
  echo "[error] Health check: Failed to install dependencies"
  exit 1
fi

echo "[ok] Health check: Dependencies successfully installed."

# Execute the Python health check script
poetry run python /healthcheck/health_check.py

# Check the exit status of the Python script
if [ $? -eq 0 ]; then
    echo "Health check passed."
    exit 0
else
    echo "Health check failed."
    exit 1
fi
