#!/bin/bash
# Registers a custom URL scheme "xscraper://" to trigger the scripts from an email click

APP_NAME="XScraperRunner.app"

CURRENT_DIR="$PWD"

echo "Creating macOS application..."
osacompile -o "$APP_NAME" -e "
on open location this_URL
    do shell script \"cd '$CURRENT_DIR' && ./run.sh && ./run_newsletter.sh > /tmp/xscraper.log 2>&1 &\"
end open location
"

echo "Configuring URL scheme in Info.plist..."
defaults write "$PWD/$APP_NAME/Contents/Info.plist" CFBundleURLTypes -array "<dict><key>CFBundleURLName</key><string>XScraperRunner</string><key>CFBundleURLSchemes</key><array><string>xscraper</string></array></dict>"
plutil -convert xml1 "$PWD/$APP_NAME/Contents/Info.plist"

echo "Registering app in LaunchServices..."
/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister -f "$PWD/$APP_NAME"

echo "Done! The 'xscraper://run' link in emails will now securely trigger the script on your Mac."
