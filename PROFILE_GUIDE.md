# Chrome Profile Guide for Crawler

## Your Current Profile Structure

```
Profile_new/
  ├── Default/          ← The actual Chrome profile
  ├── Bookmarks
  ├── Cookies
  ├── History
  └── ... (other Chrome data)
```

This is a **backed-up Chrome profile** where `Profile_new` acts as the User Data directory, and `Default` is the profile folder inside it.

## Profile Types You Might Have

1. **Regular Chrome Profile** (in normal Chrome location):
   ```
   C:\Users\YourName\AppData\Local\Google\Chrome\User Data\Default
   ```

2. **Your Custom Profile** (what you're using):
   ```
   C:\Users\nitin.verma\PythonProjects\pythonLearning\Profile_new\Default
   ```

3. **Multiple Profiles** (if Chrome has multiple profiles):
   ```
   Chrome\User Data\
     ├── Default
     ├── Profile 1
     └── Profile 2
   ```

## Important Notes

### ✅ DO:
- **Close Chrome completely** before running the crawler
- Use the path that contains the `Default` folder as your `--user-data-dir`
- Let the crawler finish before opening Chrome manually

### ❌ DON'T:
- Open Chrome while the crawler is running
- Copy or move profile files while they're in use
- Run multiple crawler instances with the same profile

## If You Have Duplicate Profiles

If you have both a regular Chrome profile and your `Profile_new`:

1. **To use your regular Chrome profile:**
   ```bash
   python sso_crawler.py --user-data-dir "C:\Users\nitin.verma\AppData\Local\Google\Chrome\User Data" ...
   ```

2. **To use your backed-up profile (Profile_new):**
   ```bash
   python sso_crawler.py --user-data-dir "C:\Users\nitin.verma\PythonProjects\pythonLearning\Profile_new" ...
   ```

## Checking Which Profile Has Your SSO Auth

To see which profile has your authentication cookies:

1. Close all Chrome windows
2. Open Chrome normally and check if you're still logged in
3. That's your active profile

## Current Command (Using Profile_new)

```bash
python sso_crawler.py --start-url "https://www.t-mobile.com/" --user-data-dir "C:\Users\nitin.verma\PythonProjects\pythonLearning\Profile_new" --headless false
```

This loads the `Default` profile inside `Profile_new` directory.

## If Profile Seems Incorrect

If the crawler doesn't have the right authentication:

1. Make sure Chrome is completely closed
2. Open Chrome manually and verify you're logged in to the site
3. Note which profile Chrome opened with (Profile 1, Default, etc.)
4. Update your command to point to the correct User Data directory

## Troubleshooting "Duplicate Profile" Error

If you see a "profile already in use" error:
1. Open Task Manager (Ctrl+Shift+Esc)
2. End all Chrome processes
3. End all Chromium processes
4. Wait 5 seconds
5. Try running the crawler again

The crawler now uses persistent context properly and should handle your profile structure correctly.

