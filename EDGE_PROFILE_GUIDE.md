# Edge Browser Automation with Profile Support

Complete guide for launching Microsoft Edge with user profiles using Python and Playwright.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Understanding Profiles](#understanding-profiles)
- [Usage Examples](#usage-examples)
- [Advanced Topics](#advanced-topics)
- [Troubleshooting](#troubleshooting)

## Overview

This guide demonstrates how to launch Microsoft Edge browser with a specific user profile using Playwright. Using profiles allows you to:

- **Maintain authentication sessions**: Stay logged in to websites
- **Preserve cookies and local storage**: Keep your preferences and settings
- **Use browser extensions**: If installed in the profile
- **Separate contexts**: Use different profiles for different purposes

## Prerequisites

- Python 3.8 or higher
- Microsoft Edge browser installed on your system
- Basic knowledge of Python async/await

## Installation

### Step 1: Install Playwright

```bash
pip install playwright
```

### Step 2: Install Playwright Browsers

```bash
# Install Microsoft Edge for Playwright
python -m playwright install msedge

# Or install all browsers
python -m playwright install
```

### Step 3: Verify Installation

```bash
python -m playwright --version
```

## Quick Start

### Basic Example

```python
import asyncio
from playwright.async_api import async_playwright

async def launch_edge():
    async with async_playwright() as p:
        # Launch Edge with a profile
        context = await p.chromium.launch_persistent_context(
            user_data_dir="./my_edge_profile",  # Profile directory
            channel="msedge",  # Use Microsoft Edge
            headless=False,  # Set to True for headless mode
        )
        
        # Get or create a page
        page = context.pages[0] if context.pages else await context.new_page()
        
        # Navigate to a website
        await page.goto("https://www.example.com")
        print(f"Page title: {await page.title()}")
        
        await asyncio.sleep(3)
        await context.close()

# Run the example
asyncio.run(launch_edge())
```

### Using the Command-Line Script

```bash
# Basic usage
python launch_edge_with_profile.py --url "https://www.example.com"

# With custom profile directory
python launch_edge_with_profile.py --url "https://github.com" --profile-dir "/path/to/profile"

# In headed mode (visible browser)
python launch_edge_with_profile.py --url "https://google.com" --headless false

# Keep browser open for manual interaction
python launch_edge_with_profile.py --url "https://google.com" --keep-open true --headless false
```

## Understanding Profiles

### What is a Browser Profile?

A browser profile (also called user data directory) contains:

- **Cookies**: Authentication tokens and session data
- **Local Storage**: Website data and preferences
- **Cache**: Cached files and resources
- **Extensions**: Installed browser extensions
- **Bookmarks**: Saved bookmarks
- **History**: Browsing history
- **Passwords**: Saved passwords (encrypted)

### Default Profile Locations

#### Windows
```
%LOCALAPPDATA%\Microsoft\Edge\User Data
```
Example: `C:\Users\YourName\AppData\Local\Microsoft\Edge\User Data`

#### macOS
```
~/Library/Application Support/Microsoft Edge
```

#### Linux
```
~/.config/microsoft-edge
```

### Profile Directory Structure

```
Profile Directory/
├── Default/              # Default profile
├── Profile 1/            # Additional profiles
├── Profile 2/
├── Local State           # Browser-wide settings
└── ...
```

### Important Notes

⚠️ **Profile Locking**: Only one browser instance can use a profile at a time. If Edge is already running with a profile, you cannot launch another instance with the same profile.

💡 **Tip**: Create a separate profile for automation to avoid conflicts with your regular browsing.

## Usage Examples

### Example 1: Launch with Default System Profile

```python
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
import platform

def get_edge_profile_path():
    """Get default Edge profile path based on OS."""
    system = platform.system()
    if system == "Windows":
        import os
        return str(Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "Edge" / "User Data")
    elif system == "Darwin":  # macOS
        return str(Path.home() / "Library" / "Application Support" / "Microsoft Edge")
    elif system == "Linux":
        return str(Path.home() / ".config" / "microsoft-edge")
    return ""

async def use_system_profile():
    profile_path = get_edge_profile_path()
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=profile_path,
            channel="msedge",
            headless=False,
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://www.example.com")
        await asyncio.sleep(3)
        await context.close()

asyncio.run(use_system_profile())
```

### Example 2: Create a New Profile for Automation

```python
import asyncio
from playwright.async_api import async_playwright

async def create_automation_profile():
    async with async_playwright() as p:
        # This creates a new profile if it doesn't exist
        context = await p.chromium.launch_persistent_context(
            user_data_dir="./automation_profile",
            channel="msedge",
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",  # Hide automation
                "--no-first-run",  # Skip first run wizard
            ],
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        
        # First time: You might need to log in manually
        await page.goto("https://github.com/login")
        
        # Wait for manual login (increase timeout as needed)
        print("Please log in manually...")
        await asyncio.sleep(60)  # Wait 60 seconds for login
        
        # After login, cookies are saved in the profile
        cookies = await context.cookies()
        print(f"Saved {len(cookies)} cookies to profile")
        
        await context.close()
        print("Profile created and authentication saved!")

asyncio.run(create_automation_profile())
```

### Example 3: Run with Authentication Preserved

```python
import asyncio
from playwright.async_api import async_playwright

async def use_authenticated_profile():
    async with async_playwright() as p:
        # Use the profile created in Example 2
        context = await p.chromium.launch_persistent_context(
            user_data_dir="./automation_profile",
            channel="msedge",
            headless=False,
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        
        # Navigate to protected page - should be already logged in!
        await page.goto("https://github.com")
        
        # Check if logged in
        is_logged_in = await page.is_visible("img[alt*='@']", timeout=5000) \
                       if await page.query_selector("img[alt*='@']") else False
        
        if is_logged_in:
            print("✅ Successfully logged in using profile!")
        else:
            print("❌ Not logged in - profile may not have auth cookies")
        
        await asyncio.sleep(3)
        await context.close()

asyncio.run(use_authenticated_profile())
```

### Example 4: Multiple Profiles for Different Accounts

```python
import asyncio
from playwright.async_api import async_playwright

async def use_multiple_profiles():
    """
    Use different profiles for different accounts/purposes.
    """
    profiles = {
        "work": "./edge_profile_work",
        "personal": "./edge_profile_personal",
        "testing": "./edge_profile_testing",
    }
    
    # Example: Use work profile
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=profiles["work"],
            channel="msedge",
            headless=False,
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://work-site.com")
        
        print(f"Using work profile with {len(await context.cookies())} cookies")
        
        await asyncio.sleep(3)
        await context.close()

asyncio.run(use_multiple_profiles())
```

### Example 5: Headless Mode with Profile

```python
import asyncio
from playwright.async_api import async_playwright

async def headless_with_profile():
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir="./edge_profile_headless",
            channel="msedge",
            headless=True,  # Run without UI
            args=["--disable-gpu"],  # Recommended for headless
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://www.example.com")
        
        # Take screenshot
        await page.screenshot(path="screenshot.png")
        print(f"Title: {await page.title()}")
        print("Screenshot saved: screenshot.png")
        
        await context.close()

asyncio.run(headless_with_profile())
```

## Advanced Topics

### Custom Browser Arguments

```python
context = await p.chromium.launch_persistent_context(
    user_data_dir="./profile",
    channel="msedge",
    args=[
        "--start-maximized",                          # Start maximized
        "--disable-blink-features=AutomationControlled",  # Hide automation
        "--no-first-run",                              # Skip first run
        "--no-default-browser-check",                  # Skip default browser check
        "--disable-dev-shm-usage",                     # Overcome limited resources
        "--disable-gpu",                               # Disable GPU (for headless)
        "--window-size=1920,1080",                     # Set window size
    ],
)
```

### Viewport Configuration

```python
context = await p.chromium.launch_persistent_context(
    user_data_dir="./profile",
    channel="msedge",
    viewport={"width": 1920, "height": 1080},  # Set viewport size
    device_scale_factor=2,  # For high-DPI displays
)
```

### Handling Cookies Programmatically

```python
# Get all cookies
cookies = await context.cookies()

# Get cookies for specific domain
github_cookies = await context.cookies(["https://github.com"])

# Add cookies
await context.add_cookies([
    {
        "name": "session_token",
        "value": "abc123",
        "domain": ".example.com",
        "path": "/",
        "expires": -1,  # Session cookie
        "httpOnly": True,
        "secure": True,
        "sameSite": "Lax",
    }
])

# Clear cookies
await context.clear_cookies()
```

### Network Interception

```python
async def intercept_requests():
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir="./profile",
            channel="msedge",
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        
        # Intercept and modify requests
        async def handle_route(route):
            # Modify request headers
            headers = {
                **route.request.headers,
                "Custom-Header": "Custom Value"
            }
            await route.continue_(headers=headers)
        
        await page.route("**/*", handle_route)
        
        await page.goto("https://www.example.com")
        await asyncio.sleep(3)
        await context.close()
```

### Taking Screenshots and PDFs

```python
# Full page screenshot
await page.screenshot(path="full_page.png", full_page=True)

# Viewport screenshot
await page.screenshot(path="viewport.png")

# PDF export (only in headless mode)
await page.pdf(path="page.pdf", format="A4")

# Screenshot of specific element
element = await page.query_selector(".specific-class")
await element.screenshot(path="element.png")
```

## Troubleshooting

### Issue: "Profile is already in use"

**Problem**: Another Edge instance is using the profile.

**Solution**:
1. Close all Edge browser windows
2. Use a different profile directory for automation
3. Check Task Manager for Edge processes and kill them

### Issue: "No element found" errors

**Problem**: Elements not loading in time.

**Solution**:
```python
# Wait for element to be visible
await page.wait_for_selector(".my-element", state="visible", timeout=10000)

# Wait for network to be idle
await page.wait_for_load_state("networkidle")

# Add explicit wait
await asyncio.sleep(2)
```

### Issue: "Browser closed unexpectedly"

**Problem**: Browser crashes or closes.

**Solution**:
```python
# Add more stable arguments
args=[
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--no-sandbox",  # Only if needed (security risk)
]
```

### Issue: Headless mode behaves differently

**Problem**: Some websites detect headless mode.

**Solution**:
```python
context = await p.chromium.launch_persistent_context(
    user_data_dir="./profile",
    channel="msedge",
    headless=False,  # Use headed mode
    args=[
        "--disable-blink-features=AutomationControlled",
        "--window-position=-2400,-2400",  # Move off-screen
    ],
)
```

### Issue: Authentication not persisting

**Problem**: Login state not saved between runs.

**Solution**:
1. Ensure you're using `launch_persistent_context` (not regular `launch`)
2. Use the same `user_data_dir` path
3. Wait for login to complete before closing browser
4. Check if cookies have `sameSite` or `secure` restrictions

### Debug Mode

Enable debug logging:

```bash
# Set environment variable
export DEBUG=pw:api

# Or in Python
import os
os.environ["DEBUG"] = "pw:api"
```

## Best Practices

1. **Use Separate Profiles**: Create dedicated profiles for automation
2. **Handle Errors**: Use try-except blocks for robust error handling
3. **Wait Appropriately**: Use proper wait strategies instead of fixed sleeps
4. **Clean Up**: Always close contexts and browsers
5. **Security**: Don't commit profile directories or cookies to git
6. **Testing**: Test in headed mode first, then switch to headless

## Additional Resources

- [Playwright Documentation](https://playwright.dev/python/)
- [Playwright API Reference](https://playwright.dev/python/docs/api/class-playwright)
- [Browser Contexts](https://playwright.dev/python/docs/browser-contexts)

## License

This guide is provided as-is for educational and automation purposes.
