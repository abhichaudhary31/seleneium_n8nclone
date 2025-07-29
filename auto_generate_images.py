#!/usr/bin/env python3
"""
Auto Image Generator
===================
Automatically finds the latest scene JSON file and generates images.
No user interaction required - just run and go!
"""

import subprocess
import sys
import os

def main():
    print("🎨 Auto Image Generator - Starting...")
    print("=" * 50)
    
    # Get the Python executable path
    python_path = "/Users/abhchaudhary/personnel_github/seleneium_n8nclone/.venv/bin/python"
    script_path = "scene_image_generator.py"
    
    # Check if the script exists
    if not os.path.exists(script_path):
        print(f"❌ Error: {script_path} not found!")
        return 1
    
    try:
        # Run the scene image generator automatically
        print("🚀 Launching automatic image generation...")
        result = subprocess.run([python_path, script_path], check=True)
        print("\n✅ Image generation completed successfully!")
        return 0
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Image generation failed with error code: {e.returncode}")
        return e.returncode
    except KeyboardInterrupt:
        print("\n⚠️  Image generation cancelled by user.")
        return 130
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
