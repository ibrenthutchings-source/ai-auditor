#!/bin/sh
set -e

ollama serve &
OLLAMA_PID=$!

echo "Waiting for Ollama service to start..."
until ollama list >/dev/null 2>&1; do
  sleep 1
done

echo "Pulling Llama 3.1 8B model..."
ollama pull llama3.1

wait $OLLAMA_PID
