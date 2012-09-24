tell application "iPhone Simulator"
    activate
    end tell
    tell application "System Events"
        tell process "iPhone Simulator"
                tell menu bar 1
                       tell menu 2
                           click menu item 5
                       end tell
                 end tell
            tell window 1
            click button 2
        end tell
    end tell
end tell
