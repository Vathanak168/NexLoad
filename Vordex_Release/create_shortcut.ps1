$AppDir = "C:\Users\U-ser\Desktop\AI_Tool"
$Launcher = "$AppDir\Run_NexLoad.vbs"
$IconFile = "$AppDir\nexload.ico"
$Desktop = [Environment]::GetFolderPath("Desktop")
$Shortcut = "$Desktop\NexLoad.lnk"

# Create shortcut to wscript.exe running our VBS
$WScriptShell = New-Object -ComObject WScript.Shell
$SC = $WScriptShell.CreateShortcut($Shortcut)
$SC.TargetPath = "wscript.exe"
$SC.Arguments = """$Launcher"""
$SC.WorkingDirectory = $AppDir
$SC.Description = "NexLoad - Professional Video Downloader"
if (Test-Path $IconFile) {
    $SC.IconLocation = "$IconFile,0"
}
$SC.Save()

Write-Host "Updated Shortcut created: $Shortcut" -ForegroundColor Green
