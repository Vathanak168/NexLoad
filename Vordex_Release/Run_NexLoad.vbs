Set oShell = CreateObject("WScript.Shell")
Set oFSO = CreateObject("Scripting.FileSystemObject")

' Get current folder
strPath = oFSO.GetParentFolderName(WScript.ScriptFullName)

' Build the command to run everything silently
' 1. Change to the directory
' 2. Install missing required modules (silently)
' 3. Start the Flask server hidden
' 4. Wait 3 seconds for server to start
' 5. Open Chrome (or Edge) in App Mode (looks like Native App)
strCmd = "cmd /c cd /d """ & strPath & """ && " & _
         "python -m pip install flask flask-cors yt-dlp requests --quiet && " & _
         "(tasklist | findstr /I ""python"" >nul || start """" /B python server.py) && " & _
         "timeout /t 3 >nul && " & _
         "start """" chrome --app=http://localhost:5000 --window-size=1280,860 2>nul || " & _
         "start """" msedge --app=http://localhost:5000 --window-size=1280,860 2>nul || " & _
         "start http://localhost:5000"

' Run the command completely hidden (0)
oShell.Run strCmd, 0, False
