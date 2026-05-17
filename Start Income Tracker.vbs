' Double-click this to launch the Income Tracker.
'
' First time: a small setup window appears, builds a private
' Python environment and downloads everything automatically.
' Every time after that: it just starts, silently, no window.
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
base = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = base

worker = "cmd /c """ & base & "\_setup_and_run.bat"""
venvReady = fso.FileExists(base & "\.venv\Scripts\pythonw.exe") _
            And fso.FileExists(base & "\.venv\.deps-ok")

If venvReady Then
  ' Everything is already installed - run completely silently.
  sh.Run worker, 0, False
Else
  ' First run - show the setup window so progress is visible.
  sh.Run worker, 1, False
End If
