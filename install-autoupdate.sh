#!/bin/bash
# Enables the twice-daily self-updating build for the GoldRock metals chart.
# Run once:  bash ~/goldrock-metals-chart/install-autoupdate.sh
set -e
PLIST="$HOME/goldrock-metals-chart/launchd/com.goldrock.metals-chart.plist"
DEST="$HOME/Library/LaunchAgents/com.goldrock.metals-chart.plist"
cp "$PLIST" "$DEST"
launchctl unload "$DEST" 2>/dev/null || true
launchctl load "$DEST"
echo "Loaded. Scheduled builds: 06:00 and 15:15 local time (plus once now)."
launchctl list | grep metals-chart || true
echo "Logs: ~/Library/Logs/goldrock-metals-chart.log"

# To disable later:
#   launchctl unload ~/Library/LaunchAgents/com.goldrock.metals-chart.plist
#   rm ~/Library/LaunchAgents/com.goldrock.metals-chart.plist
