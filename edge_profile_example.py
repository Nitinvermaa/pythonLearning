#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simple example demonstrating Edge browser automation with profile support.

This is a minimal example showing the core concepts of launching Edge
with a profile and performing basic automation tasks.
"""

import asyncio
from playwright.async_api import async_playwright


async def simple_edge_automation():
    """
    Simple example: Launch Edge with profile and perform basic automation.
    """
    async with async_playwright() as p:
        # Method 1: Launch with persistent context (recommended for profile usage)
        # This maintains all cookies, login sessions, and browser settings
        context = await p.chromium.launch_persistent_context(
            user_data_dir="./edge_profile",  # Creates/uses profile in current directory
            channel="msedge",  # Use Microsoft Edge
            headless=False,  # Set to True for headless mode
            args=["--start-maximized"],
        )
        
        # Get or create a page
        page = context.pages[0] if context.pages else await context.new_page()
        
        # Navigate to a website
        await page.goto("https://www.example.com")
        print(f"Page title: {await page.title()}")
        
        # Perform some actions
        # await page.click("selector")
        # await page.fill("input", "text")
        # await page.screenshot(path="screenshot.png")
        
        # Wait a bit to see the result
        await asyncio.sleep(3)
        
        # Close the browser
        await context.close()


async def advanced_edge_automation():
    """
    Advanced example with multiple pages, screenshots, and interactions.
    """
    async with async_playwright() as p:
        # Launch Edge with profile and additional options
        context = await p.chromium.launch_persistent_context(
            user_data_dir="./edge_profile_advanced",
            channel="msedge",
            headless=False,
            viewport={"width": 1920, "height": 1080},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
            ],
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        
        # Navigate to a website
        print("Navigating to example.com...")
        await page.goto("https://www.example.com", wait_until="networkidle")
        
        # Get page information
        title = await page.title()
        url = page.url
        print(f"Title: {title}")
        print(f"URL: {url}")
        
        # Take a screenshot
        await page.screenshot(path="example_screenshot.png", full_page=True)
        print("Screenshot saved: example_screenshot.png")
        
        # Get all links on the page
        links = await page.query_selector_all("a")
        print(f"Found {len(links)} links on the page")
        
        # Example: Navigate to another page
        print("\nNavigating to GitHub...")
        await page.goto("https://github.com")
        await page.wait_for_load_state("networkidle")
        print(f"GitHub page title: {await page.title()}")
        
        # Wait before closing
        await asyncio.sleep(2)
        
        # Close browser
        await context.close()
        print("\nBrowser closed successfully!")


async def edge_with_authentication():
    """
    Example showing how to handle authenticated sessions with profile.
    
    The profile preserves login sessions, so if you're already logged in
    to a website, you'll remain logged in when using the same profile.
    """
    async with async_playwright() as p:
        # Use a specific profile directory
        # This is useful for maintaining separate authentication states
        context = await p.chromium.launch_persistent_context(
            user_data_dir="./edge_profile_auth",
            channel="msedge",
            headless=False,
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        
        # Navigate to a site that requires authentication
        # If you've logged in before with this profile, you'll be already logged in
        await page.goto("https://github.com")
        
        # Check cookies to see if authenticated
        cookies = await context.cookies()
        print(f"Profile has {len(cookies)} cookies")
        
        # You can also set cookies manually if needed
        # await context.add_cookies([
        #     {"name": "session", "value": "value", "domain": ".example.com", "path": "/"}
        # ])
        
        await asyncio.sleep(3)
        await context.close()


async def multiple_pages_example():
    """
    Example showing how to work with multiple pages (tabs).
    """
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir="./edge_profile_tabs",
            channel="msedge",
            headless=False,
        )
        
        # Create multiple pages (tabs)
        page1 = context.pages[0] if context.pages else await context.new_page()
        page2 = await context.new_page()
        page3 = await context.new_page()
        
        # Navigate each page to different URLs
        await page1.goto("https://www.example.com")
        await page2.goto("https://www.github.com")
        await page3.goto("https://www.stackoverflow.com")
        
        print(f"Page 1: {await page1.title()}")
        print(f"Page 2: {await page2.title()}")
        print(f"Page 3: {await page3.title()}")
        
        # Work with specific pages
        await page1.bring_to_front()  # Focus on page 1
        
        await asyncio.sleep(5)
        await context.close()


# Main execution
if __name__ == "__main__":
    print("=" * 70)
    print("Edge Browser Automation Examples")
    print("=" * 70)
    print("\nChoose an example to run:")
    print("1. Simple Edge automation")
    print("2. Advanced Edge automation with screenshots")
    print("3. Edge with authentication (profile usage)")
    print("4. Multiple pages (tabs) example")
    print("5. Run all examples")
    
    choice = input("\nEnter choice (1-5): ").strip()
    
    if choice == "1":
        print("\n🚀 Running: Simple Edge Automation\n")
        asyncio.run(simple_edge_automation())
    elif choice == "2":
        print("\n🚀 Running: Advanced Edge Automation\n")
        asyncio.run(advanced_edge_automation())
    elif choice == "3":
        print("\n🚀 Running: Edge with Authentication\n")
        asyncio.run(edge_with_authentication())
    elif choice == "4":
        print("\n🚀 Running: Multiple Pages Example\n")
        asyncio.run(multiple_pages_example())
    elif choice == "5":
        print("\n🚀 Running: All Examples\n")
        print("\n--- Example 1: Simple ---")
        asyncio.run(simple_edge_automation())
        print("\n--- Example 2: Advanced ---")
        asyncio.run(advanced_edge_automation())
        print("\n--- Example 3: Authentication ---")
        asyncio.run(edge_with_authentication())
        print("\n--- Example 4: Multiple Pages ---")
        asyncio.run(multiple_pages_example())
    else:
        print("Invalid choice. Exiting.")
