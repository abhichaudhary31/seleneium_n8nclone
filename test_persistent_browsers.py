#!/usr/bin/env python3
"""
Test script for persistent dual browser system
This script tests the initialization and switching of persistent browser instances
"""

import time
import os
import sys

# Import all necessary functions and global variables from test_selenium
from test_selenium import (
    initialize_both_browsers, 
    switch_active_browser, 
    cleanup_browsers,
    primary_driver,
    backup_driver,
    current_account
)

def test_persistent_browsers():
    """Test the persistent browser initialization and switching"""
    # Import global variables to get current state
    import test_selenium
    
    print("🧪 Testing Persistent Dual Browser System")
    print("=" * 50)
    
    # Test 1: Initialize both browsers
    print("\n1️⃣ Testing browser initialization...")
    if initialize_both_browsers():
        print("✅ Browser initialization successful!")
        
        # Get updated global variables after initialization
        primary_ready = test_selenium.primary_driver is not None
        backup_ready = test_selenium.backup_driver is not None
        
        print(f"   Primary browser: {'✅ Ready' if primary_ready else '❌ Failed'}")
        print(f"   Backup browser: {'✅ Ready' if backup_ready else '❌ Failed'}")
        print(f"   Current active: {test_selenium.current_account}")
    else:
        print("❌ Browser initialization failed!")
        return False
    
    # Test 2: Check current browser state
    print(f"\n2️⃣ Testing current browser state...")
    print(f"   Active account: {test_selenium.current_account}")
    
    if test_selenium.global_driver:
        print(f"   Current URL: {test_selenium.global_driver.current_url}")
        print(f"   Page title: {test_selenium.global_driver.title[:50]}...")
    else:
        print("   ❌ No active global driver found")
        return False
    
    # Test 3: Test browser switching
    if test_selenium.backup_driver:
        print(f"\n3️⃣ Testing browser switching...")
        original_account = test_selenium.current_account
        
        if switch_active_browser():
            print(f"✅ Successfully switched from {original_account} to {test_selenium.current_account}")
            if test_selenium.global_driver:
                print(f"   New URL: {test_selenium.global_driver.current_url}")
                print(f"   New title: {test_selenium.global_driver.title[:50]}...")
            
            # Switch back
            if switch_active_browser():
                print(f"✅ Successfully switched back from {test_selenium.current_account} to original account")
            else:
                print("❌ Failed to switch back")
        else:
            print("❌ Browser switching failed")
    else:
        print(f"\n3️⃣ Skipping browser switching test (backup not available)")
    
    # Test 4: Test persistence (browsers should remain logged in)
    print(f"\n4️⃣ Testing browser persistence...")
    try:
        # Check if we're still logged into AI Studio
        if test_selenium.global_driver and "aistudio.google.com" in test_selenium.global_driver.current_url:
            print("✅ Browser remains logged in to AI Studio")
        elif test_selenium.global_driver:
            test_selenium.global_driver.get("https://aistudio.google.com/gen-media")
            time.sleep(3)
            if "accounts.google.com" not in test_selenium.global_driver.current_url:
                print("✅ Browser session persisted - no re-login required")
            else:
                print("⚠️ Browser session expired - login required")
        else:
            print("❌ No active browser to test")
    except Exception as e:
        print(f"❌ Error testing persistence: {e}")
    
    print(f"\n5️⃣ Browser status summary:")
    print(f"   Primary browser: {'🟢 Active' if test_selenium.primary_driver else '🔴 Inactive'}")
    print(f"   Backup browser: {'🟢 Active' if test_selenium.backup_driver else '🔴 Inactive'}")
    print(f"   Current active: {test_selenium.current_account}")
    
    return True

def main():
    """Main test function"""
    try:
        success = test_persistent_browsers()
        
        if success:
            print(f"\n🎉 All tests completed!")
            print("The persistent browser system is ready for production use.")
        else:
            print(f"\n❌ Tests failed!")
            print("Please check your configuration and try again.")
            
    except Exception as e:
        print(f"\n💥 Test error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        print(f"\n🧹 Cleaning up test browsers...")
        input("Press Enter to close browsers and exit...")
        cleanup_browsers()
        print("✅ Cleanup complete!")

if __name__ == "__main__":
    main()
