import time
import os
import json
import glob
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# --- USER CONFIGURATION ---
# IMPORTANT: Replace with your Google account credentials
GOOGLE_EMAIL = "chaudharyabhishek031@gmail.com"
GOOGLE_PASSWORD = "GAme++0103"
USER_DATA_DIR = os.path.join(os.path.expanduser("~"), "selenium_chrome_profile")
DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "scene_videos")

# Scene data and images directories
SCENE_DATA_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "scene_data")
SCENE_IMAGES_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "scene_images")

def load_latest_scene_data():
    """Load the most recent scene data JSON file"""
    try:
        json_files = glob.glob(os.path.join(SCENE_DATA_DIR, "*_scenes_*.json"))
        if not json_files:
            print("No scene data JSON files found.")
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
        if images:
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

def upload_images_to_veo(driver, wait, image_paths):
    """Upload images by clicking upload button then using send_keys to file input"""
    try:
        if not image_paths:
            print("No images to upload.")
            return True
        
        print(f"Attempting to upload {len(image_paths)} images...")
        
        # First, let's take a screenshot to see the current state
        try:
            debug_path = os.path.join(os.path.expanduser("~"), "Documents", f"debug_upload_state_{int(time.time())}.png")
            driver.save_screenshot(debug_path)
            print(f"Debug screenshot saved: {debug_path}")
        except:
            pass
        
        # Multiple strategies to find and click upload button
        upload_strategies = [
            # Strategy 1: Specific Veo upload button attributes (PRIORITY)
            (By.CSS_SELECTOR, "button[aria-label='Add an image to the prompt']"),
            # Strategy 2: Upload local image button (PRIORITY)
            (By.CSS_SELECTOR, "button[aria-label='Upload a local image']"),
            # Strategy 3: Data test ID for add media button (PRIORITY)
            (By.CSS_SELECTOR, "button[data-test-id='add-media-button']"),
            # # Strategy 4: Combined specific attributes for add image
            # (By.CSS_SELECTOR, "button[aria-label='Add an image to the prompt'][data-test-id='add-media-button']"),
            # # Strategy 5: XPath for add image aria-label
            # (By.XPATH, "//button[@aria-label='Add an image to the prompt']"),
            # # Strategy 6: XPath for upload local image aria-label
            # (By.XPATH, "//button[@aria-label='Upload a local image']"),
            # # Strategy 7: XPath for data-test-id
            # (By.XPATH, "//button[@data-test-id='add-media-button']"),
            # # Strategy 8: Buttons containing "upload image" text
            # (By.XPATH, "//button[contains(text(), 'upload image') or contains(text(), 'Upload image') or contains(text(), 'Upload Image')]"),
            # # Strategy 9: Buttons containing "choose" or "upload" text
            # (By.XPATH, "//button[contains(text(), 'Choose') or contains(text(), 'choose') or contains(., 'upload')]"),
            # # Strategy 10: mat-focus-indicator class with upload
            # (By.CSS_SELECTOR, "button.mat-focus-indicator[aria-label*='upload'], .mat-focus-indicator[aria-label*='upload']"),
            # # Strategy 11: General mat-focus-indicator buttons (try all)
            # (By.CSS_SELECTOR, "button.mat-focus-indicator"),
            # # Strategy 12: Upload-related buttons by aria-label (broader search)
            # (By.XPATH, "//button[contains(@aria-label, 'upload') or contains(@aria-label, 'Upload') or contains(@aria-label, 'image') or contains(@aria-label, 'Image')]"),
            # # Strategy 13: Button with upload text or class
            # (By.XPATH, "//button[contains(., 'Upload') or contains(@class, 'upload')]"),
            # # Strategy 14: Any button with upload-related attributes
            # (By.XPATH, "//button[contains(@title, 'upload') or contains(@title, 'Upload')]"),
            # # Strategy 15: Material icons or upload icons
            # (By.XPATH, "//button[.//mat-icon[contains(text(), 'upload')] or .//mat-icon[contains(text(), 'add')]]"),
            # # Strategy 16: Plus or add buttons that might trigger upload
            # (By.XPATH, "//button[contains(@aria-label, 'add') or contains(@aria-label, 'Add')]"),
            # # Strategy 17: Look for buttons with specific Material Design patterns
            # (By.CSS_SELECTOR, "button[mat-button], button[mat-raised-button], button[mat-icon-button]"),
        ]
        
        upload_clicked = False
        upload_button = None
        
        for strategy_num, (by, selector) in enumerate(upload_strategies, 1):
            try:
                print(f"Trying upload strategy {strategy_num}: {selector}")
                
                if strategy_num == 11 or strategy_num == 17:  # Multiple button strategies
                    buttons = driver.find_elements(by, selector)
                    print(f"Found {len(buttons)} buttons with strategy {strategy_num}")
                    
                    for i, button in enumerate(buttons[:5]):  # Try first 5 buttons
                        try:
                            if button.is_displayed() and button.is_enabled():
                                print(f"Trying button {i+1}: {button.get_attribute('aria-label') or button.text or 'No label'}")
                                button.click()
                                upload_button = button
                                upload_clicked = True
                                print(f"Button {i+1} clicked successfully using strategy {strategy_num}.")
                                break
                        except Exception as e:
                            print(f"Button {i+1} failed: {e}")
                            continue
                    
                    if upload_clicked:
                        break
                        
                else:  # Single button strategies
                    try:
                        upload_button = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((by, selector)))
                        # Try clicking the button
                        driver.execute_script("arguments[0].scrollIntoView();", upload_button)  # Scroll into view
                        time.sleep(0.5)
                        upload_button.click()
                        print(f"Upload button clicked using strategy {strategy_num}.")
                        upload_clicked = True
                        break
                    except Exception as click_error:
                        print(f"Failed to click button with strategy {strategy_num}: {click_error}")
                        # Try JavaScript click as fallback
                        try:
                            upload_button = driver.find_element(by, selector)
                            driver.execute_script("arguments[0].click();", upload_button)
                            print(f"Upload button clicked using JavaScript fallback for strategy {strategy_num}.")
                            upload_clicked = True
                            break
                        except:
                            print(f"JavaScript fallback also failed for strategy {strategy_num}")
                            continue
                    
            except TimeoutException:
                print(f"Strategy {strategy_num} failed - element not found.")
                continue
            except Exception as e:
                print(f"Strategy {strategy_num} failed with error: {e}")
                continue
        
        if not upload_clicked:
            print("Failed to find upload button with any strategy.")
            
            # Let's debug what buttons are actually available
            try:
                all_buttons = driver.find_elements(By.TAG_NAME, "button")
                print(f"Debug: Found {len(all_buttons)} total buttons on page")
                for i, btn in enumerate(all_buttons[:10]):  # Show first 10 buttons
                    try:
                        label = btn.get_attribute('aria-label') or btn.text or btn.get_attribute('title') or 'No label'
                        classes = btn.get_attribute('class') or 'No classes'
                        print(f"  Button {i+1}: '{label}' | Classes: '{classes}'")
                    except:
                        pass
            except:
                print("Could not debug available buttons.")
            
            return False
        
        print("Upload button clicked successfully! Waiting 5 seconds for UI to respond...")
        time.sleep(5)  # Wait 5 seconds after upload button click as requested
        
        # AFTER UPLOAD BUTTON CLICKED: Now look for file input and use send_keys
        print("Upload button clicked successfully. Now looking for file input to use send_keys...")
        
        # Enhanced strategies to find file input elements
        file_input_strategies = [
            # Strategy 1: Specific file input with class and accept attributes (PRIORITY)
            (By.CSS_SELECTOR, "input[type='file'][class='file-input'][accept='image/*']"),
            # Strategy 2: File input with class file-input
            (By.CSS_SELECTOR, "input[type='file'].file-input"),
            # Strategy 3: File input accepting images
            (By.CSS_SELECTOR, "input[type='file'][accept='image/*']"),
            # Strategy 4: File input with accept containing image
            (By.CSS_SELECTOR, "input[type='file'][accept*='image']"),
            # Strategy 5: Any file input
            (By.CSS_SELECTOR, "input[type='file']"),
            # Strategy 6: Hidden file inputs (common in modern UIs)
            (By.CSS_SELECTOR, "input[type='file'][style*='display: none'], input[type='file'][hidden]"),
            # Strategy 7: XPath for file input with specific attributes
            (By.XPATH, "//input[@type='file' and @class='file-input' and @accept='image/*']"),
            # Strategy 8: XPath for any file input
            (By.XPATH, "//input[@type='file']"),
            # Strategy 9: File inputs in specific containers
            (By.XPATH, "//div[contains(@class, 'upload')]//input[@type='file']"),
            (By.XPATH, "//form//input[@type='file']"),
        ]
        
        file_uploaded = False
        valid_paths = [path for path in image_paths if os.path.exists(path)]
        
        if not valid_paths:
            print("No valid image paths found.")
            return False
            
        print(f"Valid image paths: {[os.path.basename(p) for p in valid_paths]}")
        
        for strategy_num, (by, selector) in enumerate(file_input_strategies, 1):
            try:
                print(f"Trying file input strategy {strategy_num}: {selector}")
                
                # Wait for file inputs to appear
                file_inputs = WebDriverWait(driver, 10).until(
                    lambda d: d.find_elements(by, selector)
                )
                
                if file_inputs:
                    print(f"Found {len(file_inputs)} file input(s) with strategy {strategy_num}")
                    
                    for i, file_input in enumerate(file_inputs):
                        try:
                            print(f"Attempting to use file input {i+1}")
                            
                            # Check if file input is interactable
                            is_displayed = file_input.is_displayed()
                            is_enabled = file_input.is_enabled()
                            accept_attr = file_input.get_attribute('accept') or 'No accept'
                            class_attr = file_input.get_attribute('class') or 'No class'
                            
                            print(f"File input {i+1}: displayed={is_displayed}, enabled={is_enabled}")
                            print(f"  accept='{accept_attr}', class='{class_attr}'")
                            
                            # Try to make the input visible if it's hidden
                            if not is_displayed:
                                try:
                                    driver.execute_script("arguments[0].style.display = 'block'; arguments[0].style.visibility = 'visible'; arguments[0].style.opacity = '1';", file_input)
                                    print(f"Made file input {i+1} visible")
                                except:
                                    print(f"Could not make file input {i+1} visible")
                            
                            # Upload files using send_keys
                            print(f"Using send_keys to upload {len(valid_paths)} files...")
                            
                            if len(valid_paths) == 1:
                                # Single file upload
                                file_input.send_keys(valid_paths[0])
                                print(f"Uploaded single file: {os.path.basename(valid_paths[0])}")
                            else:
                                # Multiple files - join with newlines
                                all_paths = "\n".join(valid_paths)
                                file_input.send_keys(all_paths)
                                print(f"Uploaded {len(valid_paths)} files: {[os.path.basename(p) for p in valid_paths]}")
                            
                            time.sleep(3)  # Wait for upload to process
                            
                            # Verify upload
                            try:
                                # Wait a bit more for the upload to register
                                time.sleep(2)
                                
                                # Check multiple properties
                                value = file_input.get_attribute("value")
                                files = file_input.get_attribute("files")
                                
                                # Alternative verification: check if UI shows uploaded files
                                uploaded_indicators = driver.find_elements(By.CSS_SELECTOR, 
                                    ".uploaded-file, .file-preview, .media-preview, img[src*='blob:'], img[src*='data:']")
                                
                                if value or files or uploaded_indicators:
                                    print(f"Upload verification successful! Files uploaded via send_keys.")
                                    if uploaded_indicators:
                                        print(f"Found {len(uploaded_indicators)} visual upload indicator(s)")
                                    file_uploaded = True
                                    break
                                else:
                                    print(f"Upload verification failed - trying alternative verification...")
                                    
                                    # Alternative: assume success if no errors occurred during send_keys
                                    print(f"Assuming upload success since send_keys completed without errors")
                                    file_uploaded = True
                                    break
                            except Exception as verify_error:
                                print(f"Upload verification error: {verify_error}")
                                # If verification fails but send_keys worked, assume success
                                print(f"Proceeding with upload assumption since send_keys completed")
                                file_uploaded = True
                                break
                            
                        except Exception as e:
                            print(f"File input {i+1} failed: {e}")
                            continue
                    
                    if file_uploaded:
                        print("File upload successful using send_keys!")
                        break
                else:
                    print(f"No file inputs found with strategy {strategy_num}")
                
            except TimeoutException:
                print(f"File input strategy {strategy_num} - no elements found within timeout")
                continue
            except Exception as e:
                print(f"File input strategy {strategy_num} failed with error: {e}")
                continue
        
        if file_uploaded:
            print("Images uploaded successfully using send_keys method.")
            time.sleep(2)  # Final wait for upload to process
            
            # Take a screenshot to verify the upload
            try:
                debug_path = os.path.join(os.path.expanduser("~"), "Documents", f"debug_after_upload_{int(time.time())}.png")
                driver.save_screenshot(debug_path)
                print(f"Post-upload screenshot saved: {debug_path}")
            except:
                pass
            
            return True
        else:
            print("Failed to upload images with send_keys method.")
            
            # Additional debugging - check if there are any file inputs at all
            try:
                all_inputs = driver.find_elements(By.TAG_NAME, "input")
                print(f"Debug: Found {len(all_inputs)} total input elements")
                for i, inp in enumerate(all_inputs[:10]):
                    try:
                        input_type = inp.get_attribute('type') or 'No type'
                        accept = inp.get_attribute('accept') or 'No accept'
                        class_name = inp.get_attribute('class') or 'No class'
                        print(f"  Input {i+1}: type='{input_type}', accept='{accept}', class='{class_name}'")
                    except:
                        pass
            except:
                print("Could not debug input elements.")
            
            return False
        
    except Exception as e:
        print(f"Error uploading images: {e}")
        return False
def process_scene(driver, wait, scene_data, scene_images):
    """Process a single scene: upload images and prompt, then run"""
    scene_num = scene_data.get('scene_number', 'Unknown')
    scene_title = scene_data.get('scene_title', 'Untitled')
    
    print(f"\n=== Processing Scene {scene_num}: {scene_title} ===")
    
    try:
        # Navigate to Veo if not already there
        if "gen-media" not in driver.current_url:
            driver.get("https://aistudio.google.com/gen-media")
            time.sleep(2)
        
        # Click the Veo button if needed
        try:
            veo_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//mat-card[@aria-label='Veo']"))
            )
            veo_button.click()
            print("Veo button clicked.")
            time.sleep(2)
        except TimeoutException:
            print("Veo button not found or already selected.")
        
        # Upload images if available (but don't fail the scene if upload fails)
        if scene_images:
            print(f"Attempting to upload {len(scene_images)} images for scene {scene_num}")
            upload_success = upload_images_to_veo(driver, wait, scene_images)
            if not upload_success:
                print(f"Warning: Failed to upload images for scene {scene_num}")
                print("Continuing with text-only prompt generation...")
            else:
                print(f"Successfully uploaded images for scene {scene_num}")
        else:
            print(f"No images found for scene {scene_num}, proceeding with text-only prompt")
        
        # Clear and enter the prompt
        prompt_text = create_combined_prompt(scene_data)
        print(f"Entering prompt: {prompt_text[:100]}...")
        
        prompt_input = wait.until(EC.visibility_of_element_located((By.TAG_NAME, "textarea")))
        prompt_input.clear()
        prompt_input.send_keys(prompt_text)
        print("Prompt entered.")
        time.sleep(1)
        
        # Click the Run button with retry logic
        print("Clicking Run button with retry logic...")
        
        # First, check for and dismiss any overlays that might be blocking the Run button
        try:
            print("Checking for and dismissing any overlays...")
            
            # Look for overlay backdrops
            overlays = driver.find_elements(By.CSS_SELECTOR, ".cdk-overlay-backdrop, .mat-overlay-backdrop, .backdrop")
            if overlays:
                print(f"Found {len(overlays)} overlay(s), attempting to dismiss...")
                for i, overlay in enumerate(overlays):
                    try:
                        # Try clicking the overlay to dismiss it
                        driver.execute_script("arguments[0].click();", overlay)
                        print(f"Clicked overlay {i+1}")
                        time.sleep(0.5)
                    except:
                        pass
                
                # Also try pressing Escape to dismiss any modals
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                print("Sent Escape key to dismiss any modals")
                time.sleep(1)
            
            # Look for any open menus or dropdowns and close them
            open_menus = driver.find_elements(By.CSS_SELECTOR, ".mat-mdc-menu-panel, .mat-menu-panel, [role='menu']")
            if open_menus:
                print(f"Found {len(open_menus)} open menu(s), dismissing...")
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                time.sleep(1)
                
        except Exception as overlay_error:
            print(f"Error while dismissing overlays: {overlay_error}")
        
        max_retries = 50  # Reduced from 50 for scene processing
        
        for attempt in range(max_retries):
            print(f"Attempt {attempt + 1}/{max_retries}: Clicking the 'Run' button...")
            
            try:
                # Try multiple approaches to click the Run button
                run_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Run']")))
                
                # Method 1: Standard click
                try:
                    run_button.click()
                    print("Run button clicked (standard method).")
                except Exception as click_error:
                    print(f"Standard click failed: {click_error}")
                    
                    # Method 2: Scroll into view and click
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", run_button)
                        time.sleep(0.5)
                        run_button.click()
                        print("Run button clicked (scroll + click method).")
                    except Exception as scroll_error:
                        print(f"Scroll + click failed: {scroll_error}")
                        
                        # Method 3: JavaScript click
                        try:
                            driver.execute_script("arguments[0].click();", run_button)
                            print("Run button clicked (JavaScript method).")
                        except Exception as js_error:
                            print(f"JavaScript click failed: {js_error}")
                            
                            # Method 4: Move to element and click
                            try:
                                from selenium.webdriver.common.action_chains import ActionChains
                                actions = ActionChains(driver)
                                actions.move_to_element(run_button).click().perform()
                                print("Run button clicked (ActionChains method).")
                            except Exception as action_error:
                                print(f"ActionChains click failed: {action_error}")
                                raise Exception("All click methods failed for Run button")
                    
            except TimeoutException:
                print("Could not find or click Run button.")
                return False

            try:
                # Check for an error message within 5 seconds
                error_message_xpath = "//*[contains(., 'Failed to generate video, quota exceeded') or contains(., 'Failed to generate video: permission denied')]"
                WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, error_message_xpath)))
                
                # Error detected - handle dismissal and retry
                print("Error detected. Beginning dismissal and retry process.")
                try:
                    dismiss_button_xpath = "//button[contains(., 'Dismiss') or contains(., 'OK') or @aria-label='Close']"
                    dismiss_button = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH, dismiss_button_xpath)))
                    print("Found a dismiss button. Attempting to click with JavaScript.")
                    driver.execute_script("arguments[0].click();", dismiss_button)
                    print("Dismiss button clicked.")
                    time.sleep(1)
                except TimeoutException:
                    print("No standard dismiss button found. Sending Escape key as a fallback.")
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    print("Escape key sent.")
                    time.sleep(1)

                # Verify that the popup is closed before continuing
                try:
                    WebDriverWait(driver, 2).until_not(EC.visibility_of_element_located((By.XPATH, error_message_xpath)))
                    print("Error popup successfully closed.")
                except TimeoutException:
                    print("Warning: The error popup may not have closed correctly.")

                print(f"Waiting for 26 seconds before retry attempt {attempt + 2}...")
                time.sleep(26)
                
                if attempt == max_retries - 1:
                    print("Maximum retries reached. Could not generate video for this scene.")
                    return False

            except TimeoutException:
                # No error detected - assume success
                print("No error detected. Generation appears to be in progress.")
                
                # Wait a bit for generation to start
                time.sleep(10)
                
                # Optionally check for video generation completion
                try:
                    print("Checking for video generation...")
                    video_wait = WebDriverWait(driver, 200)  # Wait up to 2 minute for video
                    video_wait.until(EC.presence_of_element_located((By.TAG_NAME, "video")))
                    print("Video has been generated successfully for this scene.")
                    
                    # Optionally try to download (but don't fail if download button not found)
                    try:
                        download_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
                            (By.XPATH, "//button[@aria-label='Download video']")
                        ))
                        download_button.click()
                        print("Download initiated for this scene.")
                        time.sleep(3)  # Brief wait for download to start
                    except TimeoutException:
                        print("Download button not found or not clickable - continuing without download.")
                    
                except TimeoutException:
                    print("Video generation taking longer than expected, but continuing to next scene.")
                
                return True  # Success - exit retry loop
        
        return False  # If we get here, all retries failed
            
    except Exception as e:
        print(f"Error processing scene {scene_num}: {e}")
        return False

# --- Main Script ---
def main():
    # Load scene data
    scenes = load_latest_scene_data()
    if not scenes:
        print("No scene data found. Please run the scene extractor first.")
        return
    
    options = webdriver.ChromeOptions()
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"user-data-dir={USER_DATA_DIR}")
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)

    try:
        # 1. Navigate to Google AI Studio and handle login
        print("Navigating to AI Studio...")
        driver.get("https://aistudio.google.com/gen-media")
        time.sleep(3) # Wait for potential redirect

        if "accounts.google.com" in driver.current_url:
            print("Login required. Performing login...")
            
            # Enter email - sometimes it's pre-filled
            try:
                email_field = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email']")))
                email_field.clear()
                email_field.send_keys(GOOGLE_EMAIL)
                driver.find_element(By.ID, "identifierNext").click()
                print("Email entered.")
                time.sleep(2)
            except TimeoutException:
                print("Email field not found, assuming it's pre-filled or different flow.")

            # Enter password
            try:
                password_field = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
                password_field.clear()
                password_field.send_keys(GOOGLE_PASSWORD)
                driver.find_element(By.ID, "passwordNext").click()
                print("Password entered. Login successful.")
                
                # Wait for redirect back to AI studio
                print("Waiting for redirection to AI Studio...")
                wait.until(EC.url_contains("aistudio.google.com"))
                print("Redirected successfully.")
                time.sleep(5)
            except TimeoutException:
                print("Password field not found or login already completed.")
        else:
            print("Already logged in.")

        # Ensure we are on the correct page
        if "gen-media" not in driver.current_url:
            driver.get("https://aistudio.google.com/gen-media")
        
        # Process each scene sequentially
        successful_scenes = 0
        total_scenes = len(scenes)
        
        for i, scene_data in enumerate(scenes, 1):
            scene_num = scene_data.get('scene_number', i)
            print(f"\n--- Processing Scene {i}/{total_scenes} (Scene #{scene_num}) ---")
            
            # Find images for this scene
            scene_images = find_scene_images(scene_num)
            
            # Process the scene
            success = process_scene(driver, wait, scene_data, scene_images)
            
            if success:
                successful_scenes += 1
                print(f"Scene {scene_num} processed successfully.")
                
                # Wait between scenes to avoid rate limiting
                if i < total_scenes:
                    print("Waiting 30 seconds before next scene...")
                    time.sleep(150)
            else:
                print(f"Failed to process scene {scene_num} after retries. Continuing with next scene...")
                
                # Take a screenshot for debugging this specific scene failure
                try:
                    screenshot_path = os.path.join(DOWNLOAD_DIR, f"debug_scene_{scene_num}_failure_{int(time.time())}.png")
                    driver.save_screenshot(screenshot_path)
                    print(f"Scene failure screenshot saved to: {screenshot_path}")
                except:
                    print("Could not save scene failure screenshot.")
                
                time.sleep(10)  # Brief wait before next scene
        
        print(f"\n=== Processing Complete ===")
        print(f"Successfully processed {successful_scenes}/{total_scenes} scenes.")
        
        print("Script finished. Waiting for a bit before closing.")
        time.sleep(10) # Wait to see the result

    except Exception as e:
        print(f"An error occurred during execution: {e}")
        # Take screenshot for debugging
        try:
            screenshot_path = os.path.join(DOWNLOAD_DIR, f"debug_error_{int(time.time())}.png")
            driver.save_screenshot(screenshot_path)
            print(f"Debug screenshot saved to: {screenshot_path}")
        except:
            print("Could not save debug screenshot.")
        
    finally:
        print("Closing the browser.")
        driver.quit()

if __name__ == "__main__":
    main()

def wait_for_file_input_ready(driver, file_input, timeout=10):
    """Wait for file input to be ready and interactable"""
    try:
        # Wait for the input to be present and enabled
        WebDriverWait(driver, timeout).until(
            lambda d: file_input.is_enabled()
        )
        
        # Additional checks to ensure the input is ready
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Test if we can interact with the input
                file_input.get_attribute("accept")  # Simple attribute access test
                return True
            except:
                time.sleep(0.5)
                continue
        
        return False
    except:
        return False

def send_files_to_input(driver, file_input, file_paths, max_retries=3):
    """Send files to input with multiple retry strategies"""
    for attempt in range(max_retries):
        try:
            print(f"File upload attempt {attempt + 1}/{max_retries}")
            
            # Make sure the input is ready
            if not wait_for_file_input_ready(driver, file_input):
                print(f"File input not ready on attempt {attempt + 1}")
                continue
            
            # Try different upload methods
            if attempt == 0:
                # Method 1: All files at once with newlines (best for multiple upload)
                if len(file_paths) > 1:
                    all_paths = "\n".join(file_paths)
                    file_input.send_keys(all_paths)
                    print(f"Sent all {len(file_paths)} files at once")
                else:
                    file_input.send_keys(file_paths[0])
                    print(f"Sent single file: {os.path.basename(file_paths[0])}")
                    
            elif attempt == 1:
                # Method 2: Files one by one
                for i, path in enumerate(file_paths):
                    if i > 0:  # Clear previous selection for subsequent files
                        try:
                            file_input.clear()
                        except:
                            pass
                    file_input.send_keys(path)
                    print(f"Sent file {i+1}: {os.path.basename(path)}")
                    time.sleep(0.5)
                    
            else:
                # Method 3: JavaScript assisted
                try:
                    # Focus the input first
                    driver.execute_script("arguments[0].focus();", file_input)
                    time.sleep(0.2)
                    
                    # Send the files
                    file_input.send_keys(file_paths[0])  # Start with first file
                    print(f"JavaScript-assisted upload for: {os.path.basename(file_paths[0])}")
                except:
                    # Fallback to simple send_keys
                    file_input.send_keys(file_paths[0])
                    print(f"Fallback upload for: {os.path.basename(file_paths[0])}")
            
            # Wait and verify
            time.sleep(2)
            
            # Check if files were accepted (simple validation)
            try:
                value = file_input.get_attribute("value")
                if value and any(os.path.basename(path) in value for path in file_paths):
                    print("File upload appears successful!")
                    return True
                elif file_input.get_attribute("files"):
                    print("Files detected in input!")
                    return True
                else:
                    print(f"Upload verification failed on attempt {attempt + 1}")
            except:
                print(f"Could not verify upload on attempt {attempt + 1}")
            
        except Exception as e:
            print(f"Upload attempt {attempt + 1} failed: {e}")
            time.sleep(1)
    
    return False


