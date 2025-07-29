import time
import os
import json
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# --- USER CONFIGURATION ---
# IMPORTANT: Replace with your Google account credentials
GOOGLE_EMAIL = "chaudharyabhishek031@gmail.com"
GOOGLE_PASSWORD = "GAme++0103"
USER_DATA_DIR = os.path.join(os.path.expanduser("~"), "selenium_chrome_profile")
OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "scene_data")

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- STORY CONFIGURATION ---
# Enter your story here between the triple quotes
STORY_TEXT = """
One day, a jackal called Gomaya was very hungry, and was wandering about in search of food.After some time, he wandered out of the jungle he lived in, and reached a deserted battlefield.In this deserted battlefield, a battle was fought recently. The fighting armies had left behind a drum, which was lying near a tree.As strong winds blew, the branches of the tree got rubbed against the drum. This made a strange noise.When the jackal heard this sound, he got very frightened and thought of running away, "If I cannot flee from here before I am seen by the person making all this noise, I will be in trouble".As he was about to run away, he had a second thought. "It is unwise to run away from something without knowing. Instead, I must be careful in finding out the source of this noise".He took the courage to creep forward cautiously. When he saw the drum, he realized that it was only the wind that was causing all the noise.He continued his search for food, and near the drum he found sufficient food and water."""

# Story title for filename (optional)
STORY_TITLE = "monkey_and_wedge_panchatantra"

# --- STORY PROMPT TEMPLATE ---
# Since the model is already trained at the specific link, we just send the story directly
STORY_ANALYSIS_PROMPT = "{story_text}"

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
    """Wait for Gemini to complete its response"""
    print("Waiting for Gemini response...")
    
    # Wait for response to appear and complete
    start_time = time.time()
    last_response_length = 0
    stable_count = 0
    
    while time.time() - start_time < timeout:
        try:
            # Look for response containers
            response_selectors = [
                "[data-response-id]",
                ".response-container",
                ".markdown",
                ".message-content",
                "[role='presentation']",
                ".model-response"
            ]
            
            response_text = ""
            for selector in response_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        for element in elements[-3:]:  # Check last few elements
                            if element.is_displayed():
                                text = element.get_attribute('textContent') or element.text
                                if text and len(text) > len(response_text):
                                    response_text = text
                        break
                except:
                    continue
            
            # If no specific selectors work, try getting all text from main content
            if not response_text:
                try:
                    main_content = driver.find_element(By.CSS_SELECTOR, "main, .conversation, .chat-container")
                    response_text = main_content.get_attribute('textContent') or main_content.text
                except:
                    pass
            
            current_length = len(response_text)
            
            # Check if response has stopped growing (indicating completion)
            if current_length == last_response_length:
                stable_count += 1
                if stable_count >= 3:  # Response has been stable for 3 checks
                    print("Response appears complete.")
                    return response_text
            else:
                stable_count = 0
                last_response_length = current_length
                print(f"Response length: {current_length} characters...")
            
            time.sleep(2)
            
        except Exception as e:
            print(f"Error while waiting for response: {e}")
            time.sleep(2)
    
    print("Timeout reached while waiting for response.")
    return None

def extract_scene_data(response_text):
    """Extract structured scene data from Gemini's response"""
    print("Extracting scene data from response...")
    
    scenes = []
    
    # Try multiple patterns to match different formats
    
    # Pattern 1: Standard format with line breaks
    scene_pattern_1 = r'Scene\s*\((\d+)\):\s*\n(.*?)(?=Scene\s*\(\d+\):|$)'
    matches_1 = re.findall(scene_pattern_1, response_text, re.DOTALL | re.IGNORECASE)
    
    # Pattern 2: Inline format (Scene 1: Title...Scene 2: Title...)
    scene_pattern_2 = r'Scene\s*(\d+):\s*(.*?)(?=Scene\s*\d+:|$)'
    matches_2 = re.findall(scene_pattern_2, response_text, re.DOTALL | re.IGNORECASE)
    
    # Use whichever pattern found more matches
    matches = matches_1 if len(matches_1) > len(matches_2) else matches_2
    
    print(f"Found {len(matches)} potential scenes using pattern matching")
    
    for scene_num, scene_content in matches:
        scene_data = {
            'scene_number': int(scene_num),
            'scene_title': '',
            'image_prompt': '',
            'composition': '',
            'lighting': '',
            'art_style': '',
            'technical_parameters': '--ar 16:9'
        }
        
        # Extract individual fields with more flexible patterns
        content = scene_content.strip()
        
        # Extract Scene Title
        title_patterns = [
            r'Scene\s+Title:\s*([^\n]*?)(?:Image\s+Prompt:|Composition:|$)',
            r'^([^\n]*?)(?:Image\s+Prompt:|Scene\s+Title:|$)',
            r'Scene\s+Title:\s*([^\.]*?)(?=\.|\n|Image\s+Prompt:|Composition:)'
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
            if match and match.group(1).strip():
                scene_data['scene_title'] = match.group(1).strip()
                break
        
        # Extract Image Prompt
        prompt_patterns = [
            r'Image\s+Prompt:\s*(.*?)(?=Composition:|Lighting:|Art\s+Style:|Technical\s+Parameters:|Scene\s+\d+:|$)',
            r'Image\s+Prompt:\s*([^\.]*?)(?=\..*?Composition:|\..*?Lighting:|\..*?Art\s+Style:)'
        ]
        
        for pattern in prompt_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match and match.group(1).strip():
                scene_data['image_prompt'] = match.group(1).strip()
                break
        
        # Extract Composition
        comp_patterns = [
            r'Composition:\s*(.*?)(?=Lighting:|Art\s+Style:|Technical\s+Parameters:|Scene\s+\d+:|$)',
            r'Composition:\s*([^\.]*?)(?=\..*?Lighting:|\..*?Art\s+Style:|\..*?Technical)'
        ]
        
        for pattern in comp_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match and match.group(1).strip():
                scene_data['composition'] = match.group(1).strip()
                break
        
        # Extract Lighting
        lighting_patterns = [
            r'Lighting:\s*(.*?)(?=Art\s+Style:|Technical\s+Parameters:|Scene\s+\d+:|$)',
            r'Lighting:\s*([^\.]*?)(?=\..*?Art\s+Style:|\..*?Technical)'
        ]
        
        for pattern in lighting_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match and match.group(1).strip():
                scene_data['lighting'] = match.group(1).strip()
                break
        
        # Extract Art Style
        style_patterns = [
            r'Art\s+Style:\s*(.*?)(?=Technical\s+Parameters:|Scene\s+\d+:|$)',
            r'Art\s+Style:\s*([^\.]*?)(?=\..*?Technical|$)'
        ]
        
        for pattern in style_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match and match.group(1).strip():
                scene_data['art_style'] = match.group(1).strip()
                break
        
        # Extract Technical Parameters
        tech_patterns = [
            r'Technical\s+Parameters:\s*(.*?)(?=Scene\s+\d+:|$)',
            r'Technical\s+Parameters:\s*([^\n]*)',
            r'--ar\s+16:9'
        ]
        
        for pattern in tech_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                tech_params = match.group(1).strip() if len(match.groups()) > 0 else match.group(0)
                if tech_params:
                    scene_data['technical_parameters'] = tech_params
                    break
        
        # Clean up extracted text
        for key in scene_data:
            if isinstance(scene_data[key], str):
                # Remove extra whitespace and clean up
                scene_data[key] = re.sub(r'\s+', ' ', scene_data[key]).strip()
                # Remove trailing punctuation from titles
                if key == 'scene_title':
                    scene_data[key] = scene_data[key].rstrip('.,!?:')
        
        # Only add scene if it has meaningful content
        if scene_data['image_prompt'] or scene_data['scene_title']:
            scenes.append(scene_data)
            print(f"Extracted Scene {scene_data['scene_number']}: {scene_data['scene_title']}")
    
    print(f"Successfully extracted {len(scenes)} scenes from response.")
    return scenes

def save_scene_data(scenes, story_title="story"):
    """Save scene data to JSON file"""
    timestamp = int(time.time())
    filename = f"{story_title}_scenes_{timestamp}.json"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(scenes, f, indent=2, ensure_ascii=False)
    
    print(f"Scene data saved to: {filepath}")
    return filepath

def main():
    # Use story from script configuration
    print("=== Gemini Scene Extractor ===")
    print("This script will analyze your story and extract scene data for image generation.")
    
    # Get story from configuration
    story_text = STORY_TEXT.strip()
    
    if not story_text or story_text == "Enter your story here...":
        print("Error: Please edit the STORY_TEXT variable in the script with your actual story.")
        print("Look for the STORY_TEXT variable at the top of the script and replace the placeholder text.")
        return
    
    # Use story title from configuration
    story_title = STORY_TITLE.strip()
    if not story_title:
        story_title = "story"
    
    # Clean title for filename
    story_title = re.sub(r'[^\w\s-]', '', story_title).strip()
    story_title = re.sub(r'[-\s]+', '_', story_title)
    
    print(f"Processing story: '{story_title}'")
    print(f"Story length: {len(story_text)} characters")
    
    # Setup Chrome options
    options = webdriver.ChromeOptions()
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"--user-data-dir={USER_DATA_DIR}")
    
    # Start browser
    print("\nStarting browser...")
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)
    
    try:
        # Navigate to Gemini
        print("Navigating to Gemini...")
        driver.get("https://gemini.google.com/app/b58951e9acc687c4")

       
        time.sleep(3)
        
        # Handle authentication
        authenticate_google(driver, wait)
        
        
        
        # Wait for page to load
        print("Waiting for Gemini interface to load...")
        time.sleep(5)
        
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
            print("Could not find chat input field. Taking screenshot for debugging...")
            driver.save_screenshot(os.path.join(OUTPUT_DIR, "debug_no_input.png"))
            return
        
        # Prepare the full prompt
        full_prompt = STORY_ANALYSIS_PROMPT.format(story_text=story_text)

    
        
        # Send the prompt
        print("Sending story analysis prompt to Gemini...")
        chat_input.click()
        time.sleep(1)
        
        # Type the prompt (splitting into chunks to avoid issues with long text)
        chunk_size = 1000
        for i in range(0, len(full_prompt), chunk_size):
            chunk = full_prompt[i:i + chunk_size]
            chat_input.send_keys(chunk)
            time.sleep(0.1)  # Small delay between chunks
        
        # Send the message
        chat_input.send_keys(Keys.ENTER)
        print("Prompt sent. Waiting for Gemini response...")
        
        # MANDATORY WAIT: Wait at least 150 seconds before reading response
        # This ensures we don't read cached/stale data from previous responses
        print("Implementing mandatory 150-second wait to ensure fresh response...")
        print("This prevents reading cached or ambiguous data from previous interactions.")
        
        for remaining in range(100, 0, -10):
            print(f"Waiting {remaining} more seconds before reading response...")
            time.sleep(10)
        
        print("Mandatory wait completed. Now reading fresh response...")
        
        # Wait for response
        response_text = wait_for_gemini_response(driver, wait)
        
        if response_text:
            print("Response received! Processing scene data...")
            
            # Save raw response for debugging
            raw_response_file = os.path.join(OUTPUT_DIR, f"{story_title}_raw_response_{int(time.time())}.txt")
            with open(raw_response_file, 'w', encoding='utf-8') as f:
                f.write(response_text)
            print(f"Raw response saved to: {raw_response_file}")
            
            # Extract scene data
            scenes = extract_scene_data(response_text)
            
            if scenes:
                # Save structured scene data
                scene_file = save_scene_data(scenes, story_title)
                
                print(f"\n=== SUCCESS ===")
                print(f"Extracted {len(scenes)} scenes from your story!")
                print(f"Scene data saved to: {scene_file}")
                print(f"Raw response saved to: {raw_response_file}")
                
                # Print summary
                print(f"\n=== SCENE SUMMARY ===")
                for scene in scenes:
                    print(f"Scene {scene['scene_number']}: {scene['scene_title']}")
                
            else:
                print("No scenes could be extracted from the response.")
                print("Check the raw response file for debugging.")
        else:
            print("No response received from Gemini.")
            
        print("\nKeeping browser open for 10 seconds to view results...")
        time.sleep(200)
        
    except Exception as e:
        print(f"An error occurred: {e}")
        # Take screenshot for debugging
        driver.save_screenshot(os.path.join(OUTPUT_DIR, f"debug_error_{int(time.time())}.png"))
        
    finally:
        print("Closing browser...")
        driver.quit()

if __name__ == "__main__":
    main()