-- Capture the current Claude or Gemini conversation into input/<provider>/chat/browser-{API,DOM}/.
-- Delegates to safari_capture.sh --agent <claude|gemini> --id, which handles JS injection,
-- file moving, API JSON fetch, and logging.
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

	set captureScript to scriptDir & "/safari_capture.sh"
	if currentURL starts with "https://claude.ai/chat/" then
		set agentFlag to "--agent claude"
	else if currentURL starts with "https://gemini.google.com/app/" and currentURL is not "https://gemini.google.com/app/" then
		set agentFlag to "--agent gemini"
	else
		display alert "Navigate to a specific conversation first." & return & return & "For bulk capture, run from Terminal at the repo root: src/main/browser-captures/PREP.sh — or run export-all-conversations.applescript from the recents page." buttons {"OK"} default button "OK"
		return
	end if

	set oldDelimiters to AppleScript's text item delimiters
	set AppleScript's text item delimiters to "/"
	set convId to last text item of currentURL
	set AppleScript's text item delimiters to oldDelimiters
end tell

do shell script quoted form of captureScript & " " & agentFlag & " --id " & quoted form of convId
