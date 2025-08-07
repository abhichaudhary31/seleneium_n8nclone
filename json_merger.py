#!/usr/bin/env python3
"""
JSON Scene File Merger
======================

This script merges individual scene JSON files from Downloads/scene_data 
into a single video_prompt_final.json file for video generation.

HARDCODED CONFIGURATION:
- Input directory: ~/Downloads/scene_data
- Pattern: *scene*.json (individual scene files only)
- Output: video_prompt_final.json
- Strategy: scenes (sorted by scene number)

Usage:
    python json_merger.py
"""

import os
import json
import glob
import re
from datetime import datetime

def load_json_file(file_path):
    """Load and parse a JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ Loaded: {os.path.basename(file_path)}")
        return data
    except Exception as e:
        print(f"❌ Error loading {file_path}: {e}")
        return None

def merge_as_array(json_files, output_file):
    """Merge JSON files into a single array"""
    merged_data = []
    
    for file_path in json_files:
        data = load_json_file(file_path)
        if data is not None:
            # If the loaded data is already a list, extend the merged data
            if isinstance(data, list):
                merged_data.extend(data)
            else:
                # If it's a single object, append it
                merged_data.append(data)
    
    # Save merged data
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Merged {len(json_files)} files into {output_file}")
    print(f"📊 Total items in merged file: {len(merged_data)}")
    return True

def merge_as_object(json_files, output_file):
    """Merge JSON files by combining object keys"""
    merged_data = {}
    
    for file_path in json_files:
        data = load_json_file(file_path)
        if data is not None:
            if isinstance(data, dict):
                # Merge dictionaries
                merged_data.update(data)
            elif isinstance(data, list):
                # Convert list to numbered keys
                filename = os.path.splitext(os.path.basename(file_path))[0]
                for i, item in enumerate(data):
                    merged_data[f"{filename}_{i}"] = item
            else:
                # Handle primitive types
                filename = os.path.splitext(os.path.basename(file_path))[0]
                merged_data[filename] = data
    
    # Save merged data
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Merged {len(json_files)} files into {output_file}")
    print(f"📊 Total keys in merged file: {len(merged_data)}")
    return True

def merge_scene_files(json_files, output_file, sort_scenes=True):
    """Special merge for scene files with Scene1, Scene2, etc. format"""
    merged_scenes = {}
    
    for file_path in json_files:
        data = load_json_file(file_path)
        if data is not None:
            if isinstance(data, dict):
                # Add all keys from this file
                merged_scenes.update(data)
            else:
                print(f"⚠️ Skipping {file_path}: Expected dict format for scene files")
    
    # Sort scenes if requested
    if sort_scenes and merged_scenes:
        # Extract scene numbers for sorting
        scene_items = []
        other_items = {}
        
        for key, value in merged_scenes.items():
            # Try to extract scene number from key
            scene_match = re.search(r'[Ss]cene\s*(\d+)', key)
            if scene_match:
                scene_num = int(scene_match.group(1))
                scene_items.append((scene_num, key, value))
            else:
                other_items[key] = value
        
        # Sort by scene number
        scene_items.sort(key=lambda x: x[0])
        
        # Rebuild the dictionary in sorted order
        sorted_scenes = {}
        for _, key, value in scene_items:
            sorted_scenes[key] = value
        
        # Add any non-scene items at the end
        sorted_scenes.update(other_items)
        merged_scenes = sorted_scenes
        
        print(f"📋 Sorted {len(scene_items)} scenes by number")
    
    # Save merged data
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(merged_scenes, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Merged {len(json_files)} scene files into {output_file}")
    print(f"📊 Total scenes in merged file: {len(merged_scenes)}")
    
    # Show first few scenes for verification
    if merged_scenes:
        print("\n📋 Preview of merged scenes:")
        for i, (key, value) in enumerate(list(merged_scenes.items())[:5]):
            preview = str(value)[:80] + "..." if len(str(value)) > 80 else str(value)
            print(f"  {key}: {preview}")
        if len(merged_scenes) > 5:
            print(f"  ... and {len(merged_scenes) - 5} more scenes")
    
    return True

def find_json_files(input_dir, pattern):
    """Find JSON files matching the pattern"""
    search_pattern = os.path.join(input_dir, pattern)
    files = glob.glob(search_pattern)
    
    # Filter for JSON files and sort
    json_files = [f for f in files if f.endswith('.json')]
    json_files.sort()
    
    print(f"🔍 Found {len(json_files)} JSON files in {input_dir}")
    if json_files:
        print("📁 Files to merge:")
        for f in json_files:
            file_size = os.path.getsize(f)
            print(f"  - {os.path.basename(f)} ({file_size} bytes)")
    
    return json_files

def validate_output_path(output_file):
    """Validate and prepare output file path"""
    # Create directory if it doesn't exist
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        print(f"📁 Created output directory: {output_dir}")
    
    # Check if file exists and warn user
    if os.path.exists(output_file):
        print(f"⚠️ Output file already exists: {output_file}")
        response = input("Do you want to overwrite it? (y/n): ").strip().lower()
        if response not in ['y', 'yes']:
            # Generate a new filename with timestamp
            name, ext = os.path.splitext(output_file)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"{name}_{timestamp}{ext}"
            print(f"📝 Using new filename: {output_file}")
    
    return output_file

def main():
    # HARDCODED CONFIGURATION FOR SCENE FILES
    # Set fixed parameters for scene file merging
    input_dir = os.path.join(os.path.expanduser("~"), "Downloads", "scene_data")
    pattern = "*scene*.json"  # Files containing "scene" in the name
    output_file = os.path.join(input_dir, "video_prompt_final.json")  # Save in same folder as scene data
    strategy = "scenes"
    sort_scenes = True
    
    print("="*60)
    print("🔗 JSON Scene File Merger")
    print("="*60)
    print("🎯 HARDCODED MODE: Merging scene files")
    print(f"📁 Input directory: {input_dir}")
    print(f"🔍 Pattern: {pattern}")
    print(f"📄 Output file: {output_file}")
    print(f"🔧 Strategy: {strategy} (with sorting)")
    print("="*60)
    
    # Validate input directory
    if not os.path.exists(input_dir):
        print(f"❌ Input directory does not exist: {input_dir}")
        print("💡 Make sure you have run the scene extraction first!")
        return 1
    
    # Find JSON files with scene pattern
    json_files = find_json_files(input_dir, pattern)
    if not json_files:
        print(f"❌ No scene JSON files found in {input_dir}")
        print("💡 Looking for files matching pattern: *scene*.json")
        print("💡 Make sure you have individual scene files generated!")
        return 1
    
    # Filter out combined scene files (keep only individual scene files)
    individual_scene_files = []
    combined_files = []
    
    for file_path in json_files:
        filename = os.path.basename(file_path)
        # Check if it's an individual scene file (contains _scene followed by number)
        if re.search(r'_scene\d+_', filename):
            individual_scene_files.append(file_path)
        else:
            combined_files.append(file_path)
    
    if individual_scene_files:
        print(f"\n✅ Found {len(individual_scene_files)} individual scene files:")
        for f in individual_scene_files:
            print(f"  - {os.path.basename(f)}")
        json_files = individual_scene_files
    else:
        print(f"\n⚠️ No individual scene files found, using all scene files:")
        for f in json_files:
            print(f"  - {os.path.basename(f)}")
    
    if combined_files:
        print(f"\n📋 Skipping {len(combined_files)} combined scene files:")
        for f in combined_files:
            print(f"  - {os.path.basename(f)}")
    
    # Validate output path
    output_file = validate_output_path(output_file)
    
    # Show merge plan
    print(f"\n📋 Final Merge Plan:")
    print(f"  📁 Input: {len(json_files)} individual scene files")
    print(f"  🔧 Strategy: {strategy} (sorted by scene number)")
    print(f"  📄 Output: {output_file}")
    
    # Auto-proceed without confirmation for hardcoded mode
    print(f"\n🚀 Auto-proceeding with hardcoded configuration...")
    
    
    # Perform the merge using hardcoded scene strategy
    print(f"\n🔗 Starting merge using '{strategy}' strategy...")
    
    try:
        # Always use scenes strategy with sorting for this hardcoded version
        success = merge_scene_files(json_files, output_file, sort_scenes)
        
        if success:
            # Show output file info
            output_size = os.path.getsize(output_file)
            print(f"\n🎉 Scene file merge completed successfully!")
            print(f"📄 Output file: {output_file}")
            print(f"📊 File size: {output_size:,} bytes")
            
            # Verify the output by loading it
            try:
                with open(output_file, 'r') as f:
                    merged_data = json.load(f)
                print(f"✅ Output file is valid JSON")
                
                if isinstance(merged_data, dict):
                    print(f"📋 Contains {len(merged_data)} scenes")
                    print(f"🎬 Scene files successfully merged and ready for video generation!")
                    
            except Exception as e:
                print(f"⚠️ Warning: Could not verify output file: {e}")
            
            return 0
        else:
            print("❌ Scene file merge failed")
            return 1
            
    except Exception as e:
        print(f"❌ Error during scene file merge: {e}")
        return 1

if __name__ == "__main__":
    exit(main())

