-- Export all Claude.ai conversations to markdown, one tab at a time.
-- The front tab must already be on https://claude.ai/recents.
-- Downloads go to ~/Downloads/ as Safari normally places them.
-- Log is appended to claude-export.log in the same directory as this script.
--
-- Prerequisite (one-time): Safari > Develop > Allow JavaScript from Apple Events

set scriptPath to POSIX path of (path to me)
set scriptDir to do shell script "dirname " & quoted form of scriptPath
set singleScript to POSIX file (scriptDir & "/export-conversation.applescript")
set logFile to scriptDir & "/claude-export.log"
set downloadsDir to (do shell script "echo $HOME") & "/Downloads/"

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
	if currentURL does not start with "https://claude.ai/recents" then
		display alert "Front tab is not the Claude.ai recents page." & return & return & currentURL buttons {"OK"} default button "OK"
		return
	end if

	-- Click "Show more" until all conversations are loaded
	repeat
		set hasMore to do JavaScript "!!Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'Show more')" in front document
		if hasMore is false then exit repeat
		do JavaScript "Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'Show more').click()" in front document
		delay 1
	end repeat

	-- Extract unique conversation UUIDs (in DOM order, first occurrence wins)
	set uuidsRaw to do JavaScript "(function(){ var seen=new Set(),r=[]; document.querySelectorAll('a[href*=\"/chat/\"]').forEach(function(a){ var u=a.pathname.split('/').pop(); if(u&&!seen.has(u)){seen.add(u);r.push(u);} }); return r.join('\\n'); })()" in front document

	-- Extract names: normalise whitespace first, then strip DOM metadata
	set namesRaw to do JavaScript "(function(){ var seen=new Set(),r=[]; document.querySelectorAll('a[href*=\"/chat/\"]').forEach(function(a){ var u=a.pathname.split('/').pop(); if(u&&!seen.has(u)){seen.add(u);var n=a.textContent.replace(/\\s+/g,' ').trim().replace(/(Last message \\d+ \\w+ ago|Shared)/g,'').trim();r.push(n);} }); return r.join('\\n'); })()" in front document

	if uuidsRaw is "" then
		display alert "No conversations found." buttons {"OK"} default button "OK"
		return
	end if

	set uuidList to paragraphs of uuidsRaw
	set nameList to paragraphs of namesRaw
	set totalCount to count of uuidList

	set response to button returned of (display dialog "Export " & totalCount & " conversations to markdown?" & return & return & "Each opens briefly in Safari and downloads to your Downloads folder." buttons {"Cancel", "Export All"} default button "Export All")
	if response is "Cancel" then return

	my logHeader(logFile, "=== " & totalCount & " conversations ===")

	repeat with i from 1 to totalCount
		set convId to item i of uuidList
		set convName to item i of nameList
		set prefix to i & "/" & totalCount & " | " & convId & " | " & convName

		my logHeader(logFile, prefix)
		my logLine(logFile, "opening")

		tell front window
			set newTab to make new tab with properties {URL: "https://claude.ai/chat/" & convId}
			set current tab to newTab
		end tell

		repeat
			delay 1
			try
				if (do JavaScript "document.readyState" in front document) is "complete" then exit repeat
			end try
		end repeat

		-- Wait for React to render copy buttons
		repeat
			delay 0.5
			try
				if (do JavaScript "!!document.querySelector('button[data-testid=\"action-bar-copy\"]')" in front document) is true then exit repeat
			end try
		end repeat

		my logLine(logFile, "running export")

		try
			run script singleScript
		on error errMsg
			my logLine(logFile, "error: " & errMsg)
		end try

		-- Check for JSON ({uuid}.json fetched by export-conversation.applescript)
		try
			do shell script "test -f " & quoted form of (downloadsDir & convId & ".json")
			my logLine(logFile, "json: " & convId & ".json")
		on error
			my logLine(logFile, "json: missing")
		end try

		try
			tell front window to close current tab
		end try
	end repeat
end tell
