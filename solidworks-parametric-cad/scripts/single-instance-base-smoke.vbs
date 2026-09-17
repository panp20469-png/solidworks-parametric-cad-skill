' SW_SCRIPT_KIND=baseline
Option Explicit
On Error Resume Next

Const swSaveAsCurrentVersion = 0
Const swSaveAsOptionsSilent = 1
Const swEndCondBlind = 0
Const swFullyConstrained = 3

Dim fso, scriptDir, outDir, outPart, outLog
Dim swApp, model, templatePath, selected, sketch, sketchFeature
Dim segments(3), sketchSegments, sketchStatus, regions, selectData, selectedCount
Dim feature, saveResult, savedFile, resultBodyCount

Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
outDir = fso.BuildPath(scriptDir, "output")
If Not fso.FolderExists(outDir) Then fso.CreateFolder outDir

outPart = fso.BuildPath(outDir, "single_instance_base_smoke.SLDPRT")
outLog = fso.BuildPath(outDir, "single_instance_base_smoke.log")
If fso.FileExists(outPart) Then fso.DeleteFile outPart, True
If fso.FileExists(outLog) Then fso.DeleteFile outLog, True

Sub Log(ByVal text)
  Dim stream
  WScript.Echo text
  Set stream = fso.OpenTextFile(outLog, 8, True)
  stream.WriteLine text
  stream.Close
End Sub

Sub Fail(ByVal reason)
  Log "RESULT=FAILED|REASON=" & reason & "|ERROR=" & Hex(Err.Number) & " " & Err.Description
  WScript.Quit 1
End Sub

Function Mm(ByVal value)
  Mm = CDbl(value) / 1000.0
End Function

Function U(ByVal codes)
  Dim i, text
  text = ""
  For i = 0 To UBound(codes)
    text = text & ChrW(codes(i))
  Next
  U = text
End Function

Function TopPlane()
  TopPlane = U(Array(&H4E0A, &H89C6, &H57FA, &H51C6, &H9762))
End Function

Function BodyCount(ByVal targetModel)
  Dim localBodies
  Err.Clear
  localBodies = targetModel.GetBodies2(0, False)
  If Err.Number <> 0 Then
    BodyCount = -1
    Err.Clear
  ElseIf IsEmpty(localBodies) Then
    BodyCount = 0
  ElseIf IsArray(localBodies) Then
    BodyCount = UBound(localBodies) - LBound(localBodies) + 1
  Else
    BodyCount = 1
  End If
End Function

' This is intentionally one process and one COM application object.
Log "STAGE=start"
Err.Clear
Set swApp = CreateObject("SldWorks.Application")
If Err.Number <> 0 Or swApp Is Nothing Then Fail "CREATE_SOLIDWORKS"
Log "CREATE_OK=True"

Err.Clear
swApp.Visible = True
If Err.Number <> 0 Then Fail "SET_VISIBLE"
Log "VISIBLE_OK=True"

Err.Clear
templatePath = swApp.GetUserPreferenceStringValue(8)
If Err.Number <> 0 Or Len(templatePath) = 0 Then Fail "GET_PART_TEMPLATE"
Log "TEMPLATE=" & templatePath

Err.Clear
Set model = swApp.NewDocument(templatePath, 0, 0, 0)
If Err.Number <> 0 Or model Is Nothing Then Fail "NEW_DOCUMENT"
Log "NEW_DOCUMENT_OK=True"

model.ClearSelection2 True
Err.Clear
selected = model.Extension.SelectByID2(TopPlane(), "PLANE", 0, 0, 0, False, 0, Nothing, 0)
If Not selected Then
  model.ClearSelection2 True
  selected = model.Extension.SelectByID2("Top Plane", "PLANE", 0, 0, 0, False, 0, Nothing, 0)
End If
If Err.Number <> 0 Or Not selected Then Fail "SELECT_TOP_PLANE"
Log "SELECT_TOP_PLANE_OK=True"

Err.Clear
model.SketchManager.InsertSketch True
If Err.Number <> 0 Then Fail "INSERT_SKETCH"

Set segments(0) = model.SketchManager.CreateLine(Mm(-30), Mm(-30), 0, Mm(30), Mm(-30), 0)
Set segments(1) = model.SketchManager.CreateLine(Mm(30), Mm(-30), 0, Mm(30), Mm(30), 0)
Set segments(2) = model.SketchManager.CreateLine(Mm(30), Mm(30), 0, Mm(-30), Mm(30), 0)
Set segments(3) = model.SketchManager.CreateLine(Mm(-30), Mm(30), 0, Mm(-30), Mm(-30), 0)
If Err.Number <> 0 Then Fail "CREATE_RECTANGLE"

' Fixed relations are used only to isolate lifecycle and extrusion behavior.
Set sketch = model.SketchManager.ActiveSketch
If sketch Is Nothing Then Fail "GET_ACTIVE_SKETCH"
model.ClearSelection2 True
Err.Clear
sketchSegments = sketch.GetSketchSegments()
If Err.Number <> 0 Or IsEmpty(sketchSegments) Then Fail "GET_RECTANGLE_SEGMENTS"
selectedCount = model.Extension.MultiSelect2(sketchSegments, False, Nothing)
If Err.Number <> 0 Or selectedCount <> 4 Then Fail "SELECT_RECTANGLE_SEGMENTS"
model.SketchAddConstraints "sgFIXED"
If Err.Number <> 0 Then Fail "FIX_RECTANGLE_SEGMENTS"

Err.Clear
sketchStatus = sketch.GetConstrainedStatus()
If Err.Number <> 0 Then Fail "GET_SKETCH_STATUS"
Log "SKETCH_STATUS=" & CStr(sketchStatus)
If sketchStatus <> swFullyConstrained Then Fail "SKETCH_NOT_FULLY_CONSTRAINED"

Set sketchFeature = sketch.GetFeature()
Err.Clear
model.SketchManager.InsertSketch True
If Err.Number <> 0 Then Fail "EXIT_SKETCH"
model.ForceRebuild3 False

Err.Clear
regions = sketch.GetSketchRegions()
If Err.Number <> 0 Or IsEmpty(regions) Then Fail "GET_SKETCH_REGIONS"
Set selectData = model.SelectionManager.CreateSelectData
selectData.Mark = 4
model.ClearSelection2 True
selectedCount = model.Extension.MultiSelect2(regions, False, selectData)
If Err.Number <> 0 Or selectedCount < 1 Then Fail "SELECT_SKETCH_REGION"

Err.Clear
Set feature = model.FeatureManager.FeatureExtrusion2(True, False, False, swEndCondBlind, swEndCondBlind, Mm(10), Mm(10), False, False, False, False, 0.01745329251994, 0.01745329251994, False, False, False, False, True, True, True, 0, 0, False)
If Err.Number <> 0 Or feature Is Nothing Then Fail "BASE_EXTRUSION"
Log "EXTRUSION_OK=True"

model.ForceRebuild3 False
resultBodyCount = BodyCount(model)
Log "BODY_COUNT=" & CStr(resultBodyCount)
If resultBodyCount <> 1 Then Fail "BODY_COUNT_NOT_ONE"

Err.Clear
saveResult = model.SaveAs3(outPart, swSaveAsCurrentVersion, swSaveAsOptionsSilent)
Log "SAVE_RETURN=" & CStr(saveResult) & "|ERROR=" & Hex(Err.Number) & " " & Err.Description
If Err.Number <> 0 Then Fail "SAVE_PART_COM_ERROR"
If Not fso.FileExists(outPart) Then Fail "SAVE_PART_FILE_MISSING"
Set savedFile = fso.GetFile(outPart)
If savedFile.Size <= 0 Then Fail "SAVE_PART_FILE_EMPTY"
Log "SAVE_OK=True|SIZE=" & CStr(savedFile.Size) & "|PATH=" & outPart

model.ViewZoomtofit2
Log "RESULT=PASS"
Log "NOTE=SolidWorks intentionally remains open for visual inspection."
