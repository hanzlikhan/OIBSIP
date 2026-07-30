"""
Main entry point for the Voice Assistant.
Launches the FastAPI server and automatically opens the browser-based dashboard.
"""

import sys
import time
import webbrowser
import threading
import uvicorn

def open_browser():
    """Helper thread to open the dashboard web browser once the server is active."""
    time.sleep(1.5)
    url = "http://127.0.0.1:8000"
    print(f"\n[System] Automatically opening dashboard in web browser: {url}")
    webbrowser.open(url)

if __name__ == "__main__":
    print("=========================================================")
    print("           NOVA VOICE ASSISTANT LAUNCHER                 ")
    print("=========================================================")
    
    # Verify Python runtime
    if sys.version_info < (3, 9):
        print("[Warning] This application is designed for Python 3.9+. Older runtimes may experience threading issues.", file=sys.stderr)
        
    # Start web browser opener thread
    threading.Thread(target=open_browser, daemon=True).start()

    # Boot the FastAPI uvicorn server
    print("[System] Initializing server on http://127.0.0.1:8000 ...")
    uvicorn.run(
        "gui.server:app",
        host="127.0.0.1",
        port=8000,
        log_level="info",
        reload=False
    )
