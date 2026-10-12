import os
import sys
import subprocess

def main():
    print("=" * 70)
    print(" 🌾 Paddy & Modern Rice Mill Dynamic Billing & Accounting System")
    print(" Lightweight Single-File Application")
    print("=" * 70)
    print("\nStarting application at http://localhost:8501 ...")
    
    # Launch Streamlit app.py
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", "app.py",
        "--server.port", "8501"
    ])

if __name__ == "__main__":
    main()
