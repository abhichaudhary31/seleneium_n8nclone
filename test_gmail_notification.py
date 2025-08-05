#!/usr/bin/env python3
"""
Test script for Gmail notification functionality.
This script tests the Gmail notification feature without running the full workflow.
"""

import sys
import os
from datetime import datetime

# Add current directory to path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import configuration
try:
    from config import *
    print("✅ Loaded configuration from config.py")
except ImportError:
    try:
        from config_template import *
        print("⚠️ Using template configuration. Please copy config_template.py to config.py and update with your credentials.")
    except ImportError:
        print("❌ No configuration file found.")
        sys.exit(1)

# Import the notification function
from test_selenium import send_gmail_notification

def test_gmail_notification():
    """Test the Gmail notification functionality"""
    print("🧪 Testing Gmail notification functionality...")
    print("=" * 60)
    
    # Check if notifications are enabled
    try:
        enable_notifications = ENABLE_EMAIL_NOTIFICATIONS
    except NameError:
        enable_notifications = False
        
    if not enable_notifications:
        print("📧 Email notifications are disabled in config.")
        print("✏️  To enable notifications, set ENABLE_EMAIL_NOTIFICATIONS = True in config.py")
        return False
    
    # Get notification settings
    try:
        notification_email = NOTIFICATION_EMAIL
        app_password = NOTIFICATION_APP_PASSWORD
        recipient_email = NOTIFICATION_RECIPIENT
    except NameError:
        print("❌ Gmail notification settings not found in config!")
        return False
    
    print(f"📧 Sender email: {notification_email}")
    print(f"📧 Recipient email: {recipient_email}")
    print(f"🔐 App password configured: {'Yes' if app_password and app_password != 'your_gmail_app_password_here' else 'No'}")
    
    if not app_password or app_password == "your_gmail_app_password_here":
        print("\n❌ Gmail App Password not configured!")
        print("ℹ️  To set up Gmail notifications:")
        print("   1. Go to https://myaccount.google.com/security")
        print("   2. Enable 2-Step Verification if not already enabled")
        print("   3. Go to 'App passwords' section")
        print("   4. Generate an app password for 'Mail'")
        print("   5. Update NOTIFICATION_APP_PASSWORD in config.py with the generated password")
        return False
    
    # Test notification
    print("\n📤 Sending test notification...")
    
    # Mock current_account for the test
    import test_selenium
    test_selenium.current_account = "test_account"
    
    success = send_gmail_notification(
        subject="🧪 Test Notification - Story-to-Video Workflow",
        message="This is a test notification to verify Gmail integration is working correctly.",
        successful_scenes=5,
        total_scenes=10,
        duration_minutes=15.5
    )
    
    if success:
        print("✅ Test notification sent successfully!")
        print("📱 Check your email to confirm the notification was received.")
        return True
    else:
        print("❌ Test notification failed!")
        return False

def main():
    """Main test function"""
    print("Gmail Notification Test")
    print("=" * 60)
    print("This script tests the Gmail notification feature.")
    print("Make sure you have configured your Gmail App Password in config.py")
    print("=" * 60)
    
    # Run the test
    success = test_gmail_notification()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Gmail notification test completed successfully!")
        print("The notification feature is ready to use in the main workflow.")
    else:
        print("💥 Gmail notification test failed.")
        print("Please check your configuration and try again.")
    print("=" * 60)

if __name__ == "__main__":
    main()
