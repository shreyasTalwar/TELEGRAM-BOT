import os
import sys
from pathlib import Path

# Add the parent directory to Python path so we can import BOT2
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

# Import the FastAPI app from BOT2 module
from BOT2 import web_app  # type: ignore

# Vercel serverless function entry point - this is what Vercel looks for
app = web_app

# For local development
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        web_app,
        host="0.0.0.0",
        port=port,
        reload=True,
        reload_dirs=["."]
    )
