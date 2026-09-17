' SW_SCRIPT_KIND=qualification
' Visible, one-process qualification for the shared SolidWorks VBS driver.
' This script intentionally uses sgFIXED only inside qualification geometry.

On Error Resume Next

Dim fso, scriptDir, outputDir, outputPart, outputStep, outputLog, outputPass, libraryPath
Dim stream, app, model, feature, sketchName, planeName

Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
libraryPath = fso.BuildPath(fso.BuildPath(scriptDir, "lib"), "solidworks-com-driver.vbs")
If Not fso.FileExists(libraryPath) Then
  WScript.Echo "GROUP=start|RESULT=FAIL|API_CALL=LoadLibrary|DETAIL=missing " & libraryPath
  WScript.Quit 1
End If
Set stream = fso.OpenTextFile(libraryPath, 1)
ExecuteGlobal stream.ReadAll
stream.Close

If WScript.Arguments.Count > 0 Then
  outputDir = fso.GetAbsolutePathName(WScript.Arguments.Item(0))
Else
  outputDir = fso.BuildPath(scriptDir, "qualification-output")
End If
If Not fso.FolderExists(outputDir) Then fso.CreateFolder outputDir

outputPart = fso.BuildPath(outputDir, "solidworks_vbs_driver_qualification.SLDPRT")
outputStep = fso.BuildPath(outputDir, "solidworks_vbs_driver_qualification.STEP")
outputLog = fso.BuildPath(outputDir, "solidworks_vbs_driver_qualification.log")
outputPass = fso.BuildPath(outputDir, "solidworks_vbs_driver_qualification.pass")
If fso.FileExists(outputPart) Then fso.DeleteFile outputPart, True
If fso.FileExists(outputStep) Then fso.DeleteFile outputStep, True
If fso.FileExists(outputLog) Then fso.DeleteFile outputLog, True
If fso.FileExists(outputPass) Then fso.DeleteFile outputPass, True
DriverConfigure outputLog

Set app = DriverAttachSolidWorks(True)
If Not IsObject(app) Then DriverFail "start", "DriverAttachSolidWorks", "cannot attach or create SolidWorks"
Err.Clear
app.CloseDoc fso.GetFileName(outputPart)
Err.Clear
Set model = DriverNewPart(app)
If model Is Nothing Then DriverFail "start", "DriverNewPart", "cannot create part document"
DriverPass "start", "single_session=True"

' Group 1: base extrusion.
If Not DriverSelectPlaneFallback(model, DriverTopPlaneName(), "Top Plane") Then DriverFail "base", "DriverSelectPlaneFallback", "top plane"
model.SketchManager.InsertSketch True
DriverLineLocal model, -30, -30, 30, -30
DriverLineLocal model, 30, -30, 30, 30
DriverLineLocal model, 30, 30, -30, 30
DriverLineLocal model, -30, 30, -30, -30
If Not DriverFixActiveSketchForQualification(model) Then DriverFail "base", "DriverFixActiveSketchForQualification", "base sketch"
sketchName = "qualification_base_sketch"
If Not DriverCloseSketchAndRename(model, sketchName) Then DriverFail "base", "DriverCloseSketchAndRename", sketchName
If Not DriverSelectAllSketchRegions(model, sketchName) Then DriverFail "base", "DriverSelectAllSketchRegions", sketchName
Set feature = DriverBossExtrude(model, 10, True)
If feature Is Nothing Then DriverFail "base", "DriverBossExtrude", "depth=10"
If Not DriverSaveCheckpoint(model, outputPart) Then DriverFail "base", "DriverSaveCheckpoint", outputPart
DriverPass "base", "body_count=" & CStr(DriverBodyCount(model))

' Group 2: four through holes on the same Top Plane coordinates as the base.
If Not DriverSelectPlaneFallback(model, DriverTopPlaneName(), "Top Plane") Then DriverFail "base_holes", "DriverSelectPlaneFallback", "top plane"
model.SketchManager.InsertSketch True
DriverCircleLocal model, -20, -20, 4
DriverCircleLocal model, 20, -20, 4
DriverCircleLocal model, -20, 20, 4
DriverCircleLocal model, 20, 20, 4
If Not DriverFixActiveSketchForQualification(model) Then DriverFail "base_holes", "DriverFixActiveSketchForQualification", "four holes"
sketchName = "qualification_base_holes_sketch"
If Not DriverCloseSketchAndRename(model, sketchName) Then DriverFail "base_holes", "DriverCloseSketchAndRename", sketchName
If Not DriverSelectAllSketchRegions(model, sketchName) Then DriverFail "base_holes", "DriverSelectAllSketchRegions", sketchName
Set feature = DriverCutThroughAll(model)
If feature Is Nothing Then DriverFail "base_holes", "DriverCutThroughAll", "4x diameter 8"
If Not DriverSaveCheckpoint(model, outputPart) Then DriverFail "base_holes", "DriverSaveCheckpoint", outputPart
DriverPass "base_holes", "body_count=" & CStr(DriverBodyCount(model))

' Group 3: circular sweep and sweep cut.
If Not DriverSelectPlaneFallback(model, DriverFrontPlaneName(), "Front Plane") Then DriverFail "sweep", "DriverSelectPlaneFallback", "front plane"
model.SketchManager.InsertSketch True
DriverLineLocal model, 0, 10, 0, 60
If Not DriverFixActiveSketchPointsForQualification(model) Then DriverFail "sweep", "DriverFixActiveSketchPointsForQualification", "path"
sketchName = "qualification_sweep_path"
If Not DriverCloseSketchAndRename(model, sketchName) Then DriverFail "sweep", "DriverCloseSketchAndRename", sketchName
Set feature = DriverSweepBossCircular(model, sketchName, 20)
If feature Is Nothing Then DriverFail "sweep", "DriverSweepBossCircular", "diameter=20"
Set feature = DriverSweepCutCircular(model, sketchName, 12)
If feature Is Nothing Then DriverFail "sweep", "DriverSweepCutCircular", "diameter=12"
If Not DriverSaveCheckpoint(model, outputPart) Then DriverFail "sweep", "DriverSaveCheckpoint", outputPart
DriverPass "sweep", "body_count=" & CStr(DriverBodyCount(model))

' Group 4: end plane, local face-plane sketch, flange boss, and through bore.
planeName = "qualification_end_plane"
If Not DriverCreateFixedPlane(model, planeName, 0, 50, 0, 20, 0, 0, 0, 0, 20) Then DriverFail "end_face", "DriverCreateFixedPlane", planeName
If Not DriverSelectPlaneByName(model, planeName) Then DriverFail "end_face", "DriverSelectPlaneByName", planeName
model.SketchManager.InsertSketch True
DriverCircleLocal model, 0, 0, 15
If Not DriverFixActiveSketchForQualification(model) Then DriverFail "end_face", "DriverFixActiveSketchForQualification", "flange outer"
sketchName = "qualification_end_flange_sketch"
If Not DriverCloseSketchAndRename(model, sketchName) Then DriverFail "end_face", "DriverCloseSketchAndRename", sketchName
If Not DriverSelectAllSketchRegions(model, sketchName) Then DriverFail "end_face", "DriverSelectAllSketchRegions", sketchName
Set feature = DriverBossExtrude(model, 6, True)
If feature Is Nothing Then DriverFail "end_face", "DriverBossExtrude", "flange depth=6"

If Not DriverSelectPlaneByName(model, planeName) Then DriverFail "end_face", "DriverSelectPlaneByName", planeName
model.SketchManager.InsertSketch True
DriverCircleLocal model, 0, 0, 6
If Not DriverFixActiveSketchForQualification(model) Then DriverFail "end_face", "DriverFixActiveSketchForQualification", "flange bore"
sketchName = "qualification_end_bore_sketch"
If Not DriverCloseSketchAndRename(model, sketchName) Then DriverFail "end_face", "DriverCloseSketchAndRename", sketchName
If Not DriverSelectAllSketchRegions(model, sketchName) Then DriverFail "end_face", "DriverSelectAllSketchRegions", sketchName
Set feature = DriverCutThroughAll(model)
If feature Is Nothing Then DriverFail "end_face", "DriverCutThroughAll", "flange bore diameter=12"
If Not DriverSaveCheckpoint(model, outputPart) Then DriverFail "end_face", "DriverSaveCheckpoint", outputPart
DriverPass "end_face", "body_count=" & CStr(DriverBodyCount(model))

' Group 5: final rebuild, body count, and neutral export.
model.ForceRebuild3 False
If DriverBodyCount(model) <> 1 Then DriverFail "verify", "DriverBodyCount", "expected=1 actual=" & CStr(DriverBodyCount(model))
If Not DriverSaveCheckpoint(model, outputPart) Then DriverFail "verify", "DriverSaveCheckpoint", outputPart
If Not DriverExportStep(model, outputStep) Then DriverFail "verify", "DriverExportStep", outputStep
model.ViewZoomtofit2
DriverPass "verify", "body_count=1|part=" & outputPart & "|step=" & outputStep
Set stream = fso.CreateTextFile(outputPass, True)
stream.WriteLine "QUALIFICATION_PASS=True"
stream.Close
DriverLog "QUALIFICATION_PASS=True"
