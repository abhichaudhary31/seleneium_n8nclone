#!/usr/bin/env python3
"""
Test script to validate the scene processing workflow
This script tests loading scene data and finding images without running the full Selenium automation
"""

import os
import json
import glob

# Scene data and images directories
SCENE_DATA_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "scene_data")
SCENE_IMAGES_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "scene_images")

def load_latest_scene_data():
    """Load the most recent scene data JSON file"""
    try:
        print(f"Looking for scene data in: {SCENE_DATA_DIR}")
        json_files = glob.glob(os.path.join(SCENE_DATA_DIR, "*_scenes_*.json"))
        
        if not json_files:
            print("No scene data JSON files found.")
            print("Please run the gemini_scene_extractor.py first to generate scene data.")
            return []
        
        # Get the most recent file
        latest_file = max(json_files, key=os.path.getctime)
        print(f"Loading scene data from: {latest_file}")
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            scenes = json.load(f)
        
        print(f"Loaded {len(scenes)} scenes from JSON file.")
        return scenes
    except Exception as e:
        print(f"Error loading scene data: {e}")
        return []

def find_scene_images(scene_number):
    """Find all images for a specific scene number"""
    try:
        # Look for images in scene directories (new format)
        scene_dir_patterns = [
            os.path.join(SCENE_IMAGES_DIR, f"scene_{scene_number:02d}_*"),  # scene_01_Title format
            os.path.join(SCENE_IMAGES_DIR, f"scene_{scene_number}_*"),      # scene_1_Title format
        ]
        
        images = []
        for pattern in scene_dir_patterns:
            scene_dirs = glob.glob(pattern)
            for scene_dir in scene_dirs:
                if os.path.isdir(scene_dir):
                    # Look for PNG files in the scene directory
                    image_files = glob.glob(os.path.join(scene_dir, "*.png"))
                    images.extend(image_files)
        
        # Also check for direct files (old format)
        direct_image_pattern = os.path.join(SCENE_IMAGES_DIR, f"scene_{scene_number}_*.png")
        direct_images = glob.glob(direct_image_pattern)
        images.extend(direct_images)
        
        print(f"Found {len(images)} images for scene {scene_number}")
        for img in images:
            print(f"  - {os.path.basename(img)}")
        return images
    except Exception as e:
        print(f"Error finding images for scene {scene_number}: {e}")
        return []

def create_combined_prompt(scene_data):
    """Create a comprehensive prompt from scene data"""
    prompt_parts = []
    
    if scene_data.get('scene_title'):
        prompt_parts.append(f"Scene: {scene_data['scene_title']}")
    
    if scene_data.get('image_prompt'):
        prompt_parts.append(scene_data['image_prompt'])
    
    if scene_data.get('composition'):
        prompt_parts.append(f"Composition: {scene_data['composition']}")
    
    if scene_data.get('lighting'):
        prompt_parts.append(f"Lighting: {scene_data['lighting']}")
    
    if scene_data.get('art_style'):
        prompt_parts.append(f"Art Style: {scene_data['art_style']}")
    
    if scene_data.get('technical_parameters'):
        prompt_parts.append(f"Technical: {scene_data['technical_parameters']}")
    
    return ". ".join(prompt_parts)

def test_workflow():
    """Test the complete workflow"""
    print("=== Testing Scene Workflow ===\n")
    
    # Check if directories exist
    print("1. Checking directories...")
    if not os.path.exists(SCENE_DATA_DIR):
        print(f"❌ Scene data directory does not exist: {SCENE_DATA_DIR}")
        print("Please run gemini_scene_extractor.py first to create scene data.")
        return
    else:
        print(f"✅ Scene data directory exists: {SCENE_DATA_DIR}")
    
    if not os.path.exists(SCENE_IMAGES_DIR):
        print(f"❌ Scene images directory does not exist: {SCENE_IMAGES_DIR}")
        print("Please run scene_image_generator.py first to generate images.")
        return
    else:
        print(f"✅ Scene images directory exists: {SCENE_IMAGES_DIR}")
    
    # Load scene data
    print("\n2. Loading scene data...")
    scenes = load_latest_scene_data()
    
    if not scenes:
        print("❌ No scenes loaded. Cannot proceed.")
        return
    
    print(f"✅ Successfully loaded {len(scenes)} scenes.")
    
    # Test each scene
    print("\n3. Testing scene processing...")
    for i, scene_data in enumerate(scenes, 1):
        scene_num = scene_data.get('scene_number', i)
        scene_title = scene_data.get('scene_title', 'Untitled')
        
        print(f"\n--- Scene {i}/{len(scenes)} (Scene #{scene_num}) ---")
        print(f"Title: {scene_title}")
        
        # Find images for this scene
        scene_images = find_scene_images(scene_num)
        
        if scene_images:
            print(f"✅ Found {len(scene_images)} images for scene {scene_num}")
        else:
            print(f"⚠️  No images found for scene {scene_num}")
        
        # Create combined prompt
        prompt = create_combined_prompt(scene_data)
        print(f"Combined prompt ({len(prompt)} chars): {prompt[:100]}...")
        
        # Show scene data structure
        print("Scene data structure:")
        for key, value in scene_data.items():
            if isinstance(value, str):
                display_value = value[:50] + "..." if len(value) > 50 else value
                print(f"  {key}: {display_value}")
            else:
                print(f"  {key}: {value}")
    
    print(f"\n=== Workflow Test Complete ===")
    print(f"Ready to run the full Selenium automation with {len(scenes)} scenes.")
    print("\nTo run the full automation:")
    print("python test_selenium.py")

if __name__ == "__main__":
    test_workflow()
