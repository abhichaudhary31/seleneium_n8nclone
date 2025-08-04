import time
import os
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
DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "ai_studio_image")

# --- Main Script ---
options = webdriver.ChromeOptions()
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)
prefs = {
    "download.default_directory": os.path.join(os.path.expanduser("~"), "Downloads", "ai_studio_image"),
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True,
    "profile.default_content_settings.popups": 0,
    "profile.default_content_setting_values.automatic_downloads": 1,
    "profile.content_settings.exceptions.automatic_downloads.*.setting": 1,
    "safebrowsing.enabled": False
}
options.add_experimental_option("prefs", prefs)
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument(f"user-data-dir={USER_DATA_DIR}")
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 20)

try:
    # 1. Navigate to Google AI Studio Image Generation and handle login
    print("Navigating to AI Studio Image Generation...")
    driver.get("https://aistudio.google.com/prompts/new_image")
    time.sleep(3) # Wait for potential redirect

    if "accounts.google.com" in driver.current_url:
        print("Login required. Performing login...")
        
        # Enter email - sometimes it's pre-filled
        try:
            email_field = WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email']")))
            email_field.send_keys(GOOGLE_EMAIL)
            driver.find_element(By.ID, "identifierNext").click()
            print("Email entered.")
        except TimeoutException:
            print("Email field not found, assuming it's pre-filled.")

        # Enter password
        password_field = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
        password_field.send_keys(GOOGLE_PASSWORD)
        driver.find_element(By.ID, "passwordNext").click()
        print("Password entered. Login successful.")

        # Wait for redirect back to AI studio
        print("Waiting for redirection to AI Studio...")
        wait.until(EC.url_contains("aistudio.google.com"))
        print("Redirected successfully.")
    else:
        print("Already logged in.")

    # Ensure we are on the correct page
    if "new_image" not in driver.current_url:
        driver.get("https://aistudio.google.com/prompts/new_image")
        time.sleep(3)

    # 2. Type the prompt into the text input field for image generation
    print("Typing image generation prompt...")
    prompt_text = "A heartwarming, softly lit, full-body shot of a cute cartoon girl gently applying an ice pack to her boyfriend's forehead. The art style should be a modern, friendly cartoon with slightly exaggerated, expressive features, reminiscent of popular animated movies (e.g., Disney/Pixar but distinctly 2D). The girl has large, kind eyes, a small upturned nose, and a sweet, concerned smile. Her hair is styled in soft, flowing waves or a cute ponytail, with a few stray strands. She's wearing comfortable, casual attire, like a pastel-colored t-shirt and shorts. Her posture should convey tenderness and care as she leans slightly towards him. The boyfriend is depicted with a slightly flushed face, indicative of a mild fever or bump, but with a faint, appreciative smile as he looks up at her. He has soft, tousled hair and is wearing a relaxed, perhaps slightly rumpled, t-shirt. He's sitting comfortably on a sofa or bed, leaning back slightly. The ice pack is a simple, light blue or clear gel pack, slightly frosted, held delicately in her hands. The background is a soft-focus, cozy bedroom or living room, with warm, inviting colors. Perhaps a few blurred elements like a lamp, a book, or a pillow in the background to add to the domestic atmosphere. The overall mood is one of comfort, care, and gentle affection. High detail on facial expressions and hand gestures to convey emotion. Cinematic lighting."
    
    # Wait for the prompt input field and enter the text
    try:
        # Try different selectors for the prompt input field
        prompt_input = None
        selectors_to_try = [
            "textarea",
            "input[type='text']",
            "[contenteditable='true']",
            ".prompt-input",
            "[placeholder*='prompt']",
            "[placeholder*='Prompt']"
        ]
        
        for selector in selectors_to_try:
            try:
                prompt_input = WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))
                print(f"Found prompt input using selector: {selector}")
                break
            except TimeoutException:
                continue
        
        if prompt_input is None:
            raise TimeoutException("Could not find prompt input field")
            
        prompt_input.clear()
        prompt_input.send_keys(prompt_text)
        print("Image generation prompt entered successfully.")
        
    except TimeoutException:
        print("Could not find prompt input field. Page may have different structure.")

    # 3. Click the "Generate" or "Run" button with retry logic
    max_retries = 10
    retry_counter = 0  # Counter for failed attempts that needed 26-second waits
    
    for attempt in range(max_retries):
        print(f"Attempt {attempt + 1}/{max_retries}: Looking for and clicking the generate button...")
        
        try:
            # Try different selectors for the generate/run button
            generate_button = None
            button_selectors = [
                "//button[contains(text(), 'Generate')]",
                "//button[contains(text(), 'Run')]",
                "//button[@aria-label='Generate']",
                "//button[@aria-label='Run']",
                "//button[contains(@class, 'generate')]",
                "//button[contains(@class, 'run')]"
            ]
            
            for selector in button_selectors:
                try:
                    generate_button = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, selector)))
                    print(f"Found generate button using selector: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if generate_button is None:
                print("Could not find generate button. Looking for any clickable button...")
                # Fallback: look for any button that might be the generate button
                buttons = driver.find_elements(By.TAG_NAME, "button")
                for button in buttons:
                    if button.is_enabled() and button.is_displayed():
                        button_text = button.text.lower()
                        if any(word in button_text for word in ['generate', 'run', 'create', 'submit']):
                            generate_button = button
                            print(f"Found potential generate button with text: '{button.text}'")
                            break
            
            if generate_button:
                generate_button.click()
                print("Generate button clicked.")
                
                # Check for immediate errors after clicking generate (same mechanism as video generation)
                try:
                    # Check for error message within 10 seconds (adapted for image generation)
                    error_message_xpath = "//*[contains(., 'Failed to ') or contains(., 'Failed to generate') or contains(., 'quota exceeded') or contains(., 'permission denied')]"
                    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, error_message_xpath)))
                    
                    # Error detected - handle dismissal and retry
                    print("Error detected. Beginning dismissal and retry process.")
                    
                    # Try to get the specific error message for logging
                    error_text = ""
                    try:
                        error_elements = driver.find_elements(By.XPATH, error_message_xpath)
                        for error_elem in error_elements:
                            if error_elem.is_displayed():
                                error_text = error_elem.text
                                print(f"❌ Error message detected: {error_text}")
                                break
                    except:
                        print("Could not read specific error message.")
                    
                    # Dismiss error popup with same strategy as video generation
                    try:
                        dismiss_button_xpath = "//button[@aria-label='Dismiss'] | //button[contains(., 'Dismiss') or contains(., 'OK') or @aria-label='Close'] | //button[contains(@class, 'dismiss-button')] | //button[.//span[contains(text(), 'close')]]"
                        dismiss_button = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, dismiss_button_xpath)))
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

                    # Check if this is a permanent error (exit immediately)
                    permanent_errors = [
                        "permission denied",
                        "content policy",
                        "safety filter",
                        "not allowed",
                        "blocked",
                        "inappropriate"
                    ]
                    
                    error_text_lower = error_text.lower()
                    is_permanent = any(perm_pattern in error_text_lower for perm_pattern in permanent_errors)
                    
                    if is_permanent:
                        print("❌ Permanent error detected - exiting immediately.")
                        break
                    
                    # Increment retry counter for errors that require waiting
                    retry_counter += 1
                    print(f"Error retry count: {retry_counter}")
                    
                    # After 5 retries, switch to specific model option
                    if retry_counter > 5:
                        print(f"🔄 After {retry_counter} failed attempts, switching to Imagen 3.0 model...")
                        try:
                            # Step 1: Click the model selector dropdown (shows "Imagen 4.0 (Preview)")
                            # Start with simpler, more direct approaches
                            model_selector_xpaths = [
                                "//*[contains(text(), 'Imagen 4.0 (Preview)')]",
                                "//*[contains(text(), 'Imagen 4.0') and contains(text(), 'Preview')]",
                                "//*[contains(text(), 'imagen 4.0') and contains(text(), 'preview')]",
                                "//*[text()='Imagen 4.0 (Preview)']",
                                "//span[contains(text(), 'Imagen 4.0 (Preview)')]",
                                "//div[contains(text(), 'Imagen 4.0 (Preview)')]",
                                "//button[contains(text(), 'Imagen 4.0 (Preview)')]",
                                "//*[contains(text(), 'Imagen 4')]",
                                "//*[contains(text(), 'imagen 4')]"
                            ]
                            
                            model_selector = None
                            print("Searching for model selector dropdown with text 'Imagen 4.0 (Preview)'...")
                            
                            for i, xpath in enumerate(model_selector_xpaths):
                                try:
                                    print(f"Trying XPath strategy {i+1}: {xpath}")
                                    elements = driver.find_elements(By.XPATH, xpath)
                                    print(f"Found {len(elements)} elements with this XPath")
                                    
                                    for element in elements:
                                        try:
                                            if element.is_displayed():
                                                element_text = element.text
                                                print(f"Found visible element with text: '{element_text}'")
                                                if element.is_enabled():
                                                    model_selector = element
                                                    print(f"Found clickable model selector with text: '{element_text}'")
                                                    break
                                                else:
                                                    print("Element found but not clickable, checking parent...")
                                                    # Try parent element if current element is not clickable
                                                    try:
                                                        parent = element.find_element(By.XPATH, "..")
                                                        if parent.is_enabled():
                                                            model_selector = parent
                                                            print(f"Found clickable parent element")
                                                            break
                                                    except:
                                                        continue
                                        except Exception as e:
                                            print(f"Error checking element: {e}")
                                            continue
                                    
                                    if model_selector:
                                        print(f"Successfully found model selector using XPath strategy {i+1}")
                                        break
                                        
                                except Exception as e:
                                    print(f"Error with XPath strategy {i+1}: {e}")
                                    continue
                            
                            # If still not found, try a more general search
                            if model_selector is None:
                                print("Direct XPath search failed. Trying general element search...")
                                all_elements = driver.find_elements(By.XPATH, "//*")
                                print(f"Searching through {len(all_elements)} elements for 'Imagen 4.0 (Preview)'...")
                                
                                for element in all_elements:
                                    try:
                                        if element.is_displayed():
                                            element_text = element.text
                                            if element_text and 'imagen 4' in element_text.lower() and 'preview' in element_text.lower():
                                                print(f"Found potential model selector: '{element_text}'")
                                                if element.is_enabled():
                                                    model_selector = element
                                                    print("Element is clickable!")
                                                    break
                                                else:
                                                    # Try parent
                                                    try:
                                                        parent = element.find_element(By.XPATH, "..")
                                                        if parent.is_enabled():
                                                            model_selector = parent
                                                            print("Parent element is clickable!")
                                                            break
                                                    except:
                                                        continue
                                    except:
                                        continue
                            
                            if model_selector is None:
                                print("🔍 DEBUG: Model selector not found. Printing all visible text on page...")
                                all_elements = driver.find_elements(By.XPATH, "//*")
                                visible_texts = []
                                for element in all_elements:
                                    try:
                                        if element.is_displayed():
                                            text = element.text.strip()
                                            if text and len(text) < 100:  # Avoid very long texts
                                                visible_texts.append(text)
                                    except:
                                        continue
                                
                                # Remove duplicates and print unique texts
                                unique_texts = list(set(visible_texts))
                                print("📝 Visible text elements on page:")
                                for text in sorted(unique_texts):
                                    if any(word in text.lower() for word in ['imagen', 'model', 'dropdown', 'select', 'button']):
                                        print(f"  🔸 {text}")
                                
                                raise TimeoutException("Could not find model selector dropdown")
                                
                            model_selector.click()
                            print("Model selector dropdown clicked. Waiting for dropdown options to appear...")
                            time.sleep(5)  # Increased wait for dropdown to fully open
                            
                            # Step 2: Select "Imagen 3.0" from the dropdown options
                            print("Searching for Imagen 3.0 option in dropdown...")
                            imagen3_option_xpaths = [
                                "//*[contains(text(), 'Imagen 3.0')]",
                                "//*[contains(text(), 'imagen 3.0')]", 
                                "//*[text()='Imagen 3.0']",
                                "//span[contains(text(), 'Imagen 3.0')]",
                                "//div[contains(text(), 'Imagen 3.0')]",
                                "//li[contains(text(), 'Imagen 3.0')]",
                                "//*[contains(text(), 'Imagen 3')]"
                            ]
                            
                            imagen3_option = None
                            for i, xpath in enumerate(imagen3_option_xpaths):
                                try:
                                    print(f"Trying Imagen 3.0 XPath strategy {i+1}: {xpath}")
                                    elements = driver.find_elements(By.XPATH, xpath)
                                    print(f"Found {len(elements)} elements with this XPath")
                                    
                                    for element in elements:
                                        try:
                                            if element.is_displayed():
                                                element_text = element.text
                                                print(f"Found visible Imagen 3.0 element: '{element_text}'")
                                                if element.is_enabled():
                                                    imagen3_option = element
                                                    print("Found clickable Imagen 3.0 option!")
                                                    break
                                                else:
                                                    # Try parent element
                                                    try:
                                                        parent = element.find_element(By.XPATH, "..")
                                                        if parent.is_enabled():
                                                            imagen3_option = parent
                                                            print("Found clickable parent for Imagen 3.0 option!")
                                                            break
                                                    except:
                                                        continue
                                        except Exception as e:
                                            print(f"Error checking Imagen 3.0 element: {e}")
                                            continue
                                    
                                    if imagen3_option:
                                        print(f"Successfully found Imagen 3.0 option using XPath strategy {i+1}")
                                        break
                                        
                                except Exception as e:
                                    print(f"Error with Imagen 3.0 XPath strategy {i+1}: {e}")
                                    continue
                            
                            # If still not found, search all elements
                            if imagen3_option is None:
                                print("Direct XPath search for Imagen 3.0 failed. Trying general search...")
                                all_elements = driver.find_elements(By.XPATH, "//*")
                                for element in all_elements:
                                    try:
                                        if element.is_displayed():
                                            element_text = element.text
                                            if element_text and 'imagen 3' in element_text.lower():
                                                print(f"Found potential Imagen 3.0 option: '{element_text}'")
                                                if element.is_enabled():
                                                    imagen3_option = element
                                                    break
                                                else:
                                                    # Try parent
                                                    try:
                                                        parent = element.find_element(By.XPATH, "..")
                                                        if parent.is_enabled():
                                                            imagen3_option = parent
                                                            break
                                                    except:
                                                        continue
                                    except:
                                        continue
                            
                            if imagen3_option is None:
                                raise TimeoutException("Could not find Imagen 3.0 option")
                                
                            imagen3_option.click()
                            print("Switched to Imagen 3.0 model.")
                            time.sleep(3)  # Wait for model switch to complete
                            
                            # Reset retry counter after model switch
                            retry_counter = 0
                            print("Retry counter reset after model switch to Imagen 3.0.")
                            
                        except TimeoutException as e:
                            print("⚠️ Could not switch to Imagen 3.0 model. Continuing with regular retry...")
                            print(f"  - Error details: {str(e)}")
                            if "model selector dropdown" in str(e):
                                print("  - Could not find the model selector dropdown")
                            elif "Imagen 3.0 option" in str(e):
                                print("  - Found dropdown but could not find Imagen 3.0 option")
                            else:
                                print("  - General timeout during model switching")
                    
                    # Wait before retry (same timing as video generation)
                    print(f"Waiting for 10 seconds before retry attempt {attempt + 2}...")
                    time.sleep(10)
                    
                    if attempt == max_retries - 1:
                        print("Maximum retries reached. Could not generate image.")
                        break
                    
                    continue  # Go to next retry attempt

                except TimeoutException:
                    # No error detected - assume success (same as video generation)
                    print("✅ No error detected. Image generation appears to be in progress.")
                    
                    # Reset retry counter on successful generation start
                    retry_counter = 0
                    
                    # Wait a bit for generation to start
                    time.sleep(10)
                
            else:
                print("No suitable generate button found.")
                break

            # Wait for image generation to complete
            print("Waiting for image generation to complete...")
            try:
                # Wait for generated image to appear with more comprehensive selectors
                image_wait = WebDriverWait(driver, 60)  # Shorter wait for images than videos
                
                # Try different selectors for generated images - more comprehensive list
                image_selectors = [
                    "img",  # All images - we'll filter later
                    "canvas",  # Canvas elements
                    "[role='img']",  # Elements with img role
                    ".image-container img",
                    ".generated-content img",
                    ".output img",
                    ".response img",
                    "img[src*='generated']",
                    "img[alt*='generated']",
                    "img[src*='blob:']",
                    "img[src*='data:']",
                    "img[src*='googleusercontent']",
                    "img[src*='storage.googleapis']"
                ]
                
                generated_image = None
                print("Searching for generated images...")
                
                # First, wait for any image to appear that wasn't there before
                initial_images = driver.find_elements(By.TAG_NAME, "img")
                initial_image_count = len(initial_images)
                print(f"Initial image count on page: {initial_image_count}")
                
                # Wait for new images to appear
                for attempt_inner in range(30):  # 30 seconds of checking
                    time.sleep(2)
                    current_images = driver.find_elements(By.TAG_NAME, "img")
                    current_image_count = len(current_images)
                    
                    if current_image_count > initial_image_count:
                        print(f"New images detected! Count increased from {initial_image_count} to {current_image_count}")
                        # Find the new images
                        new_images = current_images[initial_image_count:]
                        for img in new_images:
                            try:
                                if img.is_displayed() and img.size['width'] > 50 and img.size['height'] > 50:
                                    src = img.get_attribute('src')
                                    alt = img.get_attribute('alt')
                                    print(f"Found potential generated image - src: {src[:100] if src else 'None'}, alt: {alt}")
                                    generated_image = img
                                    break
                            except Exception as e:
                                print(f"Error checking image: {e}")
                                continue
                        
                        if generated_image:
                            break
                    else:
                        print(f"Waiting for images... Current count: {current_image_count}")
                
                # If no new images found, try the original selector approach
                if generated_image is None:
                    print("No new images detected. Trying selector-based approach...")
                    for selector in image_selectors:
                        try:
                            elements = driver.find_elements(By.CSS_SELECTOR, selector)
                            print(f"Found {len(elements)} elements with selector: {selector}")
                            
                            for element in elements:
                                try:
                                    if element.is_displayed() and element.size['width'] > 50 and element.size['height'] > 50:
                                        if element.tag_name == 'img':
                                            src = element.get_attribute('src')
                                            if src and ('blob:' in src or 'data:' in src or 'generated' in src or 'googleusercontent' in src):
                                                print(f"Found generated image using selector {selector}: {src[:100]}")
                                                generated_image = element
                                                break
                                        elif element.tag_name == 'canvas':
                                            print(f"Found canvas element using selector {selector}")
                                            generated_image = element
                                            break
                                except Exception as e:
                                    continue
                            
                            if generated_image:
                                break
                                
                        except Exception as e:
                            print(f"Error with selector {selector}: {e}")
                            continue
                
                if generated_image:
                    print("Image has been generated successfully!")
                    print(f"Generated image details - Tag: {generated_image.tag_name}, Size: {generated_image.size}")
                    
                    # Try to download the image
                    print("Attempting to download the image...")
                    try:
                        # Get the image source
                        src = generated_image.get_attribute('src')
                        if src:
                            print("Found image source, attempting to save...")
                            # For base64 encoded images
                            if src.startswith('data:image'):
                                import base64
                                # Extract the base64 data
                                img_data = src.split(',')[1]
                                # Save the image
                                img_path = os.path.join(DOWNLOAD_DIR, f"generated_image_{int(time.time())}.png")
                                with open(img_path, 'wb') as f:
                                    f.write(base64.b64decode(img_data))
                                print(f"Image saved to: {img_path}")
                            else:
                                # For direct image URLs
                                import urllib.request
                                img_path = os.path.join(DOWNLOAD_DIR, f"generated_image_{int(time.time())}.png")
                                urllib.request.urlretrieve(src, img_path)
                                print(f"Image saved to: {img_path}")
                            print("Image downloaded successfully!")
                            time.sleep(2)  # Wait a bit after download
                            break
                        
                        # If direct download fails, try the download button
                        print("Trying download button as fallback...")
                        actions = ActionChains(driver)
                        actions.move_to_element(generated_image).perform()
                        time.sleep(3)  # Longer wait for hover effect
                        
                        # Look for download button with more comprehensive selectors
                        download_selectors = [
                            "//button[@aria-label='Download this image']",
                            "//button[@aria-label='Download']",
                            "//button[contains(@aria-label, 'download')]",
                            "//button[contains(@aria-label, 'Download')]",
                            "//button[contains(text(), 'Download')]",
                            "//button[contains(text(), 'download')]",
                            "//button[contains(@class, 'download')]",
                            "//a[contains(@download, '')]",
                            "//button[contains(@title, 'Download')]",
                            "//button[contains(@title, 'download')]",
                            "//*[@role='button' and contains(@aria-label, 'download')]",
                            "//*[@role='button' and contains(text(), 'Download')]"
                        ]
                        
                        download_button = None
                        print("Searching for download button...")
                        
                        for selector in download_selectors:
                            try:
                                buttons = driver.find_elements(By.XPATH, selector)
                                print(f"Found {len(buttons)} buttons with selector: {selector}")
                                
                                for button in buttons:
                                    try:
                                        if button.is_displayed() and button.is_enabled():
                                            print(f"Found visible download button: {button.get_attribute('aria-label') or button.text or 'No text'}")
                                            download_button = button
                                            break
                                    except Exception as e:
                                        continue
                                
                                if download_button:
                                    print(f"Successfully found download button using selector: {selector}")
                                    break
                                    
                            except Exception as e:
                                print(f"Error with download selector {selector}: {e}")
                                continue
                        
                        # If download button still not found, try hovering over different areas
                        if download_button is None:
                            print("Download button not found after first hover. Trying different hover strategies...")
                            
                            # Try hovering over parent containers
                            containers_to_try = []
                            try:
                                containers_to_try.append(generated_image.find_element(By.XPATH, ".."))  # Parent
                                containers_to_try.append(generated_image.find_element(By.XPATH, "../.."))  # Grandparent
                            except:
                                pass
                            
                            for container in containers_to_try:
                                try:
                                    print("Hovering over parent container...")
                                    actions.move_to_element(container).perform()
                                    time.sleep(3)
                                    
                                    # Search for download button again
                                    for selector in download_selectors:
                                        try:
                                            buttons = driver.find_elements(By.XPATH, selector)
                                            for button in buttons:
                                                if button.is_displayed() and button.is_enabled():
                                                    print(f"Found download button after container hover using selector: {selector}")
                                                    download_button = button
                                                    break
                                            if download_button:
                                                break
                                        except:
                                            continue
                                    
                                    if download_button:
                                        break
                                        
                                except Exception as e:
                                    print(f"Error hovering over container: {e}")
                                    continue
                        
                        if download_button:
                            # Make sure we're hovering over the download button when we click
                            print("Clicking the download button...")
                            actions.move_to_element(download_button).perform()
                            time.sleep(1)
                            download_button.click()
                            print(f"Download initiated. Check '{DOWNLOAD_DIR}' for the image.")
                            time.sleep(5)  # Wait for download to start
                        else:
                            print("No download button found even after comprehensive search.")
                            
                            # Also try right-clicking on the image as a fallback
                            print("Trying right-click on image as fallback...")
                            try:
                                actions.context_click(generated_image).perform()
                                time.sleep(2)
                                print("Right-clicked on image. You may need to manually select 'Save image as...'")
                            except Exception as e:
                                print(f"Right-click failed: {e}")
                        
                    except Exception as e:
                        print(f"Could not download image automatically: {e}")
                    
                    break  # Exit the retry loop on success
                else:
                    print("Generated image not found. Retrying...")
                    
            except TimeoutException:
                print("Image generation timed out. Checking for errors...")
                
                # Check for error messages
                error_selectors = [
                    "//*[contains(text(), 'error')]",
                    "//*[contains(text(), 'failed')]",
                    "//*[contains(text(), 'quota')]",
                    "//*[contains(text(), 'limit')]"
                ]
                
                error_found = False
                for selector in error_selectors:
                    try:
                        error_element = driver.find_element(By.XPATH, selector)
                        if error_element.is_displayed():
                            print(f"Error detected: {error_element.text}")
                            error_found = True
                            break
                    except:
                        continue
                
                if error_found:
                    print("Error detected. Waiting before retry...")
                    time.sleep(10)
                else:
                    print("No specific error found. Retrying...")
                    time.sleep(5)
                
                if attempt == max_retries - 1:
                    print("Maximum retries reached. Could not generate image.")
                    break

        except Exception as e:
            print(f"Unexpected error in attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                print("Maximum retries reached due to errors.")
                break
            time.sleep(5)

    print("Script finished. Keeping browser open for 10 seconds to view results.")
    time.sleep(10)

finally:
    print("Closing the browser.")
    driver.quit()
