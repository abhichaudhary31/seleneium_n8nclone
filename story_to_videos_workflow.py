#!/usr/bin/env python3
"""
Complete Story-to-Videos Workflow
=================================

This script provides a complete workflow to:
1. Extract scene data from your story using Gemini
2. Generate images for each scene using AI Studio
3. Generate videos from scenes using Selenium automation
4. Concatenate individual scene videos into one complete story video

Usage:
1. Run this script
2. Choose option 1 to extract scenes from a new story
3. Choose option 2 to generate images from extracted scenes
4. Choose option 3 to generate videos from scenes using Selenium
5. Choose option 4 to do the complete workflow (extract + images + videos + concatenation)
6. Or choose option 5 to only concatenate existing videos into one final video
"""

import os
import subprocess
import sys
import time
import glob

def run_script(script_name, description):
    """Run a Python script and handle errors"""
    print(f"\n{'='*50}")
    print(f"Starting: {description}")
    print(f"{'='*50}")
    
    try:
        # Try multiple Python paths for Windows and Mac compatibility
        python_paths = [
            "python",  # Windows Python in PATH
            "python3",  # Python 3 in PATH
            sys.executable,  # Current Python interpreter
            "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3",  # Mac system Python
            "/Users/abhchaudhary/personnel_github/seleneium_n8nclone/.venv/bin/python",  # Virtual env
            "/usr/bin/python3",  # System Python 3
            "/usr/local/bin/python3",  # Homebrew Python 3
        ]
        
        python_path = None
        for path in python_paths:
            try:
                # Check if the Python command works
                if path == sys.executable:
                    # If it's the current interpreter, we know it works
                    python_path = path
                    break
                result = subprocess.run([path, "--version"], 
                                     capture_output=True, 
                                     text=True, 
                                     timeout=5,
                                     shell=True if os.name == 'nt' else False)  # Use shell=True for Windows
                if result.returncode == 0:
                    python_path = path
                    break
            except:
                continue
        
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

def check_ffmpeg():
    """Check if FFmpeg is installed and available"""
    try:
        subprocess.run(['ffmpeg', '-version'], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL, 
                      check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def concatenate_videos(videos_dir, output_file):
    """Concatenate videos using the video_concatenator.py script"""
    print(f"\n{'='*50}")
    print(f"Starting: Video Concatenation")
    print(f"{'='*50}")
    
    if not os.path.exists("video_concatenator.py"):
        print("❌ Error: video_concatenator.py script not found!")
        return False
    
    if not check_ffmpeg():
        print("❌ Error: FFmpeg is not installed or not available in PATH.")
        print("Please install FFmpeg: https://ffmpeg.org/download.html")
        print("On macOS with Homebrew: brew install ffmpeg")
        return False
    
    # Try multiple Python paths for Mac and Windows compatibility
    python_paths = [
        "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3",  # Mac system Python
        "/Users/abhchaudhary/personnel_github/seleneium_n8nclone/.venv/bin/python",  # Virtual env
        "/usr/bin/python3",  # System Python 3
        "/usr/local/bin/python3",  # Homebrew Python 3
        "python3",  # Python 3 in PATH
        "python"  # Windows Python in PATH
    ]
    
    python_path = None
    for path in python_paths:
        try:
            # Check if the Python command works
            result = subprocess.run([path, "--version"], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5)
            if result.returncode == 0:
                python_path = path
                break
        except:
            continue
    
    if not python_path:
        print("❌ Error: No Python executable found!")
        return False
    
    try:
        # Check if directory exists
        if not os.path.isdir(videos_dir):
            print(f"❌ Error: Directory '{videos_dir}' does not exist!")
            return False
            
        # Check if there are video files in the directory
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v']
        has_videos = False
        
        for ext in video_extensions:
            if glob.glob(os.path.join(videos_dir, f"*{ext}")) or glob.glob(os.path.join(videos_dir, f"*{ext.upper()}")):
                has_videos = True
                break
                
        if not has_videos:
            print(f"❌ Error: No video files found in '{videos_dir}'")
            print("Make sure you have generated videos first using the workflow.")
            return False
        
        # Run the video concatenation script
        print(f"Concatenating videos from: {videos_dir}")
        print(f"Output will be saved to: {output_file}")
        
        cmd = [python_path, "video_concatenator.py", videos_dir, "-o", output_file]
        result = subprocess.run(cmd, check=True)
        
        if os.path.exists(output_file):
            file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
            print(f"✅ Video concatenation completed successfully!")
            print(f"Final video created: {output_file} ({file_size_mb:.1f} MB)")
            return True
        else:
            print(f"❌ Video concatenation failed: Output file not created")
            return False
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Video concatenation failed with error code: {e.returncode}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during video concatenation: {e}")
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
    
    # Check for ffmpeg (needed for video concatenation)
    if check_ffmpeg():
        print("✓ FFmpeg found (required for video concatenation)")
    else:
        print("⚠️  FFmpeg not found. Video concatenation will not be available.")
        print("   Install FFmpeg to enable video concatenation.")
    
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
    print("4. Concatenate videos into one complete story")
    print("5. Run a complete end-to-end workflow (extraction → images → videos → concatenation)")
    print()
    
    while True:
        print("Available options:")
        print("1. Extract scenes from story (using Gemini)")
        print("2. Generate images from scenes (using AI Studio)")
        print("3. Generate videos from scenes (using Selenium automation)")
        print("4. Generate videos using CDP automation (more robust)")
        print("5. Complete workflow (extract scenes + images + videos + concatenation)")
        print("6. Concatenate existing videos into final story video")
        print("7. Check system setup")
        print("8. Exit")
        print()
        
        choice = input("Select an option (1-8): ").strip()
        
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
            print("   - Videos will be downloaded to ~/Downloads/scene_videos/")
            print()
            
            # Check if user wants to continue
            continue_video = input("Continue with video generation? (y/n): ").strip().lower()
            if continue_video == 'y':
                success = run_script("test_selenium.py", "Video Generation (Selenium)")
                if success:
                    print("\n✅ Video generation completed!")
                    print("Videos should be downloaded to ~/Downloads/scene_videos/")
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
            print("\n🎥 Starting video generation using CDP automation (more robust)...")
            print("⚠️  Important Notes:")
            print("   - This uses Chrome DevTools Protocol for more reliable automation")
            print("   - Make sure you have Chrome browser installed")
            print("   - This process will take several minutes per scene")
            print("   - Videos will be downloaded to ~/Downloads/scene_videos/")
            print("   - Supports auto login, account switching, and robust error handling")
            print()
            
            # Check if new_test.py exists
            if not os.path.exists("new_test.py"):
                print("❌ new_test.py not found. This script is required for CDP automation.")
                continue
                
            # Check if user wants to continue
            continue_video = input("Continue with CDP-based video generation? (y/n): ").strip().lower()
            if continue_video == 'y':
                success = run_script("new_test.py", "Video Generation (CDP)")
                if success:
                    print("\n✅ CDP-based video generation completed!")
                    print("Videos should be downloaded to ~/Downloads/scene_videos/")
                else:
                    print("\n❌ CDP-based video generation encountered issues!")
                    print("Check the output above for specific errors.")
            else:
                print("CDP-based video generation cancelled.")
            
        elif choice == "5":
            print("\n🚀 Starting COMPLETE workflow...")
            print("This will take a significant amount of time!")
            print("Estimated time: 10-30 minutes depending on number of scenes")
            print("\n⚠️  IMPORTANT:")
            print("   - This workflow will run completely automatically")
            print("   - Make sure you are already logged into Google AI Studio")
            print("   - No further input will be required until completion")
            print("   - Chrome browser will open automatically during the process")
            print()
            
            # Ask which video generation approach to use
            print("Which video generation approach would you like to use?")
            print("1. Standard Selenium automation")
            print("2. CDP-based automation (more robust)")
            video_choice = input("Select video generation approach (1/2): ").strip()
            
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
                    
                    # Step 3: Generate videos based on user choice
                    print("\n" + "="*60)
                    print("STEP 3: Generating videos...")
                    print("="*60)
                    print("⚠️  Important note:")
                    print("   - Chrome will open automatically")
                    print("   - Process will run automatically with retry mechanisms")
                    print()
                    
                    # Choose the video generation approach based on user selection
                    if video_choice == "2":
                        print("Using CDP-based automation for video generation...")
                        success3 = run_script("new_test.py", "Video Generation (CDP)")
                    else:
                        print("Using standard Selenium automation for video generation...")
                        success3 = run_script("test_selenium.py", "Video Generation (Selenium)")
                    
                    if success3:
                        print("\n✅ Videos generated successfully!")
                        
                        # Step 4: Concatenate all videos into a final video
                        print("\n" + "="*60)
                        print("STEP 4: Concatenating videos into final story...")
                        print("="*60)
                        
                        # Wait a moment for any video downloads to complete
                        print("Waiting for video downloads to complete (5 seconds)...")
                        time.sleep(5)
                        
                        # Automatically proceed with video concatenation (no prompt)
                        print("Automatically proceeding with video concatenation...")
                        
                        # Set up paths for video concatenation
                        videos_dir = os.path.join(os.path.expanduser("~"), "Downloads", "scene_videos")
                        timestamp = int(time.time())
                        output_file = os.path.join(os.path.expanduser("~"), "Downloads", f"complete_story_{timestamp}.mp4")
                        
                        # Run the concatenation
                        success4 = concatenate_videos(videos_dir, output_file)
                        
                        if success4:
                            print("\n🎉 COMPLETE WORKFLOW FINISHED SUCCESSFULLY!")
                            print("="*60)
                            print("Your story has been converted to videos!")
                            print("Check the following locations:")
                            print(f"   - Scene data: ~/Downloads/scene_data/")
                            print(f"   - Generated images: ~/Downloads/scene_images/")
                            print(f"   - Individual scene videos: ~/Downloads/scene_videos/")
                            print(f"   - Complete story video: {output_file}")
                            print("="*60)
                        else:
                            print("\n⚠️  Scene extraction, image and video generation succeeded,")
                            print("    but video concatenation failed.")
                            print("    Your individual scene videos are still available in ~/Downloads/scene_videos/")
                            print("    You can try running the video concatenation separately (option 5) later.")
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
            
        elif choice == "6":
            print("\n🎞️  Starting video concatenation...")
            print("This will combine all videos in your scene_videos folder into one final video.")
            print("⚠️  Important Notes:")
            print("   - Make sure you have FFmpeg installed")
            print("   - Individual scene videos should be in ~/Downloads/scene_videos/")
            print("   - Videos will be concatenated in time-based order")
            print()
            
            # Check if user wants to specify a custom videos directory
            use_custom_dir = input("Use a custom videos directory? (default is ~/Downloads/scene_videos) (y/n): ").strip().lower()
            if use_custom_dir == 'y':
                custom_dir = input("Enter the full path to the videos directory: ").strip()
                videos_dir = os.path.expanduser(custom_dir) if custom_dir.startswith("~") else custom_dir
                if not os.path.isdir(videos_dir):
                    print(f"❌ Error: Directory '{videos_dir}' does not exist!")
                    print("Using default directory ~/Downloads/scene_videos instead.")
                    videos_dir = os.path.join(os.path.expanduser("~"), "Downloads", "scene_videos")
            else:
                videos_dir = os.path.join(os.path.expanduser("~"), "Downloads", "scene_videos")
            
            # Let user customize output file name
            default_name = f"complete_story_{int(time.time())}.mp4"
            custom_name = input(f"Enter output file name (default: {default_name}): ").strip()
            output_name = custom_name if custom_name else default_name
            
            # Ensure output file has .mp4 extension
            if not output_name.lower().endswith('.mp4'):
                output_name += '.mp4'
                
            output_file = os.path.join(os.path.expanduser("~"), "Downloads", output_name)
            
            # Check if user wants to continue
            print(f"\nVideo concatenation will:")
            print(f"   - Look for videos in: {videos_dir}")
            print(f"   - Create output file: {output_file}")
            continue_concat = input("\nContinue with video concatenation? (y/n): ").strip().lower()
            
            if continue_concat == 'y':
                success = concatenate_videos(videos_dir, output_file)
                if success:
                    print("\n✅ Video concatenation completed!")
                    print(f"Final video saved to: {output_file}")
                else:
                    print("\n❌ Video concatenation failed!")
                    print("Common issues:")
                    print("   - FFmpeg not installed")
                    print("   - No compatible video files found")
                    print("   - Video files have incompatible formats")
            else:
                print("Video concatenation cancelled.")
                
        elif choice == "7":
            print("\n🔧 Checking system setup...")
            setup_ok = check_selenium_setup()
            if setup_ok:
                print("\n✅ System setup looks good!")
            else:
                print("\n❌ System setup needs attention. Please resolve the issues above.")
            
        elif choice == "8":
            print("\nGoodbye! 👋")
            print("Happy video creating! 🎬")
            break
            
        else:
            print("Invalid choice. Please select 1, 2, 3, 4, 5, 6, 7, or 8.")
        
        print("\n" + "-"*60)

if __name__ == "__main__":
    # Check if required scripts exist
    required_scripts = [
        "gemini_scene_extractor.py", 
        "scene_image_generator.py", 
        "image_generation.py",
        "test_selenium.py"
    ]
    
    # Check for CDP automation script
    if os.path.exists("new_test.py"):
        print("✅ CDP automation script found: new_test.py")
    else:
        print("⚠️ CDP automation script not found: new_test.py")
        print("    You won't be able to use the more robust CDP-based automation option.")
        print("    Only standard Selenium automation will be available.")
    
    optional_scripts = [
        "video_concatenator.py"
    ]
    
    missing_required = []
    missing_optional = []
    video_concatenation_available = True
    
    for script in required_scripts:
        if not os.path.exists(script):
            missing_required.append(script)
    
    for script in optional_scripts:
        if not os.path.exists(script):
            missing_optional.append(script)
            if script == "video_concatenator.py":
                video_concatenation_available = False
    
    if missing_required:
        print("❌ Missing required scripts:")
        for script in missing_required:
            print(f"   - {script}")
        print("\nPlease ensure all required scripts are in the current directory.")
        print("\nRequired scripts:")
        print("   - gemini_scene_extractor.py (for scene extraction)")
        print("   - scene_image_generator.py (for image generation)")
        print("   - image_generation.py (helper for image generation)")
        print("   - test_selenium.py (for video generation)")
        sys.exit(1)
    
    if missing_optional:
        print("⚠️  Missing optional scripts:")
        for script in missing_optional:
            print(f"   - {script}")
        print("\nOptional scripts:")
        print("   - video_concatenator.py (for video concatenation)")
        print("     Without this script, video concatenation functionality will be unavailable.")
        print("     You can still extract scenes, generate images, and create individual videos.")
        print("")
    
    # Check for FFmpeg (needed for video concatenation)
    ffmpeg_available = check_ffmpeg()
    if not ffmpeg_available:
        video_concatenation_available = False
        print("⚠️  FFmpeg not found. Video concatenation will not be available.")
        print("   To enable video concatenation, please install FFmpeg:")
        print("   macOS: brew install ffmpeg")
        print("   Ubuntu: sudo apt install ffmpeg")
        print("")
    
    print("✅ All required scripts found!")
    main()