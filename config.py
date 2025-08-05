# Configuration file for test_selenium.py
# This file contains your actual credentials and settings

# --- ACCOUNT CREDENTIALS ---
# Primary Google Account
GOOGLE_EMAIL = "chaudharyabhishek031@gmail.com"
GOOGLE_PASSWORD = "GAme++0103"

# Backup Google Account (for automatic failover)
BACKUP_EMAIL = "theladyinsaree@gmail.com"
BACKUP_PASSWORD = "Stuti@0103"

# --- BROWSER SETTINGS ---
# Number of retry attempts before switching accounts
SWITCH_ACCOUNT_AFTER_RETRIES = 1  # Switch every 2 attempts (1+1)

# Browser profile directories
USER_DATA_DIR_NAME = "selenium_chrome_profile"
BACKUP_USER_DATA_DIR_NAME = "selenium_chrome_profile_backup"

# --- OVERLAY HANDLING ---
# Options: "simplified", "minimal", "off"
# - "simplified": Basic overlay removal with common selectors (recommended)
# - "minimal": Just send escape keys when needed
# - "off": No overlay handling (let click fallbacks handle it)
OVERLAY_HANDLING = "simplified"

# --- PAGE RELOAD SETTINGS ---
# Enable page reload every N failed attempts to reset state
ENABLE_PAGE_RELOAD = False  # Disabled for better performance
PAGE_RELOAD_INTERVAL = 2    # Reload every N attempts if enabled

# --- TIMING SETTINGS ---
# Wait time between retry attempts (seconds)
RETRY_WAIT_TIME = 22  # Random between 16-22 seconds for more human-like behavior

# Wait time between scenes to avoid rate limiting (seconds)
SCENE_WAIT_TIME = 30

# --- PAUSE AND RESUME SETTINGS ---
# Restart script after every N successful video generations (closes browser and restarts)
RESTART_AFTER_VIDEOS = 3

# Pause duration in minutes before restarting
RESTART_PAUSE_MINUTES = 10

# Checkpoint file to track progress
CHECKPOINT_FILE = "video_progress_checkpoint.json"

# --- DIRECTORY SETTINGS ---
DOWNLOAD_DIR_NAME = "scene_videos"
SCENE_DATA_DIR_NAME = "scene_data"
SCENE_IMAGES_DIR_NAME = "scene_images"

# --- ERROR HANDLING ---
# Maximum retries per scene before giving up
MAX_RETRIES_PER_SCENE = 25

# Video generation timeout (seconds)
VIDEO_GENERATION_TIMEOUT = 200

# --- DEBUG SETTINGS ---
# Enable debug screenshots
ENABLE_DEBUG_SCREENSHOTS = True

# Save screenshots to Documents folder
DEBUG_SCREENSHOT_DIR = "Documents"

# --- GMAIL NOTIFICATION SETTINGS ---
# Enable email notifications when script finishes
ENABLE_EMAIL_NOTIFICATIONS = True

# Gmail credentials for sending notifications (usually same as primary account)
NOTIFICATION_EMAIL = "theladyinsaree@gmail.com"
NOTIFICATION_APP_PASSWORD = "ydypyvjkbkatfnuz"  # Generate this in Google Account Security settings

# Email recipient (can be same as sender or different)
NOTIFICATION_RECIPIENT = "chaudharyabhishek031@gmail.com"

# SMTP settings for Gmail
GMAIL_SMTP_SERVER = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587
