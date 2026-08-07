-- Delegate to the appropriate capture script based on the front tab URL:
--   https://claude.ai/chat/*         → capture-conversation.applescript
--   https://claude.ai/recents        → capture-all-conversations.applescript
--   https://gemini.google.com/app/*  → capture-conversation.applescript
--   https://gemini.google.com/app    → capture-all-conversations.applescript
--
-- Prerequisite (one-time): Safari > Develop > Allow JavaScript from Apple Events

set scriptPath to POSIX path of (path to me)
set scriptDir to do shell script "dirname " & quoted form of scriptPath

tell application "Safari"
	if (count of windows) = 0 then
		display alert "No Safari window open." buttons {"OK"} default button "OK"
		return
	end if

	-- Fail fast if Safari blocks JavaScript from Apple Events — without this, every
	-- injection silently returns nothing and the capture appears to do nothing.
	try
		do JavaScript "1+1" in front document
	on error
		display alert "Safari is blocking JavaScript from Apple Events." message "Enable it via Safari → Settings → Advanced → 'Show features for web developers', then Settings → Developer → 'Allow JavaScript from Apple Events' — and run the shortcut again." buttons {"OK"} default button "OK"
		return
	end try

	set currentURL to URL of front document

	if currentURL starts with "https://claude.ai/chat/" or currentURL starts with "https://gemini.google.com/app/" then
		run script POSIX file (scriptDir & "/capture-conversation.applescript")
	else if currentURL starts with "https://claude.ai/recents" or currentURL starts with "https://gemini.google.com/app" then
		run script POSIX file (scriptDir & "/capture-all-conversations.applescript")
	else
		display alert "Front tab is not a recognised capture page." & return & return & currentURL buttons {"OK"} default button "OK"
	end if
end tell
