#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Launch Microsoft Edge browser with a specific user profile using Playwright.

This script demonstrates how to:
1. Launch Edge with an existing user profile (persistent context)
2. Navigate to a specified URL
3. Maintain authentication and cookies from the profile
4. Run in both headless and headed modes

Prerequisites:
    pip install playwright
    python -m playwright install msedge

Usage:
    # Basic usage with default profile
    python launch_edge_with_profile.py --url "https://www.example.com"
    
    # With custom profile directory
    python launch_edge_with_profile.py --url "https://www.example.com" --profile-dir "/path/to/edge/profile"
    
    # In headed mode (visible browser)
    python launch_edge_with_profile.py --url "https://www.example.com" --headless false
    
    # Keep browser open after navigation
    python launch_edge_with_profile.py --url "https://www.example.com" --keep-open true
"""

import argparse
import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright


async def launch_edge_with_profile(url: str, profile_dir: str, headless: bool = False, keep_open: bool = False):
    """
    Launch Microsoft Edge browser with a user profile and navigate to URL.
    
    Args:
        url: The URL to navigate to
        profile_dir: Path to Edge user data directory (profile)
        headless: Run in headless mode if True
        keep_open: Keep browser open after navigation if True
    """
    print("=" * 70)
    print("🚀 Edge Browser Launcher with Profile Support")
    print("=" * 70)
    print(f"📍 Target URL: {url}")
    print(f"📁 Profile Directory: {profile_dir}")
    print(f"👁️  Headless Mode: {headless}")
    print(f"⏱️  Keep Open: {keep_open}")
    print("-" * 70)
    
    async with async_playwright() as playwright:
        try:
            print("\n🔧 Launching Microsoft Edge with profile...")
            
            # Launch Edge with persistent context (using profile)
            # This preserves cookies, local storage, authentication, etc.
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                channel="msedge",  # Use Microsoft Edge
                headless=headless,
                args=[
                    "--disable-dev-shm-usage",  # Overcome limited resource problems
                    "--no-default-browser-check",  # Skip default browser check
                    "--no-first-run",  # Skip first run wizards
                    "--disable-blink-features=AutomationControlled",  # Hide automation
                ],
                viewport={"width": 1920, "height": 1080},
                ignore_default_args=["--disable-component-extensions-with-background-pages"],
            )
            
            print("✅ Edge browser launched successfully with profile!")
            print(f"📊 Context has {len(context.pages)} page(s)")
            
            # Get the first page or create a new one
            if context.pages:
                page = context.pages[0]
                print("✅ Using existing page from context")
            else:
                page = await context.new_page()
                print("✅ Created new page in context")
            
            # Navigate to the target URL
            print(f"\n🌐 Navigating to: {url}")
            response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            if response:
                status = response.status
                print(f"✅ Page loaded successfully!")
                print(f"   HTTP Status: {status}")
                print(f"   Final URL: {page.url}")
            else:
                print("⚠️  Page loaded but no response object returned")
            
            # Wait for network to be idle
            try:
                print("\n⏳ Waiting for network to be idle...")
                await page.wait_for_load_state("networkidle", timeout=10000)
                print("✅ Network is idle")
            except Exception as e:
                print(f"⚠️  Network idle timeout (this is normal): {e}")
            
            # Get page title and other info
            title = await page.title()
            print(f"\n📄 Page Details:")
            print(f"   Title: {title}")
            print(f"   URL: {page.url}")
            
            # Get cookies to verify profile is working
            cookies = await context.cookies()
            print(f"   Cookies: {len(cookies)} cookie(s) loaded from profile")
            
            if keep_open:
                print("\n⏸️  Browser will remain open. Press Ctrl+C to close...")
                try:
                    # Keep the browser open indefinitely
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    print("\n⚠️  Interrupted by user")
            else:
                print("\n⏱️  Waiting 3 seconds before closing...")
                await asyncio.sleep(3)
            
            print("\n🔧 Closing browser...")
            await context.close()
            print("✅ Browser closed successfully")
            
        except Exception as e:
            print(f"\n❌ Error occurred: {type(e).__name__}")
            print(f"   Message: {str(e)}")
            raise


def get_default_edge_profile_path():
    """
    Get the default Edge profile path based on the operating system.
    
    Returns:
        str: Default Edge user data directory path
    """
    import platform
    
    system = platform.system()
    
    if system == "Windows":
        # Windows: %LOCALAPPDATA%\Microsoft\Edge\User Data
        import os
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        return str(Path(local_appdata) / "Microsoft" / "Edge" / "User Data")
    
    elif system == "Darwin":  # macOS
        # macOS: ~/Library/Application Support/Microsoft Edge
        return str(Path.home() / "Library" / "Application Support" / "Microsoft Edge")
    
    elif system == "Linux":
        # Linux: ~/.config/microsoft-edge
        return str(Path.home() / ".config" / "microsoft-edge")
    
    else:
        return ""


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Launch Microsoft Edge with a user profile using Playwright",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Launch with URL only (uses default profile)
  python launch_edge_with_profile.py --url "https://www.example.com"
  
  # Use custom profile directory
  python launch_edge_with_profile.py --url "https://github.com" --profile-dir "/path/to/profile"
  
  # Run in headed mode (visible browser)
  python launch_edge_with_profile.py --url "https://google.com" --headless false
  
  # Keep browser open for manual interaction
  python launch_edge_with_profile.py --url "https://google.com" --keep-open true --headless false
        """
    )
    
    parser.add_argument(
        "--url",
        required=True,
        help="URL to navigate to after launching Edge"
    )
    
    parser.add_argument(
        "--profile-dir",
        help="Path to Edge user data directory (profile). If not specified, uses system default.",
        default=None
    )
    
    parser.add_argument(
        "--headless",
        type=lambda x: x.lower() == "true",
        default=False,
        help="Run in headless mode (true/false). Default: false"
    )
    
    parser.add_argument(
        "--keep-open",
        type=lambda x: x.lower() == "true",
        default=False,
        help="Keep browser open after navigation (true/false). Default: false"
    )
    
    return parser.parse_args()


def validate_profile_directory(profile_dir: str) -> bool:
    """
    Validate that the profile directory exists and is accessible.
    
    Args:
        profile_dir: Path to the profile directory
        
    Returns:
        bool: True if valid, False otherwise
    """
    path = Path(profile_dir)
    
    if not path.exists():
        print(f"⚠️  Warning: Profile directory does not exist: {profile_dir}")
        print(f"   A new profile will be created at this location.")
        return True  # Playwright will create it
    
    if not path.is_dir():
        print(f"❌ Error: Profile path exists but is not a directory: {profile_dir}")
        return False
    
    print(f"✅ Profile directory exists and is valid")
    return True


async def main():
    """Main entry point for the script."""
    args = parse_arguments()
    
    # Determine profile directory
    profile_dir = args.profile_dir
    if not profile_dir:
        profile_dir = get_default_edge_profile_path()
        print(f"ℹ️  Using default Edge profile path: {profile_dir}")
    
    # Validate profile directory
    if not validate_profile_directory(profile_dir):
        sys.exit(1)
    
    # Launch Edge with profile
    try:
        await launch_edge_with_profile(
            url=args.url,
            profile_dir=profile_dir,
            headless=args.headless,
            keep_open=args.keep_open
        )
        print("\n" + "=" * 70)
        print("✅ Script completed successfully!")
        print("=" * 70)
        
    except KeyboardInterrupt:
        print("\n⚠️  Script interrupted by user")
        sys.exit(0)
        
    except Exception as e:
        print("\n" + "=" * 70)
        print("❌ Script failed!")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
