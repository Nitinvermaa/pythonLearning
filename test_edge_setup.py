#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script to verify Edge browser automation setup.

This script checks if:
1. Playwright is installed correctly
2. Microsoft Edge is available
3. Profile launching works
4. Basic navigation works

Run this script after installation to verify everything is set up correctly.
"""

import sys
import asyncio
from pathlib import Path


def check_playwright_installed():
    """Check if playwright package is installed."""
    try:
        import playwright
        version = playwright.__version__
        print(f"✅ Playwright is installed (version {version})")
        return True
    except ImportError:
        print("❌ Playwright is not installed")
        print("   Install it with: pip install playwright")
        return False


def check_playwright_browsers():
    """Check if playwright browsers are installed."""
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            # Try to get browser version
            try:
                browser = p.chromium.launch(channel="msedge", headless=True)
                version = browser.version
                browser.close()
                print(f"✅ Microsoft Edge is installed (version {version})")
                return True
            except Exception as e:
                print(f"❌ Microsoft Edge is not available for Playwright")
                print(f"   Error: {str(e)}")
                print("   Install it with: python -m playwright install msedge")
                return False
    except Exception as e:
        print(f"❌ Error checking browsers: {str(e)}")
        return False


async def test_basic_launch():
    """Test basic Edge launch."""
    print("\n🧪 Testing basic Edge launch...")
    
    try:
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            # Launch Edge in headless mode
            browser = await p.chromium.launch(channel="msedge", headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            await page.goto("https://www.example.com")
            title = await page.title()
            
            await browser.close()
            
            print(f"✅ Basic launch successful!")
            print(f"   Page title: {title}")
            return True
            
    except Exception as e:
        print(f"❌ Basic launch failed: {str(e)}")
        return False


async def test_profile_launch():
    """Test Edge launch with profile."""
    print("\n🧪 Testing Edge launch with profile...")
    
    try:
        from playwright.async_api import async_playwright
        
        # Use a test profile
        test_profile = Path("./test_edge_profile")
        
        async with async_playwright() as p:
            # Launch Edge with persistent context
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(test_profile),
                channel="msedge",
                headless=True,
            )
            
            page = context.pages[0] if context.pages else await context.new_page()
            
            await page.goto("https://www.example.com", timeout=30000)
            title = await page.title()
            
            # Check cookies
            cookies = await context.cookies()
            
            await context.close()
            
            print(f"✅ Profile launch successful!")
            print(f"   Page title: {title}")
            print(f"   Profile location: {test_profile.absolute()}")
            print(f"   Cookies: {len(cookies)}")
            
            # Clean up test profile
            try:
                import shutil
                if test_profile.exists():
                    shutil.rmtree(test_profile)
                    print(f"   Cleaned up test profile")
            except Exception:
                pass
            
            return True
            
    except Exception as e:
        print(f"❌ Profile launch failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_navigation_and_interaction():
    """Test navigation and basic interactions."""
    print("\n🧪 Testing navigation and interaction...")
    
    try:
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(channel="msedge", headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Navigate
            await page.goto("https://www.example.com")
            
            # Check if h1 exists
            h1 = await page.query_selector("h1")
            if h1:
                h1_text = await h1.text_content()
                print(f"✅ Found H1: {h1_text}")
            
            # Get page URL
            url = page.url
            print(f"✅ Current URL: {url}")
            
            # Take screenshot
            screenshot_path = Path("test_screenshot.png")
            await page.screenshot(path=str(screenshot_path))
            print(f"✅ Screenshot saved: {screenshot_path.absolute()}")
            
            await browser.close()
            
            # Clean up screenshot
            try:
                screenshot_path.unlink()
                print(f"   Cleaned up screenshot")
            except Exception:
                pass
            
            return True
            
    except Exception as e:
        print(f"❌ Navigation test failed: {str(e)}")
        return False


def print_system_info():
    """Print system information."""
    import platform
    
    print("\n📋 System Information:")
    print(f"   OS: {platform.system()} {platform.release()}")
    print(f"   Python: {sys.version.split()[0]}")
    print(f"   Architecture: {platform.machine()}")


async def main():
    """Main test runner."""
    print("=" * 70)
    print("Edge Browser Automation Setup Verification")
    print("=" * 70)
    
    print_system_info()
    
    print("\n" + "=" * 70)
    print("Running Tests")
    print("=" * 70)
    
    results = []
    
    # Test 1: Playwright installed
    print("\n📦 Checking Playwright installation...")
    results.append(("Playwright Installation", check_playwright_installed()))
    
    if not results[-1][1]:
        print("\n❌ Cannot continue without Playwright. Please install it first.")
        print("\nInstallation steps:")
        print("1. pip install playwright")
        print("2. python -m playwright install msedge")
        return
    
    # Test 2: Edge browser installed
    print("\n🌐 Checking Microsoft Edge...")
    results.append(("Edge Browser", check_playwright_browsers()))
    
    if not results[-1][1]:
        print("\n❌ Cannot continue without Edge browser. Please install it.")
        return
    
    # Test 3: Basic launch
    results.append(("Basic Launch", await test_basic_launch()))
    
    # Test 4: Profile launch
    results.append(("Profile Launch", await test_profile_launch()))
    
    # Test 5: Navigation
    results.append(("Navigation & Interaction", await test_navigation_and_interaction()))
    
    # Print summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ All tests passed! Your setup is ready.")
        print("\nYou can now use:")
        print("  - launch_edge_with_profile.py")
        print("  - edge_profile_example.py")
        print("\nSee EDGE_PROFILE_GUIDE.md for detailed documentation.")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        print("\nTroubleshooting:")
        print("1. Ensure Playwright is installed: pip install playwright")
        print("2. Install Edge browser: python -m playwright install msedge")
        print("3. Check EDGE_PROFILE_GUIDE.md for more help")
    print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
