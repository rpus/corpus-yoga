-- Capture all conversations to markdown, one tab at a time.
-- Supports Claude (claude.ai/recents) and Gemini (gemini.google.com/app).
-- Downloads go to ~/Downloads/ as Safari normally places them.
--
-- Prerequisite (one-time): Safari > Develop > Allow JavaScript from Apple Events

set SELF to "src/main/cli/browser/capture-all-conversations.applescript"
set scriptPath to POSIX path of (path to me)
set scriptDir to do shell script "dirname " & quoted form of scriptPath
set singleScript to POSIX file (scriptDir & "/capture-conversation.applescript")
-- The declared-address root (#352's discipline, #403): suffix-strip, refused
-- loudly when this file is not at SELF — before anything is written anywhere.
set repoDir to do shell script "p=" & quoted form of scriptPath & "; s=" & quoted form of SELF & "; r=\"${p%/$s}\"; [ \"$r/$s\" = \"$p\" ] || { echo \"$p: not at its declared address $s\" >&2; exit 1; }; printf %s \"$r\""
set logDir to repoDir & "/tmp/logs/browser/capture/all-conversations"
do shell script "mkdir -p " & quoted form of logDir
set logFile to logDir & "/" & (do shell script "date -u '+%Y-%m-%dT%H%M%SZ'") & ".log"

on logHeader(logFile, msg)
	do shell script "echo " & quoted form of ((do shell script "date '+%Y-%m-%d %H:%M:%S'") & " " & msg) & " >> " & quoted form of logFile
end logHeader

on logLine(logFile, msg)
	do shell script "echo " & quoted form of ((do shell script "date '+%Y-%m-%d %H:%M:%S'") & "   " & msg) & " >> " & quoted form of logFile
end logLine

tell application "Safari"
	if (count of windows) = 0 then
		display alert "No Safari window open." buttons {"OK"} default button "OK"
		return
	end if

	set currentURL to URL of front document

	if currentURL starts with "https://claude.ai/recents" then
		-- Scroll to bottom until count stabilises (infinite scroll)
		set prevCount to 0
		repeat
			do JavaScript "window.scrollTo(0, document.body.scrollHeight)" in front document
			delay 2
			set currCount to do JavaScript "document.querySelectorAll('a[href*=\"/chat/\"]').length" in front document
			if currCount = prevCount then exit repeat
			set prevCount to currCount
		end repeat

		-- Extract unique conversation UUIDs and names (in DOM order, first occurrence wins)
		set idsRaw to do JavaScript "(function(){ var seen=new Set(),r=[]; document.querySelectorAll('a[href*=\"/chat/\"]').forEach(function(a){ var u=a.pathname.split('/').pop(); if(u&&!seen.has(u)){seen.add(u);r.push(u);} }); return r.join('\\n'); })()" in front document
		set namesRaw to do JavaScript "(function(){ var seen=new Set(),r=[]; document.querySelectorAll('a[href*=\"/chat/\"]').forEach(function(a){ var u=a.pathname.split('/').pop(); if(u&&!seen.has(u)){seen.add(u);var n=a.textContent.replace(/\\s+/g,' ').trim().replace(/(Last message \\d+ \\w+ ago|Shared)/g,'').trim();r.push(n);} }); return r.join('\\n'); })()" in front document

		set baseURL to "https://claude.ai/chat/"
		set copyButtonSelector to "button[data-testid=\"action-bar-copy\"]"
		set isClaude to true

	else if currentURL starts with "https://gemini.google.com/app" then
		-- Scroll to bottom until count stabilises (infinite scroll)
		set prevCount to 0
		repeat
			do JavaScript "window.scrollTo(0, document.body.scrollHeight)" in front document
			delay 2
			set currCount to do JavaScript "document.querySelectorAll('a[href*=\"/app/\"]').length" in front document
			if currCount = prevCount then exit repeat
			set prevCount to currCount
		end repeat

		-- Extract unique conversation IDs and names
		set idsRaw to do JavaScript "(function(){ var seen=new Set(),r=[]; document.querySelectorAll('a[href*=\"/app/\"]').forEach(function(a){ var id=a.pathname.split('/').pop(); if(id&&/^[0-9a-f]{8,}$/.test(id)&&!seen.has(id)){seen.add(id);r.push(id);} }); return r.join('\\n'); })()" in front document
		set namesRaw to do JavaScript "(function(){ var seen=new Set(),r=[]; document.querySelectorAll('a[href*=\"/app/\"]').forEach(function(a){ var id=a.pathname.split('/').pop(); if(id&&/^[0-9a-f]{8,}$/.test(id)&&!seen.has(id)){seen.add(id);var n=a.textContent.replace(/\\s+/g,' ').trim();r.push(n||id);} }); return r.join('\\n'); })()" in front document

		set baseURL to "https://gemini.google.com/app/"
		set copyButtonSelector to "button[aria-label=\"Copy prompt\"]"
		set isClaude to false

	else
		display alert "Front tab is not a recognised recents page." & return & return & currentURL buttons {"OK"} default button "OK"
		return
	end if

	if idsRaw is "" then
		display alert "No conversations found." buttons {"OK"} default button "OK"
		return
	end if

	set idList to paragraphs of idsRaw
	set nameList to paragraphs of namesRaw
	set totalCount to count of idList

	set response to button returned of (display dialog "Capture " & totalCount & " conversations to markdown?" & return & return & "Each opens briefly in Safari and downloads to your Downloads folder." buttons {"Cancel", "Capture All"} default button "Capture All")
	if response is "Cancel" then return

	my logHeader(logFile, "=== " & totalCount & " conversations ===")

	repeat with i from 1 to totalCount
		set convId to item i of idList
		set convName to item i of nameList
		set prefix to i & "/" & totalCount & " | " & convId & " | " & convName

		my logHeader(logFile, prefix)
		my logLine(logFile, "opening")

		tell front window
			set newTab to make new tab with properties {URL: baseURL & convId}
			set current tab to newTab
		end tell

		repeat
			delay 1
			try
				if (do JavaScript "document.readyState" in front document) is "complete" then exit repeat
			end try
		end repeat

		-- Wait for copy buttons to appear
		repeat
			delay 0.5
			try
				if (do JavaScript "!!document.querySelector('" & copyButtonSelector & "')" in front document) is true then exit repeat
			end try
		end repeat

		my logLine(logFile, "running capture")

		try
			run script singleScript
		on error errMsg
			my logLine(logFile, "error: " & errMsg)
		end try

		try
			tell front window to close current tab
		end try
	end repeat
end tell
