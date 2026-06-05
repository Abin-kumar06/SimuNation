import uvicorn
import os

if __name__ == "__main__":
    print("Starting SimuNation V2 Backend on Port 8000...")
    # Add project root directory to python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.join(current_dir, "app")
    import sys
    sys.path.insert(0, app_dir)
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
