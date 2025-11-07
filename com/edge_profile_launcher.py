from __future__ import annotations

import argparse
import os
import platform
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright, BrowserContext


def resolve_default_edge_user_data_dir() -> Path:
    system = platform.system()
    home = Path.home()

    if system == "Windows":
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            return Path(local_appdata) / "Microsoft" / "Edge" / "User Data"
        # Fallback to standard path if env var is missing
        return home / "AppData" / "Local" / "Microsoft" / "Edge" / "User Data"

    if system == "Darwin":  # macOS
        return home / "Library" / "Application Support" / "Microsoft Edge"

    # Linux and others
    # For stable channel user data dir is typically ~/.config/microsoft-edge
    # For beta/dev/canary, names differ (microsoft-edge-beta, -dev, -canary)
    candidates = [
        home / ".config" / "microsoft-edge",
        home / ".config" / "microsoft-edge-stable",
        home / ".config" / "microsoft-edge-beta",
        home / ".config" / "microsoft-edge-dev",
        home / ".config" / "microsoft-edge-canary",
    ]
    for path in candidates:
        if path.exists():
            return path
    # Default to stable name even if not present (Playwright will create it)
    return candidates[0]


def launch_edge_with_profile(
    url: str,
    user_data_dir: Optional[str] = None,
    profile_directory_name: Optional[str] = None,
    headless: bool = False,
) -> BrowserContext:
    """Launch Edge with a specific user profile and open a URL.

    Args:
        url: Target URL to open.
        user_data_dir: Absolute path to Edge user data directory. If not provided, a sensible per-OS default is used.
        profile_directory_name: Edge profile directory name, e.g., "Default", "Profile 1", "Profile 2".
        headless: Whether to run headless.

    Returns:
        The launched persistent browser context. Caller is responsible for closing it.
    """
    resolved_user_data_dir = Path(user_data_dir) if user_data_dir else resolve_default_edge_user_data_dir()
    launch_args = []

    # If a profile directory is specified, pass it via Chromium arg expected by Edge
    if profile_directory_name:
        launch_args.append(f"--profile-directory={profile_directory_name}")

    # Ensure the directory exists; Chromium will create if missing, but creating avoids surprises
    resolved_user_data_dir.mkdir(parents=True, exist_ok=True)

    playwright = sync_playwright().start()
    try:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(resolved_user_data_dir),
            channel="msedge",
            headless=headless,
            args=launch_args or None,
        )

        page = context.pages[0] if context.pages else context.new_page()
        page.goto(url)
        page.wait_for_load_state("domcontentloaded")
        return context
    except Exception:
        # Ensure Playwright is stopped on failure
        playwright.stop()
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch Microsoft Edge with a specific profile and open a URL.")
    parser.add_argument("--url", required=True, help="Target URL to open, e.g., https://example.com")
    parser.add_argument(
        "--user-data-dir",
        dest="user_data_dir",
        default=os.environ.get("EDGE_USER_DATA_DIR"),
        help="Absolute path to Edge user data dir. Defaults to OS-specific location.",
    )
    parser.add_argument(
        "--profile",
        dest="profile_directory_name",
        default=os.environ.get("EDGE_PROFILE", "Default"),
        help='Edge profile directory name, e.g., "Default", "Profile 1".',
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode.",
    )

    args = parser.parse_args()

    context: Optional[BrowserContext] = None
    try:
        context = launch_edge_with_profile(
            url=args.url,
            user_data_dir=args.user_data_dir,
            profile_directory_name=args.profile_directory_name,
            headless=args.headless,
        )
        # Keep the browser open until user presses Enter
        print("Edge launched. Press Enter to close...")
        input()
    finally:
        if context is not None:
            context.close()


if __name__ == "__main__":
    main()
