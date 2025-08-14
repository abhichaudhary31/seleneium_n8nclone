import time
import os
import sys
import subprocess
import json
import glob
import random
import re
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from enum import Enum
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# --- CONFIGURATION LOADING ---
try:
    from config import *
    print("✅ Loaded configuration from config.py")
except ImportError:
    try:
        from config_template import *
        print("⚠️ Using template configuration. Please copy config_template.py to config.py and update with your credentials.")
    except ImportError:
        print("❌ No configuration file found. Using fallback settings.")
        # Fallback configuration
        GOOGLE_EMAIL = "your_primary_email@gmail.com"
        GOOGLE_PASSWORD = "your_primary_password"
        BACKUP_EMAIL = "your_backup_email@gmail.com"
        BACKUP_PASSWORD = "your_backup_password"
        SWITCH_ACCOUNT_AFTER_RETRIES = 12
        USER_DATA_DIR_NAME = "selenium_chrome_profile"
        BACKUP_USER_DATA_DIR_NAME = "selenium_chrome_profile_backup"
        OVERLAY_HANDLING = "simplified"
        ENABLE_PAGE_RELOAD = False
        PAGE_RELOAD_INTERVAL = 2
        RETRY_WAIT_TIME = 26
        SCENE_WAIT_TIME = 30
        RESTART_AFTER_VIDEOS = 3
        RESTART_PAUSE_MINUTES = 10
        CHECKPOINT_FILE = "video_progress_checkpoint.json"
        DOWNLOAD_DIR_NAME = "scene_videos"
        SCENE_DATA_DIR_NAME = "scene_data"
        SCENE_IMAGES_DIR_NAME = "scene_images"
        MAX_RETRIES_PER_SCENE = 25
        VIDEO_GENERATION_TIMEOUT = 200
        ENABLE_DEBUG_SCREENSHOTS = True
        DEBUG_SCREENSHOT_DIR = "Documents"
        # Gmail notification fallback settings
        ENABLE_EMAIL_NOTIFICATIONS = False
        NOTIFICATION_EMAIL = "your_gmail_here@gmail.com"
        NOTIFICATION_APP_PASSWORD = "your_gmail_app_password_here"
        NOTIFICATION_RECIPIENT = "your_gmail_here@gmail.com"
        GMAIL_SMTP_SERVER = "smtp.gmail.com"
        GMAIL_SMTP_PORT = 587

# Build paths from configuration
USER_DATA_DIR = os.path.join(os.path.expanduser("~"), USER_DATA_DIR_NAME)
BACKUP_USER_DATA_DIR = os.path.join(os.path.expanduser("~"), BACKUP_USER_DATA_DIR_NAME)
DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads", DOWNLOAD_DIR_NAME)
SCENE_DATA_DIR = os.path.join(os.path.expanduser("~"), "Downloads", SCENE_DATA_DIR_NAME)
SCENE_IMAGES_DIR = os.path.join(os.path.expanduser("~"), "Downloads", SCENE_IMAGES_DIR_NAME)

# --- ERROR CATEGORIZATION ---
class ErrorType(Enum):
    QUOTA_EXCEEDED = "quota_exceeded"
    PERMISSION_DENIED = "permission_denied"
    NETWORK_ERROR = "network_error"
    ELEMENT_NOT_FOUND = "element_not_found"
    CLICK_INTERCEPTED = "click_intercepted"
    UPLOAD_FAILED = "upload_failed"
    ACCOUNT_SWITCH_FAILED = "account_switch_failed"
    CONFIGURATION_ERROR = "configuration_error"
    UNKNOWN_ERROR = "unknown_error"

# Global state
current_account = "primary"  # Track which account is currently active

# Persistent browser instances
primary_driver = None    # Primary account browser instance
primary_wait = None      # Primary account wait instance
backup_driver = None     # Backup account browser instance  
backup_wait = None       # Backup account wait instance
global_driver = None     # Currently active driver
global_wait = None       # Currently active wait

def categorize_error(error_message):
    """Categorize errors for better handling and reporting"""
    error_msg = str(error_message).lower()
    
    if "quota exceeded" in error_msg:
        return ErrorType.QUOTA_EXCEEDED
    elif "permission denied" in error_msg:
        return ErrorType.PERMISSION_DENIED
    elif "element click intercepted" in error_msg or "overlay" in error_msg:
        return ErrorType.CLICK_INTERCEPTED
    elif "no such element" in error_msg or "element not found" in error_msg:
        return ErrorType.ELEMENT_NOT_FOUND
    elif "network" in error_msg or "connection" in error_msg:
        return ErrorType.NETWORK_ERROR
    else:
        return ErrorType.UNKNOWN_ERROR

def handle_overlay_simple():
    """Simplified overlay handling based on configuration"""
    global global_driver
    
    if OVERLAY_HANDLING == "off":
        return
    
    try:
        if OVERLAY_HANDLING == "minimal":
            # Just send escape key
            body = global_driver.find_element(By.TAG_NAME, 'body')
            body.send_keys(Keys.ESCAPE)
            time.sleep(0.2)
            
        elif OVERLAY_HANDLING == "simplified":
            # Basic overlay removal with common selectors
            print("🔍 Dismissing overlays (simplified approach)...")
            
            # Send Escape keys first
            body = global_driver.find_element(By.TAG_NAME, 'body')
            for i in range(2):
                body.send_keys(Keys.ESCAPE)
                time.sleep(0.3)
            
            # Remove common overlay types
            overlays = global_driver.find_elements(By.CSS_SELECTOR, 
                ".cdk-overlay-backdrop, .mat-overlay-backdrop, .backdrop")
            
            if overlays:
                print(f"Found {len(overlays)} overlay(s) - removing...")
                for overlay in overlays:
                    try:
                        global_driver.execute_script("arguments[0].remove();", overlay)
                    except:
                        pass
            
            print("✅ Overlay dismissal completed")
            
    except Exception as e:
        print(f"⚠️ Error during overlay dismissal: {e}")

def save_debug_screenshot(context="debug"):
    """Save debug screenshot if enabled"""
    if not ENABLE_DEBUG_SCREENSHOTS:
        return None
        
    try:
        timestamp = int(time.time())
        screenshot_path = os.path.join(
            os.path.expanduser("~"), 
            DEBUG_SCREENSHOT_DIR, 
            f"{context}_{current_account}_{timestamp}.png"
        )
        global_driver.save_screenshot(screenshot_path)
        print(f"📸 Debug screenshot saved: {screenshot_path}")
        return screenshot_path
    except Exception as e:
        print(f"⚠️ Could not save debug screenshot: {e}")
        return None

def load_latest_scene_data():
    """Load scene data from video_prompt_final.json"""
    try:
        video_prompt_file = os.path.join(SCENE_DATA_DIR, "video_prompt_final.json")
        if not os.path.exists(video_prompt_file):
            print(f"video_prompt_final.json not found at: {video_prompt_file}")
            print("Please make sure the merged scene data file exists.")
            return []
        
        print(f"Loading scene data from: {video_prompt_file}")
        
        with open(video_prompt_file, 'r', encoding='utf-8') as f:
            scene_prompts = json.load(f)
        
        # Convert the scene prompts dict to a list of scene dicts
        scenes = []
        for scene_key, prompt in scene_prompts.items():
            # Extract scene number from various possible formats (Scene1, Scene(2), etc.)
            scene_num_match = re.search(r'(\d+)', scene_key)
            if scene_num_match:
                scene_number = int(scene_num_match.group(1))
            else:
                # Fallback: use position in dict + 1
                scene_number = len(scenes) + 1
            
            scene_dict = {
                'scene_number': scene_number,
                'prompt': prompt
            }
            scenes.append(scene_dict)
        
        # Sort scenes by scene number to ensure correct order
        scenes.sort(key=lambda x: x['scene_number'])
        
        print(f"Loaded {len(scenes)} scenes from video_prompt_final.json")
        for scene in scenes:
            print(f"  Scene {scene['scene_number']}: {scene['prompt'][:50]}...")
        
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
        
        # Use a set to avoid processing the same directory twice
        processed_dirs = set()
        images = []
        
        for pattern in scene_dir_patterns:
            scene_dirs = glob.glob(pattern)
            for scene_dir in scene_dirs:
                if os.path.isdir(scene_dir) and scene_dir not in processed_dirs:
                    processed_dirs.add(scene_dir)
                    # Look for PNG files in the scene directory
                    image_files = glob.glob(os.path.join(scene_dir, "*.png"))
                    images.extend(image_files)
                elif scene_dir in processed_dirs:
                    print(f"  Skipping already processed directory: {os.path.basename(scene_dir)}")
        
        # Also check for direct files (old format)
        direct_image_pattern = os.path.join(SCENE_IMAGES_DIR, f"scene_{scene_number}_*.png")
        direct_images = glob.glob(direct_image_pattern)
        images.extend(direct_images)
        
        # Remove duplicates by filename - keep only unique basenames
        unique_images = {}
        for img_path in images:
            filename = os.path.basename(img_path)
            if filename not in unique_images:
                unique_images[filename] = img_path
            else:
                print(f"  Duplicate detected: {filename} (keeping first occurrence)")
        
        # Convert back to list of paths
        deduplicated_images = list(unique_images.values())
        
        print(f"Found {len(images)} images for scene {scene_number} ({len(images) - len(deduplicated_images)} duplicates removed)")
        if deduplicated_images:
            for img in deduplicated_images:
                print(f"  - {os.path.basename(img)}")
        
        return deduplicated_images
    except Exception as e:
        print(f"Error finding images for scene {scene_number}: {e}")
        return []

def create_combined_prompt(scene_data):
    """Create a prompt from scene data - now simply returns the prompt string"""
    # For the new format, scene_data contains 'scene_number' and 'prompt'
    if isinstance(scene_data, dict) and 'prompt' in scene_data:
        return scene_data['prompt']
    
    # Fallback for legacy format (if needed for compatibility)
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
    
    return ". ".join(prompt_parts) if prompt_parts else "No prompt available"

def upload_images_to_veo(driver, wait, image_paths):
    """Upload images by clicking upload button then using send_keys to file input"""
    try:
        if not image_paths:
            print("No images to upload.")
            return True
        
        print(f"Attempting to upload {len(image_paths)} images...")
        
        # Save debug screenshot if enabled
        save_debug_screenshot("upload_state")
        
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
                                print(f"Button {i+1} clicked successfully with strategy {strategy_num}.")
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
        
        print("Upload button clicked successfully! Human-like delay for UI to respond...")
        # Human delay after upload button click (simulating patience while UI responds)
        time.sleep(random.uniform(4.5, 6.0))  # Slightly random delay instead of fixed 5 seconds
        
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
                            
                            # Check if input supports multiple files
                            supports_multiple = file_input.get_attribute('multiple') is not None
                            print(f"File input supports multiple files: {supports_multiple}")
                            
                            if len(valid_paths) == 1:
                                # Single file upload
                                file_input.send_keys(valid_paths[0])
                                print(f"Uploaded single file: {os.path.basename(valid_paths[0])}")
                            elif supports_multiple:
                                # Multiple files - join with newlines (only if supported)
                                all_paths = "\n".join(valid_paths)
                                file_input.send_keys(all_paths)
                                print(f"Uploaded {len(valid_paths)} files: {[os.path.basename(p) for p in valid_paths]}")
                            else:
                                # Upload only the first file if multiple not supported
                                print(f"Warning: File input doesn't support multiple files. Uploading only the first image.")
                                file_input.send_keys(valid_paths[0])
                                print(f"Uploaded single file (first of {len(valid_paths)}): {os.path.basename(valid_paths[0])}")
                            
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
            
            # Save post-upload screenshot if enabled
            save_debug_screenshot("after_upload")
            
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

def select_dropdown_option(driver, wait, context="", target_duration=None):
    """Select a duration from dropdown that currently shows 8s
    
    Parameters:
    - driver: WebDriver instance
    - wait: WebDriverWait instance
    - context: Optional context string for logging
    - target_duration: Optional specific duration to select ('5s', '6s', or '7s'). If None, randomly chooses.
    """
    try:
        # If no specific duration provided, randomly select one
        if not target_duration:
            duration_options = ['5s', '6s', '7s']
            target_duration = random.choice(duration_options)
        
        context_msg = f" {context}" if context else ""
        print(f"\n====== DROPDOWN SELECTION DEBUG ======")
        print(f"🔽 Attempting to select {target_duration} duration from dropdown{context_msg}...")
        print(f"🎯 PRIMARY TARGET: Dropdown with class='mat-mdc-select-value' and id='mat-select-value-1'")
        print(f"🎯 SECONDARY TARGET: Element showing '8s' text that can be clicked")
        print(f"🎯 OPTION TARGET: Option with text '{target_duration}'")
        print(f"📊 Current URL: {driver.current_url}")
        
        # Debug: Check page state
        try:
            page_title = driver.title
            body_text = driver.find_element(By.TAG_NAME, "body").text[:100] + "..."
            print(f"📄 Page title: {page_title}")
            print(f"📝 Page content snippet: {body_text}")
            
            # Look for any mat-select elements on the page
            all_selects = driver.find_elements(By.TAG_NAME, "mat-select")
            print(f"🔢 Found {len(all_selects)} mat-select elements on page")
            
            # Look for elements with exact mat-mdc-select-value class
            mdc_select_values = driver.find_elements(By.CSS_SELECTOR, ".mat-mdc-select-value")
            print(f"🎯 Found {len(mdc_select_values)} elements with class 'mat-mdc-select-value'")
            
            # Look specifically for the target element we want
            target_element = driver.find_elements(By.CSS_SELECTOR, ".mat-mdc-select-value#mat-select-value-4")
            print(f"🎯 Found {len(target_element)} elements with class 'mat-mdc-select-value' AND id='mat-select-value-4'")
            
            # Show details of all elements with the exact class we want
            for i, elem in enumerate(mdc_select_values[:3]):
                try:
                    elem_id = elem.get_attribute('id') or 'No ID'
                    elem_text = elem.text or elem.get_attribute('textContent') or 'No text'
                    is_displayed = elem.is_displayed()
                    is_enabled = elem.is_enabled()
                    print(f"  Select element {i+1}: ID='{elem_id}', Text='{elem_text}', Displayed={is_displayed}, Enabled={is_enabled}")
                except Exception as elem_error:
                    print(f"  Error getting select element {i+1} details: {elem_error}")
            
            # Look for elements with '8s' text
            elements_with_8s = driver.find_elements(By.XPATH, "//*[contains(text(), '8s')]")
            print(f"🔢 Found {len(elements_with_8s)} elements containing '8s' text")
            
            # Show the first few elements with '8s' if any
            if elements_with_8s:
                print("📋 Elements with '8s' text:")
                for i, elem in enumerate(elements_with_8s[:3]):
                    try:
                        tag = elem.tag_name
                        classes = elem.get_attribute('class') or 'No class'
                        text = elem.text or elem.get_attribute('textContent') or 'No text'
                        print(f"  Element {i+1}: <{tag}> '{text}' | Classes: '{classes}'")
                    except:
                        print(f"  Element {i+1}: <error getting details>")
        except Exception as debug_error:
            print(f"⚠️ Debug info collection error: {debug_error}")
        
        print("====== DROPDOWN SEARCH STARTING ======")
        
        # Multiple strategies to find and click the dropdown showing "8s"
        dropdown_strategies = [
            # Strategy 1: Element with ID mat-select-value-1 (based on debug output)
            (By.ID, "mat-select-value-1"),
            # Strategy 2: Element with 8s text and specific class
            (By.XPATH, "//div[contains(@class, 'mat-mdc-select-value') and contains(text(), '8s')]"),
            # Strategy 3: Exact match for ID and class combination
            (By.CSS_SELECTOR, ".mat-mdc-select-value#mat-select-value-1"),
            # Strategy 4: Any element containing "8s" text
            (By.XPATH, "//*[contains(text(), '8s')]"),
            # Strategy 5: Mat-select element containing "8s" text
            (By.XPATH, "//mat-select//*[contains(text(), '8s')]"),
            # Strategy 6: Any clickable element with "8s"
            (By.XPATH, "//*[contains(text(), '8s') and (@role='button' or @role='combobox')]"),
            # Strategy 7: Look for any mat-select-value element as fallback
            (By.CSS_SELECTOR, ".mat-mdc-select-value"),
        ]
        
        dropdown_clicked = False
        print(f"🔍 Will try {len(dropdown_strategies)} different strategies to find the dropdown")
        
        for strategy_num, (by, selector) in enumerate(dropdown_strategies, 1):
            try:
                print(f"\n🔍 Strategy #{strategy_num}: {by} '{selector}'")
                
                # First check if elements matching selector exist at all
                matching_elements = driver.find_elements(by, selector)
                print(f"  ↳ Found {len(matching_elements)} matching elements")
                
                if matching_elements:
                    # Display details of the first few matching elements
                    for i, elem in enumerate(matching_elements[:2]):
                        try:
                            is_displayed = elem.is_displayed()
                            is_enabled = elem.is_enabled()
                            elem_text = elem.text or elem.get_attribute('textContent') or 'No text'
                            elem_id = elem.get_attribute('id') or 'No ID'
                            elem_class = elem.get_attribute('class') or 'No class'
                            print(f"  ↳ Element {i+1}: '{elem_text}' | ID: '{elem_id}' | Displayed: {is_displayed} | Enabled: {is_enabled}")
                        except Exception as detail_error:
                            print(f"  ↳ Error getting element {i+1} details: {detail_error}")
                
                # Wait for dropdown to be clickable
                print("  ↳ Waiting for element to be clickable...")
                dropdown = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((by, selector))
                )
                
                print("  ↳ Element is clickable! Scrolling into view...")
                # Scroll into view and click
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", dropdown)
                time.sleep(0.5)
                
                # Get element properties before clicking
                try:
                    dropdown_text = dropdown.text or dropdown.get_attribute('textContent') or 'No text'
                    dropdown_tag = dropdown.tag_name
                    dropdown_id = dropdown.get_attribute('id') or 'No ID'
                    print(f"  ↳ Ready to click: <{dropdown_tag}> '{dropdown_text}' | ID: {dropdown_id}")
                except Exception as prop_error:
                    print(f"  ↳ Error getting element properties: {prop_error}")
                
                # Try clicking the dropdown
                try:
                    # Get more detailed properties of the found dropdown
                    print(f"⭐ Found dropdown to click with strategy {strategy_num}")
                    try:
                        dropdown_classes = dropdown.get_attribute('class') or 'No class'
                        dropdown_role = dropdown.get_attribute('role') or 'No role'
                        dropdown_ariaOwns = dropdown.get_attribute('aria-owns') or 'No aria-owns'
                        print(f"  ↳ Classes: '{dropdown_classes}' | Role: '{dropdown_role}' | aria-owns: '{dropdown_ariaOwns}'")
                    except Exception as attr_error:
                        print(f"  ↳ Error getting additional attributes: {attr_error}")
                    
                    # Try regular click
                    # Human delay before clicking dropdown (simulating consideration)
                    time.sleep(random.uniform(1.5, 2.5))
                    dropdown.click()
                    print(f"✅ Dropdown clicked using strategy {strategy_num}")
                    # Human delay after dropdown click to let options appear
                    time.sleep(random.uniform(2.0, 3.0))
                    dropdown_clicked = True
                    break
                except Exception as click_error:
                    print(f"⚠️ Standard click failed for strategy {strategy_num}: {click_error}")
                    # Try JavaScript click
                    try:
                        # Human delay before JavaScript fallback
                        time.sleep(random.uniform(1.0, 2.0))
                        driver.execute_script("arguments[0].click();", dropdown)
                        print(f"✅ Dropdown clicked using JavaScript for strategy {strategy_num}")
                        # Human delay after JavaScript click
                        time.sleep(random.uniform(2.0, 3.0))
                        dropdown_clicked = True
                        break
                    except Exception as js_error:
                        print(f"⚠️ JavaScript click also failed for strategy {strategy_num}: {js_error}")
                        continue
                        
            except TimeoutException:
                print(f"Dropdown strategy {strategy_num} - element not found")
                continue
            except Exception as e:
                print(f"Dropdown strategy {strategy_num} failed: {e}")
                continue
        
        if not dropdown_clicked:
            print(f"⚠️ Warning: Could not find or click dropdown{context_msg}. Continuing without dropdown selection...")
            return False
        
        # Wait for dropdown options to appear with human-like delay
        print("Waiting for dropdown options to appear...")
        time.sleep(random.uniform(2.5, 3.5))
        
        # Debug: Check if dropdown is expanded and options are visible
        try:
            overlay_panels = driver.find_elements(By.CSS_SELECTOR, ".cdk-overlay-pane, .mat-select-panel-wrap, mat-option")
            print(f"\n====== OPTION SELECTION DEBUG ======")
            print(f"📊 Found {len(overlay_panels)} possible overlay panels/options")
            
            # Look for any mat-option elements
            all_options = driver.find_elements(By.CSS_SELECTOR, "mat-option, [role='option']")
            print(f"📊 Found {len(all_options)} total options/listbox items on page")
            
            # Show available options
            if all_options:
                print("📋 Available options:")
                for i, opt in enumerate(all_options[:5]):  # Show first 5 options
                    try:
                        opt_text = opt.text or opt.get_attribute('textContent') or 'No text'
                        opt_id = opt.get_attribute('id') or 'No ID'
                        opt_value = opt.get_attribute('value') or 'No value'
                        print(f"  Option {i+1}: '{opt_text}' | ID: '{opt_id}' | Value: '{opt_value}'")
                    except Exception as opt_err:
                        print(f"  Option {i+1}: <error getting details: {opt_err}>")
            
            # Look specifically for mat-option-25
            target_option = driver.find_elements(By.ID, "mat-option-25")
            print(f"🎯 Found {len(target_option)} elements with ID 'mat-option-25'")
            if target_option:
                try:
                    opt = target_option[0]
                    tag = opt.tag_name
                    visible = opt.is_displayed()
                    opt_text = opt.text or opt.get_attribute('textContent') or 'No text'
                    print(f"  Target Option: <{tag}> '{opt_text}' | Visible: {visible}")
                except Exception as opt_err:
                    print(f"  Error getting target option details: {opt_err}")
            
            # Specifically look for options with "5s" text
            options_with_5s = driver.find_elements(By.XPATH, "//*[contains(text(), '5s')]")
            print(f"🎯 Found {len(options_with_5s)} elements containing '5s' text")
            if options_with_5s:
                for i, opt in enumerate(options_with_5s[:3]):
                    try:
                        tag = opt.tag_name
                        visible = opt.is_displayed()
                        opt_id = opt.get_attribute('id') or 'No ID'
                        opt_text = opt.text or opt.get_attribute('textContent') or 'No text'
                        print(f"  5s Element {i+1}: <{tag}> ID='{opt_id}' '{opt_text}' | Visible: {visible}")
                    except Exception as opt_err:
                        print(f"  5s Element {i+1}: <error getting details: {opt_err}>")
        except Exception as debug_error:
            print(f"⚠️ Option debug info error: {debug_error}")
        
        # Get all available options in the dropdown
        try:
            print(f"\n====== AVAILABLE OPTIONS CHECK ======")
            # Try to get all mat-options in the current dropdown
            all_mat_options = driver.find_elements(By.TAG_NAME, "mat-option")
            print(f"📋 Found {len(all_mat_options)} total mat-option elements")
            
            if all_mat_options:
                print(f"📋 Listing all available mat-options:")
                for i, opt in enumerate(all_mat_options):
                    try:
                        opt_id = opt.get_attribute('id') or 'No ID'
                        opt_text = opt.text or opt.get_attribute('textContent') or 'No text'
                        print(f"  Option {i+1}: ID='{opt_id}', Text='{opt_text}'")
                    except Exception as e:
                        print(f"  Option {i+1}: Error getting details: {e}")
        except Exception as e:
            print(f"Error listing available options: {e}")
            
        # Now find and click the target duration option
        print(f"\n====== OPTION SEARCH STARTING ======")
        print(f"🔍 Looking for {target_duration} option{context_msg}...")
        
        option_strategies = [
            # Strategy 1: Mat-option containing target duration text
            (By.XPATH, f"//mat-option[contains(text(), '{target_duration}')]"),
            # Strategy 2: Any option with specific class and target duration text
            (By.XPATH, f"//*[contains(@class, 'mat-option') and contains(text(), '{target_duration}')]"),
            # Strategy 3: Option role with target duration text
            (By.XPATH, f"//*[@role='option' and contains(text(), '{target_duration}')]"),
            # Strategy 4: Any clickable element containing target duration text in the overlay
            (By.XPATH, f"//div[contains(@class, 'overlay')]//*[contains(text(), '{target_duration}')]"),
            # Strategy 5: Broader search for target duration in any element
            (By.XPATH, f"//*[contains(text(), '{target_duration}')]"),
        ]
        
        option_selected = False
        print(f"🔍 Will try {len(option_strategies)} different strategies to find the 5s option")
        
        for strategy_num, (by, selector) in enumerate(option_strategies, 1):
            try:
                print(f"\n🔍 Option Strategy #{strategy_num}: {by} '{selector}'")
                
                # Wait for option to be clickable
                option = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((by, selector))
                )
                
                # Try clicking the option
                try:
                    # Get detailed properties of the found option
                    print(f"⭐ Found {target_duration} option to click with strategy {strategy_num}")
                    try:
                        option_text = option.text or option.get_attribute('textContent') or 'No text'
                        option_id = option.get_attribute('id') or 'No ID'
                        option_classes = option.get_attribute('class') or 'No class'
                        option_value = option.get_attribute('value') or 'No value'
                        option_visible = option.is_displayed()
                        print(f"  ↳ ID: '{option_id}' | Text: '{option_text}' | Visible: {option_visible}")
                        print(f"  ↳ Classes: '{option_classes}' | Value: '{option_value}'")
                    except Exception as attr_error:
                        print(f"  ↳ Error getting option attributes: {attr_error}")
                    
                    # Try regular click
                    # Human delay before selecting option (simulating decision making)
                    time.sleep(random.uniform(1.5, 2.5))
                    option.click()
                    print(f"✅ {target_duration} option selected using strategy {strategy_num}")
                    # Human delay after option selection
                    time.sleep(random.uniform(1.0, 2.0))
                    option_selected = True
                    break
                except Exception as click_error:
                    print(f"⚠️ Standard click failed for option strategy {strategy_num}: {click_error}")
                    # Try JavaScript click
                    try:
                        # Human delay before JavaScript fallback
                        time.sleep(random.uniform(1.0, 1.5))
                        driver.execute_script("arguments[0].click();", option)
                        print(f"✅ {target_duration} option selected using JavaScript for strategy {strategy_num}")
                        # Human delay after JavaScript option selection
                        time.sleep(random.uniform(1.0, 2.0))
                        option_selected = True
                        break
                    except Exception as js_error:
                        print(f"⚠️ JavaScript click also failed for option strategy {strategy_num}: {js_error}")
                        continue
                        
            except TimeoutException:
                print(f"Option strategy {strategy_num} - element not found")
                continue
            except Exception as e:
                print(f"Option strategy {strategy_num} failed: {e}")
                continue
        
        if option_selected:
            print(f"✅ Successfully selected {target_duration} duration{context_msg}")
            # Human delay for selection to register (simulating confirmation)
            time.sleep(random.uniform(2.0, 3.0))
            return True
        else:
            print(f"⚠️ Warning: Could not find or select {target_duration} option{context_msg}. Continuing with current setting...")
            
            # Debug: Show available options
            try:
                all_options = driver.find_elements(By.CSS_SELECTOR, "mat-option, [role='option']")
                print(f"Debug: Found {len(all_options)} total options")
                for i, opt in enumerate(all_options[:10]):  # Show first 10 options
                    try:
                        text = opt.text or opt.get_attribute('textContent') or 'No text'
                        option_id = opt.get_attribute('id') or 'No ID'
                        print(f"  Option {i+1}: '{text}' | ID: '{option_id}'")
                    except:
                        pass
            except:
                print("Could not debug available options")
            
            return False
        
    except Exception as e:
        print(f"⚠️ Error during dropdown selection{context_msg}: {e}")
        return False

def process_scene(driver, wait, scene_data, scene_images):
    """Process a single scene: upload images and prompt, then run"""
    global current_account, global_driver, global_wait
    
    scene_num = scene_data.get('scene_number', 'Unknown')
    # For the new format, we don't have scene_title, just the prompt
    scene_title = f"Scene {scene_num}"
    
    print(f"\n=== Processing Scene {scene_num}: {scene_title} ===")
    print(f"🔄 Using {current_account} account")
    
    # Use global driver instances
    driver = global_driver
    wait = global_wait
    
    try:
        # Navigate to Veo if not already there
        if "gen-media" not in driver.current_url:
            driver.get("https://aistudio.google.com/gen-media")
            # Human delay after page navigation
            time.sleep(random.randint(3, 4))
        
        # Click the Veo button if needed
        try:
            veo_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//mat-card[@aria-label='Veo']"))
            )
            # Human delay before clicking Veo button
            time.sleep(random.uniform(2.5, 3.5))
            veo_button.click()
            print("Veo button clicked.")
            # Human delay after clicking Veo button
            time.sleep(random.randint(3, 4))
        except TimeoutException:
            print("Veo button not found or already selected.")
        
        # Upload images if available (but don't fail the scene if upload fails)
        if scene_images:
            print(f"Attempting to upload {len(scene_images)} images for scene {scene_num}")
            # Human delay before image upload
            time.sleep(random.uniform(2.5, 3.5))
            upload_success = upload_images_to_veo(driver, wait, scene_images)
            if not upload_success:
                print(f"Warning: Failed to upload images for scene {scene_num}")
                print("Continuing with text-only prompt generation...")
            else:
                print(f"Successfully uploaded images for scene {scene_num}")
                # Human delay after successful image upload
                time.sleep(random.randint(3, 4))
        else:
            print(f"No images found for scene {scene_num}, proceeding with text-only prompt")
        
        # Clear and enter the prompt
        prompt_text = create_combined_prompt(scene_data)
        print(f"Entering prompt: {prompt_text[:100]}...")
        
        # Human delay before interacting with prompt input
        time.sleep(random.uniform(2.0, 3.0))
        
        prompt_input = wait.until(EC.visibility_of_element_located((By.TAG_NAME, "textarea")))
        # Human delay before clearing field
        time.sleep(random.uniform(1.5, 2.5))
        prompt_input.clear()
        
        # Human delay before typing (simulating reading/thinking)
        time.sleep(random.uniform(2.0, 3.0))
        prompt_input.send_keys(prompt_text)
        print("Prompt entered.")
        
        # Human delay after entering text (simulating review)
        time.sleep(random.randint(3, 4))
        
        # Select dropdown (8s -> random duration) before clicking Run button
        print("\n===== 🔽 ATTEMPTING DROPDOWN SELECTION BEFORE RUN =====")
        # Pick a random duration between 5s, 6s, and 7s
        duration_options = ['5s', '6s', '7s']
        selected_duration = random.choice(duration_options)
        print(f"🎲 Randomly selected {selected_duration} for this attempt")
        
        # Human delay before dropdown selection (simulating consideration)
        time.sleep(random.uniform(2.5, 3.5))
        select_dropdown_option(driver, wait, target_duration=selected_duration)
        print("===== DROPDOWN SELECTION ATTEMPT COMPLETE =====\n")
        
        # Human delay after dropdown selection before Run button
        time.sleep(random.randint(3, 4))
        
        # Click the Run button with retry logic
        print("Clicking Run button with retry logic...")
        if ENABLE_PAGE_RELOAD:
            print(f"🔄 Auto-reload: Page will reload every {PAGE_RELOAD_INTERVAL} failed attempts to reset state")
        print(f"🔄 Account Switch: Will alternate accounts every {SWITCH_ACCOUNT_AFTER_RETRIES} failed attempts")
        
        # Use simplified overlay handling
        handle_overlay_simple()
        
        max_retries = MAX_RETRIES_PER_SCENE  # Max retries per scene before giving up
        
        for attempt in range(max_retries):
            print(f"Attempt {attempt + 1}/{max_retries}: Clicking the 'Run' button... [Account: {current_account}]")
            
            # Check if we need to switch accounts every SWITCH_ACCOUNT_AFTER_RETRIES retries
            # Switch at: SWITCH_ACCOUNT_AFTER_RETRIES, 2*SWITCH_ACCOUNT_AFTER_RETRIES, 3*SWITCH_ACCOUNT_AFTER_RETRIES, etc.
            if attempt > 0 and attempt % SWITCH_ACCOUNT_AFTER_RETRIES == 0:
                print(f"\n🔄 SWITCHING ACCOUNTS after {attempt} failed attempts (every {SWITCH_ACCOUNT_AFTER_RETRIES} retries)...")
                
                # Switch to the other persistent browser
                new_driver, new_wait = switch_to_backup_account()
                
                # Update driver references to the newly active browser
                driver = new_driver
                wait = new_wait
                
                # The browser is already logged in and ready - just ensure we're on the right page
                if "gen-media" not in driver.current_url:
                    # Human delay before navigating (simulating account switch pause)
                    time.sleep(random.uniform(2.0, 3.0))
                    driver.get("https://aistudio.google.com/gen-media")
                    # Human delay after navigation to new account
                    time.sleep(random.uniform(3.0, 4.0))
                
                # Re-setup the scene in the switched browser
                try:
                    # Click the Veo button if needed
                    try:
                        # Human delay before looking for Veo button in new account
                        time.sleep(random.uniform(2.0, 3.0))
                        veo_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, "//mat-card[@aria-label='Veo']"))
                        )
                        # Human delay before clicking Veo in switched account
                        time.sleep(random.uniform(1.5, 2.5))
                        veo_button.click()
                        print(f"Veo button clicked in {current_account} browser.")
                        # Human delay after Veo button click in switched account
                        time.sleep(random.uniform(3.0, 4.0))
                    except TimeoutException:
                        print(f"Veo button not found in {current_account} browser, continuing...")
                    
                    # Re-upload images if available
                    if scene_images:
                        print(f"Re-uploading {len(scene_images)} images in {current_account} browser...")
                        # Human delay before re-uploading images in switched account
                        time.sleep(random.uniform(2.0, 3.0))
                        upload_success = upload_images_to_veo(driver, wait, scene_images)
                        if upload_success:
                            print(f"Images uploaded successfully in {current_account} browser.")
                            # Human delay after successful re-upload
                            time.sleep(random.uniform(2.0, 3.0))
                        else:
                            print(f"Warning: Failed to upload images in {current_account} browser, continuing with text-only...")
                    
                    # Re-enter the prompt
                    try:
                        # Human delay before re-entering prompt in switched account
                        time.sleep(random.uniform(2.0, 3.0))
                        prompt_input = wait.until(EC.visibility_of_element_located((By.TAG_NAME, "textarea")))
                        # Human delay before clearing field in switched account
                        time.sleep(random.uniform(1.0, 2.0))
                        prompt_input.clear()
                        # Human delay before typing in switched account
                        time.sleep(random.uniform(1.5, 2.5))
                        prompt_input.send_keys(prompt_text)
                        print(f"Prompt re-entered in {current_account} browser.")
                        # Human delay after re-entering prompt
                        time.sleep(random.uniform(2.0, 3.0))
                    except Exception as prompt_error:
                        print(f"Warning: Failed to re-enter prompt in {current_account} browser: {prompt_error}")
                    
                    # Re-select dropdown option after account switch
                    print(f"\n===== 🔽 ATTEMPTING DROPDOWN SELECTION IN {current_account.upper()} BROWSER =====")
                    # Pick a random duration between 5s, 6s, and 7s
                    duration_options = ['5s', '6s', '7s']
                    selected_duration = random.choice(duration_options)
                    print(f"🎲 Randomly selected {selected_duration} for this account switch attempt")
                    select_dropdown_option(driver, wait, f"in {current_account} browser", target_duration=selected_duration)
                    print(f"===== DROPDOWN SELECTION ATTEMPT COMPLETE IN {current_account.upper()} =====\n")
                    
                    print(f"{current_account.capitalize()} browser setup completed. Continuing with retry...")
                    
                except Exception as setup_error:
                    print(f"Error setting up {current_account} browser: {setup_error}")
                    return False  # Fail this scene if account switch fails
            
            # Show reload schedule information only if page reload is enabled
            if ENABLE_PAGE_RELOAD:
                if (attempt + 1) % PAGE_RELOAD_INTERVAL == 0:
                    print(f"📅 Note: Page reload will occur after this attempt if it fails. [Account: {current_account}]")
                elif attempt > 0:
                    next_reload = PAGE_RELOAD_INTERVAL - ((attempt + 1) % PAGE_RELOAD_INTERVAL)
                    if next_reload == PAGE_RELOAD_INTERVAL:
                        next_reload = PAGE_RELOAD_INTERVAL
                    print(f"📅 Next page reload in {next_reload} attempts if needed. [Account: {current_account}]")
            
            try:
                # Try multiple approaches to click the Run button
                # Human delay before looking for Run button (simulating final review)
                time.sleep(random.uniform(2.0, 3.0))
                
                run_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Run']")))
                
                # Method 1: Standard click
                try:
                    # Human delay before clicking Run button (simulating hesitation/confidence building)
                    time.sleep(random.uniform(1.5, 2.5))
                    run_button.click()
                    print("Run button clicked (standard method).")
                    # Human delay after clicking Run to simulate waiting for response
                    time.sleep(random.uniform(2.0, 3.0))
                except Exception as click_error:
                    error_type = categorize_error(click_error)
                    print(f"Standard click failed ({error_type.value}): {click_error}")
                    
                    # Handle click interception specifically
                    if error_type == ErrorType.CLICK_INTERCEPTED:
                        print("🔍 Overlay detected blocking click - performing overlay dismissal...")
                        handle_overlay_simple()
                        time.sleep(1)
                    
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
                error_message_xpath = "//*[contains(., 'Failed to generate video, quota exceeded') or contains(., 'Failed to')]"
                WebDriverWait(driver, 100).until(EC.visibility_of_element_located((By.XPATH, error_message_xpath)))
                
                # Error detected - handle dismissal and retry
                error_type = categorize_error("quota exceeded")  # Detect specific error type
                print(f"Error detected ({error_type.value}). Beginning dismissal and retry process.")
                try:
                    # Human delay before looking for dismiss button (simulating reading error)
                    time.sleep(random.uniform(2.0, 3.0))
                    dismiss_button_xpath = "//button[contains(., 'Dismiss') or contains(., 'OK') or @aria-label='Close']"
                    dismiss_button = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH, dismiss_button_xpath)))
                    print("Found a dismiss button. Attempting to click with JavaScript.")
                    # Human delay before dismissing error (simulating acknowledgment)
                    time.sleep(random.uniform(1.0, 2.0))
                    driver.execute_script("arguments[0].click();", dismiss_button)
                    print("Dismiss button clicked.")
                    # Human delay after dismissing error
                    time.sleep(random.uniform(1.5, 2.5))
                except TimeoutException:
                    print("No standard dismiss button found. Sending Escape key as a fallback.")
                    # Human delay before using Escape fallback
                    time.sleep(random.uniform(1.0, 1.5))
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    print("Escape key sent.")
                    # Human delay after Escape key
                    time.sleep(random.uniform(1.5, 2.5))

                # Verify that the popup is closed before continuing
                try:
                    WebDriverWait(driver, 2).until_not(EC.visibility_of_element_located((By.XPATH, error_message_xpath)))
                    print("Error popup successfully closed.")
                except TimeoutException:
                    print("Warning: The error popup may not have closed correctly.")

                print(f"Waiting {RETRY_WAIT_TIME} seconds before retry attempt {attempt + 2}...")
                
                # Add some randomness to wait time to appear more human-like
                actual_wait = random.randint(int(RETRY_WAIT_TIME * 0.8), int(RETRY_WAIT_TIME * 1.2))
                time.sleep(actual_wait)
                
                # Pick a new random duration for the next attempt
                duration_options = ['5s', '6s', '7s']
                selected_duration = random.choice(duration_options)
                print(f"🎲 Randomly selecting {selected_duration} for next retry attempt")
                select_dropdown_option(driver, wait, f"for retry #{attempt + 2}", target_duration=selected_duration)
                
                # Page reload functionality (only if enabled)
                if ENABLE_PAGE_RELOAD and (attempt + 1) % PAGE_RELOAD_INTERVAL == 0 and attempt < max_retries - 1:
                    print(f"\n🔄 Performing page reload after {attempt + 1} attempts to reset page state...")
                    try:
                        # Save current scene data for re-entry after reload
                        current_prompt = prompt_text
                        current_scene_images = scene_images
                        
                        # Reload the page
                        driver.refresh()
                        print("Page reloaded successfully.")
                        time.sleep(5)  # Wait for page to load
                        
                        # Navigate back to Veo if needed
                        if "gen-media" not in driver.current_url:
                            driver.get("https://aistudio.google.com/gen-media")
                            time.sleep(3)
                        
                        # Re-select Veo button if needed
                        try:
                            veo_button = WebDriverWait(driver, 5).until(
                                EC.element_to_be_clickable((By.XPATH, "//mat-card[@aria-label='Veo']"))
                            )
                            veo_button.click()
                            print("Veo button re-selected after reload.")
                            time.sleep(2)
                        except TimeoutException:
                            print("Veo button not found after reload, continuing...")
                        
                        # Re-upload images if they were previously uploaded
                        if current_scene_images:
                            print(f"Re-uploading {len(current_scene_images)} images after page reload...")
                            upload_success = upload_images_to_veo(driver, wait, current_scene_images)
                            if upload_success:
                                print("Images re-uploaded successfully after reload.")
                            else:
                                print("Warning: Failed to re-upload images after reload, continuing with text-only...")
                        
                        # Re-enter the prompt
                        try:
                            prompt_input = wait.until(EC.visibility_of_element_located((By.TAG_NAME, "textarea")))
                            prompt_input.clear()
                            prompt_input.send_keys(current_prompt)
                            print("Prompt re-entered after page reload.")
                            time.sleep(1)
                        except Exception as prompt_error:
                            print(f"Warning: Failed to re-enter prompt after reload: {prompt_error}")
                        
                        # Select a random duration for this attempt after reload
                        try:
                            duration_options = ['5s', '6s', '7s']
                            selected_duration = random.choice(duration_options)
                            print(f"🎲 Randomly selecting {selected_duration} after page reload")
                            select_dropdown_option(driver, wait, "after page reload", target_duration=selected_duration)
                        except Exception as dropdown_error:
                            print(f"Warning: Failed to select duration dropdown after reload: {dropdown_error}")
                        
                        print("Page reload and setup completed. Continuing with retry...")
                        
                    except Exception as reload_error:
                        print(f"Error during page reload: {reload_error}")
                        print("Continuing with normal retry process...")
                
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
                    video_wait = WebDriverWait(driver, VIDEO_GENERATION_TIMEOUT)
                    video_wait.until(EC.presence_of_element_located((By.TAG_NAME, "video")))
                    print("Video has been generated successfully for this scene.")
                    
                    # Optionally try to download (but don't fail if download button not found)
                    try:
                        # Human delay before looking for download button (simulating appreciation of result)
                        time.sleep(random.uniform(3.0, 5.0))
                        download_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
                            (By.XPATH, "//button[@aria-label='Download video']")
                        ))
                        # Human delay before clicking download (simulating decision to save)
                        time.sleep(random.uniform(2.0, 3.0))
                        download_button.click()
                        print("Download initiated for this scene.")
                        # Human delay for download to start (simulating waiting for download)
                        time.sleep(random.uniform(4.0, 6.0))
                        
                        # Rename the downloaded video with scene number
                        rename_success = rename_downloaded_video_for_scene(scene_num)
                        if rename_success:
                            print(f"✅ Video successfully renamed for Scene {scene_num}")
                        else:
                            print(f"⚠️ Failed to rename video for Scene {scene_num}")
                            
                    except TimeoutException:
                        print("Download button not found or not clickable - continuing without download.")
                    
                except TimeoutException:
                    print("Video generation taking longer than expected, but continuing to next scene.")
                
                return True  # Success - exit retry loop
        
        return False  # If we get here, all retries failed
            
    except Exception as e:
        print(f"Error processing scene {scene_num}: {e}")
        return False

def save_checkpoint(successful_scenes, current_scene_index, total_scenes):
    """Save current progress to checkpoint file"""
    try:
        checkpoint_data = {
            "successful_scenes": successful_scenes,
            "current_scene_index": current_scene_index,
            "total_scenes": total_scenes,
            "timestamp": time.time(),
            "last_account": current_account
        }
        
        checkpoint_path = os.path.join(os.path.expanduser("~"), "Downloads", CHECKPOINT_FILE)
        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
        
        print(f"💾 Checkpoint saved: {successful_scenes}/{total_scenes} scenes completed")
        return True
    except Exception as e:
        print(f"❌ Error saving checkpoint: {e}")
        return False

def load_checkpoint():
    """Load progress from checkpoint file"""
    try:
        checkpoint_path = os.path.join(os.path.expanduser("~"), "Downloads", CHECKPOINT_FILE)
        if not os.path.exists(checkpoint_path):
            print("📍 No checkpoint found - starting from beginning")
            return None
            
        with open(checkpoint_path, 'r') as f:
            checkpoint_data = json.load(f)
        
        print(f"📍 Checkpoint loaded: {checkpoint_data['successful_scenes']}/{checkpoint_data['total_scenes']} scenes completed")
        print(f"📍 Resuming from scene {checkpoint_data['current_scene_index'] + 1}")
        return checkpoint_data
    except Exception as e:
        print(f"❌ Error loading checkpoint: {e}")
        return None

def clear_checkpoint():
    """Remove checkpoint file when workflow is complete"""
    try:
        checkpoint_path = os.path.join(os.path.expanduser("~"), "Downloads", CHECKPOINT_FILE)
        if os.path.exists(checkpoint_path):
            os.remove(checkpoint_path)
            print("🗑️ Checkpoint cleared - workflow complete")
    except Exception as e:
        print(f"❌ Error clearing checkpoint: {e}")

def wait_for_download_completion(timeout=60):
    """Wait for download to complete by monitoring the download directory"""
    print("⏳ Waiting for download to complete...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        # Look for .crdownload files (Chrome's partial download files)
        partial_files = glob.glob(os.path.join(DOWNLOAD_DIR, "*.crdownload"))
        if not partial_files:
            # No partial downloads, check if any new files appeared
            time.sleep(2)  # Give a moment for the file to appear
            break
        time.sleep(1)
    
    # Return the most recently downloaded file
    files = glob.glob(os.path.join(DOWNLOAD_DIR, "*"))
    if files:
        latest_file = max(files, key=os.path.getctime)
        return latest_file
    return None

def rename_downloaded_video_for_scene(scene_num, timeout=60):
    """Rename the most recently downloaded video to SCENE{num}.mp4 format"""
    try:
        print(f"📝 Renaming downloaded video for Scene {scene_num}...")
        
        # Wait for download to complete
        downloaded_file = wait_for_download_completion(timeout)
        
        if not downloaded_file:
            print(f"❌ No downloaded file found for Scene {scene_num}")
            return False
        
        # Skip if file is already renamed correctly
        expected_name = f"SCENE{scene_num}.mp4"
        if os.path.basename(downloaded_file) == expected_name:
            print(f"✅ File already named correctly: {expected_name}")
            return True
        
        # Only rename video files
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v']
        file_ext = os.path.splitext(downloaded_file)[1].lower()
        
        if file_ext not in video_extensions:
            print(f"⚠️ Downloaded file is not a video: {downloaded_file}")
            return False
        
        # Create new filename with scene number
        new_filename = f"SCENE{scene_num}.mp4"
        new_filepath = os.path.join(DOWNLOAD_DIR, new_filename)
        
        # Handle existing file with same name
        if os.path.exists(new_filepath):
            print(f"⚠️ File {new_filename} already exists, removing old version...")
            os.remove(new_filepath)
        
        # Rename the file
        os.rename(downloaded_file, new_filepath)
        print(f"✅ Successfully renamed to: {new_filename}")
        return True
        
    except Exception as e:
        print(f"❌ Error renaming video for Scene {scene_num}: {e}")
        return False

def restart_script_after_pause():
    """Restart the script after closing browsers and waiting"""
    
    print(f"\n🔄 RESTART SEQUENCE: Closing browsers and restarting script...")
    
    # Clean up current browser instances
    cleanup_browsers()
    
    # Wait for the specified pause duration
    pause_minutes = RESTART_PAUSE_MINUTES
    print(f"⏳ Waiting {pause_minutes} minutes before restart...")
    
    # Show countdown timer
    pause_seconds = pause_minutes * 60
    for remaining in range(pause_seconds, 0, -60):
        mins_left = remaining // 60
        if remaining % 60 == 0:  # Only show at minute intervals
            print(f"⏳ {mins_left} minute(s) remaining...")
        time.sleep(60)
    
    print("🚀 Restarting script with fresh browser instances...")
    
    # Restart the script
    python_executable = sys.executable
    script_path = __file__
    subprocess.Popen([python_executable, script_path])
    
    # Exit current instance
    sys.exit(0)

def get_user_scene_selection(total_scenes):
    """Get user input for scene range selection"""
    print(f"\n🎬 Scene Selection")
    print(f"📋 Total scenes available: {total_scenes}")
    print("="*50)
    
    while True:
        try:
            print("\nChoose an option:")
            print("1️⃣  Process ALL scenes (1 to {})".format(total_scenes))
            print("2️⃣  Process SPECIFIC RANGE (e.g., scenes 3 to 8)")
            print("3️⃣  Process SINGLE SCENE (e.g., scene 5)")
            print("4️⃣  Continue from LAST CHECKPOINT")
            print("5️⃣  EXIT script")
            
            choice = input("\nEnter your choice (1-5): ").strip()
            
            if choice == "1":
                # Process all scenes
                return 1, total_scenes, "all"
            
            elif choice == "2":
                # Process specific range
                while True:
                    try:
                        range_input = input(f"\nEnter range (e.g., '3-8' or '3 to 8'): ").strip()
                        # Handle different input formats
                        if '-' in range_input:
                            start_str, end_str = range_input.split('-')
                        elif ' to ' in range_input.lower():
                            start_str, end_str = range_input.lower().split(' to ')
                        elif ',' in range_input:
                            start_str, end_str = range_input.split(',')
                        else:
                            print("❌ Invalid format. Use formats like '3-8' or '3 to 8'")
                            continue
                        
                        start_scene = int(start_str.strip())
                        end_scene = int(end_str.strip())
                        
                        if start_scene < 1 or end_scene > total_scenes:
                            print(f"❌ Scene numbers must be between 1 and {total_scenes}")
                            continue
                        
                        if start_scene > end_scene:
                            print("❌ Start scene must be less than or equal to end scene")
                            continue
                        
                        return start_scene, end_scene, "range"
                    
                    except ValueError:
                        print("❌ Please enter valid numbers")
                        continue
            
            elif choice == "3":
                # Process single scene
                while True:
                    try:
                        scene_num = int(input(f"\nEnter scene number (1-{total_scenes}): ").strip())
                        
                        if scene_num < 1 or scene_num > total_scenes:
                            print(f"❌ Scene number must be between 1 and {total_scenes}")
                            continue
                        
                        return scene_num, scene_num, "single"
                    
                    except ValueError:
                        print("❌ Please enter a valid number")
                        continue
            
            elif choice == "4":
                # Continue from checkpoint
                return None, None, "checkpoint"
            
            elif choice == "5":
                # Exit
                print("👋 Exiting script...")
                return None, None, "exit"
            
            else:
                print("❌ Invalid choice. Please enter 1, 2, 3, 4, or 5")
                continue
        
        except KeyboardInterrupt:
            print("\n\n👋 Script cancelled by user")
            return None, None, "exit"
        except Exception as e:
            print(f"❌ Error: {e}")
            continue

def display_scene_summary(scenes, start_idx, end_idx):
    """Display a summary of selected scenes"""
    print(f"\n📋 Selected Scene Summary:")
    print("="*60)
    
    selected_scenes = scenes[start_idx-1:end_idx]
    
    for i, scene_data in enumerate(selected_scenes, start_idx):
        scene_num = scene_data.get('scene_number', i)
        # For the new format, we don't have scene_title, just use scene number
        scene_title = f"Scene {scene_num}"
        
        # Check for images
        scene_images = find_scene_images(scene_num)
        image_count = len(scene_images)
        
        print(f"Scene {i:2d}: {scene_title}")
        print(f"         Images: {image_count} found")
        
        # Show preview of prompt
        prompt = create_combined_prompt(scene_data)
        preview = prompt[:80] + "..." if len(prompt) > 80 else prompt
        print(f"         Prompt: {preview}")
        print()
    
    print("="*60)
    print(f"📊 Total scenes to process: {end_idx - start_idx + 1}")
    
    # Confirm with user
    while True:
        confirm = input("\n✅ Proceed with these scenes? (y/n): ").strip().lower()
        if confirm in ['y', 'yes']:
            return True
        elif confirm in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' or 'n'")

def send_gmail_notification(subject, message, successful_scenes, total_scenes, duration_minutes=None):
    """Send Gmail notification when script finishes"""
    
    # Check if notifications are enabled
    try:
        if not ENABLE_EMAIL_NOTIFICATIONS:
            print("📧 Email notifications disabled in config")
            return False
    except NameError:
        print("📧 Email notifications not configured")
        return False
    
    try:
        # Get notification settings with fallbacks
        try:
            sender_email = NOTIFICATION_EMAIL
        except NameError:
            sender_email = GOOGLE_EMAIL
            
        try:
            app_password = NOTIFICATION_APP_PASSWORD
        except NameError:
            app_password = None
            
        try:
            recipient_email = NOTIFICATION_RECIPIENT
        except NameError:
            recipient_email = GOOGLE_EMAIL
            
        try:
            smtp_server = GMAIL_SMTP_SERVER
        except NameError:
            smtp_server = 'smtp.gmail.com'
            
        try:
            smtp_port = GMAIL_SMTP_PORT
        except NameError:
            smtp_port = 587
        
        # Validate required settings
        if not app_password or app_password == "your_gmail_app_password_here":
            print("❌ Gmail notification failed: NOTIFICATION_APP_PASSWORD not configured")
            print("ℹ️  To enable notifications:")
            print("   1. Go to Google Account Security settings")
            print("   2. Enable 2-Step Verification")
            print("   3. Generate an App Password for this script")
            print("   4. Update NOTIFICATION_APP_PASSWORD in config.py")
            return False
            
        print("📧 Sending Gmail notification...")
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        # Create detailed message body
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        body = f"""
Story-to-Video Workflow Completed
=================================

🎬 Results Summary:
   • Successfully processed: {successful_scenes}/{total_scenes} scenes
   • Completion rate: {(successful_scenes/total_scenes*100):.1f}%
   • Finished at: {timestamp}
"""
        
        if duration_minutes:
            body += f"   • Total duration: {duration_minutes:.1f} minutes\n"
            
        body += f"""
📊 Processing Details:
   • Final account used: {current_account}
   • Script location: {os.path.abspath(__file__)}
   
{message}

---
Automated notification from Story-to-Video Workflow
"""

        msg.attach(MIMEText(body, 'plain'))
        
        # Connect to Gmail SMTP server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Enable encryption
        server.login(sender_email, app_password)
        
        # Send email
        text = msg.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()
        
        print(f"✅ Gmail notification sent to {recipient_email}")
        return True
        
    except smtplib.SMTPAuthenticationError:
        print("❌ Gmail notification failed: Authentication error")
        print("ℹ️  Please check your NOTIFICATION_EMAIL and NOTIFICATION_APP_PASSWORD settings")
        return False
    except Exception as e:
        print(f"❌ Gmail notification failed: {e}")
        return False

# --- Main Script ---
def main():
    global current_account, global_driver, global_wait
    
    # Track start time for duration calculation
    start_time = datetime.now()
    
    # Validate configuration before proceeding
    if not validate_configuration():
        print("Configuration validation failed. Please fix the issues before running the workflow.")
        return
    
    # Load scene data
    scenes = load_latest_scene_data()
    if not scenes:
        print("No scene data found. Please run the scene extractor first.")
        return

    # Check if this is an automatic restart from RESTART_AFTER_VIDEOS
    checkpoint = load_checkpoint()
    if checkpoint and checkpoint.get('restart_mode', False):
        print("🔄 ═══════════════════════════════════════════════════════════")
        print("🔄                 AUTOMATIC RESTART DETECTED               ")
        print("🔄 ═══════════════════════════════════════════════════════════")
        print(f"📍 Continuing from automatic restart checkpoint...")
        print(f"📊 Progress: {checkpoint['successful_scenes']} videos completed")
        print(f"📍 Last completed scene: {checkpoint['current_scene_index']}")
        print(f"📍 Resuming from scene: {checkpoint['current_scene_index'] + 1}")
        print(f"📍 Target end scene: {checkpoint.get('original_end_scene', len(scenes))}")
        print("🔄 ═══════════════════════════════════════════════════════════")
        
        # Restore original selection parameters
        selection_type = checkpoint.get('original_selection_type', 'all')
        starting_scene_index = checkpoint['current_scene_index'] + 1
        end_scene_index = checkpoint.get('original_end_scene', len(scenes))
        successful_scenes = checkpoint['successful_scenes']
        
        print(f"🎬 Auto-resuming: Processing scenes {starting_scene_index} to {end_scene_index}")
        print(f"🔄 Original selection type: {selection_type}")
        print(f"🎯 Will continue until scene {end_scene_index} is complete")
        print("")
        
    else:
        # Normal startup - get user scene selection
        total_scenes = len(scenes)
        start_scene, end_scene, selection_type = get_user_scene_selection(total_scenes)
        
        # Handle user choice
        if selection_type == "exit":
            return
        
        # Handle checkpoint continuation
        if selection_type == "checkpoint":
            checkpoint = load_checkpoint()
            if checkpoint:
                successful_scenes = checkpoint['successful_scenes'] 
                starting_scene_index = checkpoint['current_scene_index'] + 1
                end_scene_index = total_scenes
                print(f"📍 Continuing from checkpoint: {successful_scenes} videos completed")
                print(f"📍 Will process scenes {starting_scene_index} to {total_scenes}")
            else:
                print("❌ No checkpoint found. Please select a different option.")
                return
        else:
            # User selected specific range
            starting_scene_index = start_scene
            end_scene_index = end_scene
            successful_scenes = 0
            
            # Display summary and get confirmation
            if not display_scene_summary(scenes, start_scene, end_scene):
                print("👋 Operation cancelled by user")
                return
            
            # Clear any existing checkpoint since we're doing a custom range
            clear_checkpoint()

    # Validate backup credentials
    if BACKUP_EMAIL == "your_backup_email@gmail.com" or BACKUP_PASSWORD == "your_backup_password":
        print("⚠️  WARNING: Backup credentials not configured!")
        print("Please update BACKUP_EMAIL and BACKUP_PASSWORD in your config.py file.")
        print("Account switching will be disabled.")
    else:
        print(f"✅ Backup account configured: {BACKUP_EMAIL}")
    
    # Initialize persistent browser instances for both accounts
    print("🚀 Initializing persistent browser instances...")
    if not initialize_both_browsers():
        print("❌ Failed to initialize browsers. Exiting.")
        return

    try:
        # Prepare scenes to process based on selection
        if selection_type == "checkpoint":
            scenes_to_process = scenes[starting_scene_index-1:]
            actual_total = total_scenes
        else:
            scenes_to_process = scenes[starting_scene_index-1:end_scene_index]
            actual_total = end_scene_index
        
        print(f"\n🎬 Video generation: Processing scenes {starting_scene_index} to {end_scene_index}")
        print(f"🔄 Account switching enabled every {SWITCH_ACCOUNT_AFTER_RETRIES} retries per scene")
        print(f"🔄 Auto-restart: Script will restart after every {RESTART_AFTER_VIDEOS} successful videos (pause: {RESTART_PAUSE_MINUTES} min)")
        
        print(f"📋 Processing {len(scenes_to_process)} scenes total")
        
        # --- User Scene Selection ---
        
        # Process each scene in the selected range
        for relative_i, scene_data in enumerate(scenes_to_process):
            # Calculate actual scene number based on selection type
            if selection_type == "checkpoint":
                actual_i = starting_scene_index + relative_i
            else:
                actual_i = starting_scene_index + relative_i
            
            scene_num = scene_data.get('scene_number', actual_i)
            print(f"\n--- Processing Scene {actual_i}/{end_scene_index} (Scene #{scene_num}) ---")
            
            # Find images for this scene
            scene_images = find_scene_images(scene_num)
            
            # Process the scene (driver switching handled internally)
            success = process_scene(global_driver, global_wait, scene_data, scene_images)
            
            if success:
                successful_scenes += 1
                print(f"Scene {scene_num} processed successfully using {current_account} account.")
                
                # Save checkpoint after each successful scene (for all selection types to enable restart)
                save_checkpoint(successful_scenes, actual_i, actual_total)
                
                # Check if we need to restart after every RESTART_AFTER_VIDEOS successful videos
                if successful_scenes % RESTART_AFTER_VIDEOS == 0 and actual_i < end_scene_index:
                    print(f"\n🔄 RESTART TRIGGER: Successfully completed {successful_scenes} videos!")
                    print(f"📍 Current progress: Scene {actual_i}/{end_scene_index} completed")
                    print(f"📍 Next resume point: Scene {actual_i+1}/{end_scene_index}")
                    
                    # Save special restart checkpoint with additional metadata
                    restart_checkpoint_data = {
                        "successful_scenes": successful_scenes,
                        "current_scene_index": actual_i,  # Last completed scene
                        "total_scenes": actual_total,
                        "timestamp": time.time(),
                        "last_account": current_account,
                        "restart_mode": True,  # Flag to indicate this is a restart
                        "original_selection_type": selection_type,
                        "original_start_scene": starting_scene_index,
                        "original_end_scene": end_scene_index
                    }
                    
                    checkpoint_path = os.path.join(os.path.expanduser("~"), "Downloads", CHECKPOINT_FILE)
                    with open(checkpoint_path, 'w') as f:
                        json.dump(restart_checkpoint_data, f, indent=2)
                    
                    print(f"💾 Restart checkpoint saved for automatic continuation")
                    
                    # Trigger restart sequence (closes browsers, waits, restarts script)
                    restart_script_after_pause()
                    
                # Regular wait between scenes (if not at restart interval)
                elif actual_i < end_scene_index:
                    print(f"Waiting {SCENE_WAIT_TIME} seconds before next scene...")
                    # Add some human-like variation to scene wait time
                    human_wait = random.uniform(SCENE_WAIT_TIME * 0.9, SCENE_WAIT_TIME * 1.1)
                    time.sleep(human_wait)
            else:
                print(f"Failed to process scene {scene_num} after retries. Continuing with next scene...")
                
                # Save debug screenshot for scene failure
                save_debug_screenshot(f"scene_{scene_num}_failure")
                
                time.sleep(10)  # Brief wait before next scene
        
        print(f"\n=== Processing Complete ===")
        print(f"Successfully processed {successful_scenes}/{len(scenes_to_process)} selected scenes.")
        print(f"Scene range: {starting_scene_index} to {end_scene_index}")
        print(f"Final account used: {current_account}")
        
        # Calculate total duration
        end_time = datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()
        duration_minutes = duration_seconds / 60
        
        print(f"Total processing time: {duration_minutes:.1f} minutes")
        
        # Clear checkpoint after successful run (for all workflows when truly complete)
        clear_checkpoint()
        
        # Send Gmail notification on completion
        notification_subject = f"✅ Story-to-Video Workflow Complete - {successful_scenes}/{len(scenes_to_process)} scenes processed"
        notification_message = f"Workflow completed successfully with {(successful_scenes/len(scenes_to_process)*100):.1f}% success rate."
        
        send_gmail_notification(
            subject=notification_subject,
            message=notification_message, 
            successful_scenes=successful_scenes,
            total_scenes=len(scenes_to_process),
            duration_minutes=duration_minutes
        )
        
        print("Script finished. Waiting for a bit before closing.")
        # Human-like wait to see results (with some variation)
        final_wait = random.uniform(8.0, 12.0)
        time.sleep(final_wait)

    except Exception as e:
        error_type = categorize_error(e)
        print(f"An error occurred during execution ({error_type.value}): {e}")
        # Save debug screenshot for general error
        save_debug_screenshot("general_error")
        
        # Send error notification
        end_time = datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()
        duration_minutes = duration_seconds / 60
        
        error_subject = f"❌ Story-to-Video Workflow Error - Script terminated unexpectedly"
        error_message = f"Error occurred: {error_type.value} - {str(e)}"
        
        # Try to get successful scenes count
        try:
            successful_count = successful_scenes if 'successful_scenes' in locals() else 0
            total_count = len(scenes_to_process) if 'scenes_to_process' in locals() else 0
        except:
            successful_count = 0
            total_count = 0
        
        send_gmail_notification(
            subject=error_subject,
            message=error_message,
            successful_scenes=successful_count,
            total_scenes=total_count,
            duration_minutes=duration_minutes
        )
        
    finally:
        print("🧹 Cleaning up persistent browser instances...")
        cleanup_browsers()

def validate_configuration():
    """Validate the configuration before starting the workflow"""
    print("🔍 Validating configuration...")
    
    issues = []
    warnings = []
    
    # Check primary account credentials
    if not GOOGLE_EMAIL or GOOGLE_EMAIL == "your_primary_email@gmail.com":
        issues.append("❌ Primary GOOGLE_EMAIL not configured - update config.py")
    else:
        print(f"✅ Primary account: {GOOGLE_EMAIL}")
        
    if not GOOGLE_PASSWORD or GOOGLE_PASSWORD == "your_primary_password":
        issues.append("❌ Primary GOOGLE_PASSWORD not configured - update config.py")
    else:
        print("✅ Primary password: ●●●●●●●●")
    
    # Check backup account credentials
    if BACKUP_EMAIL == "your_backup_email@gmail.com":
        warnings.append("⚠️ Backup email not configured - account switching disabled")
    else:
        print(f"✅ Backup account: {BACKUP_EMAIL}")
        
    if BACKUP_PASSWORD == "your_backup_password":
        warnings.append("⚠️ Backup password not configured - account switching disabled")
    else:
        print("✅ Backup password: ●●●●●●●●")
    
    # Check configuration settings
    print(f"⚙️ Overlay handling: {OVERLAY_HANDLING}")
    print(f"⚙️ Page reload: {'Enabled' if ENABLE_PAGE_RELOAD else 'Disabled'}")
    print(f"⚙️ Max retries per scene: {MAX_RETRIES_PER_SCENE}")
    print(f"⚙️ Account switch threshold: {SWITCH_ACCOUNT_AFTER_RETRIES}")
    print(f"🔄 Auto-restart: {RESTART_AFTER_VIDEOS} videos")
    print(f"⏰ Restart pause: {RESTART_PAUSE_MINUTES} minutes")
    
    # Check directories
    if os.path.exists(USER_DATA_DIR):
        print(f"✅ Primary profile directory: {USER_DATA_DIR}")
    else:
        print(f"📁 Primary profile directory will be created: {USER_DATA_DIR}")
        
    if os.path.exists(BACKUP_USER_DATA_DIR):
        print(f"✅ Backup profile directory: {BACKUP_USER_DATA_DIR}")
    else:
        print(f"📁 Backup profile directory will be created: {BACKUP_USER_DATA_DIR}")
    
    # Check download directory
    if not os.path.exists(DOWNLOAD_DIR):
        try:
            os.makedirs(DOWNLOAD_DIR, exist_ok=True)
            print(f"📁 Created download directory: {DOWNLOAD_DIR}")
        except Exception as e:
            issues.append(f"❌ Cannot create download directory: {e}")
    else:
        print(f"✅ Download directory: {DOWNLOAD_DIR}")
    
    # Check Gmail notification settings
    try:
        enable_notifications = ENABLE_EMAIL_NOTIFICATIONS
    except NameError:
        enable_notifications = False
        
    if enable_notifications:
        try:
            notification_email = NOTIFICATION_EMAIL
        except NameError:
            notification_email = None
            
        try:
            app_password = NOTIFICATION_APP_PASSWORD
        except NameError:
            app_password = None
        
        if not notification_email or notification_email == "your_gmail_here@gmail.com":
            warnings.append("⚠️ NOTIFICATION_EMAIL not configured - notifications will be disabled")
        elif not app_password or app_password == "your_gmail_app_password_here":
            warnings.append("⚠️ NOTIFICATION_APP_PASSWORD not configured - notifications will be disabled")
        else:
            print(f"📧 Gmail notifications: Enabled ({notification_email})")
    else:
        print("📧 Gmail notifications: Disabled")
    
    # Print results
    print("\n" + "="*50)
    if issues:
        print("🚫 CONFIGURATION ISSUES:")
        for issue in issues:
            print(f"   {issue}")
        print("\nPlease fix these issues before running the workflow.")
        return False
        
    if warnings:
        print("⚠️ CONFIGURATION WARNINGS:")
        for warning in warnings:
            print(f"   {warning}")
        print("\nWorkflow will run with limited functionality.")
    
    print("✅ Configuration validation complete!")
    return True

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

def initialize_both_browsers():
    """Initialize both primary and backup browser instances"""
    global primary_driver, primary_wait, backup_driver, backup_wait, global_driver, global_wait, current_account
    
    print("� Initializing both browser instances...")
    
    # Initialize Primary Browser
    print("📱 Setting up Primary browser...")
    primary_options = webdriver.ChromeOptions()
    primary_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    primary_options.add_experimental_option('useAutomationExtension', False)
    primary_prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    primary_options.add_experimental_option("prefs", primary_prefs)
    primary_options.add_argument("--disable-blink-features=AutomationControlled")
    primary_options.add_argument(f"user-data-dir={USER_DATA_DIR}")
    
    try:
        primary_driver = webdriver.Chrome(options=primary_options)
        primary_wait = WebDriverWait(primary_driver, 20)
        
        # Login to primary account
        print(f"🔐 Logging into primary account: {GOOGLE_EMAIL}")
        if not login_browser(primary_driver, primary_wait, GOOGLE_EMAIL, GOOGLE_PASSWORD, "primary"):
            print("❌ Failed to login to primary account")
            return False
        
        print("✅ Primary browser ready!")
        
    except Exception as e:
        print(f"❌ Error setting up primary browser: {e}")
        return False
    
    # Initialize Backup Browser (only if credentials are configured)
    if BACKUP_EMAIL != "your_backup_email@gmail.com" and BACKUP_PASSWORD != "your_backup_password":
        print("📱 Setting up Backup browser...")
        backup_options = webdriver.ChromeOptions()
        backup_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        backup_options.add_experimental_option('useAutomationExtension', False)
        backup_options.add_experimental_option("prefs", primary_prefs)  # Same download settings
        backup_options.add_argument("--disable-blink-features=AutomationControlled")
        backup_options.add_argument(f"user-data-dir={BACKUP_USER_DATA_DIR}")
        
        try:
            backup_driver = webdriver.Chrome(options=backup_options)
            backup_wait = WebDriverWait(backup_driver, 20)
            
            # Login to backup account
            print(f"🔐 Logging into backup account: {BACKUP_EMAIL}")
            if not login_browser(backup_driver, backup_wait, BACKUP_EMAIL, BACKUP_PASSWORD, "backup"):
                print("❌ Failed to login to backup account")
                # Don't return False here, continue with just primary
                try:
                    backup_driver.quit()
                except:
                    pass
                backup_driver = None
                backup_wait = None
            else:
                print("✅ Backup browser ready!")
                
        except Exception as e:
            print(f"❌ Error setting up backup browser: {e}")
            backup_driver = None
            backup_wait = None
    else:
        print("⚠️ Backup credentials not configured, skipping backup browser setup")
    
    # Set initial active browser to primary
    global_driver = primary_driver
    global_wait = primary_wait
    current_account = "primary"
    
    print(f"🎯 Active browser: {current_account}")
    return True

def login_browser(driver, wait, email, password, account_name):
    """Login to a specific browser instance"""
    try:
        # Navigate to AI Studio
        driver.get("https://aistudio.google.com/gen-media")
        # Human delay after navigation (simulating page load time)
        time.sleep(random.uniform(3.0, 4.0))
        
        if "accounts.google.com" in driver.current_url:
            print(f"🔐 Login required for {account_name} account...")
            
            # Enter email
            try:
                email_field = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
                )
                # Human delay before entering email (simulating reading the form)
                time.sleep(random.uniform(2.0, 3.0))
                email_field.clear()
                # Human delay before typing email (simulating typing speed)
                time.sleep(random.uniform(1.0, 2.0))
                email_field.send_keys(email)
                # Human delay before clicking Next (simulating review)
                time.sleep(random.uniform(1.5, 2.5))
                driver.find_element(By.ID, "identifierNext").click()
                print(f"📧 {account_name.capitalize()} email entered.")
                # Human delay after email submission
                time.sleep(random.uniform(3.0, 4.0))
            except TimeoutException:
                print(f"📧 {account_name.capitalize()} email field not found, assuming pre-filled.")

            # Enter password
            try:
                password_field = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='password']"))
                )
                # Human delay before entering password (simulating thinking/security pause)
                time.sleep(random.uniform(2.0, 3.0))
                password_field.clear()
                # Human delay before typing password (simulating careful typing)
                time.sleep(random.uniform(1.0, 2.0))
                password_field.send_keys(password)
                # Human delay before submitting password (simulating double-check)
                time.sleep(random.uniform(1.5, 2.5))
                driver.find_element(By.ID, "passwordNext").click()
                print(f"🔑 {account_name.capitalize()} password entered.")
                
                # Wait for redirect
                wait.until(EC.url_contains("aistudio.google.com"))
                print(f"✅ {account_name.capitalize()} login successful!")
                # Human delay after successful login (simulating settling in)
                time.sleep(random.uniform(3.0, 4.0))
                
            except TimeoutException:
                print(f"🔑 {account_name.capitalize()} password field not found or already logged in.")
        else:
            print(f"✅ {account_name.capitalize()} account already logged in.")

        # Ensure we're on the correct page
        if "gen-media" not in driver.current_url:
            # Human delay before final navigation
            time.sleep(random.uniform(2.0, 3.0))
            driver.get("https://aistudio.google.com/gen-media")
            # Human delay after final navigation
            time.sleep(random.uniform(3.0, 4.0))
        
        return True
        
    except Exception as e:
        print(f"❌ Error logging into {account_name} account: {e}")
        return False

def switch_active_browser():
    """Switch between the two persistent browser instances"""
    global current_account, global_driver, global_wait
    
    if current_account == "primary" and backup_driver:
        # Switch to backup
        print(f"\n🔄 SWITCHING: {current_account} → backup")
        current_account = "backup"
        global_driver = backup_driver
        global_wait = backup_wait
        
        # Ensure backup browser is on the right page
        if "gen-media" not in global_driver.current_url:
            global_driver.get("https://aistudio.google.com/gen-media")
            time.sleep(2)
            
    elif current_account == "backup" and primary_driver:
        # Switch to primary
        print(f"\n🔄 SWITCHING: {current_account} → primary")
        current_account = "primary"
        global_driver = primary_driver
        global_wait = primary_wait
        
        # Ensure primary browser is on the right page
        if "gen-media" not in global_driver.current_url:
            global_driver.get("https://aistudio.google.com/gen-media")
            time.sleep(2)
    else:
        print(f"⚠️ Cannot switch - backup browser not available")
        return False
    
    print(f"✅ Switched to {current_account} account!")
    print(f"🎯 Active browser: {current_account}")
    return True

def switch_to_backup_account():
    """Switch to the other account using persistent browsers"""
    global current_account, global_driver, global_wait
    
    print(f"🔄 Switching to alternate account...")
    
    # Use the fast browser switching instead of creating new instances
    if switch_active_browser():
        print(f"✅ Successfully switched to {current_account} account!")
        return global_driver, global_wait
    else:
        print("❌ Failed to switch browsers - backup browser not available")
        # Return current browser to continue with same account
        return global_driver, global_wait

def cleanup_browsers():
    """Properly closes both browser instances if they exist"""
    global primary_driver, backup_driver, current_account
    
    print("🧹 Cleaning up browser instances...")
    
    try:
        if primary_driver:
            print("📴 Closing primary browser instance")
            primary_driver.quit()
    except Exception as e:
        print(f"⚠️ Error closing primary browser: {e}")
    
    try:
        if backup_driver:
            print("📴 Closing backup browser instance")
            backup_driver.quit()
    except Exception as e:
        print(f"⚠️ Error closing backup browser: {e}")
    
    # Reset global variables
    primary_driver = None
    backup_driver = None
    current_account = "primary"
    
    print("✅ Browser cleanup complete")

# Entry point for direct script execution
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Script interrupted by user (Ctrl+C)")
        cleanup_browsers()
    except Exception as e:
        print(f"\n\n❌ Unhandled error: {e}")
        cleanup_browsers()
