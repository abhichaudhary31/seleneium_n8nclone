#!/usr/bin/env python3
"""
Complete Story-to-Images Workflow
=================================

This script provides a complete workflow to:
1. Extract scene data from your story using Gemini
2. Generate images for each scene using AI Studio

Usage:
1. Run this script
2. Choose option 1 to extract scenes from a new story
3. Choose option 2 to generate images from extracted scenes
4. Or choose option 3 to do both in sequence
"""

import os
import subprocess
import sys

def run_script(script_name, description):
    """Run a Python script and handle errors"""
    print(f"\n{'='*50}")
    print(f"Starting: {description}")
    print(f"{'='*50}")
    
    try:
        python_path = "/Users/abhchaudhary/personnel_github/seleneium_n8nclone/.venv/bin/python"
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

def main():
    print("="*60)
    print("     STORY TO IMAGES - Complete Workflow")
    print("="*60)
    print()
    print("This workflow will help you:")
    print("1. Extract scene data from your story using Gemini AI")
    print("2. Generate images for each scene using Google AI Studio")
    print()
    
    while True:
        print("Available options:")
        print("1. Extract scenes from story (using Gemini)")
        print("2. Generate images from scenes (using AI Studio)")
        print("3. Complete workflow (extract scenes + generate images)")
        print("4. Exit")
        print()
        
        choice = input("Select an option (1-4): ").strip()
        
        if choice == "1":
            print("\n🎬 Starting scene extraction...")
            success = run_script("gemini_scene_extractor.py", "Scene Extraction")
            if success:
                print("\n✅ Scene extraction completed!")
                print("You can now run option 2 to generate images,")
                print("or option 3 to continue with image generation.")
            
        elif choice == "2":
            print("\n🎨 Starting image generation...")
            success = run_script("scene_image_generator.py", "Image Generation")
            if success:
                print("\n✅ Image generation completed!")
                print("Check the ~/Downloads/scene_images/ folder for your generated images.")
            
        elif choice == "3":
            print("\n🚀 Starting complete workflow...")
            
            # Step 1: Extract scenes
            print("\nStep 1: Extracting scenes from story...")
            success1 = run_script("gemini_scene_extractor.py", "Scene Extraction")
            
            if success1:
                print("\n✅ Scene extraction completed!")
                
                # Ask if user wants to continue with image generation
                continue_gen = input("\nProceed with image generation? (y/n): ").strip().lower()
                if continue_gen == 'y':
                    # Step 2: Generate images
                    print("\nStep 2: Generating images for scenes...")
                    success2 = run_script("scene_image_generator.py", "Image Generation")
                    
                    if success2:
                        print("\n🎉 Complete workflow finished successfully!")
                        print("Check the ~/Downloads/scene_images/ folder for your generated images.")
                    else:
                        print("\n⚠️  Scene extraction succeeded, but image generation failed.")
                        print("You can try running option 2 separately to retry image generation.")
                else:
                    print("Image generation skipped. You can run option 2 later.")
            else:
                print("\n❌ Scene extraction failed. Cannot proceed with image generation.")
                print("Please check the error messages above and try again.")
            
        elif choice == "4":
            print("\nGoodbye! 👋")
            break
            
        else:
            print("Invalid choice. Please select 1, 2, 3, or 4.")
        
        print("\n" + "-"*60)

if __name__ == "__main__":
    # Check if required scripts exist
    required_scripts = ["gemini_scene_extractor.py", "scene_image_generator.py", "image_generation.py"]
    missing_scripts = []
    
    for script in required_scripts:
        if not os.path.exists(script):
            missing_scripts.append(script)
    
    if missing_scripts:
        print("❌ Missing required scripts:")
        for script in missing_scripts:
            print(f"   - {script}")
        print("\nPlease ensure all scripts are in the current directory.")
        sys.exit(1)
    
    main()
