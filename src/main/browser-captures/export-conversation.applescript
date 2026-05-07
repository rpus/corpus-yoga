-- Export the current Claude.ai conversation to markdown.
-- Reads browser-chat-capture.js from the same directory, so any edits to the JS
-- are picked up automatically without touching this script.
--
-- Prerequisite (one-time): Safari > Develop > Allow JavaScript from Apple Events

set scriptPath to POSIX path of (path to me)
set scriptDir to do shell script "dirname " & quoted form of scriptPath
set jsPath to scriptDir & "/browser-chat-capture.js"

tell application "Safari"
	if (count of windows) = 0 then
		display alert "No Safari window open." buttons {"OK"} default button "OK"
		return
	end if

	set currentURL to URL of front document
	if currentURL does not start with "https://claude.ai/chat/" then
		display alert "Front tab is not a Claude.ai chat page." & return & return & currentURL buttons {"OK"} default button "OK"
		return
	end if

	try
		set jsCode to read POSIX file jsPath as «class utf8»
	on error errMsg
		display alert "Could not read browser-chat-capture.js:" & return & return & errMsg buttons {"OK"} default button "OK"
		return
	end try

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

	-- Fetch API JSON → {uuid}.json in ~/Downloads/
	try
		do JavaScript "(async function(){ const orgId=document.cookie.match(/lastActiveOrg=([^;]+)/)?.[1]; const uuid=window.location.pathname.split('/').pop(); if(!orgId||!uuid)return; const r=await fetch('/api/organizations/'+orgId+'/chat_conversations/'+uuid+'?tree=true&rendering_mode=messages&render_all_tools=true',{credentials:'include'}); if(!r.ok)return; const a=document.createElement('a'); a.href=URL.createObjectURL(new Blob([JSON.stringify(await r.json(),null,2)],{type:'application/json'})); a.download=uuid+'.json'; document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(a.href); })()" in front document
	end try

end tell
