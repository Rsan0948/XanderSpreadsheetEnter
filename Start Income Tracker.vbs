' Double-click this to launch the Income Tracker.
' Runs quietly in the background (no black terminal window)
' and opens the tracker in your web browser automatically.
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = fso.GetParentFolderName(WScript.ScriptFullName)

On Error Resume Next
sh.Run "pythonw app.py", 0, False
If Err.Number <> 0 Then
  Err.Clear
  sh.Run "pyw app.py", 0, False
End If
