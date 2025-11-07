# Edge Browser Automation - Quick Reference

## 🚀 Installation (One-Time Setup)

### Option 1: Automated Setup
```bash
# Linux/macOS
./setup_edge_automation.sh

# Windows
setup_edge_automation.bat
```

### Option 2: Manual Setup
```bash
# Install dependencies
pip install playwright pandas openpyxl matplotlib

# Install Edge browser
python -m playwright install msedge

# Verify installation
python test_edge_setup.py
```

## 📖 Common Commands

### Launch Edge with Profile
```bash
# Basic - uses default profile
python launch_edge_with_profile.py --url "https://example.com"

# Custom profile
python launch_edge_with_profile.py --url "https://github.com" --profile-dir "/path/to/profile"

# Visible browser (not headless)
python launch_edge_with_profile.py --url "https://google.com" --headless false

# Keep browser open
python launch_edge_with_profile.py --url "https://google.com" --keep-open true --headless false
```

### Run Examples
```bash
python edge_profile_example.py
# Select: 1=Simple, 2=Advanced, 3=Auth, 4=Tabs, 5=All
```

### Verify Setup
```bash
python test_edge_setup.py
```

## 💻 Code Snippets

### Basic Launch
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
        await page.goto("https://example.com")
        await asyncio.sleep(3)
        await context.close()

asyncio.run(main())
```

### With Authentication
```python
# Profile preserves cookies and login state
context = await p.chromium.launch_persistent_context(
    user_data_dir="./auth_profile",
    channel="msedge",
    headless=False,
)
page = context.pages[0] if context.pages else await context.new_page()
await page.goto("https://protected-site.com")  # Already logged in!
```

### Take Screenshot
```python
await page.goto("https://example.com")
await page.screenshot(path="screenshot.png", full_page=True)
```

### Multiple Pages
```python
page1 = context.pages[0] if context.pages else await context.new_page()
page2 = await context.new_page()
await page1.goto("https://example.com")
await page2.goto("https://github.com")
```

### Get Cookies
```python
cookies = await context.cookies()
print(f"Found {len(cookies)} cookies")
```

### Wait for Element
```python
await page.wait_for_selector(".my-element", state="visible")
element = await page.query_selector(".my-element")
text = await element.text_content()
```

## 🔧 Configuration Options

### Command-Line Arguments
| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--url` | string | required | URL to navigate to |
| `--profile-dir` | string | system default | Path to Edge profile |
| `--headless` | bool | false | Run without UI |
| `--keep-open` | bool | false | Keep browser open |

### Browser Arguments
```python
args=[
    "--start-maximized",              # Maximize window
    "--no-first-run",                 # Skip first run wizard
    "--disable-blink-features=AutomationControlled",  # Hide automation
    "--window-size=1920,1080",        # Set window size
]
```

### Viewport Settings
```python
viewport={"width": 1920, "height": 1080}
```

## 📁 Default Profile Locations

### Windows
```
%LOCALAPPDATA%\Microsoft\Edge\User Data
C:\Users\YourName\AppData\Local\Microsoft\Edge\User Data
```

### macOS
```
~/Library/Application Support/Microsoft Edge
```

### Linux
```
~/.config/microsoft-edge
```

## 🐛 Quick Troubleshooting

### Profile in Use Error
```bash
# Close all Edge windows or use different profile
python launch_edge_with_profile.py --url "URL" --profile-dir "./my_automation_profile"
```

### Element Not Found
```python
# Wait for element
await page.wait_for_selector(".element", timeout=10000)
await page.wait_for_load_state("networkidle")
```

### Browser Not Installed
```bash
# Install Edge browser for Playwright
python -m playwright install msedge
```

### Import Error
```bash
# Install Playwright
pip install playwright
```

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| `EDGE_AUTOMATION_README.md` | Main user guide |
| `EDGE_PROFILE_GUIDE.md` | Detailed technical guide |
| `EDGE_AUTOMATION_SUMMARY.md` | Implementation overview |
| `QUICK_REFERENCE.md` | This file - quick lookup |

## 🎯 Common Use Cases

### 1. Navigate to Site
```bash
python launch_edge_with_profile.py --url "https://example.com"
```

### 2. Login and Save Session
```bash
# First run - login manually
python launch_edge_with_profile.py --url "https://site.com/login" --keep-open true --headless false
# Subsequent runs - already logged in
python launch_edge_with_profile.py --url "https://site.com/dashboard"
```

### 3. Take Screenshot
```python
async with async_playwright() as p:
    context = await p.chromium.launch_persistent_context(
        user_data_dir="./profile", channel="msedge", headless=True
    )
    page = context.pages[0] if context.pages else await context.new_page()
    await page.goto("https://example.com")
    await page.screenshot(path="output.png", full_page=True)
    await context.close()
```

### 4. Scrape Authenticated Content
```python
# Uses profile to maintain login state
context = await p.chromium.launch_persistent_context(
    user_data_dir="./scraper_profile",
    channel="msedge",
    headless=True,
)
page = context.pages[0] if context.pages else await context.new_page()
await page.goto("https://protected-content.com")
content = await page.content()
```

### 5. Multiple Accounts
```python
# Work account
work_ctx = await p.chromium.launch_persistent_context(
    user_data_dir="./work_profile", channel="msedge"
)

# Personal account
personal_ctx = await p.chromium.launch_persistent_context(
    user_data_dir="./personal_profile", channel="msedge"
)
```

## ⚡ Tips & Best Practices

1. **Start with headed mode** - See what's happening
2. **Use separate profiles** - Don't use your main browser profile
3. **Wait appropriately** - Use `wait_for_selector` instead of sleep
4. **Handle errors** - Use try-except blocks
5. **Close resources** - Always close contexts and pages
6. **Secure profiles** - Don't commit profile directories to git
7. **Test incrementally** - Build up complexity gradually

## 🔗 Quick Links

- **Playwright Docs**: https://playwright.dev/python/
- **Selectors Guide**: https://playwright.dev/python/docs/selectors
- **API Reference**: https://playwright.dev/python/docs/api/class-playwright

## 📞 Getting Help

1. Run `python test_edge_setup.py` to diagnose issues
2. Check `EDGE_AUTOMATION_README.md` for detailed help
3. Review `EDGE_PROFILE_GUIDE.md` for advanced topics
4. Try examples in `edge_profile_example.py`

---

**Quick Start:** Run `./setup_edge_automation.sh` (or `.bat` on Windows), then `python launch_edge_with_profile.py --url "https://example.com"`
