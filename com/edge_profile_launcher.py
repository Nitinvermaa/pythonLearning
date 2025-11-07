"""Utilities for launching Microsoft Edge with a specific profile using Playwright.

Prerequisites:
    pip install playwright
    playwright install msedge

Usage example:
    python -m com.edge_profile_launcher --profile-dir ~/.config/microsoft-edge \
        --profile-name "Profile 1" --url https://example.com
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright

EDGE_CHANNEL = "msedge"


async def launch_with_profile(
    url: str,
    user_data_dir: Path,
    profile_name: str,
    headless: bool,
    slow_mo: Optional[int] = None,
) -> None:
    """Launch Edge with the given profile and navigate to ``url``."""
    async with async_playwright() as playwright:
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            channel=EDGE_CHANNEL,
            headless=headless,
            slow_mo=slow_mo,
            args=[f"--profile-directory={profile_name}"],
        )

        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(url, wait_until="networkidle", timeout=120_000)

        try:
            # Keep the browser open until the user stops the script (Ctrl+C).
            await page.wait_for_timeout(3_600_000)
        except KeyboardInterrupt:
            pass
        finally:
            await context.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Launch Microsoft Edge via Playwright with a specific profile."
    )
    parser.add_argument(
        "--url",
        default="https://www.microsoft.com/edge",
        help="Destination URL to load after launching (default: Edge product page).",
    )
    parser.add_argument(
        "--profile-dir",
        required=True,
        type=Path,
        help="Path to Edge user data directory that contains profile folders.",
    )
    parser.add_argument(
        "--profile-name",
        default="Default",
        help="Name of the profile folder inside the user data dir (default: Default).",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Edge in headless mode (default: UI mode).",
    )
    parser.add_argument(
        "--slow-mo",
        type=int,
        default=None,
        help="Delay (ms) to slow down Playwright actions for debugging.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(
        launch_with_profile(
            url=args.url,
            user_data_dir=args.profile_dir.expanduser().resolve(),
            profile_name=args.profile_name,
            headless=args.headless,
            slow_mo=args.slow_mo,
        )
    )


if __name__ == "__main__":
    main()
