import json
import os
import time
import subprocess
import tempfile
from pathlib import Path

# --- CONFIGURATION ---
OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "scene_data")
GENERATED_IMAGES_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "scene_images")
IMAGE_GENERATION_SCRIPT = "image_generation.py"

# Create directories
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(GENERATED_IMAGES_DIR, exist_ok=True)

def find_latest_scene_file():
    """Find the most recent scene data JSON file"""
    scene_files = []
    
    if not os.path.exists(OUTPUT_DIR):
        print(f"❌ Scene data directory not found: {OUTPUT_DIR}")
        return None
    
    for file in os.listdir(OUTPUT_DIR):
        if file.endswith('.json') and 'scenes' in file:
            filepath = os.path.join(OUTPUT_DIR, file)
            scene_files.append((filepath, os.path.getmtime(filepath)))
    
    if not scene_files:
        print(f"❌ No scene JSON files found in {OUTPUT_DIR}")
        return None
    
    # Return the most recent file
    latest_file = max(scene_files, key=lambda x: x[1])[0]
    print(f"📋 Found {len(scene_files)} scene file(s), using latest: {os.path.basename(latest_file)}")
    return latest_file

def load_scene_data(filepath):
    """Load scene data from JSON file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading scene data: {e}")
        return None

def create_image_generation_prompt(scene):
    """Create a comprehensive image generation prompt from scene data"""
    # Combine all the scene elements into a detailed prompt
    prompt_parts = []
    
    # Start with the main image prompt
    if scene.get('image_prompt'):
        prompt_parts.append(scene['image_prompt'])
    
    # Add composition details
    if scene.get('composition'):
        prompt_parts.append(f"Composition: {scene['composition']}")
    
    # Add lighting information
    if scene.get('lighting'):
        prompt_parts.append(f"Lighting: {scene['lighting']}")
    
    # Add art style
    if scene.get('art_style'):
        prompt_parts.append(f"Art Style: {scene['art_style']}")
    
    # Add technical parameters
    if scene.get('technical_parameters'):
        prompt_parts.append(f"Technical Parameters: {scene['technical_parameters']}")
    
    # Join all parts
    full_prompt = ". ".join(prompt_parts)
    
    # Clean up and ensure it's properly formatted
    full_prompt = full_prompt.replace('..', '.').strip()
    
    return full_prompt

def create_modified_image_script(original_script_path, custom_prompt, scene_number, scene_title):
    """Create a temporary version of the image generation script with custom prompt"""
    
    # Read the original script
    with open(original_script_path, 'r', encoding='utf-8') as f:
        script_content = f.read()
    
    # Find and replace the prompt_text assignment
    # Look for the line that assigns prompt_text
    import re
    
    # Pattern to match the prompt_text assignment
    pattern = r'prompt_text\s*=\s*"[^"]*"'
    
    # Create the new prompt assignment with proper escaping
    escaped_prompt = custom_prompt.replace('"', '\\"').replace('\n', '\\n')
    new_assignment = f'prompt_text = "{escaped_prompt}"'
    
    # Replace the prompt assignment
    modified_content = re.sub(pattern, new_assignment, script_content, flags=re.DOTALL)
    
    # Also modify the download directory to be scene-specific
    scene_folder = f"scene_{scene_number:02d}_{scene_title.replace(' ', '_').replace('/', '_').replace('(', '').replace(')', '').replace(':', '').replace('?', '').replace('!', '')}"
    scene_download_dir = os.path.join(GENERATED_IMAGES_DIR, scene_folder)
    os.makedirs(scene_download_dir, exist_ok=True)
    
    # Replace the DOWNLOAD_DIR assignment - be very specific to avoid the prefs section
    # First, let's replace the specific line that defines DOWNLOAD_DIR
    download_line_pattern = r'^DOWNLOAD_DIR\s*=\s*os\.path\.join\(os\.path\.expanduser\("~"\),\s*"Downloads",\s*"ai_studio_image"\)$'
    new_download_dir = f'DOWNLOAD_DIR = "{scene_download_dir}"'
    
    # Split into lines for precise replacement
    lines = modified_content.split('\n')
    replaced = False
    
    for i, line in enumerate(lines):
        # Look for the exact DOWNLOAD_DIR line (not in prefs)
        if line.strip().startswith('DOWNLOAD_DIR = os.path.join(os.path.expanduser'):
            lines[i] = new_download_dir
            print(f"Replaced DOWNLOAD_DIR line: {line.strip()}")
            replaced = True
            break
    
    if not replaced:
        print("Warning: Could not find DOWNLOAD_DIR line to replace")
    
    modified_content = '\n'.join(lines)
    
    # Create temporary script file
    temp_script = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8')
    temp_script.write(modified_content)
    temp_script.close()
    
    return temp_script.name, scene_download_dir

def run_image_generation(script_path, scene_number, scene_title):
    """Run the image generation script"""
    print(f"\n--- Generating image for Scene {scene_number}: {scene_title} ---")
    
    try:
        # Get the Python executable path
        python_path = "python3"  # Use python3 to match your system
        
        # Run the script with real-time output (no capture_output)
        print(f"🚀 Starting image generation for Scene {scene_number}...")
        result = subprocess.run([python_path, script_path], 
                              timeout=300)  # 5 minute timeout, removed capture_output=True
        
        print(f"\n✅ Image generation process completed for Scene {scene_number}")
        print(f"Return code: {result.returncode}")
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print(f"⏰ Timeout: Image generation for Scene {scene_number} took too long")
        return False
    except Exception as e:
        print(f"❌ Error running image generation for Scene {scene_number}: {e}")
        return False

def generate_images_from_scenes(scenes):
    """Generate images for all scenes"""
    print(f"\n=== Starting image generation for {len(scenes)} scenes ===")
    
    successful_generations = 0
    
    for i, scene in enumerate(scenes):
        scene_number = scene.get('scene_number', i + 1)
        scene_title = scene.get('scene_title', f'Scene {scene_number}')
        
        print(f"\n[{i+1}/{len(scenes)}] Processing Scene {scene_number}: {scene_title}")
        
        # Create the image generation prompt
        image_prompt = create_image_generation_prompt(scene)
        print(f"Generated prompt: {image_prompt[:200]}...")
        
        # Create modified script
        temp_script_path, scene_dir = create_modified_image_script(
            IMAGE_GENERATION_SCRIPT, 
            image_prompt, 
            scene_number, 
            scene_title
        )
        
        try:
            # Run image generation
            success = run_image_generation(temp_script_path, scene_number, scene_title)
            
            if success:
                successful_generations += 1
                print(f"✓ Successfully generated image for Scene {scene_number}")
                print(f"  Check folder: {scene_dir}")
            else:
                print(f"✗ Failed to generate image for Scene {scene_number}")
            
            # Clean up temporary script
            os.unlink(temp_script_path)
            
            # Wait between generations to avoid overwhelming the system
            if i < len(scenes) - 1:  # Don't wait after the last scene
                print("Waiting 30 seconds before next generation...")
                time.sleep(30)
                
        except Exception as e:
            print(f"Error processing Scene {scene_number}: {e}")
            # Clean up temporary script
            try:
                os.unlink(temp_script_path)
            except:
                pass
    
    print(f"\n=== Image Generation Complete ===")
    print(f"Successfully generated: {successful_generations}/{len(scenes)} images")
    print(f"Images saved in: {GENERATED_IMAGES_DIR}")

def main():
    print("=== Automatic Scene Image Generator ===")
    print("Automatically finding latest scene data and generating images...")
    
    # Automatically find and use the latest scene file
    latest_file = find_latest_scene_file()
    
    if not latest_file:
        print("❌ No scene files found. Please run gemini_scene_extractor.py first.")
        return
    
    print(f"📄 Using latest scene file: {os.path.basename(latest_file)}")
    
    # Load scene data automatically
    scenes = load_scene_data(latest_file)
    
    if not scenes:
        print("❌ Failed to load scene data.")
        return
    
    print(f"✅ Loaded {len(scenes)} scenes:")
    for scene in scenes:
        print(f"   Scene {scene.get('scene_number', '?')}: {scene.get('scene_title', 'Untitled')}")
    
    # Check if image generation script exists
    if not os.path.exists(IMAGE_GENERATION_SCRIPT):
        print(f"❌ Error: {IMAGE_GENERATION_SCRIPT} not found in current directory.")
        return
    
    # Auto-confirm and start generation
    print(f"\n🚀 Auto-starting image generation for {len(scenes)} scenes...")
    print(f"⏱️  Estimated time: {len(scenes) * 3} minutes")
    print("🔥 Starting automatic generation in 3 seconds...")
    time.sleep(3)
    
    # Start image generation automatically
    generate_images_from_scenes(scenes)

if __name__ == "__main__":
    main()
