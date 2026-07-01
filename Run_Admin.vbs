' Admin Panel Silent Launcher
Dim sDir, sPython, sScript, oShell, oFSO

Set oShell = CreateObject("WScript.Shell")
Set oFSO   = CreateObject("Scripting.FileSystemObject")

sDir    = oFSO.GetParentFolderName(WScript.ScriptFullName)
sScript = sDir & "\admin_panel\admin_server.py"

' Find pythonw or python
On Error Resume Next
Dim sPython
sPython = oShell.Exec("cmd /c where pythonw.exe 2>nul").StdOut.ReadLine()
If sPython = "" Then
    sPython = oShell.Exec("cmd /c where python.exe 2>nul").StdOut.ReadLine()
End If
On Error GoTo 0

If sPython = "" Then
    MsgBox "Python not found! Please install Python.", 16, "Admin Error"
    WScript.Quit
End If

' Run admin_server.py silently (0 = hidden)
oShell.Run """" & sPython & """ """ & sScript & """", 0, False

' Wait 2.5 seconds for Flask to start
WScript.Sleep 2500

' Open browser automatically
oShell.Run "http://127.0.0.1:5050", 1, False
