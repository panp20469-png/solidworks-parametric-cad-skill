On Error Resume Next

Dim swApp
Set swApp = CreateObject("SldWorks.Application")
If Err.Number <> 0 Then
  WScript.Echo "CREATE_ERROR=" & Hex(Err.Number) & " " & Err.Description
  WScript.Quit 1
End If

WScript.Echo "CREATE_OK=True"

Err.Clear
swApp.Visible = True
If Err.Number <> 0 Then
  WScript.Echo "VISIBLE_ERROR=" & Hex(Err.Number) & " " & Err.Description
Else
  WScript.Echo "VISIBLE_SET=True"
End If

Err.Clear
Dim revision
revision = swApp.RevisionNumber()
If Err.Number <> 0 Then
  WScript.Echo "REVISION_ERROR=" & Hex(Err.Number) & " " & Err.Description
Else
  WScript.Echo "REVISION=" & revision
End If

Err.Clear
swApp.ExitApp
If Err.Number <> 0 Then
  WScript.Echo "EXIT_ERROR=" & Hex(Err.Number) & " " & Err.Description
Else
  WScript.Echo "EXIT_OK=True"
End If
