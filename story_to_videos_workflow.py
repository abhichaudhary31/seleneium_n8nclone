#!/usr/bin/env python3
"""
Complete Story-to-Videos Workflow
=================================

This script provides a complete workflow to:
1. Extract scene data from your story using Gemini
2. Generate images for each scene using AI Studio
3. Generate videos from scenes using Selenium automation

Usage:
1. Run this script
2. Choose option 1 to extract scenes from a new story
3. Choose option 2 to generate images from extracted scenes
4. Choose option 3 to generate videos from scenes using Selenium
5. Or choose option 4 to do the complete workflow (extract + images + videos)
"""

import os
import subprocess
import sys
import time

def run_script(script_name, description):
    """Run a Python script and handle errors"""
    print(f"\n{'='*50}")
    print(f"Starting: {description}")
    print(f"{'='*50}")
    
    try:
        # Try multiple Python paths for Mac compatibility
        python_paths = [
            "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3",  # Mac system Python
            "/Users/abhchaudhary/personnel_github/seleneium_n8nclone/.venv/bin/python",  # Virtual env
            "/usr/bin/python3",  # System Python 3
            "/usr/local/bin/python3",  # Homebrew Python 3
            "python3",  # Python 3 in PATH
        ]
        
        python_path = None
        for path in python_paths:
            if path == "python3":
                # For commands in PATH, check if they exist
                try:
                    result = subprocess.run([path, "--version"], 
                                          capture_output=True, 
                                          text=True, 
                                          timeout=5)
                    if result.returncode == 0:
                        python_path = path
                        break
                except:
                    continue
            else:
                # For absolute paths, check if file exists
                if os.path.exists(path):
                    python_path = path
                    break
        
        if not python_path:
            print("❌ Error: No Python executable found!")
            return False
        
        print(f"Using Python: {python_path}")
        result = subprocess.run([python_path, script_name], check=True)
        print(f"✓ {description} completed successfully!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed with error code: {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"✗ Script not found: {script_name}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def check_selenium_setup():
    """Check if Selenium automation is properly configured"""
    print("\n🔍 Checking Selenium setup...")
    
    # Check if Chrome is installed
    chrome_paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium"
    ]
    
    chrome_found = False
    for path in chrome_paths:
        if os.path.exists(path):
            chrome_found = True
            print(f"✓ Chrome browser found: {path}")
            break
    
    if not chrome_found:
        print("❌ Chrome browser not found. Please install Google Chrome.")
        return False
    
    # Check if test_selenium.py exists
    if not os.path.exists("test_selenium.py"):
        print("❌ test_selenium.py not found. This script is required for video generation.")
        return False
    
    print("✓ Selenium script found: test_selenium.py")
    
    # Check for scene data and images
    scene_data_dir = os.path.join(os.path.expanduser("~"), "Downloads", "scene_data")
    scene_images_dir = os.path.join(os.path.expanduser("~"), "Downloads", "scene_images")
    
    if not os.path.exists(scene_data_dir):
        print(f"⚠️  Scene data directory not found: {scene_data_dir}")
        print("   You'll need to extract scenes first (option 1)")
    else:
        print(f"✓ Scene data directory found: {scene_data_dir}")
    
    if not os.path.exists(scene_images_dir):
        print(f"⚠️  Scene images directory not found: {scene_images_dir}")
        print("   You'll need to generate images first (option 2)")
    else:
        print(f"✓ Scene images directory found: {scene_images_dir}")
    
    return True

def main():
    print("="*60)
    print("     STORY TO VIDEOS - Complete Workflow")
    print("="*60)
    print()
    print("This workflow will help you:")
    print("1. Extract scene data from your story using Gemini AI")
    print("2. Generate images for each scene using Google AI Studio")
    print("3. Generate videos from scenes using Selenium automation")
    print("4. Complete end-to-end video generation workflow")
    print()
    
    while True:
        print("Available options:")
        print("1. Extract scenes from story (using Gemini)")
        print("2. Generate images from scenes (using AI Studio)")
        print("3. Generate videos from scenes (using Selenium automation)")
        print("4. Complete workflow (extract scenes + generate images + generate videos)")
        print("5. Check system setup")
        print("6. Exit")
        print()
        
        choice = input("Select an option (1-6): ").strip()
        
        if choice == "1":
            print("\n🎬 Starting scene extraction...")
            success = run_script("gemini_scene_extractor.py", "Scene Extraction")
            if success:
                print("\n✅ Scene extraction completed!")
                print("Scene data saved to ~/Downloads/scene_data/")
                print("You can now run option 2 to generate images.")
            
        elif choice == "2":
            print("\n🎨 Starting image generation...")
            success = run_script("scene_image_generator.py", "Image Generation")
            if success:
                print("\n✅ Image generation completed!")
                print("Images saved to ~/Downloads/scene_images/")
                print("You can now run option 3 to generate videos.")
            
        elif choice == "3":
            print("\n🎥 Starting video generation using Selenium automation...")
            print("⚠️  Important Notes:")
            print("   - Make sure you have Chrome browser installed")
            print("   - Ensure you're logged into Google AI Studio")
            print("   - This process will take several minutes per scene")
            print("   - Videos will be downloaded to ~/Documents/")
            print()
            
            # Check if user wants to continue
            continue_video = input("Continue with video generation? (y/n): ").strip().lower()
            if continue_video == 'y':
                success = run_script("test_selenium.py", "Video Generation (Selenium)")
                if success:
                    print("\n✅ Video generation completed!")
                    print("Videos should be downloaded to ~/Documents/")
                else:
                    print("\n❌ Video generation failed!")
                    print("Common issues:")
                    print("   - Not logged into Google AI Studio")
                    print("   - Chrome browser issues")
                    print("   - Network connectivity problems")
                    print("   - Quota limits reached")
            else:
                print("Video generation cancelled.")
            
        elif choice == "4":
            print("\n🚀 Starting COMPLETE workflow...")
            print("This will take a significant amount of time!")
            print("Estimated time: 10-30 minutes depending on number of scenes")
            print("\n⚠️  IMPORTANT:")
            print("   - This workflow will run completely automatically")
            print("   - Make sure you are already logged into Google AI Studio")
            print("   - No further input will be required until completion")
            print("   - Chrome browser will open automatically during the process")
            print()
            
            continue_complete = input("Start complete automated workflow? (y/n): ").strip().lower()
            if continue_complete != 'y':
                print("Complete workflow cancelled.")
                continue
            
            # Step 1: Extract scenes
            print("\n" + "="*60)
            print("STEP 1: Extracting scenes from story...")
            print("="*60)
            success1 = run_script("gemini_scene_extractor.py", "Scene Extraction")
            
            if success1:
                print("\n✅ Scene extraction completed!")
                
                # Step 2: Generate images
                print("\n" + "="*60)
                print("STEP 2: Generating images for scenes...")
                print("="*60)
                
                # Automatically proceed with image generation (no prompt)
                print("\nAutomatically proceeding with image generation...")
                success2 = run_script("scene_image_generator.py", "Image Generation")
                
                if success2:
                    print("\n✅ Image generation completed!")
                    
                    # Step 3: Generate videos
                    print("\n" + "="*60)
                    print("STEP 3: Generating videos using Selenium...")
                    print("="*60)
                    print("⚠️  Important note:")
                    print("   - Chrome will open automatically")
                    print("   - Ensure you're already logged into Google AI Studio")
                    print("   - Process will run automatically with retry mechanisms")
                    print()
                    
                    # Automatically proceed with video generation (no prompt)
                    print("Automatically proceeding with video generation...")
                    success3 = run_script("test_selenium.py", "Video Generation (Selenium)")
                    
                    if success3:
                        print("\n🎉 COMPLETE WORKFLOW FINISHED SUCCESSFULLY!")
                        print("="*60)
                        print("Your story has been converted to videos!")
                        print("Check the following locations:")
                        print(f"   - Scene data: ~/Downloads/scene_data/")
                        print(f"   - Generated images: ~/Downloads/scene_images/")
                        print(f"   - Generated videos: ~/Documents/")
                        print("="*60)
                    else:
                        print("\n⚠️  Scene extraction and image generation succeeded,")
                        print("    but video generation failed.")
                        print("    You can retry video generation with option 3.")
                else:
                    print("\n❌ Image generation failed. Cannot proceed with video generation.")
                    print("You can retry image generation with option 2.")
            else:
                print("\n❌ Scene extraction failed. Cannot proceed with workflow.")
                print("Please check the error messages above and try again.")
            
        elif choice == "5":
            print("\n🔧 Checking system setup...")
            setup_ok = check_selenium_setup()
            if setup_ok:
                print("\n✅ System setup looks good!")
            else:
                print("\n❌ System setup needs attention. Please resolve the issues above.")
            
        elif choice == "6":
            print("\nGoodbye! 👋")
            print("Happy video creating! 🎬")
            break
            
        else:
            print("Invalid choice. Please select 1, 2, 3, 4, 5, or 6.")
        
        print("\n" + "-"*60)

if __name__ == "__main__":
    # Check if required scripts exist
    required_scripts = [
        "gemini_scene_extractor.py", 
        "scene_image_generator.py", 
        "image_generation.py",
        "test_selenium.py"
    ]
    missing_scripts = []
    
    for script in required_scripts:
        if not os.path.exists(script):
            missing_scripts.append(script)
    
    if missing_scripts:
        print("❌ Missing required scripts:")
        for script in missing_scripts:
            print(f"   - {script}")
        print("\nPlease ensure all scripts are in the current directory.")
        print("\nRequired scripts:")
        print("   - gemini_scene_extractor.py (for scene extraction)")
        print("   - scene_image_generator.py (for image generation)")
        print("   - image_generation.py (helper for image generation)")
        print("   - test_selenium.py (for video generation)")
        sys.exit(1)
    
    print("✅ All required scripts found!")
    main()
