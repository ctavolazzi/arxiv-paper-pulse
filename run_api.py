#!/usr/bin/env python3
"""Run the ArXiv Paper Pulse API server"""
import uvicorn
from arxiv_paper_pulse.api import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)

