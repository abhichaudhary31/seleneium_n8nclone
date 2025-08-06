import time
import os
import sys
import json
import random
import base64
import glob
import subprocess
from datetime import datetime
from enum import Enum
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException

# Import configuration (modify path if needed)
try:
    from config import *
    print("✅ Loaded configuration from config.py")
except ImportError:
    try:
        from config_template import *
        print("⚠️ Using template configuration. Please update with your credentials.")
    except ImportError:
        print("❌ Configuration file not found. Please create config.py with your credentials.")
        exit(1)

# Define paths based on configuration
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
    API_ERROR = "api_error"
    UNKNOWN_ERROR = "unknown_error"

# Global state tracking
current_account = "primary"  # Track which account is currently active

class GoogleAIStudioAutomator:
    """
    Advanced automation for Google AI Studio using Chrome DevTools Protocol (CDP)
    to intercept and replay XHR requests. This version includes multi-account support,
    error handling, and checkpointing for robust workflow execution.
    """
    
    def __init__(self, account_type="primary"):
        """
        Initialize the automator with Chrome options and CDP capabilities
        
        Args:
            account_type (str): Either 'primary' or 'backup' to use the corresponding profile
        """
        self.api_requests = {}
        self.video_responses = {}
        self.network_enabled = False
        self.account_type = account_type
        self.retry_count = 0
        self.max_retries = MAX_RETRIES_PER_SCENE
        
        # Set user_data_dir based on account type
        if account_type == "primary":
            self.user_data_dir = USER_DATA_DIR
        else:
            self.user_data_dir = BACKUP_USER_DATA_DIR
            
        self.driver = None
        self.wait = None
        
        # API request tracking
        self.last_successful_api_request = None
        self.last_failed_request_reason = None
        self.last_api_error_message = None
        
        print(f"🔧 Initialized {account_type} automator with profile: {self.user_data_dir}")
        
    def categorize_error(self, error_message):
        """Categorize errors for better handling and reporting"""
        error_msg = str(error_message).lower()
        
        if "quota exceeded" in error_msg:
            return ErrorType.QUOTA_EXCEEDED
        elif "permission denied" in error_msg:
            return ErrorType.PERMISSION_DENIED
        elif "element click intercepted" in error_msg or "overlay" in error_msg:
            return ErrorType.CLICK_INTERCEPTED
        elif "network" in error_msg or "timeout" in error_msg or "connection" in error_msg:
            return ErrorType.NETWORK_ERROR
        elif "no such element" in error_msg or "not found" in error_msg:
            return ErrorType.ELEMENT_NOT_FOUND
        elif "upload" in error_msg and ("fail" in error_msg or "error" in error_msg):
            return ErrorType.UPLOAD_FAILED
        elif "api" in error_msg or "request" in error_msg or "response" in error_msg:
            return ErrorType.API_ERROR
        else:
            return ErrorType.UNKNOWN_ERROR
        
    def start_browser(self):
        """Start Chrome browser with CDP enabled and appropriate profile"""
        options = Options()
        options.add_argument(f"user-data-dir={self.user_data_dir}")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-notifications")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        
        # Set download directory
        prefs = {
            "download.default_directory": DOWNLOAD_DIR,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", prefs)
        
        # Create directory if it doesn't exist
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        
        # Create a new instance of Chrome with DevTools Protocol enabled
        try:
            self.driver = webdriver.Chrome(options=options)
            self.wait = WebDriverWait(self.driver, 10)
            print(f"✅ {self.account_type.capitalize()} browser started with Chrome DevTools Protocol enabled")
            return True
        except Exception as e:
            error_type = self.categorize_error(e)
            print(f"❌ Failed to start {self.account_type} browser: {error_type.value} - {e}")
            return False
        
    def enable_network_interception(self):
        """Enable network interception using Chrome DevTools Protocol"""
        if not self.driver:
            print("❌ Browser not started. Call start_browser() first.")
            return False
        
        try:
            # Enable network interception
            self.driver.execute_cdp_cmd("Network.enable", {})
            
            # Set up event listeners for network traffic
            self.driver.execute_cdp_cmd("Network.setRequestInterception", {"patterns": [{"urlPattern": "*"}]})
            
            # Add event listener for request interception
            self.network_enabled = True
            print("✅ Network interception enabled")
            return True
        except Exception as e:
            error_type = self.categorize_error(e)
            print(f"❌ Failed to enable network interception: {error_type.value} - {e}")
            return False
        
    def add_request_listener(self):
        """Add CDP event listeners to intercept requests and responses with improved error tracking"""
        # Save original method to reference in our modified version
        original_execute = self.driver.execute
        
        def intercept_network_events(driver, cmd, params=None):
            """Intercept and process CDP events"""
            # Process request interception
            if cmd == "Network.requestWillBeSent":
                request = params.get('request', {})
                request_id = params.get('requestId')
                url = request.get('url', '')
                
                # Store API requests related to video generation - targeting specific MakerSuite endpoints
                is_generate_video = (
                    "alkalimakersuite-pa.clients6.google.com" in url and 
                    "MakerSuiteService/GenerateVideo" in url and 
                    request.get('method') == 'POST'
                )
                
                is_get_operation = (
                    "alkalimakersuite-pa.clients6.google.com" in url and 
                    "MakerSuiteService/GetGenerateVideoOperation" in url and 
                    request.get('method') == 'POST'
                )
                
                if is_generate_video or is_get_operation:
                    endpoint_type = "GenerateVideo" if is_generate_video else "GetGenerateVideoOperation"
                    print(f"🔍 Intercepted {endpoint_type} API request: {url}")
                    self.api_requests[request_id] = {
                        'url': url,
                        'method': request.get('method'),
                        'headers': request.get('headers', {}),
                        'body': request.get('postData', {}),
                        'timestamp': time.time(),
                        'requestId': request_id,
                        'endpoint_type': endpoint_type
                    }
                    
                    # Print request body for debugging
                    try:
                        body_json = json.loads(request.get('postData', '{}'))
                        print(f"📤 Request body: {json.dumps(body_json, indent=2)[:200]}...")
                    except:
                        pass
            
            # Process response interception            
            elif cmd == "Network.responseReceived":
                response = params.get('response', {})
                request_id = params.get('requestId')
                url = response.get('url', '')
                status = response.get('status', 0)
                
                # Store API responses related to video generation
                if request_id in self.api_requests:
                    print(f"📥 Received response for video generation API: {url} (Status: {status})")
                    
                    # Create response object
                    self.video_responses[request_id] = {
                        'status': status,
                        'headers': response.get('headers', {}),
                        'url': url,
                        'body': None,  # Will be populated with getResponseBody
                        'timestamp': time.time()
                    }
                    
                    # Try to get response body
                    try:
                        body = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})
                        self.video_responses[request_id]['body'] = body
                        
                        # Check if this is a successful response
                        if 200 <= status < 300:
                            print(f"✅ Successful API response: {status}")
                            self.last_successful_api_request = {
                                'request': self.api_requests[request_id],
                                'response': self.video_responses[request_id]
                            }
                        else:
                            # Store error information
                            print(f"⚠️ API Error: {status}")
                            self.last_failed_request_reason = f"HTTP error {status}"
                            
                            try:
                                # Try to extract error message from response
                                if isinstance(body, dict) and 'body' in body:
                                    error_body = json.loads(body['body'])
                                    if 'error' in error_body:
                                        error_msg = error_body['error'].get('message', 'Unknown error')
                                        self.last_api_error_message = error_msg
                                        print(f"⚠️ API Error message: {error_msg}")
                            except:
                                pass
                            
                    except Exception as e:
                        print(f"⚠️ Could not get response body for request {request_id}: {e}")
                        
            # Process loading failures
            elif cmd == "Network.loadingFailed":
                request_id = params.get('requestId')
                error_text = params.get('errorText', 'Unknown error')
                
                if request_id in self.api_requests:
                    print(f"❌ API request failed: {error_text}")
                    self.last_failed_request_reason = error_text
            
            # Call the original execute method
            return original_execute(cmd, params)
        
        # Replace the execute method with our interceptor
        self.driver.execute = lambda cmd, params=None: intercept_network_events(self.driver, cmd, params)
        
        print("✅ Request listeners configured with error tracking")
    
    def navigate_to_ai_studio(self):
        """Navigate to Google AI Studio with improved error handling"""
        if not self.driver:
            print("❌ Browser not started. Call start_browser() first.")
            return False
            
        try:
            self.driver.get("https://aistudio.google.com/gen-media")
            print(f"✅ Navigated to Google AI Studio using {self.account_type} account")
            
            # Wait for the page to load completely
            time.sleep(3)
            
            # Check if we need to log in
            if "signin" in self.driver.current_url or "accounts.google.com" in self.driver.current_url:
                if self.account_type == "primary":
                    email = GOOGLE_EMAIL
                    password = GOOGLE_PASSWORD
                else:
                    email = BACKUP_EMAIL
                    password = BACKUP_PASSWORD
                
                print(f"⚠️ Login required for {self.account_type} account. Attempting automatic login...")
                
                try:
                    # Enter email
                    email_field = WebDriverWait(self.driver, 10).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
                    )
                    email_field.clear()
                    email_field.send_keys(email)
                    
                    # Click next button
                    next_button = self.driver.find_element(By.ID, "identifierNext")
                    next_button.click()
                    print(f"Email entered for {self.account_type} account.")
                    time.sleep(2)
                    
                    # Enter password
                    password_field = WebDriverWait(self.driver, 10).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='password']"))
                    )
                    password_field.clear()
                    password_field.send_keys(password)
                    
                    # Click next button
                    password_next = self.driver.find_element(By.ID, "passwordNext")
                    password_next.click()
                    print(f"Password entered for {self.account_type} account.")
                    
                    # Wait for redirect
                    print("Waiting for login completion...")
                    time.sleep(5)
                    
                    # Check if login was successful
                    if "aistudio.google.com" not in self.driver.current_url:
                        print("⚠️ Automatic login may have failed. Please check browser.")
                        input("Press Enter after verifying/completing login...")
                    else:
                        print("✅ Login successful")
                
                except Exception as login_error:
                    print(f"⚠️ Automatic login failed: {login_error}")
                    print("Please log in manually.")
                    input("Press Enter after logging in...")
            
            # Wait for Veo button if not already on Veo page
            try:
                veo_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//mat-card[@aria-label='Veo']"))
                )
                veo_button.click()
                print("✅ Veo selected")
                time.sleep(2)
            except Exception as veo_error:
                # Try a different approach to find Veo
                try:
                    # Look for Veo by partial text
                    veo_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Veo')]")
                    if veo_elements:
                        for element in veo_elements:
                            try:
                                element.click()
                                print("✅ Found and clicked Veo using text search")
                                time.sleep(2)
                                break
                            except:
                                continue
                    else:
                        print("ℹ️ Veo may already be selected or element not found")
                except:
                    print("ℹ️ Veo already selected or element not found")
                
            return True
                
        except Exception as e:
            error_type = self.categorize_error(e)
            print(f"❌ Error navigating to AI Studio: {error_type.value} - {e}")
            return False
    
    def upload_images(self, image_paths):
        """Upload images to the prompt with multiple fallback strategies"""
        if not image_paths:
            print("ℹ️ No images to upload")
            return True
            
        # Filter for valid image paths
        valid_paths = [path for path in image_paths if os.path.exists(path)]
        if not valid_paths:
            print("❌ No valid image paths provided")
            return False
            
        print(f"🖼️ Attempting to upload {len(valid_paths)} images...")
        
        # Multiple upload button selectors to try
        upload_selectors = [
            (By.CSS_SELECTOR, "button[aria-label='Add an image to the prompt']"),
            (By.CSS_SELECTOR, "button[aria-label='Upload a local image']"),
            (By.CSS_SELECTOR, "button[data-test-id='add-media-button']"),
            (By.XPATH, "//button[contains(@aria-label, 'image') or contains(@aria-label, 'Image')]"),
            (By.XPATH, "//button[.//mat-icon[contains(text(), 'upload') or contains(text(), 'add')]]")
        ]
        
        # Try each upload button strategy
        upload_button = None
        for selector_type, selector in upload_selectors:
            try:
                upload_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((selector_type, selector))
                )
                upload_button.click()
                print(f"✅ Clicked upload button using selector: {selector}")
                time.sleep(2)
                break
            except Exception as e:
                continue
                
        if not upload_button:
            print("❌ Could not find upload button using any selector")
            return False
            
        try:
            # Find file input with multiple strategies
            file_input_selectors = [
                (By.CSS_SELECTOR, "input[type='file']"),
                (By.XPATH, "//input[@type='file']"),
                (By.CSS_SELECTOR, "input[accept*='image']")
            ]
            
            file_input = None
            for selector_type, selector in file_input_selectors:
                try:
                    file_input = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((selector_type, selector))
                    )
                    break
                except:
                    continue
                    
            if not file_input:
                print("❌ Could not find file input element")
                return False
                
            # Upload files
            if len(valid_paths) == 1:
                file_input.send_keys(valid_paths[0])
            else:
                all_paths = "\n".join(valid_paths)
                file_input.send_keys(all_paths)
                
            print(f"✅ Uploaded {len(valid_paths)} images")
            time.sleep(3)
            return True
            
        except Exception as e:
            error_type = self.categorize_error(e)
            print(f"❌ Error uploading images: {error_type.value} - {e}")
            return False
    
    def enter_prompt(self, prompt_text):
        """Enter text into the prompt field with multiple strategies"""
        try:
            # Try multiple selectors to find the prompt textarea
            selectors = [
                (By.TAG_NAME, "textarea"),
                (By.CSS_SELECTOR, "textarea"),
                (By.CSS_SELECTOR, ".prompt-textarea"),
                (By.XPATH, "//textarea[@placeholder]")
            ]
            
            # Try each selector
            prompt_input = None
            for selector_type, selector in selectors:
                try:
                    prompt_input = WebDriverWait(self.driver, 5).until(
                        EC.visibility_of_element_located((selector_type, selector))
                    )
                    break
                except:
                    continue
            
            if not prompt_input:
                print("❌ Could not find prompt input using any selector")
                return False
                
            # Clear the field and enter text
            prompt_input.clear()
            prompt_input.send_keys(prompt_text)
            print(f"✅ Entered prompt: {prompt_text[:50]}...")
            time.sleep(1)
            return True
            
        except Exception as e:
            error_type = self.categorize_error(e)
            print(f"❌ Error entering prompt: {error_type.value} - {e}")
            return False
    
    def select_duration(self, target_duration=None):
        """
        Select a duration from the dropdown (5s, 6s, or 7s)
        
        Args:
            target_duration (str, optional): Specific duration to select, or random if None
        """
        # Try multiple dropdown selectors to handle potential UI changes
        dropdown_selectors = [
            (By.CSS_SELECTOR, ".mat-mdc-select-value"),
            (By.CSS_SELECTOR, ".mat-mdc-select-value-text"),
            (By.CSS_SELECTOR, ".mat-mdc-select"),
            (By.CSS_SELECTOR, "[role='combobox']"),
            (By.CSS_SELECTOR, ".mat-mdc-select-value#mat-select-value-4"),
            (By.XPATH, "//span[contains(@class, 'mat-mdc-select-value')]")
        ]
        
        # Select random duration if not specified
        durations = ['5s', '6s', '7s']
        selected = target_duration or random.choice(durations)
        print(f"🎲 Attempting to select {selected} duration")
        
        # Try different dropdown selection methods
        for attempt in range(3):
            try:
                # Try to find the dropdown with multiple selectors
                duration_dropdown = None
                for selector_type, selector in dropdown_selectors:
                    try:
                        duration_dropdown = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((selector_type, selector))
                        )
                        break
                    except:
                        continue
                
                if not duration_dropdown:
                    print(f"⚠️ Duration dropdown not found on attempt {attempt+1}")
                    continue
                
                # Method 1: Regular click
                try:
                    duration_dropdown.click()
                    print("✅ Clicked duration dropdown (standard method)")
                except Exception as click_error:
                    # Method 2: JavaScript click
                    try:
                        self.driver.execute_script("arguments[0].click();", duration_dropdown)
                        print("✅ Clicked duration dropdown (JavaScript method)")
                    except Exception as js_error:
                        # Method 3: ActionChains
                        from selenium.webdriver.common.action_chains import ActionChains
                        actions = ActionChains(self.driver)
                        actions.move_to_element(duration_dropdown).click().perform()
                        print("✅ Clicked duration dropdown (ActionChains method)")
                
                time.sleep(2)
                
                # Try multiple methods to find and click the option
                option_found = False
                
                # Method 1: Direct XPath with text
                try:
                    option = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, f"//mat-option[contains(text(), '{selected}')]"))
                    )
                    option.click()
                    option_found = True
                    print(f"✅ Selected {selected} duration (standard method)")
                except Exception as option_error:
                    print(f"⚠️ Could not find option using standard method: {option_error}")
                
                # Method 2: More specific selectors for options
                if not option_found:
                    # Map duration options to their IDs
                    option_ids = {'5s': 25, '6s': 26, '7s': 27}
                    option_id = option_ids.get(selected, 25)
                    
                    option_selectors = [
                        (By.ID, f"mat-option-{option_id}"),
                        (By.CSS_SELECTOR, f"#mat-option-{option_id}"),
                        (By.CSS_SELECTOR, f"mat-option[value='{selected}']"),
                        (By.XPATH, f"//span[contains(text(), '{selected}')]/parent::mat-option")
                    ]
                    
                    for selector_type, selector in option_selectors:
                        try:
                            option = WebDriverWait(self.driver, 3).until(
                                EC.element_to_be_clickable((selector_type, selector))
                            )
                            option.click()
                            option_found = True
                            print(f"✅ Selected {selected} duration using selector: {selector}")
                            break
                        except:
                            continue
                
                # Method 3: Try clicking by index
                if not option_found:
                    try:
                        # Find all mat-options
                        options = WebDriverWait(self.driver, 3).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "mat-option"))
                        )
                        
                        # Try to find the one with our text
                        for opt in options:
                            if selected in opt.text:
                                opt.click()
                                option_found = True
                                print(f"✅ Selected {selected} duration by finding in options list")
                                break
                        
                        # If still not found, just click the first option (5s)
                        if not option_found and options:
                            options[0].click()
                            print(f"⚠️ Selected first option as fallback (likely 5s)")
                            option_found = True
                    except Exception as list_error:
                        print(f"⚠️ Failed to select from options list: {list_error}")
                
                time.sleep(1)
                
                if option_found:
                    return True
                
            except Exception as e:
                error_type = self.categorize_error(e)
                print(f"❌ Error on attempt {attempt+1} selecting duration: {error_type.value} - {e}")
                time.sleep(1)
        
        print("⚠️ Failed to select duration after multiple attempts")
        return False
    
    def click_run_button(self):
        """Click the Run button to start video generation with multiple fallback strategies"""
        # Multiple Run button selectors
        run_button_selectors = [
            (By.XPATH, "//button[@aria-label='Run']"),
            (By.CSS_SELECTOR, "button[aria-label='Run']"),
            (By.XPATH, "//button[contains(text(), 'Run')]"),
            (By.CSS_SELECTOR, ".run-button"),
            (By.XPATH, "//button[contains(@class, 'run')]")
        ]
        
        # Try each method up to 3 times
        for attempt in range(3):
            try:
                # Try to find the Run button with multiple selectors
                run_button = None
                for selector_type, selector in run_button_selectors:
                    try:
                        run_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((selector_type, selector))
                        )
                        break
                    except:
                        continue
                
                if not run_button:
                    print(f"⚠️ Run button not found on attempt {attempt+1}")
                    continue
                
                # Method 1: Regular click
                try:
                    run_button.click()
                    print("✅ Clicked Run button (standard method)")
                    return True
                except Exception as click_error:
                    print(f"⚠️ Standard click failed: {click_error}")
                    
                    # Method 2: Scroll into view and click
                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", run_button)
                        time.sleep(0.5)
                        run_button.click()
                        print("✅ Clicked Run button (scroll + click method)")
                        return True
                    except Exception as scroll_error:
                        print(f"⚠️ Scroll + click failed: {scroll_error}")
                        
                        # Method 3: JavaScript click
                        try:
                            self.driver.execute_script("arguments[0].click();", run_button)
                            print("✅ Clicked Run button (JavaScript method)")
                            return True
                        except Exception as js_error:
                            print(f"⚠️ JavaScript click failed: {js_error}")
                            
                            # Method 4: Move to element and click
                            try:
                                from selenium.webdriver.common.action_chains import ActionChains
                                actions = ActionChains(self.driver)
                                actions.move_to_element(run_button).click().perform()
                                print("✅ Clicked Run button (ActionChains method)")
                                return True
                            except Exception as action_error:
                                print(f"⚠️ ActionChains click failed: {action_error}")
                
            except Exception as e:
                error_type = self.categorize_error(e)
                print(f"❌ Error on attempt {attempt+1} clicking Run button: {error_type.value} - {e}")
                time.sleep(1)
        
        print("❌ Failed to click Run button after multiple attempts")
        return False
    
    def extract_api_request(self):
        """Extract the most recent video generation API request with error handling"""
        if not self.api_requests:
            print("⚠️ No API requests intercepted yet")
            return None
            
        try:
            # Sort by timestamp and get the latest
            latest_request_id = sorted(self.api_requests.keys(), 
                                     key=lambda x: self.api_requests[x].get('timestamp', 0))[-1]
            
            request_data = self.api_requests[latest_request_id]
            print(f"📊 Retrieved API request: {request_data.get('url', 'Unknown URL')}")
            return request_data
        except Exception as e:
            print(f"❌ Error extracting API request: {e}")
            return None
    
    def replay_api_request(self, request_data=None, modified_params=None):
        """
        Replay a captured API request with optional parameter modifications
        
        Args:
            request_data: Specific request data to replay (uses latest if None)
            modified_params: Dictionary of parameters to modify in the request
        """
        # If no request data provided, use the latest or last successful one
        if not request_data:
            if self.last_successful_api_request:
                request_data = self.last_successful_api_request['request']
                print("📋 Using last successful API request")
            else:
                request_data = self.extract_api_request()
                print("📋 Using latest API request")
        
        if not request_data:
            print("❌ No request data available to replay")
            return False
            
        try:
            url = request_data.get('url')
            method = request_data.get('method')
            headers = request_data.get('headers', {})
            body = request_data.get('body', {})
            
            # Apply modifications to body if provided
            if modified_params and isinstance(body, str):
                try:
                    body_json = json.loads(body)
                    body_json.update(modified_params)
                    body = json.dumps(body_json)
                    print(f"📝 Modified request body with: {list(modified_params.keys())}")
                except Exception as modify_error:
                    print(f"⚠️ Could not modify request body: {modify_error}")
            
            # Execute the request using CDP
            print(f"🚀 Replaying API request to: {url}")
            
            # Prepare fetch parameters
            fetch_params = {
                "url": url,
                "method": method,
                "headers": headers,
                "postData": body if isinstance(body, str) else json.dumps(body)
            }
            
            # Execute the fetch
            result = self.driver.execute_cdp_cmd("Network.fetchRequest", fetch_params)
            
            print(f"✅ API request replayed. Response ID: {result.get('requestId')}")
            return result
            
        except Exception as e:
            error_type = self.categorize_error(e)
            print(f"❌ Error replaying API request: {error_type.value} - {e}")
            self.last_failed_request_reason = f"Error replaying API request: {str(e)}"
            return False
    
    def wait_for_video_generation(self, timeout=None):
        """
        Wait for video to be generated with improved error detection
        
        Args:
            timeout (int, optional): Override default timeout from config
        """
        actual_timeout = timeout or VIDEO_GENERATION_TIMEOUT
        
        try:
            start_time = time.time()
            print(f"⏳ Waiting for video generation (timeout: {actual_timeout}s)...")
            
            # Wait for either video element or error message
            video_wait = WebDriverWait(self.driver, actual_timeout)
            
            # Check for errors while waiting
            error_checks = 0
            while time.time() - start_time < actual_timeout:
                # Every few seconds, check for error messages
                if error_checks % 5 == 0:  # Check every 5 seconds
                    try:
                        error_elements = self.driver.find_elements(
                            By.XPATH, "//*[contains(text(), 'error') or contains(text(), 'failed') or contains(text(), 'exceeded')]"
                        )
                        
                        for error_elem in error_elements:
                            if error_elem.is_displayed() and any(keyword in error_elem.text.lower() for keyword in ['quota', 'error', 'fail']):
                                error_text = error_elem.text
                                print(f"❌ Error detected during video generation: {error_text}")
                                self.last_api_error_message = error_text
                                self.last_failed_request_reason = f"UI error: {error_text}"
                                return False
                    except:
                        pass  # Ignore errors in error detection
                
                # Try to find the video element
                try:
                    video_element = self.driver.find_element(By.TAG_NAME, "video")
                    if video_element.is_displayed():
                        duration = time.time() - start_time
                        print(f"✅ Video generated in {duration:.2f} seconds")
                        return True
                except:
                    pass  # Video not found yet
                    
                time.sleep(1)  # Wait a bit before checking again
                error_checks += 1
                
                # Every 15 seconds, print a waiting message
                if error_checks % 15 == 0:
                    elapsed = time.time() - start_time
                    print(f"⏳ Still waiting for video... ({elapsed:.1f}s elapsed)")
            
            # If we get here, we've timed out
            print("❌ Video generation timed out")
            self.last_failed_request_reason = "Timeout waiting for video"
            return False
            
        except TimeoutException:
            print("❌ Video generation timed out")
            self.last_failed_request_reason = "Timeout exception"
            return False
        except Exception as e:
            error_type = self.categorize_error(e)
            print(f"❌ Error waiting for video: {error_type.value} - {e}")
            self.last_failed_request_reason = f"Error waiting for video: {str(e)}"
            return False
    
    def download_video(self, video_number=None):
        """
        Click the download button to save the video
        
        Args:
            video_number (int, optional): Scene number for filename
        """
        try:
            # Try multiple selectors for download button
            download_selectors = [
                (By.XPATH, "//button[@aria-label='Download video']"),
                (By.CSS_SELECTOR, "button[aria-label='Download video']"),
                (By.XPATH, "//button[contains(@aria-label, 'Download')]"),
                (By.XPATH, "//button[.//mat-icon[contains(text(), 'download')]]"),
                (By.XPATH, "//button[contains(text(), 'Download')]")
            ]
            
            # Try each selector
            download_button = None
            for selector_type, selector in download_selectors:
                try:
                    download_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((selector_type, selector))
                    )
                    break
                except:
                    continue
            
            if not download_button:
                print("⚠️ Download button not found")
                return False
                
            # Click the button
            download_button.click()
            
            # Construct expected filename based on timestamp
            timestamp = int(time.time())
            scene_prefix = f"scene_{video_number}_" if video_number else ""
            expected_filename = f"{scene_prefix}video_{timestamp}.mp4"
            
            print(f"✅ Download initiated: {expected_filename}")
            time.sleep(3)  # Wait for download to start
            return True
            
        except Exception as e:
            error_type = self.categorize_error(e)
            print(f"❌ Error downloading video: {error_type.value} - {e}")
            return False
            
    def handle_error(self, error_message):
        """
        Handle errors during video generation process
        
        Args:
            error_message: Error message or exception
        """
        error_type = self.categorize_error(error_message)
        print(f"⚠️ Handling error: {error_type.value}")
        
        # Try to dismiss error dialogs
        try:
            # Look for dismiss buttons
            dismiss_selectors = [
                (By.XPATH, "//button[contains(., 'Dismiss')]"),
                (By.XPATH, "//button[contains(., 'OK')]"),
                (By.XPATH, "//button[@aria-label='Close']"),
                (By.CSS_SELECTOR, ".error-dialog button"),
                (By.CSS_SELECTOR, ".mat-dialog-actions button")
            ]
            
            for selector_type, selector in dismiss_selectors:
                try:
                    dismiss_buttons = self.driver.find_elements(selector_type, selector)
                    if dismiss_buttons:
                        for button in dismiss_buttons:
                            if button.is_displayed():
                                button.click()
                                print("✅ Dismissed error dialog")
                                time.sleep(1)
                                return True
                except:
                    continue
                    
            # Fallback: Send escape key
            self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            print("✅ Sent Escape key to dismiss dialog")
            time.sleep(1)
            
            return True
            
        except Exception as e:
            print(f"⚠️ Error handling failed: {e}")
            return False
    
    def find_scene_images(self, scene_number):
        """Find image files for a specific scene"""
        try:
            images = []
            
            # Check for directory-based scene images (newer format)
            scene_dir_pattern = os.path.join(SCENE_IMAGES_DIR, f"scene_{scene_number}")
            if os.path.isdir(scene_dir_pattern):
                # Direct match to scene directory
                image_files = glob.glob(os.path.join(scene_dir_pattern, "*.png"))
                images.extend(image_files)
            else:
                # Try pattern matching (for numbered subdirectories)
                pattern = os.path.join(SCENE_IMAGES_DIR, f"scene_{scene_number}*")
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
    
    def create_combined_prompt(self, scene_data):
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
        
        # If no parts were found, use a fallback
        if not prompt_parts and scene_data.get('prompt'):
            return scene_data['prompt']
            
        return ". ".join(prompt_parts)
        
    def save_checkpoint(self, successful_scenes, current_scene_index, total_scenes):
        """Save current progress to checkpoint file"""
        try:
            checkpoint_data = {
                "successful_scenes": successful_scenes,
                "current_scene_index": current_scene_index,
                "total_scenes": total_scenes,
                "timestamp": time.time(),
                "last_account": self.account_type,
                "using_cdp": True  # Flag to indicate CDP-based automation
            }
            
            checkpoint_path = os.path.join(os.path.expanduser("~"), "Downloads", CHECKPOINT_FILE)
            with open(checkpoint_path, 'w') as f:
                json.dump(checkpoint_data, f, indent=2)
            
            print(f"💾 Checkpoint saved: {successful_scenes}/{total_scenes} scenes completed")
            return True
        except Exception as e:
            print(f"❌ Error saving checkpoint: {e}")
            return False
    
    def load_checkpoint(self):
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
            
            # If account type in checkpoint doesn't match current instance, warn user
            if checkpoint_data.get('last_account') != self.account_type:
                print(f"⚠️ Warning: Checkpoint was using {checkpoint_data.get('last_account')} account, but current instance is using {self.account_type}")
                
            return checkpoint_data
        except Exception as e:
            print(f"❌ Error loading checkpoint: {e}")
            return None
    
    def clear_checkpoint(self):
        """Remove checkpoint file when workflow is complete"""
        try:
            checkpoint_path = os.path.join(os.path.expanduser("~"), "Downloads", CHECKPOINT_FILE)
            if os.path.exists(checkpoint_path):
                os.remove(checkpoint_path)
                print("🗑️ Checkpoint cleared - workflow complete")
        except Exception as e:
            print(f"❌ Error clearing checkpoint: {e}")
    
    def process_scene(self, scene_data, scene_images=None):
        """Process a scene with text prompt and optional images with robust error handling"""
        scene_num = scene_data.get('scene_number', 'Unknown')
        scene_title = scene_data.get('scene_title', 'Untitled')
        print(f"\n=== Processing Scene {scene_num}: {scene_title} ===")
        print(f"🔄 Using {self.account_type} account with CDP")
        
        # Reset retry count for this scene
        self.retry_count = 0
        
        # Navigate to AI Studio if needed
        if "gen-media" not in self.driver.current_url:
            self.navigate_to_ai_studio()
        
        # Create a combined prompt from scene data
        prompt_text = self.create_combined_prompt(scene_data)
        if not prompt_text:
            print("❌ No prompt could be created from scene data")
            return False
        
        print(f"📝 Using prompt: {prompt_text[:100]}...")
        
        # Start capturing API calls if not already enabled
        if not self.network_enabled:
            self.enable_network_interception()
            self.add_request_listener()
            
        # Attempt process with retries
        while self.retry_count < self.max_retries:
            try:
                # Show current attempt
                self.retry_count += 1
                print(f"\n🔄 Attempt {self.retry_count}/{self.max_retries} for scene {scene_num}")
                
                # 1. Enter the prompt
                prompt_success = self.enter_prompt(prompt_text)
                if not prompt_success:
                    print("⚠️ Failed to enter prompt, retrying...")
                    continue
                
                # 2. Upload images if available
                if scene_images:
                    upload_success = self.upload_images(scene_images)
                    if not upload_success:
                        print("⚠️ Failed to upload images, continuing with text-only...")
                
                # 3. Select a random duration
                duration_success = self.select_duration()
                if not duration_success:
                    print("⚠️ Failed to select duration, continuing anyway...")
                
                # 4. Click Run button to capture the API request
                run_success = self.click_run_button()
                if not run_success:
                    print("⚠️ Failed to click Run button, retrying...")
                    continue
                
                # 5. Wait a moment for the API request to be captured
                time.sleep(3)
                
                # 6. Check if we captured any API requests
                if self.api_requests:
                    print("🎯 API request captured! Attempting direct API replay...")
                    
                    # Try to replay the API with our current parameters
                    api_success = self.replay_makersuite_api(
                        prompt_text=prompt_text,
                        duration=None,  # Use the duration already selected in UI
                        scene_images=scene_images
                    )
                    
                    if api_success:
                        print("✅ API replay initiated, monitoring progress...")
                        generation_success = self.monitor_generation_progress()
                    else:
                        print("⚠️ API replay failed, falling back to UI monitoring...")
                        generation_success = self.wait_for_video_generation()
                else:
                    print("⚠️ No API request captured, using standard UI monitoring...")
                    generation_success = self.wait_for_video_generation()
                
                if generation_success:
                    # 6. Download the generated video
                    download_success = self.download_video(scene_num)
                    if download_success:
                        print(f"✅ Successfully processed scene {scene_num} on attempt {self.retry_count}")
                        return True
                    else:
                        print(f"⚠️ Video generated but download failed for scene {scene_num}")
                        # Consider this a success anyway since video was generated
                        return True
                else:
                    # Handle error and prepare for retry
                    error_reason = self.last_failed_request_reason or "Unknown error"
                    print(f"⚠️ Video generation failed: {error_reason}")
                    
                    # Dismiss any error dialogs
                    self.handle_error(error_reason)
                    
                    # Add a delay before retry with some randomness
                    retry_delay = random.randint(
                        int(RETRY_WAIT_TIME * 0.8), 
                        int(RETRY_WAIT_TIME * 1.2)
                    )
                    print(f"⏳ Waiting {retry_delay} seconds before retry...")
                    time.sleep(retry_delay)
                    
            except Exception as e:
                error_type = self.categorize_error(e)
                print(f"❌ Error on attempt {self.retry_count}: {error_type.value} - {e}")
                time.sleep(5)  # Brief delay before retry
        
        # If we get here, all retries failed
        print(f"❌ Failed to process scene {scene_num} after {self.max_retries} attempts")
        return False
    
    def close(self):
        """Close the browser and clean up"""
        if self.driver:
            try:
                self.driver.quit()
                print(f"✅ {self.account_type.capitalize()} browser closed")
            except Exception as e:
                print(f"⚠️ Error closing {self.account_type} browser: {e}")
                
    def switch_account(self):
        """
        Create and return a new automator with the other account type
        
        Returns:
            GoogleAIStudioAutomator: New automator instance with other account
        """
        # Determine the other account type
        other_account = "backup" if self.account_type == "primary" else "primary"
        print(f"\n🔄 SWITCHING ACCOUNTS: {self.account_type} → {other_account}")
        
        # Create a new automator with the other account
        new_automator = GoogleAIStudioAutomator(account_type=other_account)
        new_automator.start_browser()
        new_automator.navigate_to_ai_studio()
        
        if new_automator.driver:
            # Enable network interception in new browser
            new_automator.enable_network_interception()
            new_automator.add_request_listener()
            
            # Transfer any captured API data if needed
            if self.last_successful_api_request:
                new_automator.last_successful_api_request = self.last_successful_api_request
                print(f"📋 Transferred successful API request data to {other_account} browser")
                
            print(f"✅ Successfully switched to {other_account} account")
            return new_automator
        else:
            print(f"❌ Failed to start {other_account} browser")
            return None

def load_scene_data(scene_file=None):
    """Load scene data from file or find the most recent one"""
    try:
        # If specific file provided, use that
        if scene_file and os.path.exists(scene_file):
            with open(scene_file, 'r') as f:
                scenes = json.load(f)
                print(f"✅ Loaded {len(scenes)} scenes from {scene_file}")
                return scenes
        
        # Otherwise find the most recent scene data file
        scene_pattern = os.path.join(SCENE_DATA_DIR, "scenes_*.json")
        scene_files = glob.glob(scene_pattern)
        
        if not scene_files:
            print("❌ No scene data files found in", SCENE_DATA_DIR)
            return None
            
        # Get the most recent file
        most_recent = max(scene_files, key=os.path.getmtime)
        print(f"📄 Using most recent scene file: {os.path.basename(most_recent)}")
        
        with open(most_recent, 'r') as f:
            scenes = json.load(f)
            print(f"✅ Loaded {len(scenes)} scenes")
            return scenes
            
    except Exception as e:
        print(f"❌ Error loading scene data: {e}")
        return None

def process_video_workflow(starting_scene=1, end_scene=None, scene_file=None):
    """
    Process the entire video generation workflow using CDP
    
    Args:
        starting_scene: First scene to process (1-indexed)
        end_scene: Last scene to process (defaults to all scenes)
        scene_file: Optional specific scene file to use
    """
    print("\n" + "="*60)
    print("🚀 Starting Advanced Video Generation Workflow with CDP")
    print("="*60)
    
    # Load scene data
    scenes = load_scene_data(scene_file)
    if not scenes:
        print("❌ No scene data available. Please run scene extraction first.")
        return
    
    total_scenes = len(scenes)
    
    # Create primary automator
    automator = GoogleAIStudioAutomator(account_type="primary")
    primary_automator = automator  # Keep reference to primary
    backup_automator = None        # Will create when needed
    
    # Load checkpoint if available
    checkpoint = automator.load_checkpoint()
    successful_scenes = 0
    
    if checkpoint:
        starting_scene = checkpoint.get('current_scene_index', 0) + 1
        successful_scenes = checkpoint.get('successful_scenes', 0)
        # If checkpoint was using backup account, switch to it
        if checkpoint.get('last_account') == 'backup':
            print("🔄 Checkpoint was using backup account, switching...")
            backup_automator = GoogleAIStudioAutomator(account_type="backup")
            backup_automator.start_browser()
            backup_automator.navigate_to_ai_studio()
            automator = backup_automator  # Switch to backup
    
    # Set end scene if not specified
    if not end_scene or end_scene > total_scenes:
        end_scene = total_scenes
    
    print(f"\n📋 Processing scenes {starting_scene} to {end_scene} (out of {total_scenes})")
    print(f"🔄 Account switching enabled every {SWITCH_ACCOUNT_AFTER_RETRIES} retries per scene")
    print(f"📝 Starting with {automator.account_type} account\n")
    
    # Start browser if not already started
    if not automator.driver:
        automator.start_browser()
        automator.navigate_to_ai_studio()
    
    # Initialize tracking variables
    account_switch_count = 0
    failed_scenes = []
    
    # Record start time
    start_time = datetime.now()
    
    try:
        # Process each scene in range
        for index, scene_data in enumerate(scenes[starting_scene-1:end_scene], starting_scene):
            # Ensure scene number is set
            scene_data['scene_number'] = scene_data.get('scene_number', index)
            
            print(f"\n{'='*60}")
            print(f"🎬 Scene {index} of {end_scene}")
            print(f"{'='*60}")
            
            # Find images for this scene
            scene_images = automator.find_scene_images(scene_data['scene_number'])
            
            # Process the scene
            success = automator.process_scene(scene_data, scene_images)
            
            if success:
                successful_scenes += 1
                print(f"✅ Scene {index}/{end_scene} processed successfully!")
                
                # Save checkpoint
                automator.save_checkpoint(successful_scenes, index, end_scene)
                
                # Add a pause between successful scenes
                if index < end_scene:
                    print(f"⏳ Waiting {SCENE_WAIT_TIME} seconds before next scene...")
                    time.sleep(SCENE_WAIT_TIME)
            else:
                print(f"❌ Failed to process scene {index}/{end_scene} with {automator.account_type} account")
                failed_scenes.append(index)
                
                # Check if we need to switch accounts after SWITCH_ACCOUNT_AFTER_RETRIES retries
                if automator.retry_count >= SWITCH_ACCOUNT_AFTER_RETRIES:
                    print(f"\n🔄 SWITCHING ACCOUNTS after {automator.retry_count} failed attempts")
                    
                    if automator.account_type == "primary":
                        # Switch to backup account
                        if backup_automator is None:
                            backup_automator = automator.switch_account()
                        automator = backup_automator
                    else:
                        # Switch back to primary
                        automator = primary_automator
                        
                    if automator.driver:
                        print(f"✅ Switched to {automator.account_type} account")
                        account_switch_count += 1
                        
                        # Try again with the new account
                        print(f"\n🔁 Retrying scene {index} with {automator.account_type} account...")
                        success = automator.process_scene(scene_data, scene_images)
                        
                        if success:
                            successful_scenes += 1
                            failed_scenes.pop()  # Remove from failed list
                            print(f"✅ Scene {index}/{end_scene} processed successfully after account switch!")
                            
                            # Save checkpoint
                            automator.save_checkpoint(successful_scenes, index, end_scene)
                            
                            # Add a pause between successful scenes
                            if index < end_scene:
                                print(f"⏳ Waiting {SCENE_WAIT_TIME} seconds before next scene...")
                                time.sleep(SCENE_WAIT_TIME)
                    else:
                        print(f"❌ Failed to switch to {automator.account_type} account")
            
        # Calculate total duration
        end_time = datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()
        duration_minutes = duration_seconds / 60
        
        # Show summary
        print("\n" + "="*60)
        print("📊 WORKFLOW SUMMARY")
        print("="*60)
        print(f"✅ Successfully processed {successful_scenes}/{end_scene-starting_scene+1} scenes")
        print(f"❌ Failed scenes: {failed_scenes}")
        print(f"🔄 Account switches: {account_switch_count}")
        print(f"⏱️ Total processing time: {duration_minutes:.1f} minutes")
        
        # Clear checkpoint if all scenes processed
        if successful_scenes == end_scene - starting_scene + 1:
            automator.clear_checkpoint()
            print("🏁 All scenes processed successfully!")
        else:
            print(f"⚠️ Some scenes failed. Checkpoint saved for resume.")
        
    except KeyboardInterrupt:
        print("\n⚠️ Workflow interrupted by user")
        print(f"📊 Progress: {successful_scenes}/{end_scene-starting_scene+1} scenes processed")
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
    
    finally:
        # Close all browsers
        print("\n🧹 Cleaning up resources...")
        if primary_automator and primary_automator.driver:
            primary_automator.close()
        if backup_automator and backup_automator.driver:
            backup_automator.close()
        
        print("👋 Workflow complete!")

def main():
    """Interactive main function"""
    print("\n🎬 GOOGLE AI STUDIO AUTOMATION WITH CDP")
    print("This script uses Chrome DevTools Protocol for robust automation")
    
    # Check for scene data
    scenes_exist = os.path.exists(SCENE_DATA_DIR)
    if not scenes_exist:
        print("\n⚠️ Scene data directory not found. Run scene extraction first.")
        return
        
    # Check for user directories
    for path in [USER_DATA_DIR, BACKUP_USER_DATA_DIR]:
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            print(f"✅ Created browser profile directory: {path}")
    
    print("\nOptions:")
    print("1. Process all scenes from beginning")
    print("2. Resume from checkpoint")
    print("3. Process specific scene range")
    print("4. Test with a single example scene")
    print("5. Analyze captured API requests (after running scenes)")
    print("6. Exit")
    
    choice = input("\nEnter your choice (1-6): ")
    
    if choice == "1":
        process_video_workflow()
        
    elif choice == "2":
        # Check if checkpoint exists
        checkpoint_path = os.path.join(os.path.expanduser("~"), "Downloads", CHECKPOINT_FILE)
        if not os.path.exists(checkpoint_path):
            print("❌ No checkpoint found. Please choose another option.")
            return
        process_video_workflow()
        
    elif choice == "3":
        try:
            start = int(input("Enter starting scene number: "))
            end = int(input("Enter ending scene number: "))
            process_video_workflow(start, end)
        except ValueError:
            print("❌ Invalid input. Please enter numbers only.")
            
    elif choice == "4":
        # Create a simple test scene
        test_scene = {
            "scene_number": 1,
            "scene_title": "Test Scene",
            "prompt": "A serene mountain landscape with a flowing river, majestic pine trees, and snow-capped peaks in the background. Cinematic quality, golden hour lighting."
        }
        
        automator = GoogleAIStudioAutomator()
        try:
            automator.start_browser()
            automator.navigate_to_ai_studio()
            automator.enable_network_interception()
            automator.add_request_listener()
            print("\n🧪 Testing with a single scene...")
            automator.process_scene(test_scene)
        finally:
            input("\nPress Enter to close the browser...")
            automator.close()
            
    elif choice == "5":
        print("\n📊 Analyzing captured API requests...")
        print("This will show you the structure of API calls captured during previous runs.")
        
        # Create a temporary automator to analyze existing data
        temp_automator = GoogleAIStudioAutomator()
        
        # For demonstration, we'll check if there are any recent checkpoint files
        # that might contain API data, or start a browser to capture some
        print("Starting browser to begin API capture...")
        if temp_automator.start_browser():
            temp_automator.navigate_to_ai_studio()
            temp_automator.enable_network_interception()
            temp_automator.add_request_listener()
            
            print("Browser started. You can now:")
            print("1. Manually trigger a video generation to capture API calls")
            print("2. Or press Enter to analyze any existing captured data")
            
            input("Press Enter when ready to analyze...")
            temp_automator.analyze_api_requests()
            
            input("Press Enter to close browser and continue...")
            temp_automator.close()
        else:
            print("Failed to start browser for analysis.")
        
    elif choice == "6":
        print("Goodbye! 👋")
        return
        
    else:
        print("❌ Invalid choice. Please run the script again.")

if __name__ == "__main__":
    main()