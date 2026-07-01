' NexLoad Silent Launcher (VBScript)
' Double-click this file to launch NexLoad app

Dim sDir, sPython, sScript, oShell, oFSO

Set oShell = CreateObject("WScript.Shell")
Set oFSO   = CreateObject("Scripting.FileSystemObject")

' Get the folder where this script lives
sDir    = oFSO.GetParentFolderName(WScript.ScriptFullName)
sScript = sDir & "\NexLoad.pyw"

' Try to find Python
Dim aPaths(6)
aPaths(0) = oShell.ExpandEnvironmentStrings("%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe")
aPaths(1) = oShell.ExpandEnvironmentStrings("%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe")
aPaths(2) = oShell.ExpandEnvironmentStrings("%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe")
aPaths(3) = oShell.ExpandEnvironmentStrings("%LOCALAPPDATA%\Programs\Python\Python310\pythonw.exe")
aPaths(4) = "C:\Python312\pythonw.exe"
aPaths(5) = "C:\Python311\pythonw.exe"
aPaths(6) = "C:\Python310\pythonw.exe"

sPython = ""

' Try pythonw from PATH first
On Error Resume Next
Dim sTest
sTest = oShell.Exec("cmd /c where pythonw.exe 2>nul").StdOut.ReadLine()
On Error GoTo 0
If oFSO.FileExists(sTest) Then
    sPython = sTest
End If

' Try known paths if not found
If sPython = "" Then
    Dim i
    For i = 0 To 6
        If oFSO.FileExists(aPaths(i)) Then
            sPython = aPaths(i)
            Exit For
        End If
    Next
End If

' Fallback: try python.exe (will briefly show a window)
If sPython = "" Then
    On Error Resume Next
    sTest = oShell.Exec("cmd /c where python.exe 2>nul").StdOut.ReadLine()
    On Error GoTo 0
    If oFSO.FileExists(sTest) Then
        sPython = sTest
    End If
End If

' If still not found, show error
If sPython = "" Then
    MsgBox "Python not found!" & vbCrLf & vbCrLf & _
           "Please install Python from https://python.org" & vbCrLf & _
           "Make sure to check 'Add Python to PATH'", _
           16, "NexLoad Error"
    WScript.Quit
End If

' Check script exists
If Not oFSO.FileExists(sScript) Then
    MsgBox "NexLoad.pyw not found in:" & vbCrLf & sDir, 16, "NexLoad Error"
    WScript.Quit
End If

' Run silently (0 = hidden window, False = don't wait)
oShell.Run """" & sPython & """ """ & sScript & """", 0, False

' Wait a moment then open browser (fallback if pyw fails)
WScript.Sleep 3000

' Check if server is up by trying to connect
Dim oHTTP
Set oHTTP = CreateObject("MSXML2.XMLHTTP")
On Error Resume Next
oHTTP.Open "GET", "http://localhost:5000", False
oHTTP.Send
On Error GoTo 0

If oHTTP.Status = 200 Or oHTTP.Status = 301 Or oHTTP.Status = 302 Then
    ' Server already running — open browser
    oShell.Run "http://localhost:5000", 1, False
End If
