#!/bin/zsh
# macOS Setup for AI Course Builder (Apple Silicon)

set -e

echo "1. Install Poetry"
brew install poetry || pipx install poetry

echo "2. Install browsers for Playwright"
poetry run playwright install --with-deps

echo "3. Install PyTorch MPS (Apple Silicon)"
poetry add torch torchvision torchaudio --source pytorch --extras mps

echo "4. Install system deps"
brew install redis neo4j/neo4j/neo4j  # Optional local

echo "5. Poetry install"
poetry install

echo "6. Docker setup"
docker compose -f Application/Docker/docker-compose.yml up -d

echo "✅ Setup complete! Run 'poetry shell' then 'poetry run pytest' to test."

