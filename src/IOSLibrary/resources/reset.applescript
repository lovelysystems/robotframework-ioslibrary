tell application "iPhone Simulator"
    activate
    end tell

    tell application "System Events"
        tell process "iPhone Simulator"
                tell menu bar 1
                    try
                        tell menu bar item "iOS Simulator"
                            tell menu "iOS Simulator"
                                click menu item "Reset Content and Settings…"
                            end tell
                        end tell
                    on error
                        tell menu bar item "iOS-Simulator"
                            tell menu "iOS Simulator"
                                click menu item "Reset Content and Settings…"
                            end tell
                        end tell
                    end try
                 end tell
            tell window 1
            click button "Reset"
        end tell
    end tell
end tell
