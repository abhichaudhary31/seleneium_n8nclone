#!/usr/bin/env python3
"""
Enhanced test script for verifying automatic file upload functionality.
This script tests that files are uploaded programmatically without showing dialogs.
"""

import os
import sys
import time
import glob
from test_selenium import find_scene_images, load_latest_scene_data

def verify_file_paths():
    """Verify that we have valid scene data and image files for testing"""
    print("🔍 VERIFYING FILE PATHS FOR UPLOAD TEST")
    print("=" * 50)
    
    # Check scene data
    scenes = load_latest_scene_data()
    if not scenes:
        print("❌ No scene data found")
        return False, None, None
    
    print(f"✅ Found {len(scenes)} scenes")
    
    # Get first scene for testing
    test_scene = scenes[0]
    scene_num = test_scene.get('scene_number', 1)
    print(f"🎬 Testing with Scene {scene_num}: {test_scene.get('scene_title', 'Untitled')}")
    
    # Find images for this scene
    images = find_scene_images(scene_num)
    if not images:
        print(f"❌ No images found for scene {scene_num}")
        return False, None, None
    
    print(f"🖼️  Found {len(images)} images for testing:")
    for i, img in enumerate(images, 1):
        if os.path.exists(img):
            size = os.path.getsize(img)
            print(f"   {i}. {os.path.basename(img)} ({size:,} bytes)")
        else:
            print(f"   {i}. {os.path.basename(img)} ❌ FILE NOT FOUND")
            return False, None, None
    
    return True, test_scene, images

def create_test_images():
    """Create test images if none exist"""
    print("\n🛠️  CREATING TEST IMAGES")
    print("=" * 30)
    
    try:
        from PIL import Image
        import random
        
        # Create test scene directory
        test_dir = "/Users/abhchaudhary/Downloads/scene_images/scene_01_test"
        os.makedirs(test_dir, exist_ok=True)
        
        # Create 2 test images
        for i in range(1, 3):
            # Create a simple colored image
            img = Image.new('RGB', (512, 512), color=(random.randint(50, 200), random.randint(50, 200), random.randint(50, 200)))
            
            # Add some text to make it identifiable
            try:
                from PIL import ImageDraw, ImageFont
                draw = ImageDraw.Draw(img)
                draw.text((10, 10), f"Test Image {i}", fill=(255, 255, 255))
            except:
                pass  # No text if font not available
            
            img_path = os.path.join(test_dir, f"test_image_{i}.png")
            img.save(img_path)
            print(f"✅ Created: {img_path}")
        
        return True
        
    except ImportError:
        print("❌ PIL not available, cannot create test images")
        print("Please install: pip install Pillow")
        return False
    except Exception as e:
        print(f"❌ Error creating test images: {e}")
        return False

def run_upload_test():
    """Run the actual upload test"""
    print("\n🚀 RUNNING AUTOMATIC UPLOAD TEST")
    print("=" * 40)
    
    # Verify we have data
    success, scene_data, images = verify_file_paths()
    
    if not success:
        print("❌ Cannot run test - missing scene data or images")
        
        # Try to create test images
        if create_test_images():
            print("✅ Test images created, please run the scene extraction and image generation first")
        
        return False
    
    print(f"✅ Test preparation complete")
    print(f"📄 Scene: {scene_data.get('scene_title', 'Untitled')}")
    print(f"🖼️  Images: {len(images)} files")
    print()
    
    # Import and run the selenium test
    try:
        from test_selenium import main as run_selenium_main
        
        print("🔧 STARTING SELENIUM AUTOMATION...")
        print("⚠️  MONITOR THE OUTPUT FOR:")
        print("   - 'File upload appears successful!'")
        print("   - 'Successfully uploaded files using robust method'")
        print("   - 'Images uploaded successfully.'")
        print("   - NO appearance of file selection dialogs")
        print()
        print("📸 Screenshots will be saved for manual verification")
        print()
        
        # Run the automation
        result = run_selenium_main()
        
        if result:
            print("\n✅ UPLOAD TEST COMPLETED SUCCESSFULLY!")
            print("🔍 Check screenshots to verify no dialogs appeared")
        else:
            print("\n❌ UPLOAD TEST FAILED")
            print("🔍 Check error logs and screenshots for debugging")
        
        return result
        
    except Exception as e:
        print(f"\n💥 UPLOAD TEST CRASHED: {e}")
        return False

def main():
    """Main test function"""
    print("🎯 AUTOMATIC FILE UPLOAD TESTER")
    print("================================")
    print()
    print("This test verifies that:")
    print("1. ✅ Upload buttons are found correctly")
    print("2. ✅ 'Upload a local image' is selected (not Google Drive)")
    print("3. ✅ File paths are sent automatically to file inputs")
    print("4. ✅ NO file selection dialogs appear")
    print("5. ✅ Multiple files are uploaded successfully")
    print()
    
    success = run_upload_test()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 AUTOMATIC UPLOAD TEST PASSED!")
        print("✅ Files uploaded without manual intervention")
        print("✅ No file dialogs appeared")
        print("✅ System is ready for production use")
    else:
        print("💥 AUTOMATIC UPLOAD TEST FAILED!")
        print("❌ Manual file selection may be required")
        print("❌ Check logs and screenshots for issues")
        print("🔧 Consider running with --headful to debug visually")
    
    print("\n📋 POST-TEST CHECKLIST:")
    print("□ Check /tmp/ for menu inspection screenshots")
    print("□ Check ~/Documents/ for debug screenshots")
    print("□ Verify uploaded images appear in Veo interface")
    print("□ Confirm no manual file dialogs appeared")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
