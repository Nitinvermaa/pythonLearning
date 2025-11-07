"""Launch a site in Microsoft Edge with a specific profile using Playwright.

This script opens Microsoft Edge via Playwright's Chromium binding while reusing
an existing Edge profile (for example `Default` or `Profile 1`). It works on the
three major platforms as long as the Edge browser is installed and Playwright
has the Edge channel downloaded (`playwright install msedge`).

Example
-------
python edge_profile_launcher.py --url https://learn.microsoft.com --profile "Profile 1"
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Iterable, List

from playwright.async_api import Error, async_playwright


def default_edge_user_data_root() -> Path:
    """Return the default Edge user-data directory for the current platform."""
    home = Path.home()
    if sys.platform == "win32":
        return home / "AppData" / "Local" / "Microsoft" / "Edge" / "User Data"
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "Microsoft Edge"
    # Linux and others
    return home / ".config" / "microsoft-edge"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Launch Microsoft Edge with an existing profile via Playwright."
    )
    parser.add_argument(
        "--url",
        required=True,
        help="The URL to open after Edge starts.",
    )
    parser.add_argument(
        "--profile",
        default="Default",
        help="Edge profile directory name (Default, Profile 1, Profile 2, ...).",
    )
    parser.add_argument(
        "--user-data-root",
        type=Path,
        default=default_edge_user_data_root(),
        help="Root user data directory that contains Edge profiles.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Headless (mostly for automation scenarios). Default: headed.",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Exit immediately after navigation (will close the browser).",
    )
    parser.add_argument(
        "--additional-arg",
        action="append",
        dest="additional_args",
        default=[],
        help="Extra command-line argument(s) to forward to Edge. Can be repeated.",
    )
    return parser


def validate_profile(user_data_root: Path, profile_name: str) -> None:
    """Ensure the profile directory exists; create it if it's the default profile."""
    profile_dir = user_data_root / profile_name
    if profile_dir.exists():
        return

    if profile_name == "Default":
        profile_dir.mkdir(parents=True, exist_ok=True)
    else:
        raise FileNotFoundError(
            f"Edge profile '{profile_name}' not found in '{user_data_root}'. "
            "Run Edge once with that profile or adjust --user-data-root/--profile."
        )


async def launch_edge_with_profile(
    url: str,
    user_data_root: Path,
    profile_name: str,
    headless: bool,
    extra_args: Iterable[str],
    no_wait: bool,
) -> None:
    user_data_root = user_data_root.expanduser().resolve()
    user_data_root.mkdir(parents=True, exist_ok=True)
    validate_profile(user_data_root, profile_name)

    launch_args: List[str] = [f"--profile-directory={profile_name}", *extra_args]

    async with async_playwright() as playwright:
        try:
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir=str(user_data_root),
                channel="msedge",
                headless=headless,
                args=launch_args,
            )
        except Error as exc:
            raise RuntimeError(
                "Unable to launch Microsoft Edge via Playwright. "
                "Ensure Microsoft Edge is installed and run `playwright install msedge`."
            ) from exc

        try:
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto(url, wait_until="load")
            print(f"Opened {url} in profile '{profile_name}'.")
            if no_wait:
                await context.close()
                return

            loop = asyncio.get_running_loop()
            print("Press Enter to close the browser gracefully...")
            await loop.run_in_executor(None, input)
        finally:
            await context.close()


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    try:
        asyncio.run(
            launch_edge_with_profile(
                url=args.url,
                user_data_root=args.user_data_root,
                profile_name=args.profile,
                headless=args.headless,
                extra_args=args.additional_args,
                no_wait=args.no_wait,
            )
        )
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    except Exception as error:  # noqa: BLE001 - surface to CLI
        parser.exit(status=1, message=f"Error: {error}\n")


if __name__ == "__main__":
    main()
