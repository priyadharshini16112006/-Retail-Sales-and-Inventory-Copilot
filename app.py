import os
import sys
import uvicorn
from dotenv import load_dotenv

def initialize_project():
    # 1. Create required folders if they don't exist
    os.makedirs("data/raw", exist_ok=True)
    
    # 2. Check and load env vars
    if not os.path.exists(".env"):
        print("Notice: .env file not found. Falling back to .env.example or environment variables.")
        if os.path.exists(".env.example"):
            load_dotenv(".env.example")
    else:
        load_dotenv()

    # 3. Generate demo data and init SQLite DB
    # We import here so that directories are created first
    from backend.data_loader import generate_demo_data
    generate_demo_data()

if __name__ == "__main__":
    print("Starting StockPilot AI...")
    initialize_project()
    
    # 4. Start FastAPI
    # Ensure uvicorn runs correctly with the python path
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)
