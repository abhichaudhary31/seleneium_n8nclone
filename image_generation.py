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
        # Take a screenshot for debugging
        driver.save_screenshot(os.path.join(DOWNLOAD_DIR, "debug_screenshot.png"))
        print(f"Screenshot saved to {DOWNLOAD_DIR}/debug_screenshot.png for debugging")

    # 3. Click the "Generate" or "Run" button with retry logic
    max_retries = 50
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
                            print("Taking screenshot for debugging...")
                            # Take a screenshot for debugging
                            screenshot_path = os.path.join(DOWNLOAD_DIR, f"debug_no_download_button_{int(time.time())}.png")
                            driver.save_screenshot(screenshot_path)
                            print(f"Debug screenshot saved to {screenshot_path}")
                            
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
