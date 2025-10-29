# Quick Start Guide - SSO Crawler

## Run the Crawler

```bash
cd web_crawler
python sso_crawler.py --start-url "https://tjmaxx.tjx.com/store/index.jsp" --user-data-dir "C:\Users\nitin.verma\PythonProjects\pythonLearning\Profile_new" --headless false
```

## What You'll See

### Startup:
```
🚀 Starting crawl of: https://tjmaxx.tjx.com/store/index.jsp
📁 User data dir: C:\Users\nitin.verma\PythonProjects\pythonLearning\Profile_new
👁️  Headless mode: False
📊 Max pages: 100
------------------------------------------------------------
```

### Progress:
```
[1/100] Crawling: https://tjmaxx.tjx.com/store/index.jsp
  ✓ Found 50 unique links, 0 broken

[2/100] Crawling: https://tjmaxx.tjx.com/store/page2
  ✓ Found 45 unique links, 1 broken
```

### Success:
```
✓ Crawl completed successfully!
✓ Results saved to: C:\Users\nitin.verma\PythonProjects\pythonLearning\web_crawler\crawl_results.xlsx
✓ Report saved to: C:\Users\nitin.verma\PythonProjects\pythonLearning\web_crawler\crawl_report.html
```

### Error (if something goes wrong):
```
✗ Error occurred: TimeoutError
  Message: Timeout 60000ms exceeded

Full traceback:
[detailed error info]
```

## Outputs

- **crawl_results.xlsx** → Opens in Excel
- **crawl_report.html** → Opens in browser

Both are in the `web_crawler/` folder.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Script exits immediately | Check error message - likely Playwright not installed or Chrome using the profile |
| "ModuleNotFoundError" | Run `pip install playwright pandas openpyxl matplotlib` |
| "Playwright not installed" | Run `python -m playwright install chrome` |
| Chrome profile locked | Close all Chrome windows and try again |

## Review the Fixed Code

See `CODE_REVIEW_SUMMARY.md` for detailed explanation of all fixes.

