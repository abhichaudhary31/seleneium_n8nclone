
import time
import os
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
DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Documents")

# --- Main Script ---
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
    if "gen-media" not in driver.current_url:
        driver.get("https://aistudio.google.com/gen-media")
        
    # 3. Click the "Veo" button/card
    print("Looking for and clicking the 'Veo' button...")
    veo_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//mat-card[@aria-label='Veo']")))
    veo_button.click()
    print("'Veo' button clicked.")

    # 4. Type the prompt into the text input field
    print("Typing prompt...")
    prompt_text = "A heartwarming, softly lit, full-body shot of a cute cartoon girl gently applying an ice pack to her boyfriend's forehead. The art style should be a modern, friendly cartoon with slightly exaggerated, expressive features, reminiscent of popular animated movies (e.g., Disney/Pixar but distinctly 2D).The girl has large, kind eyes, a small upturned nose, and a sweet, concerned smile. Her hair is styled in soft, flowing waves or a cute ponytail, with a few stray strands. She's wearing comfortable, casual attire, like a pastel-colored t-shirt and shorts. Her posture should convey tenderness and care as she leans slightly towards him.The boyfriend is depicted with a slightly flushed face, indicative of a mild fever or bump, but with a faint, appreciative smile as he looks up at her. He has soft, tousled hair and is wearing a relaxed, perhaps slightly rumpled, t-shirt. He's sitting comfortably on a sofa or bed, leaning back slightly.The ice pack is a simple, light blue or clear gel pack, slightly frosted, held delicately in her hands. The background is a soft-focus, cozy bedroom or living room, with warm, inviting colors. Perhaps a few blurred elements like a lamp, a book, or a pillow in the background to add to the domestic atmosphere. The overall mood is one of comfort, care, and gentle affection. High detail on facial expressions and hand gestures to convey emotion. Cinematic lighting."
    # Assuming the input field is a textarea, we wait for it to be visible
    prompt_input = wait.until(EC.visibility_of_element_located((By.TAG_NAME, "textarea")))
    prompt_input.send_keys(prompt_text)
    print(f"Prompt '{prompt_text}' entered.")

    # 5. Click the "Run" button with retry logic
    max_retries = 50
    for attempt in range(max_retries):
        print(f"Attempt {attempt + 1}/{max_retries}: Clicking the 'Run' button...")
        # Find and click the run button in each attempt, using the more specific aria-label
        run_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Run']")))
        run_button.click()

        try:
            # Check for an error message within 5 seconds. If found, handle it.
            # If not found, a TimeoutException occurs, and we assume success.
            error_message_xpath = "//*[contains(., 'Failed to generate video, quota exceeded') or contains(., 'Failed to generate video: permission denied')]"
            WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.XPATH, error_message_xpath)))
            
            # This code only runs if an error IS found
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

            print(f"Waiting for 5 seconds before retry attempt {attempt + 2}...")
            time.sleep(20)
            
            if attempt == max_retries - 1:
                print("Maximum retries reached. Could not generate video. Exiting.")

        except TimeoutException:
            # If no error was found, assume success and wait for the video.
            print("No error detected. Assuming generation is in progress. Waiting for video...")
            try:
                video_wait = WebDriverWait(driver, 300)
                video_wait.until(EC.presence_of_element_located((By.TAG_NAME, "video")))
                print("Video has been generated successfully.")

                # Download the video
                print("Attempting to download the video...")
                download_button = WebDriverWait(driver, 30).until(EC.element_to_be_clickable(
                    (By.XPATH, "//button[@aria-label='Download video']")
                ))
                download_button.click()
                
                print(f"Waiting for download to complete in '{DOWNLOAD_DIR}'...")
                time.sleep(15)
                print("Download process finished.")

                break # Exit the loop on success
            except TimeoutException:
                print("Waited for video, but it did not generate in time. Retrying...")
                if attempt == max_retries - 1:
                    print("Maximum retries reached. Could not generate video. Exiting.")


    print("Script finished. Waiting for a bit before closing.")
    time.sleep(10) # Wait to see the result

finally:
    print("Closing the browser.")
    driver.quit()

