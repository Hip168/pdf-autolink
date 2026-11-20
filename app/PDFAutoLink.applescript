-- PDF AutoLink droplet: drop PDF files onto the app icon; each one is run
-- through the `pdf-autolink` command-line tool.
-- PDF_AUTOLINK_CLI      path to the CLI (checked first)
-- PDF_AUTOLINK_HEADLESS 1 = no dialogs/notifications; the result is returned
--                       (printed by osascript) and raised as an error on failure.

property appTitle : "PDF AutoLink"
property installHint : "uv tool install git+https://github.com/Hip168/pdf-autolink"

on run
	display dialog "Kéo một hoặc nhiều file PDF thả vào biểu tượng " & appTitle & " để tự gắn link." & return & return & "Kết quả: <tên>_linked.pdf và <tên>_linked.csv nằm cạnh file gốc." buttons {"OK"} default button "OK" with title appTitle
end run

on open droppedItems
	processFiles(droppedItems)
end open

on isHeadless()
	return (system attribute "PDF_AUTOLINK_HEADLESS") is "1"
end isHeadless

on isExecutable(p)
	if p is "" then return false
	try
		do shell script "test -f " & quoted form of p & " && test -x " & quoted form of p
		return true
	on error
		return false
	end try
end isExecutable

on findCli()
	set candidates to {system attribute "PDF_AUTOLINK_CLI", (POSIX path of (path to home folder)) & ".local/bin/pdf-autolink", "/opt/homebrew/bin/pdf-autolink", "/usr/local/bin/pdf-autolink"}
	repeat with c in candidates
		if isExecutable(contents of c) then return contents of c
	end repeat
	try
		set found to do shell script "/bin/zsh -lc 'command -v pdf-autolink'"
		if isExecutable(found) then return found
	end try
	return ""
end findCli

on lastLine(t)
	set ps to paragraphs of t
	repeat with i from (count of ps) to 1 by -1
		if (item i of ps) is not "" then return item i of ps
	end repeat
	return ""
end lastLine

on fileName(p)
	set AppleScript's text item delimiters to "/"
	set n to last text item of p
	set AppleScript's text item delimiters to ""
	return n
end fileName

on processFiles(droppedItems)
	set cli to findCli()
	if cli is "" then
		set msg to "Chưa cài pdf-autolink. Cài bằng lệnh:" & linefeed & installHint
		if isHeadless() then error msg
		display dialog msg buttons {"OK"} default button "OK" with title appTitle with icon stop
		return msg
	end if

	set okCount to 0
	set errCount to 0
	set skipCount to 0
	set details to {}
	repeat with f in droppedItems
		set f to contents of f
		if class of f is text then
			set p to f
		else
			set p to POSIX path of f
		end if
		ignoring case
			set isPdf to p ends with ".pdf"
		end ignoring
		if not isPdf then
			set skipCount to skipCount + 1
		else
			try
				with timeout of 3600 seconds
					set out to do shell script "export LANG=en_US.UTF-8; " & quoted form of cli & " " & quoted form of p & " 2>&1"
				end timeout
				set okCount to okCount + 1
				set end of details to fileName(p) & ": " & lastLine(out)
			on error errMsg
				set errCount to errCount + 1
				set end of details to fileName(p) & ": LỖI — " & lastLine(errMsg)
			end try
		end if
	end repeat

	set summary to (okCount as text) & " file xong, " & (errCount as text) & " lỗi, " & (skipCount as text) & " bỏ qua"
	set AppleScript's text item delimiters to linefeed
	set report to ({summary} & details) as text
	set AppleScript's text item delimiters to ""

	if isHeadless() then
		if errCount > 0 then error report
		return report
	end if
	display notification summary with title appTitle
	if errCount > 0 then
		display dialog report buttons {"OK"} default button "OK" with title appTitle with icon caution
	end if
	return report
end processFiles
