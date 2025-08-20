#!/usr/bin/env python3
"""Test service to verify FastAPI is working"""

from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Test Service")

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9999)