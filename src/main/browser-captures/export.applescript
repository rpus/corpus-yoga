-- Delegate to the appropriate export script based on the front tab URL:
--   https://claude.ai/chat/*         → export-conversation.applescript
--   https://claude.ai/recents        → export-all-conversations.applescript
--   https://gemini.google.com/app/*  → export-conversation.applescript
--   https://gemini.google.com/app    → export-all-conversations.applescript
--
-- Prerequisite (one-time): Safari > Develop > Allow JavaScript from Apple Events

set scriptPath to POSIX path of (path to me)
set scriptDir to do shell script "dirname " & quoted form of scriptPath

tell application "Safari"
	if (count of windows) = 0 then
		display alert "No Safari window open." buttons {"OK"} default button "OK"
		return
	end if

	set currentURL to URL of front document

	if currentURL starts with "https://claude.ai/chat/" or currentURL starts with "https://gemini.google.com/app/" then
		run script POSIX file (scriptDir & "/export-conversation.applescript")
	else if currentURL starts with "https://claude.ai/recents" or currentURL starts with "https://gemini.google.com/app" then
		run script POSIX file (scriptDir & "/export-all-conversations.applescript")
	else
		display alert "Front tab is not a recognised export page." & return & return & currentURL buttons {"OK"} default button "OK"
	end if
end tell
