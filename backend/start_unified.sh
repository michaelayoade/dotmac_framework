#!/bin/bash

# Install dependencies
pip install --no-cache-dir fastapi uvicorn httpx pydantic pyyaml

# Start the unified API service
cd /app/backend && python -m uvicorn unified_api_service:app --host 0.0.0.0 --port 8000 --reload