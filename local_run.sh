#!/bin/bash
set -e

IMAGE_NAME="food-inventory:v1.0.0"

if [ ! -f .env ]; then
  echo "Error: .env file not found. Copy .env.example to .env and fill in your API keys."
  exit 1
fi

echo "Building Docker image..."
docker build -t $IMAGE_NAME .

echo "Starting container at http://localhost:8000"
echo "Swagger UI: http://localhost:8000/docs"
echo "Press Ctrl+C to stop."
echo ""
docker run --rm -p 8000:8000 --name=food-inventory --env-file .env $IMAGE_NAME
