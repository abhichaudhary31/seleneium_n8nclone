#!/usr/bin/env python3
"""
Gemini Scene Rewriter
=====================

This script takes scene data extracted from a story and sends each individual scene to your
trained AI model for rewriting. It:

1. Loads scene data from a JSON file
2. Connects to your trained model (https://gemini.google.com/app/44ed85f1a1ea23d5)
3. For each scene, sends the scene description to the trained model
4. Retrieves the rewritten scene description
5. Updates the scene data with the rewritten description
6. Saves EACH rewritten scene to its OWN file with format: "original_filename_scene{number}_{timestamp}.json"

Individual scene files can be used by other scripts in the workflow (test_selenium.py, etc.)
for further processing.

Usage:
    python gemini_scene_rewriter.py [--scene_file /path/to/scene_file.json]

If no scene file is provided, the script will find the most recent scene JSON file
in ~/Downloads/scene_data/

Output:
    - Individual files: One JSON file per scene in format "original_filename_scene{number}_{timestamp}.json"
"""

import time
import os
import json
import re
import glob
import sys
import argparse
import random
import shutil
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# --- USER CONFIGURATION ---
# IMPORTANT: Replace with your Google account credentials if different from gemini_scene_extractor.py
GOOGLE_EMAIL = "chaudharyabhishek031@gmail.com"
GOOGLE_PASSWORD = "GAme++0103"
USER_DATA_DIR = os.path.join(os.path.expanduser("~"), "selenium_chrome_profile")
OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "scene_data")

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(USER_DATA_DIR, exist_ok=True)

def human_delay(min_sec=2, max_sec=6, reason=None):
    """Add a human-like random delay to mimic real user behavior
    
    Parameters:
    - min_sec: Minimum delay in seconds
    - max_sec: Maximum delay in seconds
    - reason: Optional reason for the delay (for logging)
    """
    delay = random.uniform(min_sec, max_sec)
    if reason:
        print(f"   ⏱️ {reason} ({delay:.1f}s delay)")
    else:
        print(f"   ⏱️ Human-like delay ({delay:.1f}s)")
    time.sleep(delay)

# --- GEMINI PROMPT TEMPLATE ---
# Since the model is already trained for scene rewriting, we just send the raw scene data
SCENE_REWRITE_PROMPT = """{scene_text}"""

def authenticate_google(driver, wait):
    """Handle Google authentication"""
    print("Checking if login is required...")
    
    if "accounts.google.com" in driver.current_url or "signin" in driver.current_url:
        print("Login required. Performing login...")
        
        try:
            # Enter email
            email_field = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
            )
            email_field.clear()
            email_field.send_keys(GOOGLE_EMAIL)
            
            # Click next button
            next_button = driver.find_element(By.ID, "identifierNext")
            next_button.click()
            print("Email entered.")
            time.sleep(2)
            
        except TimeoutException:
            print("Email field not found, assuming it's pre-filled or different flow.")
        
        try:
            # Enter password
            password_field = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='password']"))
            )
            password_field.clear()
            password_field.send_keys(GOOGLE_PASSWORD)
            
            # Click next button
            password_next = driver.find_element(By.ID, "passwordNext")
            password_next.click()
            print("Password entered. Login successful.")
            
            # Wait for redirect
            print("Waiting for login completion...")
            time.sleep(5)
            
        except TimeoutException:
            print("Password field not found or login already completed.")
    else:
        print("Already logged in or no login required.")

def wait_for_gemini_response(driver, wait, timeout=120):
    """Wait for Gemini to complete its response - gets only the LATEST response"""
    print("Waiting for Gemini response...")
    
    # Wait for response to appear and complete
    start_time = time.time()
    last_response_length = 0
    stable_count = 0
    min_response_length = 20
    
    while time.time() - start_time < timeout:
        try:
            # Strategy to get ONLY the latest response (not old ones)
            latest_response = ""
            
            # Look for the most recent response container
            response_selectors = [
                "[data-response-id]",
                ".response-container", 
                ".markdown",
                ".message-content",
                "[role='presentation']",
                ".model-response"
            ]
            
            for selector in response_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        # Get ONLY the last element (most recent response)
                        last_element = elements[-1]
                        if last_element.is_displayed():
                            text = last_element.get_attribute('textContent') or last_element.text
                            if text and len(text) > len(latest_response):
                                latest_response = text
                        break
                except:
                    continue
            
            # If no specific selectors work, get all text and filter for newest
            if not latest_response:
                try:
                    # Get all text and try to isolate the newest response
                    all_text = driver.execute_script("return document.body.innerText;")
                    
                    # Look for patterns that indicate a new response
                    lines = all_text.split('\n')
                    response_started = False
                    response_lines = []
                    
                    # Find the last occurrence of JSON-like content or scene data
                    for i in range(len(lines) - 1, -1, -1):
                        line = lines[i].strip()
                        if '{' in line or 'scene_number' in line.lower():
                            response_started = True
                        if response_started:
                            response_lines.insert(0, line)
                            # Stop when we hit a clear boundary (like user input)
                            if any(keyword in line.lower() for keyword in ['enter a prompt', 'ask gemini', 'send', 'user']):
                                break
                    
                    latest_response = '\n'.join(response_lines)
                    
                except:
                    pass
            
            # Clean up the response to remove UI elements
            if latest_response:
                # Remove common UI elements that might be captured
                latest_response = re.sub(r'(Enter a prompt here|Ask Gemini|Send|Copy|Share|Like|Dislike)', '', latest_response)
                latest_response = re.sub(r'\s+', ' ', latest_response).strip()
            
            current_length = len(latest_response)
            
            # Only consider responses that have meaningful content
            if current_length > min_response_length:
                # Check if response has stopped growing (indicating completion)
                if current_length == last_response_length:
                    stable_count += 1
                    if stable_count >= 3:  # Response has been stable for 3 checks
                        print(f"Latest response appears complete. Final length: {current_length} characters")
                        return latest_response
                else:
                    stable_count = 0
                    last_response_length = current_length
                    print(f"Latest response growing... current length: {current_length} characters")
            else:
                print(f"Waiting for latest response to appear... current length: {current_length} characters")
            
            # Random delay between checks to avoid overwhelming the interface
            check_delay = random.uniform(2.5, 4.0)  # Random delay 2.5-4 seconds
            time.sleep(check_delay)
            
        except Exception as e:
            print(f"Error while waiting for response: {e}")
            error_delay = random.uniform(2.0, 4.0)  # Random delay on error
            time.sleep(error_delay)
    
    print("Timeout reached while waiting for response.")
    return latest_response if latest_response else None

def extract_rewritten_scene(response_text, scene_number):
    """Extract the rewritten scene description from the trained model's response"""
    print(f"Extracting rewritten scene {scene_number} from response...")
    
    # Try to parse as JSON first (if the model returns structured data)
    try:
        # Look for JSON-like structure in the response
        json_pattern = r'\{[\s\S]*?"scene_number"[\s\S]*?\}'
        json_match = re.search(json_pattern, response_text, re.IGNORECASE)
        
        if json_match:
            json_str = json_match.group(0)
            parsed_json = json.loads(json_str)
            if isinstance(parsed_json, dict) and 'scene_number' in parsed_json:
                print("Found structured JSON response from model")
                return parsed_json
    except (json.JSONDecodeError, AttributeError):
        pass
    
    # If no JSON found, try to extract individual fields
    rewritten_scene = {}
    
    # Extract scene_number
    scene_num_pattern = rf'"?scene_number"?\s*:\s*{scene_number}'
    if re.search(scene_num_pattern, response_text, re.IGNORECASE):
        rewritten_scene['scene_number'] = scene_number
    
    # Extract scene_title
    title_pattern = r'"?scene_title"?\s*:\s*"([^"]*)"'
    title_match = re.search(title_pattern, response_text, re.IGNORECASE)
    if title_match:
        rewritten_scene['scene_title'] = title_match.group(1)
    
    # Extract image_prompt
    prompt_pattern = r'"?image_prompt"?\s*:\s*"([^"]*)"'
    prompt_match = re.search(prompt_pattern, response_text, re.IGNORECASE)
    if prompt_match:
        rewritten_scene['image_prompt'] = prompt_match.group(1)
    
    # Extract composition
    comp_pattern = r'"?composition"?\s*:\s*"([^"]*)"'
    comp_match = re.search(comp_pattern, response_text, re.IGNORECASE)
    if comp_match:
        rewritten_scene['composition'] = comp_match.group(1)
    
    # Extract lighting
    light_pattern = r'"?lighting"?\s*:\s*"([^"]*)"'
    light_match = re.search(light_pattern, response_text, re.IGNORECASE)
    if light_match:
        rewritten_scene['lighting'] = light_match.group(1)
    
    # Extract art_style
    style_pattern = r'"?art_style"?\s*:\s*"([^"]*)"'
    style_match = re.search(style_pattern, response_text, re.IGNORECASE)
    if style_match:
        rewritten_scene['art_style'] = style_match.group(1)
    
    # Extract technical_parameters
    tech_pattern = r'"?technical_parameters"?\s*:\s*"([^"]*)"'
    tech_match = re.search(tech_pattern, response_text, re.IGNORECASE)
    if tech_match:
        rewritten_scene['technical_parameters'] = tech_match.group(1)
    
    # If we found some structured data, return it
    if rewritten_scene:
        return rewritten_scene
    
    # Fallback: treat the entire response as the image_prompt
    clean_text = re.sub(r'```.*?```', '', response_text, flags=re.DOTALL)
    clean_text = re.sub(r'^"(.*)"$', r'\1', clean_text.strip())
    
    return {
        'scene_number': scene_number,
        'image_prompt': clean_text.strip()
    }

def find_most_recent_scene_file():
    """Find the most recent scene JSON file in the output directory, excluding already rewritten files"""
    # First try to find original scene files (not rewritten ones)
    scene_files = glob.glob(os.path.join(OUTPUT_DIR, "*scenes*.json"))
    
    # Filter out already rewritten files
    original_files = [f for f in scene_files if "_rewritten" not in f]
    
    if original_files:
        # Sort by modification time (newest first)
        original_files.sort(key=os.path.getmtime, reverse=True)
        return original_files[0]
    elif scene_files:
        # If only rewritten files exist, use the newest one
        scene_files.sort(key=os.path.getmtime, reverse=True)
        return scene_files[0]
    else:
        return None

def load_scene_data(scene_file):
    """Load scene data from a JSON file"""
    try:
        with open(scene_file, 'r', encoding='utf-8') as f:
            scene_data = json.load(f)
        
        print(f"Loaded {len(scene_data)} scenes from {scene_file}")
        return scene_data
    except Exception as e:
        print(f"Error loading scene data: {e}")
        return None

def save_individual_scene(scene, original_filename):
    """Save a single scene to its own file in simple Scene(No.):prompt format"""
    # Get scene number from the rewritten scene
    scene_num = scene.get('scene_number', 0)
    
    # Get the prompt from the scene data
    prompt = scene.get('image_prompt', '')
    if not prompt:
        # Fallback to other fields if image_prompt is empty
        prompt = scene.get('scene_title', '') or scene.get('composition', '') or 'No prompt available'
    
    # Create a unique filename for this individual scene
    scene_basename = os.path.basename(original_filename)
    scene_name = scene_basename.replace('.json', '')
    
    # Create individual scene file with timestamp to avoid overwriting
    timestamp = int(time.time())
    individual_scene_name = f"{scene_name}_scene{scene_num}_{timestamp}.json"
    individual_scene_path = os.path.join(OUTPUT_DIR, individual_scene_name)
    
    # Create the simple data structure: Scene(No.):prompt
    simple_scene_data = {
        f"Scene{scene_num}": prompt
    }
    
    try:
        # First create a temporary file to avoid corruption if interrupted
        temp_path = f"{individual_scene_path}.temp"
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(simple_scene_data, f, indent=2)
        
        # If successful, rename to final file (atomic operation on most systems)
        if os.path.exists(individual_scene_path):
            os.remove(individual_scene_path)  # Remove existing file if it exists
        os.rename(temp_path, individual_scene_path)
        
        # Verify the file was saved correctly
        if os.path.exists(individual_scene_path):
            with open(individual_scene_path, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
            expected_key = f"Scene({scene_num})"
            if expected_key in saved_data:
                print(f"✅ Successfully saved scene {scene_num} to {individual_scene_path}")
                print(f"   Format: {expected_key}: {saved_data[expected_key][:50]}...")
                return individual_scene_path
            else:
                print(f"⚠️ File saved but scene verification failed")
                return None
        else:
            print(f"⚠️ File not found after save operation")
            return None
            
    except Exception as e:
        print(f"Error saving scene {scene_num}: {e}")
        return None

def rewrite_scene_with_gemini(driver, wait, scene_data):
    """Send a scene to the trained model for rewriting and update the scene data"""
    scene_number = scene_data['scene_number']
    
    print(f"\n=== Rewriting Scene {scene_number} ===")
    print(f"Original scene data: {json.dumps(scene_data, indent=2)}")
    
    # Prepare the full scene data as JSON for the trained model
    rewrite_prompt = SCENE_REWRITE_PROMPT.format(scene_text=json.dumps(scene_data, indent=2))
    
    try:
        # Only start a new chat for the first scene to avoid splitting conversations
        if scene_number == 1:
            try:
                # Add human-like delay before looking for new chat button
                human_delay(1, 3, "Looking for new chat button")
                
                new_chat_buttons = driver.find_elements(By.CSS_SELECTOR, 
                    "button[aria-label='New chat'], button:has-text('New chat')")
                if new_chat_buttons:
                    for btn in new_chat_buttons:
                        if btn.is_displayed():
                            # Brief pause before clicking (like a human would)
                            human_delay(0.5, 1.5, "About to click new chat")
                            btn.click()
                            print("Started a new chat for the rewriting session.")
                            human_delay(2, 4, "Waiting for new chat to initialize")
                            break
            except:
                print("No new chat button found or couldn't interact with it.")
        else:
            print(f"Continuing in same chat for scene {scene_number}...")
            human_delay(1, 2, "Preparing to continue in same chat")
        
        # Find the chat input field
        print("Looking for chat input field...")
        chat_input = None
        input_selectors = [
            "textarea[placeholder*='Enter a prompt']",
            "textarea[placeholder*='Ask Gemini']",
            "textarea[aria-label*='Message']",
            "textarea",
            "[contenteditable='true']",
            "input[type='text']"
        ]
        
        for selector in input_selectors:
            try:
                chat_input = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                print(f"Found chat input using selector: {selector}")
                break
            except TimeoutException:
                continue
        
        if not chat_input:
            print("Could not find chat input field.")
            return scene_data
        
        # Send the JSON data using copy-paste method for reliability
        print("Sending scene JSON data to trained model...")
        
        # Human-like interaction with input field
        human_delay(1, 2, "Looking at input field before clicking")
        chat_input.click()
        
        # Use Ctrl+A and Delete to clear content with human-like delays
        human_delay(0.3, 0.7, "Preparing to clear input field")
        chat_input.send_keys(Keys.CONTROL + "a")
        human_delay(0.3, 0.7, "Selecting all text")
        chat_input.send_keys(Keys.DELETE)
        human_delay(0.5, 1, "Cleared input field")
        
        print(f"Sending JSON data length: {len(rewrite_prompt)} characters")
        
        # Use JavaScript to set the value directly - this ensures it goes as one message
        try:
            # For contenteditable div, use textContent
            if chat_input.get_attribute('contenteditable') == 'true':
                driver.execute_script("arguments[0].textContent = arguments[1];", chat_input, rewrite_prompt)
            else:
                driver.execute_script("arguments[0].value = arguments[1];", chat_input, rewrite_prompt)
            
            # Trigger input events to make sure the content is registered
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true}));", chat_input)
            time.sleep(random.uniform(1.0, 2.0))  # Random delay after content injection
            print("✓ JSON data set using JavaScript method")
            
        except Exception as js_error:
            print(f"JavaScript method failed: {js_error}")
            print("Fallback: Using clipboard copy-paste method...")
            
            # Fallback: Use clipboard copy-paste for large text
            try:
                # Copy to clipboard and paste
                driver.execute_script(f"navigator.clipboard.writeText(arguments[0]);", rewrite_prompt)
                time.sleep(1)
                chat_input.send_keys(Keys.CONTROL + "v")
                time.sleep(1)
                print("✓ JSON data pasted from clipboard")
            except:
                print("Clipboard method failed, using direct input...")
                # Last resort: direct input but reduce chunk size to prevent splitting
                chunk_size = 50  # Smaller chunks
                for i in range(0, len(rewrite_prompt), chunk_size):
                    chunk = rewrite_prompt[i:i + chunk_size]
                    chat_input.send_keys(chunk)
                    time.sleep(0.1)  # Faster input to keep it as one message
        
        # Send the message with human-like delay
        print("Attempting to send message...")
        
        # Add a human-like delay before sending - people often pause before submitting
        human_delay(2, 4, "Reading over the prompt before sending")
        
        try:
            # Brief pause just before hitting Enter (very human-like)
            human_delay(0.2, 0.5, "About to press Enter")
            chat_input.send_keys(Keys.ENTER)
            print("✓ Message sent using Enter key")
        except Exception as send_error:
            print(f"Keyboard send failed, trying click method: {send_error}")
            # Try to find and click send button with delays
            send_buttons = driver.find_elements(By.CSS_SELECTOR, 
                "button[aria-label*='Send'], button:has-text('Send'), [data-testid*='send']")
            if send_buttons:
                for btn in send_buttons:
                    if btn.is_displayed():
                        # Human-like delay before clicking button
                        human_delay(0.5, 1.5, "Moving to click send button")
                        btn.click()
                        print("✓ Message sent using send button")
                        break
        
        print("Message sent. Waiting for model response...")
        
        # No debug screenshots needed
        
        # MANDATORY WAIT: Wait longer for the trained model to process with random component
        base_wait = random.uniform(15.0, 25.0)  # Random wait 15-25 seconds
        print(f"Waiting {base_wait:.1f} seconds for trained model to process the scene...")
        time.sleep(base_wait)
        
        # Check if model is actually responding
        print("Checking if model is generating response...")
        for check_attempt in range(6):  # Check for 60 seconds
            try:
                # Look for loading indicators or response containers
                loading_indicators = driver.find_elements(By.CSS_SELECTOR, 
                    ".loading, .generating, .thinking, [aria-label*='generating'], [aria-label*='thinking']")
                response_containers = driver.find_elements(By.CSS_SELECTOR, 
                    "[data-response-id], .response-container, .markdown")
                
                if loading_indicators or response_containers:
                    print("✓ Model is responding, proceeding to wait for completion...")
                    break
                else:
                    print(f"Attempt {check_attempt + 1}/6: No response detected yet, waiting...")
                    wait_time = random.uniform(8.0, 12.0)  # Random wait 8-12 seconds
                    time.sleep(wait_time)
                    
            except Exception as e:
                print(f"Error checking response status: {e}")
                error_wait = random.uniform(8.0, 12.0)  # Random wait on error
                time.sleep(error_wait)
        else:
            print("⚠️  Warning: No response detected after 60 seconds, but continuing...")
        
        print("Now waiting for response completion...")
        
        # Wait for response with a longer timeout for trained models
        response_text = wait_for_gemini_response(driver, wait, timeout=300)  # 5 minutes timeout
        
        if response_text:
            # Extract the rewritten scene description
            rewritten_scene_data = extract_rewritten_scene(response_text, scene_number)
            print(f"Rewritten scene data: {json.dumps(rewritten_scene_data, indent=2)}")
            
            # Update the scene data with the rewritten information
            updated_scene = scene_data.copy()
            
            # If we got a complete scene object, use it; otherwise merge specific fields
            if isinstance(rewritten_scene_data, dict):
                # Preserve the original scene_number
                updated_scene['scene_number'] = scene_number
                
                # Update each field if present in the rewritten data
                for key in ['scene_title', 'image_prompt', 'composition', 'lighting', 'art_style', 'technical_parameters']:
                    if key in rewritten_scene_data and rewritten_scene_data[key]:
                        updated_scene[key] = rewritten_scene_data[key]
            else:
                # Fallback: treat as image_prompt only
                updated_scene['image_prompt'] = str(rewritten_scene_data)
            
            # Wait a random moment before the next scene to avoid overwhelming the interface
            scene_delay = random.uniform(3.0, 8.0)  # Random delay 3-8 seconds between scenes
            print(f"Waiting {scene_delay:.1f} seconds before next scene...")
            time.sleep(scene_delay)
            
            return updated_scene
        else:
            print(f"Failed to get response for scene {scene_number}. Keeping original.")
            return scene_data
            
    except Exception as e:
        print(f"Error while rewriting scene {scene_number}: {e}")
        return scene_data

def create_rewritten_file_for_compatibility(scene_files):
    """Create a compatible rewritten file for downstream scripts"""
    print("\n=== CREATING COMPATIBILITY FILE ===")
    
    if not scene_files:
        print("❌ No individual scene files to use!")
        return None
    
    # Get the base name from the first scene file
    first_file = scene_files[0]
    original_file_parts = first_file.split('_scene')[0]
    
    # Generate filename with _rewritten suffix
    timestamp = int(time.time())
    compat_filename = f"{original_file_parts}_rewritten.json"
    compat_path = os.path.join(OUTPUT_DIR, compat_filename)
    
    # Load all scenes from the individual files
    all_scenes = []
    scene_numbers_found = set()
    
    for file_path in scene_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_scenes = json.load(f)
                
            if isinstance(file_scenes, list):
                for scene in file_scenes:
                    if isinstance(scene, dict) and 'scene_number' in scene:
                        scene_num = scene['scene_number']
                        
                        # Avoid duplicates by checking if we already have this scene
                        if scene_num not in scene_numbers_found:
                            all_scenes.append(scene)
                            scene_numbers_found.add(scene_num)
                            print(f"   ✓ Added scene {scene_num} from {os.path.basename(file_path)}")
        except Exception as e:
            print(f"   ⚠️ Error loading {os.path.basename(file_path)}: {e}")
    
    # Sort scenes by scene_number
    all_scenes.sort(key=lambda x: x.get('scene_number', 999))
    
    if not all_scenes:
        print("❌ Failed to extract any valid scenes from the individual files")
        return None
    
    print(f"✅ Successfully collected {len(all_scenes)} scenes")
    
    # Save the compatibility file
    try:
        with open(compat_path, 'w', encoding='utf-8') as f:
            json.dump(all_scenes, f, indent=2)
        
        print(f"✅ Saved compatibility file to: {compat_path}")
        print(f"   This file is for compatibility with older scripts")
        return compat_path
    except Exception as e:
        print(f"❌ Failed to save compatibility file: {e}")
        return None

def main():
    """Main function to rewrite scenes using trained model"""
    print("=== Gemini Scene Rewriter ===")
    print("This script will rewrite scene descriptions using the trained model for more cinematic output.")
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Rewrite scene descriptions using trained AI model")
    parser.add_argument("--scene_file", help="Path to scene JSON file")
    args = parser.parse_args()
    
    # Find the scene file
    scene_file = args.scene_file if args.scene_file else find_most_recent_scene_file()
    if not scene_file:
        print("No scene file found! Please provide a scene file with --scene_file.")
        return False
    
    print(f"Using scene file: {scene_file}")
    
    # Load the scene data
    scenes = load_scene_data(scene_file)
    if not scenes:
        return False
    
    print(f"Found {len(scenes)} scenes to rewrite.")
    
    try:
        # Setup Chrome options - exactly like gemini_scene_extractor.py
        options = webdriver.ChromeOptions()
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument(f"--user-data-dir={USER_DATA_DIR}")
        
        # Start browser
        print("\nStarting browser...")
        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 20)
        
        # Navigate to trained model
        print("Navigating to trained AI model...")
        driver.get("https://gemini.google.com/app/44ed85f1a1ea23d5")
        time.sleep(3)
        
        # Handle authentication - CRITICAL FIRST STEP
        authenticate_google(driver, wait)
        
        # Wait for page to load after authentication
        print("Waiting for Gemini interface to load...")
        time.sleep(5)
        
        # Process each scene individually and save immediately
        rewritten_scenes = []
        individual_scene_files = []
        total_scenes = len(scenes)
        
        print(f"\n=== STARTING REWRITE PROCESS FOR {total_scenes} SCENES ===")
        print("📝 Note: Each rewritten scene will be saved as an individual file.")
        print("📝 Individual scene files can be used by downstream scripts.")
        
        for i, scene in enumerate(scenes, 1):
            print(f"\nProcessing scene {i} of {total_scenes}...")
            
            # Add random delay before processing next scene (human-like behavior)
            if i > 1:
                human_delay(3, 8, "Taking a moment before processing next scene")
                
            rewritten_scene = rewrite_scene_with_gemini(driver, wait, scene)
            rewritten_scenes.append(rewritten_scene)
            
            print(f"✅ Scene {i} rewritten successfully. Progress: {i}/{total_scenes}")
            
            # Show a preview of what was rewritten
            if 'image_prompt' in rewritten_scene:
                preview = rewritten_scene['image_prompt'][:100] + "..." if len(rewritten_scene['image_prompt']) > 100 else rewritten_scene['image_prompt']
                print(f"   Preview: {preview}")
            
            # Save each scene individually as it's completed
            scene_file_path = save_individual_scene(rewritten_scene, scene_file)
            if scene_file_path:
                individual_scene_files.append(scene_file_path)
            
        # Create a compatibility file for downstream scripts if needed
        print(f"\n🎉 === REWRITING COMPLETE ===")
        print(f"✅ Successfully rewritten {len(rewritten_scenes)} scenes!")
        
        # Print summary of all rewritten scenes and files
        print(f"\n📋 === REWRITTEN SCENE SUMMARY ===")
        for scene in rewritten_scenes:
            scene_title = scene.get('scene_title', f"Scene {scene['scene_number']}")
            print(f"   Scene {scene['scene_number']}: {scene_title}")
        
        # Print detailed summary of individual scene files
        print_scene_files_summary(individual_scene_files)
        
        # Keep browser open for a moment before closing
        print("\n⏳ Keeping browser open for 5 seconds to view final results...")
        time.sleep(5)
            
        return True
        print("\n✅ Process complete.")
        return len(individual_scene_files) > 0
            
    except Exception as e:
        print(f"An error occurred: {e}")
        return False
        
    finally:
        print("Closing browser...")
        driver.quit()

def print_scene_files_summary(scene_files):
    """Print a summary of the individual scene files created"""
    print(f"\n🎯 === SCENE FILES SUMMARY ===")
    print(f"✅ Total individual scene files created: {len(scene_files)}")
    
    if scene_files:
        print(f"\n� Individual scene files:")
        for i, file_path in enumerate(scene_files[:10]):  # Show first 10
            print(f"   {i+1}. {os.path.basename(file_path)}")
        
        if len(scene_files) > 10:
            print(f"   ... and {len(scene_files) - 10} more files")
        
        print(f"\n🔍 File format:")
        print(f"   • Each file contains scene data in simple format: Scene(N):prompt")
        print(f"   • Filename pattern: original_filename_sceneN_timestamp.json")
        print(f"   • Where N is the scene number and timestamp is a unix timestamp")
        
        # Try to verify one of the files as example
        try:
            with open(scene_files[0], 'r', encoding='utf-8') as f:
                sample_data = json.load(f)
            print(f"\n✅ Sample file verification:")
            print(f"   • Valid JSON: Yes")
            print(f"   • File: {os.path.basename(scene_files[0])}")
            if isinstance(sample_data, dict):
                scene_keys = [k for k in sample_data.keys() if k.startswith('Scene(')]
                if scene_keys:
                    scene_key = scene_keys[0]
                    prompt_preview = sample_data[scene_key][:50] + "..." if len(sample_data[scene_key]) > 50 else sample_data[scene_key]
                    print(f"   • Contains: {scene_key}: {prompt_preview}")
        except:
            print(f"\n⚠️ Could not verify file format. Please check files manually.")
    else:
        print("\n⚠️ No scene files were created!")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
