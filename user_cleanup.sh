cat > ~/user_cleanup.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

echo "=== User cleanup script started ==="
date

# Helper
info() { echo -e "\n[INFO] $*"; }
warn() { echo -e "\n[WARN] $*"; }
ok()   { echo -e "\n[OK]   $*"; }

# 1) Show disk free before
info "Disk free (before):"
df -h ~ | awk 'NR==1 || NR==2 {print}'

# 2) Paths to clean (user-only)
CLEAN_PATHS=(
  "$HOME/Library/Caches/*"
  "$HOME/Library/Logs/*"
  "$HOME/Library/Application Support/CrashReporter/*"
  "$HOME/Library/Safari/LocalStorage/*"
  "$HOME/Library/Safari/Databases/*"
  "$HOME/Library/Containers/com.microsoft.teams/Data/Library/Caches/*"
  "$HOME/Library/Caches/Google/Chrome/*"
  "$HOME/Library/Application Support/Google/Chrome/Default/Service Worker/CacheStorage/*"
  "$HOME/Library/Caches/com.microsoft.edgemac/*"
  "$HOME/Library/Caches/com.microsoft.OneDrive/*"
)

info "Listing largest cache/log folders (top 10) under ~/Library (sizes):"
du -hs "$HOME/Library"/* 2>/dev/null | sort -hr | head -n 10 || true

# 3) Remove files (user permission only)
info "Removing user cache & log files (this may take a few seconds)..."
for p in "${CLEAN_PATHS[@]}"; do
  # show size before removing (if exists)
  if ls $p 1>/dev/null 2>&1; then
    du -sh $p 2>/dev/null || true
    rm -rf $p 2>/dev/null || true
  fi
done

# 4) Empty Trash
info "Emptying user Trash (~/.Trash)..."
if [ -d "$HOME/.Trash" ]; then
  rm -rf "$HOME/.Trash/"* 2>/dev/null || true
fi

# 5) Quit common heavy apps (non-admin)
KILL_APPS=( "Teams" "Slack" "OneDrive" "Google Chrome" "Microsoft Edge" "Dropbox" "Spotify" "Skype" "Box" )
info "Quitting common apps if running: ${KILL_APPS[*]}"
for app in "${KILL_APPS[@]}"; do
  pkill -x -f "$app" 2>/dev/null || true
done

# 6) Flush DNS cache (best-effort without sudo)
info "Attempting to flush DNS cache (best-effort)..."
dscacheutil -flushcache 2>/dev/null || true

# 7) Attempt to toggle Wi-Fi via AppleScript (may require Accessibility permission)
info "Attempting to toggle Wi-Fi off → on via AppleScript (may prompt for Accessibility permission)..."
osascript <<'APPLESCRIPT' 2>/dev/null || true
try
  tell application "System Events"
    tell process "SystemUIServer"
      -- click the Wi-Fi menu extra
      set wifiMenu to (first menu bar item whose description contains "Wi-Fi") of menu bar 1
      click wifiMenu
      delay 0.3
      try
        -- macOS menu items texts vary; try to click "Turn Wi-Fi Off"
        click menu item "Turn Wi-Fi Off" of menu 1 of wifiMenu
      on error
        -- fallback: click first "Wi-Fi" submenu's first menu item
        click menu item 1 of menu 1 of wifiMenu
      end try
      delay 4
      -- reopen and turn back on
      click wifiMenu
      delay 0.3
      try
        click menu item "Turn Wi-Fi On" of menu 1 of wifiMenu
      on error
        click menu item 1 of menu 1 of wifiMenu
      end try
    end tell
  end tell
end try
APPLESCRIPT

# 8) Show top CPU & memory hogs (user view)
info "Top CPU consumers (Activity snapshot):"
ps -eo pid,pcpu,pmem,comm --sort=-pcpu | head -n 12

info "Top memory consumers:"
ps -eo pid,pcpu,pmem,comm --sort=-pmem | head -n 12

# 9) Disk free after
ok "Disk free (after):"
df -h ~ | awk 'NR==1 || NR==2 {print}'

echo
ok "User cleanup complete. Recommended: REBOOT your Mac now (fully restart) for best effect."
echo "If Wi-Fi didn't toggle (or AppleScript couldn't run), please toggle Wi-Fi manually from the menu bar."

date
echo "=== End ==="
EOF

chmod +x ~/user_cleanup.sh
echo "Created ~/user_cleanup.sh — run it with:"
echo "  /bin/bash ~/user_cleanup.sh"
