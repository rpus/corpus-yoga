-- Export the current conversation to markdown.
-- Supports Claude (claude.ai) and Gemini (gemini.google.com).
-- Reads the appropriate JS capture script from the claude/ or gemini/ subdirectory.
-- Moves captured files directly into ext/browser-captures/{claude|gemini}/{id}/ in the repo.
--
-- Prerequisite (one-time): Safari > Develop > Allow JavaScript from Apple Events

set scriptPath to POSIX path of (path to me)
set scriptDir to do shell script "dirname " & quoted form of scriptPath
set repoDir to do shell script "cd " & quoted form of scriptDir & "/../../../ && pwd"

tell application "Safari"
	if (count of windows) = 0 then
		display alert "No Safari window open." buttons {"OK"} default button "OK"
		return
	end if

	set currentURL to URL of front document

	if currentURL starts with "https://claude.ai/chat/" then
		set jsPath to scriptDir & "/claude/browser-chat-capture.js"
		set isClaude to true
		set site to "claude"
	else if currentURL starts with "https://gemini.google.com/app/" then
		set jsPath to scriptDir & "/gemini/browser-chat-capture.js"
		set isClaude to false
		set site to "gemini"
	else
		display alert "Front tab is not a recognised conversation page." & return & return & currentURL buttons {"OK"} default button "OK"
		return
	end if

	-- Extract conversation ID from URL
	set oldDelimiters to AppleScript's text item delimiters
	set AppleScript's text item delimiters to "/"
	set convId to last text item of currentURL
	set AppleScript's text item delimiters to oldDelimiters

	try
		set jsCode to read POSIX file jsPath as «class utf8»
	on error errMsg
		display alert "Could not read capture script:" & return & return & errMsg buttons {"OK"} default button "OK"
		return
	end try

	-- Mark start time so we can identify newly downloaded files afterwards
	do shell script "touch /tmp/.capture_start"

	try
		do JavaScript jsCode in front document
	on error errMsg
		display alert "JavaScript injection failed." & return & return & errMsg & return & return & "Check: Safari > Develop > Allow JavaScript from Apple Events" buttons {"OK"} default button "OK"
		return
	end try

	-- Poll status div until export completes or stalls for 30s
	set lastStatus to ""
	set statusSeen to false
	set stallSeconds to 0
	repeat
		delay 0.5
		set stallSeconds to stallSeconds + 0.5
		if stallSeconds > 30 then exit repeat
		try
			set currentStatus to do JavaScript "(function(){ var d=document.querySelector('[style*=\"z-index: 10000\"]'); return d?d.textContent:''; })()" in front document
			if currentStatus is not "" and currentStatus is not lastStatus then
				set lastStatus to currentStatus
				set statusSeen to true
				set stallSeconds to 0
			else if statusSeen and currentStatus is "" then
				exit repeat
			end if
		end try
	end repeat

	-- Fetch API JSON for Claude only, then poll until it appears in ~/Downloads/
	if isClaude then
		try
			do JavaScript "(async function(){ const orgId=document.cookie.match(/lastActiveOrg=([^;]+)/)?.[1]; const uuid=window.location.pathname.split('/').pop(); if(!orgId||!uuid)return; const r=await fetch('/api/organizations/'+orgId+'/chat_conversations/'+uuid+'?tree=true&rendering_mode=messages&render_all_tools=true',{credentials:'include'}); if(!r.ok)return; const a=document.createElement('a'); a.href=URL.createObjectURL(new Blob([JSON.stringify(await r.json(),null,2)],{type:'application/json'})); a.download=uuid+'.json'; document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(a.href); })()" in front document
		end try
		set jsonPath to (POSIX path of (path to downloads folder)) & convId & ".json"
		repeat 20 times
			delay 0.5
			try
				do shell script "test -f " & quoted form of jsonPath
				exit repeat
			end try
		end repeat
	end if

	-- Move captured .md and .json files from Downloads into ext/
	delay 1
	set destDir to repoDir & "/ext/browser-captures/" & site & "/" & convId
	do shell script "mkdir -p " & quoted form of destDir
	set downloadsDir to POSIX path of (path to downloads folder)
	if downloadsDir ends with "/" then set downloadsDir to text 1 thru -2 of downloadsDir
	set newMd to paragraphs of (do shell script "find " & quoted form of downloadsDir & " -maxdepth 1 -newer /tmp/.capture_start -name '*.md' 2>/dev/null; true")
	set newJson to paragraphs of (do shell script "find " & quoted form of downloadsDir & " -maxdepth 1 -newer /tmp/.capture_start -name '*.json' 2>/dev/null; true")
	repeat with f in newMd
		if f is not "" then do shell script "mv " & quoted form of f & " " & quoted form of destDir & "/"
	end repeat
	repeat with f in newJson
		if f is not "" then do shell script "mv " & quoted form of f & " " & quoted form of destDir & "/"
	end repeat
	-- Rename UUID.json to match the MD title (Claude only; only if we just moved a fresh JSON)
	if isClaude and (count of newMd) >= 1 and item 1 of newMd is not "" and (count of newJson) >= 1 and item 1 of newJson is not "" then
		set mdBase to do shell script "basename " & quoted form of (item 1 of newMd) & " .md"
		do shell script "mv " & quoted form of (destDir & "/" & convId & ".json") & " " & quoted form of (destDir & "/" & mdBase & ".json") & " 2>/dev/null; true"
	end if

end tell
