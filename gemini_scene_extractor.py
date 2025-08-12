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
STORY_TEXT = """One day, a jackal called Gomaya was very hungry, and was wandering about in search of food.After some time, he wandered out of the jungle he lived in, and reached a deserted battlefield.In this deserted battlefield, a battle was fought recently. The fighting armies had left behind a drum, which was lying near a tree.As strong winds blew, the branches of the tree got rubbed against the drum. This made a strange noise.When the jackal heard this sound, he got very frightened and thought of running away, "If I cannot flee from here before I am seen by the person making all this noise, I will be in trouble".As he was about to run away, he had a second thought. "It is unwise to run away from something without knowing. Instead, I must be careful in finding out the source of this noise".He took the courage to creep forward cautiously. When he saw the drum, he realized that it was only the wind that was causing all the noise.He continued his search for food, and near the drum he found sufficient food and water."""
# Story title for filename (optional)
STORY_TITLE = "Jackal"

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

def read_latest_gemini_response(driver, wait):
    """Read the latest response from the current Gemini conversation"""
    print("Reading the latest response from Gemini conversation...")
    
    try:
        # Wait a moment for the page to settle
        time.sleep(3)
        
        # Try multiple selectors to find response content
        response_selectors = [
            # Gemini-specific selectors (most likely)
            "[data-message-author-role='model']",
            ".model-response-text",
            ".response-container",
            "[role='presentation']",
            ".markdown",
            ".message-content",
            
            # Generic selectors as fallback
            ".conversation .message:last-child",
            ".chat-message:last-child",
            "main .message:last-child"
        ]
        
        response_text = ""
        response_element = None
        
        for selector in response_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    # Get the last (most recent) response element
                    for element in reversed(elements):
                        if element.is_displayed():
                            text = element.get_attribute('textContent') or element.text
                            if text and len(text.strip()) > 100:  # Ensure it's substantial content
                                response_text = text.strip()
                                response_element = element
                                print(f"Found response using selector: {selector}")
                                break
                    if response_text:
                        break
            except Exception as e:
                print(f"Selector '{selector}' failed: {e}")
                continue
        
        # If no specific selectors work, try to get the main conversation content
        if not response_text:
            print("Trying to extract from main conversation area...")
            try:
                main_selectors = [
                    "main",
                    ".conversation",
                    ".chat-container",
                    "#main-content",
                    ".content"
                ]
                
                for main_selector in main_selectors:
                    try:
                        main_element = driver.find_element(By.CSS_SELECTOR, main_selector)
                        full_text = main_element.get_attribute('textContent') or main_element.text
                        
                        # Try to extract the last substantial block of text
                        # Look for patterns that indicate a Gemini response
                        if full_text:
                            # Split by common separators and get the last substantial chunk
                            chunks = full_text.split('\n\n')
                            for chunk in reversed(chunks):
                                if len(chunk.strip()) > 200 and ('Scene' in chunk or 'scene' in chunk):
                                    response_text = chunk.strip()
                                    print(f"Extracted response from main content using {main_selector}")
                                    break
                            if response_text:
                                break
                    except:
                        continue
            except Exception as e:
                print(f"Error extracting from main content: {e}")
        
        if response_text:
            print(f"Successfully extracted response ({len(response_text)} characters)")
            print(f"Response preview: {response_text[:200]}...")
            return response_text
        else:
            print("❌ Could not find any response content on the page")
            
            # Debug: Save screenshot and page source
            print("Saving debug information...")
            driver.save_screenshot(os.path.join(OUTPUT_DIR, f"debug_no_response_{int(time.time())}.png"))
            
            # Try to get all text content for debugging
            try:
                all_text = driver.find_element(By.TAG_NAME, "body").text
                debug_file = os.path.join(OUTPUT_DIR, f"debug_page_content_{int(time.time())}.txt")
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write("=== FULL PAGE TEXT ===\n")
                    f.write(all_text)
                print(f"Full page content saved to: {debug_file}")
            except:
                pass
            
            return None
            
    except Exception as e:
        print(f"Error reading response: {e}")
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

# Add a helper function to clean up the STORY_TEXT configuration
# This removes the need to edit the story prompt format since we're reading existing responses

def get_story_title_for_filename():
    """Get a clean story title for filename generation"""
    title = STORY_TITLE.strip()
    if not title or title == "The Biggest Fool In The Kingdom!":
        # Try to derive from current timestamp if default title
        title = f"story_{int(time.time())}"
    
    # Clean title for filename
    title = re.sub(r'[^\w\s-]', '', title).strip()
    title = re.sub(r'[-\s]+', '_', title)
    return title

def send_story_to_gemini(driver, wait, story_text):
    """Send a new story to Gemini and wait for response"""
    print("Sending new story to Gemini...")
    
    try:
        # Look for the input field/textarea
        input_selectors = [
            "textarea[placeholder*='Enter a prompt']",
            "textarea[placeholder*='Message']", 
            ".ql-editor",
            "[contenteditable='true']",
            "textarea",
            ".input-field",
            ".prompt-textarea"
        ]
        
        input_element = None
        for selector in input_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        input_element = element
                        print(f"Found input using selector: {selector}")
                        break
                if input_element:
                    break
            except:
                continue
        
        if not input_element:
            print("❌ Could not find input field. Please make sure you're on the Gemini chat page.")
            return False
        
        # Clear any existing text and send the story
        input_element.click()
        time.sleep(1)
        
        # Clear existing content
        input_element.clear()
        time.sleep(0.5)
        
        # Type the story
        print("Typing the story...")
        input_element.send_keys(story_text)
        time.sleep(2)
        
        # Send the message (try Enter or look for send button)
        print("Sending the story...")
        try:
            input_element.send_keys(Keys.RETURN)
        except:
            # Try to find and click send button
            send_selectors = [
                "[aria-label*='Send']",
                "button[type='submit']",
                ".send-button",
                "[data-testid*='send']"
            ]
            
            send_button = None
            for selector in send_selectors:
                try:
                    send_button = driver.find_element(By.CSS_SELECTOR, selector)
                    if send_button.is_displayed():
                        send_button.click()
                        break
                except:
                    continue
        
        print("✅ Story sent successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error sending story: {e}")
        return False

def wait_for_gemini_response(driver, wait, timeout_seconds=150):
    """Wait for Gemini to generate a response"""
    print(f"Waiting for Gemini response (timeout: {timeout_seconds} seconds)...")
    
    start_time = time.time()
    last_length = 0
    stable_count = 0
    
    while time.time() - start_time < timeout_seconds:
        try:
            # Check for response content
            response_text = read_latest_gemini_response(driver, wait)
            
            if response_text:
                current_length = len(response_text)
                
                # Check if response is growing (being generated)
                if current_length > last_length:
                    last_length = current_length
                    stable_count = 0
                    print(f"Response growing... ({current_length} characters)")
                else:
                    stable_count += 1
                    
                # If response has been stable for 3 checks (15 seconds), consider it complete
                if stable_count >= 3 and current_length > 500:
                    print(f"✅ Response appears complete ({current_length} characters)")
                    return response_text
            
            time.sleep(5)  # Check every 5 seconds
            
        except Exception as e:
            print(f"Error while waiting: {e}")
            time.sleep(5)
    
    print(f"⚠️ Timeout reached ({timeout_seconds}s). Attempting to read current response...")
    return read_latest_gemini_response(driver, wait)

def main():
    # Use story from script configuration
    print("=== Gemini Scene Extractor ===")
    print("This script can either:")
    print("1. Read the latest response from your current Gemini conversation")
    print("2. Send a new story and wait for Gemini's response")
    
    # Ask user what they want to do
    print("\nChoose an option:")
    print("1. Read existing response from current conversation")
    print("2. Send new story and wait for response")
    
    while True:
        choice = input("Enter choice (1 or 2): ").strip()
        if choice in ['1', '2']:
            break
        print("Please enter 1 or 2")
    
    send_new_story = (choice == '2')
    
    # Use story title from configuration for filename
    story_title = get_story_title_for_filename()
    
    print(f"\nProcessing conversation for: '{story_title}'")
    
    if send_new_story:
        print(f"\nStory to be sent:")
        print("-" * 50)
        print(STORY_TEXT[:200] + "..." if len(STORY_TEXT) > 200 else STORY_TEXT)
        print("-" * 50)
        
        confirm = input("\nSend this story to Gemini? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Cancelled.")
            return
    
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
        
        # Handle authentication if needed
        authenticate_google(driver, wait)
        
        # Wait for page to load
        print("Waiting for Gemini interface to load...")
        time.sleep(5)
        
        response_text = None
        
        if send_new_story:
            print("\n" + "="*60)
            print("SENDING NEW STORY TO GEMINI")
            print("="*60)
            
            # Send the story
            if send_story_to_gemini(driver, wait, STORY_TEXT):
                # Wait for response
                response_text = wait_for_gemini_response(driver, wait, timeout_seconds=150)
            else:
                print("❌ Failed to send story to Gemini")
                return
        else:
            print("\n" + "="*60)
            print("READING EXISTING RESPONSE FROM CONVERSATION")
            print("="*60)
            print("The script will now read the latest response that's already")
            print("displayed in your Gemini conversation.")
            print("Make sure you have already asked Gemini to analyze your story!")
            print("="*60)
            
            # Read the latest response from the page
            response_text = read_latest_gemini_response(driver, wait)
        
        if response_text:
            print("✅ Response found! Processing scene data...")
            
            # Save raw response for debugging
            raw_response_file = os.path.join(OUTPUT_DIR, f"{story_title}_raw_response_{int(time.time())}.txt")
            with open(raw_response_file, 'w', encoding='utf-8') as f:
                f.write("=== EXTRACTED RESPONSE ===\n")
                f.write(f"Extracted at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Story title: {story_title}\n")
                f.write("="*50 + "\n\n")
                f.write(response_text)
            print(f"Raw response saved to: {raw_response_file}")
            
            # Extract scene data
            scenes = extract_scene_data(response_text)
            
            if scenes:
                # Save structured scene data
                scene_file = save_scene_data(scenes, story_title)
                
                print(f"\n" + "="*50)
                print("SUCCESS!")
                print("="*50)
                print(f"✅ Extracted {len(scenes)} scenes from the response!")
                print(f"📄 Scene data saved to: {scene_file}")
                print(f"📝 Raw response saved to: {raw_response_file}")
                
                # Print summary
                print(f"\n📋 SCENE SUMMARY:")
                print("-" * 30)
                for scene in scenes:
                    print(f"Scene {scene['scene_number']}: {scene['scene_title']}")
                print("-" * 30)
                print(f"Total scenes: {len(scenes)}")
                
            else:
                print("\n❌ No scenes could be extracted from the response.")
                print("💡 Possible reasons:")
                print("   - The response doesn't contain scene breakdowns")
                print("   - The format is different than expected")
                print("   - You may need to ask Gemini to break down your story into scenes first")
                print(f"📝 Check the raw response file for debugging: {raw_response_file}")
        else:
            print("\n❌ No response found on the page.")
            print("💡 Make sure you:")
            print("   1. Have already sent your story to Gemini")
            print("   2. Received a response with scene breakdowns")
            print("   3. Are on the correct Gemini conversation page")
            
        print(f"\nKeeping browser open for 30 seconds so you can view the results...")
        print("You can close this manually or wait for auto-close.")
        time.sleep(30)
        
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        # Take screenshot for debugging
        debug_screenshot = os.path.join(OUTPUT_DIR, f"debug_error_{int(time.time())}.png")
        try:
            driver.save_screenshot(debug_screenshot)
            print(f"Debug screenshot saved to: {debug_screenshot}")
        except:
            pass
        
    finally:
        print("\n🔄 Closing browser...")
        driver.quit()
        print("✅ Done!")

if __name__ == "__main__":
    main()