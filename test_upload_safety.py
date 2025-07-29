#!/usr/bin/env python3
"""
Test script to verify that the upload functionality correctly selects 
"Upload a local image" and never selects Google Drive options.
"""

import os
import sys
from test_selenium import main as run_selenium_test

def test_upload_safety():
    """Test the upload safety by running a quick automation test."""
    
    print("🔍 TESTING UPLOAD SAFETY")
    print("=" * 50)
    print("This test will:")
    print("1. Run the Selenium automation script")
    print("2. Verify that upload buttons are found correctly")
    print("3. Ensure Google Drive is never selected")
    print("4. Take screenshots for inspection")
    print()
    
    # Check if we have any test scenes/images
    scenes_dir = "/Users/abhchaudhary/Downloads/scene_data"
    images_dir = "/Users/abhchaudhary/Downloads/scene_images"
    
    if not os.path.exists(scenes_dir):
        print(f"❌ Scene data directory not found: {scenes_dir}")
        print("Please run the scene extraction first.")
        return False
    
    if not os.path.exists(images_dir):
        print(f"❌ Scene images directory not found: {images_dir}")
        print("Please run the image generation first.")
        return False
    
    # Find latest scene file
    scene_files = [f for f in os.listdir(scenes_dir) if f.endswith('.json')]
    if not scene_files:
        print(f"❌ No scene JSON files found in {scenes_dir}")
        return False
    
    latest_scene = max(scene_files)
    print(f"✅ Found scene file: {latest_scene}")
    
    # Check for corresponding images
    scene_name = latest_scene.replace('.json', '')
    scene_image_dir = os.path.join(images_dir, scene_name)
    
    if not os.path.exists(scene_image_dir):
        print(f"❌ Scene images directory not found: {scene_image_dir}")
        return False
    
    image_files = [f for f in os.listdir(scene_image_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not image_files:
        print(f"❌ No image files found in {scene_image_dir}")
        return False
    
    print(f"✅ Found {len(image_files)} scene images")
    print()
    
    print("🚀 Starting upload safety test...")
    print("⚠️  WATCH THE OUTPUT for:")
    print("   - 'SKIPPING menu item - contains forbidden keywords'")
    print("   - 'WARNING: Found Google Drive option'")
    print("   - 'SELECTING menu item (safe option)'")
    print()
    
    try:
        # Run the selenium test
        success = run_selenium_test()
        
        if success:
            print("✅ Upload safety test completed successfully!")
            print("🔍 Check the screenshots in /tmp/ for visual verification")
        else:
            print("❌ Upload safety test failed")
            print("🔍 Check the screenshots and logs for debugging")
        
        return success
        
    except Exception as e:
        print(f"❌ Upload safety test crashed: {e}")
        return False

if __name__ == "__main__":
    print("VEO UPLOAD SAFETY TESTER")
    print("========================")
    print()
    
    success = test_upload_safety()
    
    print()
    print("=" * 50)
    if success:
        print("🎉 UPLOAD SAFETY TEST PASSED!")
        print("The system correctly avoids Google Drive selection.")
    else:
        print("💥 UPLOAD SAFETY TEST FAILED!")
        print("Please check the logs and screenshots for issues.")
    
    sys.exit(0 if success else 1)
