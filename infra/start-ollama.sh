#!/bin/sh
set -e

ollama serve &
OLLAMA_PID=$!

echo "Waiting for Ollama service to start..."
until ollama list >/dev/null 2>&1; do
  sleep 1
done

# A prior boot may have died mid-pull (e.g. ENOSPC from an earlier,
# larger model choice) and left partial blobs on the persistent volume
# taking up space a completed pull will never need. Clear them before
# pulling so the volume self-heals instead of wedging permanently.
find /root/.ollama/models -name "*-partial*" -delete 2>/dev/null || true

# llama3.2:3b (~2GB) rather than the originally-planned 8B model -- the
# default Railway volume is 5GB and resize isn't exposed via CLI/API,
# only the dashboard. 3b leaves headroom for the download's temp/partial
# blobs without requiring a manual resize step.
echo "Pulling Llama 3.2 3B model..."
ollama pull llama3.2:3b

wait $OLLAMA_PID
