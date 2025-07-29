#!/usr/bin/env python3
import json
import os
import sys
import re

# Add the current directory to Python path
sys.path.append('/Users/abhchaudhary/personnel_github/seleneium_n8nclone')

# Import the extraction function
from gemini_scene_extractor import extract_scene_data, save_scene_data

def test_extraction():
    # Read the raw response file
    raw_file = "/Users/abhchaudhary/Downloads/scene_data/monkey_and_wedge_panchatantra_raw_response_1754250662.txt"
    
    if not os.path.exists(raw_file):
        print("Raw response file not found!")
        return
    
    with open(raw_file, 'r', encoding='utf-8') as f:
        response_text = f.read()
    
    print("Testing scene extraction on existing response...")
    print(f"Response length: {len(response_text)} characters")
    
    # Extract scenes
    scenes = extract_scene_data(response_text)
    
    if scenes:
        print(f"\n=== EXTRACTION TEST SUCCESSFUL ===")
        print(f"Extracted {len(scenes)} scenes!")
        
        # Save the scenes
        scene_file = save_scene_data(scenes, "monkey_and_wedge_panchatantra_test")
        
        # Print details
        for scene in scenes:
            print(f"\n--- Scene {scene['scene_number']} ---")
            print(f"Title: {scene['scene_title']}")
            print(f"Image Prompt: {scene['image_prompt'][:100]}...")
            print(f"Composition: {scene['composition'][:80]}...")
            print(f"Lighting: {scene['lighting'][:80]}...")
            print(f"Art Style: {scene['art_style'][:80]}...")
            print(f"Technical: {scene['technical_parameters']}")
    else:
        print("No scenes extracted. Need to improve the extraction logic.")

if __name__ == "__main__":
    test_extraction()
