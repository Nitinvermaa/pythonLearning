# Edge Browser Automation with Profile Support

Complete Python solution for launching Microsoft Edge browser with user profiles using Playwright.

## 🎯 What This Does

This project provides ready-to-use scripts and examples for automating Microsoft Edge browser with full profile support, allowing you to:

- ✅ Launch Edge with any user profile
- ✅ Maintain authentication sessions across runs
- ✅ Preserve cookies, local storage, and browser settings
- ✅ Run in headed or headless mode
- ✅ Perform complex browser automation tasks
- ✅ Use multiple profiles for different purposes

## 📁 Project Structure

```
.
├── launch_edge_with_profile.py   # Main CLI script for launching Edge
├── edge_profile_example.py       # Interactive examples with different use cases
├── test_edge_setup.py            # Setup verification script
├── EDGE_PROFILE_GUIDE.md         # Comprehensive usage guide
└── requirements.txt              # Python dependencies
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt

# Install Playwright browsers
python -m playwright install msedge
```

### 2. Verify Setup

```bash
# Run the verification script
python test_edge_setup.py
```

This will check if everything is installed correctly and run basic tests.

### 3. Launch Edge with Profile

```bash
# Basic usage - launches Edge with a profile and navigates to URL
python launch_edge_with_profile.py --url "https://www.example.com"

# Use custom profile directory
python launch_edge_with_profile.py --url "https://github.com" --profile-dir "/path/to/profile"

# Keep browser open for manual interaction
python launch_edge_with_profile.py --url "https://google.com" --keep-open true --headless false
```

### 4. Try Examples

```bash
# Run interactive examples
python edge_profile_example.py
```

This will show a menu with different automation scenarios:
1. Simple Edge automation
2. Advanced Edge automation with screenshots
3. Edge with authentication (profile usage)
4. Multiple pages (tabs) example

## 📖 Usage Examples

### Example 1: Simple Launch

```python
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir="./my_profile",
            channel="msedge",
            headless=False,
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://www.example.com")
        await asyncio.sleep(3)
        await context.close()

asyncio.run(main())
```

### Example 2: With Authentication

```python
import asyncio
from playwright.async_api import async_playwright

async def authenticated_session():
    async with async_playwright() as p:
        # Use persistent profile - authentication persists between runs
        context = await p.chromium.launch_persistent_context(
            user_data_dir="./auth_profile",
            channel="msedge",
            headless=False,
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        
        # First run: Log in manually (if needed)
        await page.goto("https://github.com/login")
        print("Log in if needed... waiting 30 seconds")
        await asyncio.sleep(30)
        
        # Subsequent runs: Already logged in!
        await page.goto("https://github.com")
        
        cookies = await context.cookies()
        print(f"Profile has {len(cookies)} cookies")
        
        await context.close()

asyncio.run(authenticated_session())
```

### Example 3: Multiple Profiles

```python
async def use_work_profile():
    async with async_playwright() as p:
        # Work profile
        context = await p.chromium.launch_persistent_context(
            user_data_dir="./work_profile",
            channel="msedge",
            headless=False,
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://work-site.com")
        await context.close()

async def use_personal_profile():
    async with async_playwright() as p:
        # Personal profile
        context = await p.chromium.launch_persistent_context(
            user_data_dir="./personal_profile",
            channel="msedge",
            headless=False,
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://personal-site.com")
        await context.close()
```

## 🔧 Command-Line Options

The `launch_edge_with_profile.py` script supports the following options:

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `--url` | URL to navigate to (required) | - | `--url "https://example.com"` |
| `--profile-dir` | Path to Edge profile directory | System default | `--profile-dir "/path/to/profile"` |
| `--headless` | Run in headless mode | `false` | `--headless true` |
| `--keep-open` | Keep browser open after navigation | `false` | `--keep-open true` |

### Examples

```bash
# Navigate to GitHub
python launch_edge_with_profile.py --url "https://github.com"

# Use custom profile
python launch_edge_with_profile.py \
  --url "https://example.com" \
  --profile-dir "/Users/me/edge_profiles/automation"

# Run in headless mode
python launch_edge_with_profile.py \
  --url "https://example.com" \
  --headless true

# Keep browser open for manual interaction
python launch_edge_with_profile.py \
  --url "https://google.com" \
  --keep-open true \
  --headless false
```

## 🎓 Learning Resources

### Documentation Files

1. **EDGE_PROFILE_GUIDE.md** - Comprehensive guide covering:
   - Profile basics and locations
   - Advanced usage patterns
   - Troubleshooting
   - Best practices

2. **edge_profile_example.py** - Interactive examples:
   - Simple automation
   - Advanced features
   - Authentication handling
   - Multiple pages/tabs

### Key Concepts

#### What is a Browser Profile?

A profile (user data directory) contains:
- Cookies and authentication tokens
- Local storage and session data
- Browser extensions
- Bookmarks and history
- Saved passwords (encrypted)

#### Why Use Profiles?

- **Persistent Authentication**: Stay logged in between runs
- **Separate Contexts**: Different profiles for different purposes
- **Real Browser Behavior**: More reliable than cookie injection

#### Profile Locations

**Windows:**
```
%LOCALAPPDATA%\Microsoft\Edge\User Data
```

**macOS:**
```
~/Library/Application Support/Microsoft Edge
```

**Linux:**
```
~/.config/microsoft-edge
```

## 🛠️ Advanced Features

### Custom Browser Arguments

```python
context = await p.chromium.launch_persistent_context(
    user_data_dir="./profile",
    channel="msedge",
    args=[
        "--start-maximized",
        "--disable-blink-features=AutomationControlled",
        "--no-first-run",
        "--window-size=1920,1080",
    ],
)
```

### Taking Screenshots

```python
# Full page screenshot
await page.screenshot(path="screenshot.png", full_page=True)

# Specific element
element = await page.query_selector(".my-class")
await element.screenshot(path="element.png")
```

### Working with Cookies

```python
# Get cookies
cookies = await context.cookies()

# Add cookie
await context.add_cookies([{
    "name": "session",
    "value": "abc123",
    "domain": ".example.com",
    "path": "/",
}])

# Clear cookies
await context.clear_cookies()
```

### Multiple Pages (Tabs)

```python
# Create new page
page2 = await context.new_page()
await page2.goto("https://example.com")

# Switch between pages
await page1.bring_to_front()
await page2.bring_to_front()
```

## 🐛 Troubleshooting

### Profile Already in Use

**Problem:** Error about profile being locked.

**Solution:**
- Close all Edge browser instances
- Use a different profile directory for automation
- Check Task Manager for Edge processes

### Elements Not Found

**Problem:** Selectors not working.

**Solution:**
```python
# Wait for element
await page.wait_for_selector(".my-element", state="visible")

# Wait for network
await page.wait_for_load_state("networkidle")
```

### Authentication Not Persisting

**Problem:** Login state not saved.

**Solution:**
- Use `launch_persistent_context` (not regular `launch`)
- Use the same `user_data_dir` path every time
- Wait for login to complete before closing

### Headless Detection

**Problem:** Website detects automation.

**Solution:**
```python
args=[
    "--disable-blink-features=AutomationControlled",
    "--user-agent=Mozilla/5.0...",  # Custom user agent
]
```

## 📊 Comparison: Regular Launch vs Profile Launch

| Feature | Regular Launch | Profile Launch |
|---------|---------------|----------------|
| Authentication | Manual every time | Persists |
| Cookies | Lost on close | Preserved |
| Extensions | Not available | Available |
| Settings | Default | User's settings |
| Best for | Testing, scraping | Automation with auth |

## 🔒 Security Considerations

⚠️ **Important Security Notes:**

1. **Don't Share Profiles**: Profiles contain sensitive authentication data
2. **Use Separate Profiles**: Don't use your main browser profile for automation
3. **Secure Storage**: Keep profile directories secure and don't commit to git
4. **Review Extensions**: Disable unnecessary extensions in automation profiles

### .gitignore Recommendations

Add these to your `.gitignore`:

```gitignore
# Edge profiles
*_profile/
edge_profile*/
automation_profile/

# Test artifacts
test_screenshot.png
*.png
*.pdf
```

## 🤝 Contributing

Suggestions and improvements are welcome! Common areas:

- Additional examples
- Error handling patterns
- Performance optimizations
- Cross-platform compatibility

## 📝 License

This project is provided as-is for educational and automation purposes.

## 🆘 Getting Help

1. Check **EDGE_PROFILE_GUIDE.md** for detailed documentation
2. Run **test_edge_setup.py** to verify your setup
3. Try **edge_profile_example.py** for working examples
4. Review [Playwright Documentation](https://playwright.dev/python/)

## ✅ Checklist for Getting Started

- [ ] Install Python 3.8+
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Install Edge browser: `python -m playwright install msedge`
- [ ] Run verification: `python test_edge_setup.py`
- [ ] Try examples: `python edge_profile_example.py`
- [ ] Read guide: `EDGE_PROFILE_GUIDE.md`
- [ ] Launch your first automation: `python launch_edge_with_profile.py --url "https://example.com"`

## 🎉 You're Ready!

Once setup is complete, you have a powerful Edge automation framework at your fingertips. Start with simple examples and gradually explore more advanced features.

Happy automating! 🚀
