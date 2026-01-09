import subprocess
import sys
import os
import webbrowser
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def run_streamlit():
    streamlit_cmd = [
        sys.executable, "-m", "streamlit", "run",
        os.path.join(BASE_DIR, "app.py"),
        "--server.headless=true"
    ]
    subprocess.Popen(streamlit_cmd)

if __name__ == "__main__":
    run_streamlit()
    time.sleep(3)
    webbrowser.open("http://localhost:8501")
