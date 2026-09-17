' SW_SCRIPT_KIND=qualification
' Qualification for coordinate/parameter-driven sketch construction without sgFIXED.

On Error Resume Next

Dim fso, scriptDir, outputDir, outputLog, libraryPath, stream
Dim app, model, sketchName, feature
Dim dimObj
Dim originalInputDimValOnCreate, createdDocTitle
Dim l1, l2, l3, l4, diag, p1, p2, p3, p4, dp1, dp2, originPoint
Dim c1, c2, c3, c4, cp1, cp2, cp3, cp4

Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
libraryPath = fso.BuildPath(fso.BuildPath(scriptDir, "lib"), "solidworks-com-driver.vbs")
If Not fso.FileExists(libraryPath) Then
  WScript.Echo "GROUP=group_00|RESULT=FAIL|API_CALL=LoadLibrary|DETAIL=missing " & libraryPath
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

outputLog = fso.BuildPath(outputDir, "solidworks_vbs_sketch_constraints.log")
If fso.FileExists(outputLog) Then fso.DeleteFile outputLog, True
DriverConfigure outputLog

Set app = DriverAttachSolidWorks(True)
If Not IsObject(app) Then DriverFail "group_00", "DriverAttachSolidWorks", "cannot attach or create SolidWorks"
originalInputDimValOnCreate = DriverGetInputDimValueDialog(app)
If Not DriverSetInputDimValueDialog(app, False) Then DriverFail "group_00", "DriverSetInputDimValueDialog", "disable dimension input dialog"
DriverRegisterInputDimValueDialogRestore app, originalInputDimValOnCreate
DriverLog "GROUP=group_00|STAGE=input_dim_dialog_disabled|ORIGINAL=" & CStr(originalInputDimValOnCreate)
Set model = DriverNewPart(app)
If model Is Nothing Then DriverFail "group_00", "DriverNewPart", "cannot create part document"
createdDocTitle = model.GetTitle()
DriverPass "group_00", "single_session=True"

DriverLog "GROUP=group_01|STAGE=select_top_plane_start"
If Not DriverSelectPlaneFallback(model, DriverTopPlaneName(), "Top Plane") Then DriverFail "group_01", "DriverSelectPlaneFallback", "top plane"
DriverLog "GROUP=group_01|STAGE=select_top_plane_done"
DriverLog "GROUP=group_01|STAGE=insert_sketch_start"
model.SketchManager.InsertSketch True
If Err.Number <> 0 Then DriverFail "group_01", "InsertSketch", "start sketch"
DriverLog "GROUP=group_01|STAGE=insert_sketch_done"

DriverLog "GROUP=group_01|STAGE=create_rectangle_start"
Set l1 = DriverCreateLineLocal(model, -30, -30, 30, -30)
Set l2 = DriverCreateLineLocal(model, 30, -30, 30, 30)
Set l3 = DriverCreateLineLocal(model, 30, 30, -30, 30)
Set l4 = DriverCreateLineLocal(model, -30, 30, -30, -30)
If l1 Is Nothing Or l2 Is Nothing Or l3 Is Nothing Or l4 Is Nothing Then DriverFail "group_01", "DriverCreateLineLocal", "rectangle"
DriverLog "GROUP=group_01|STAGE=create_rectangle_done"

DriverLog "GROUP=group_01|STAGE=rectangle_relations_start"
If Not DriverAddRelation(model, Array(l1), "sgHORIZONTAL") Then DriverFail "group_01", "DriverAddRelation", "l1 horizontal"
If Not DriverAddRelation(model, Array(l3), "sgHORIZONTAL") Then DriverFail "group_01", "DriverAddRelation", "l3 horizontal"
If Not DriverAddRelation(model, Array(l2), "sgVERTICAL") Then DriverFail "group_01", "DriverAddRelation", "l2 vertical"
If Not DriverAddRelation(model, Array(l4), "sgVERTICAL") Then DriverFail "group_01", "DriverAddRelation", "l4 vertical"
DriverLog "GROUP=group_01|STAGE=rectangle_relations_done"

DriverLog "GROUP=group_01|STAGE=rectangle_points_start"
Set p1 = DriverSegmentPoint(l1, "start")
Set p2 = DriverSegmentPoint(l1, "end")
Set p3 = DriverSegmentPoint(l2, "end")
Set p4 = DriverSegmentPoint(l3, "end")
If p1 Is Nothing Or p2 Is Nothing Or p3 Is Nothing Or p4 Is Nothing Then DriverFail "group_01", "DriverSegmentPoint", "rectangle points"
DriverLog "GROUP=group_01|STAGE=rectangle_points_done"

DriverLog "GROUP=group_01|STAGE=corner_relations_start"
If Not DriverAddRelation(model, Array(p2, DriverSegmentPoint(l2, "start")), "sgCOINCIDENT") Then DriverFail "group_01", "DriverAddRelation", "corner 1"
If Not DriverAddRelation(model, Array(p3, DriverSegmentPoint(l3, "start")), "sgCOINCIDENT") Then DriverFail "group_01", "DriverAddRelation", "corner 2"
If Not DriverAddRelation(model, Array(p4, DriverSegmentPoint(l4, "start")), "sgCOINCIDENT") Then DriverFail "group_01", "DriverAddRelation", "corner 3"
If Not DriverAddRelation(model, Array(p1, DriverSegmentPoint(l4, "end")), "sgCOINCIDENT") Then DriverFail "group_01", "DriverAddRelation", "corner 4"
DriverLog "GROUP=group_01|STAGE=corner_relations_done"

DriverLog "GROUP=group_01|STAGE=center_constraint_start"
Set diag = DriverCreateLineLocal(model, -30, -30, 30, 30)
If diag Is Nothing Then DriverFail "group_01", "DriverCreateLineLocal", "center diagonal"
If Not DriverSetConstructionGeometry(diag, True) Then DriverFail "group_01", "DriverSetConstructionGeometry", "center diagonal"
Set dp1 = DriverSegmentPoint(diag, "start")
Set dp2 = DriverSegmentPoint(diag, "end")
If dp1 Is Nothing Or dp2 Is Nothing Then DriverFail "group_01", "DriverSegmentPoint", "center diagonal"
If Not DriverAddRelation(model, Array(dp1, p1), "sgCOINCIDENT") Then DriverFail "group_01", "DriverAddRelation", "diagonal start"
If Not DriverAddRelation(model, Array(dp2, p3), "sgCOINCIDENT") Then DriverFail "group_01", "DriverAddRelation", "diagonal end"
Set originPoint = DriverSketchOriginPoint(model)
If originPoint Is Nothing Then DriverFail "group_01", "DriverSketchOriginPoint", "origin"
If Not DriverAddRelation(model, Array(originPoint, diag), "sgATMIDDLE") Then DriverFail "group_01", "DriverAddRelation", "origin midpoint"
DriverLog "GROUP=group_01|STAGE=center_constraint_done"

DriverLog "GROUP=group_01|STAGE=rectangle_dimensions_start"
Set dimObj = DriverAddHorizontalDimension(model, Array(l1), 60, 0, -38)
If dimObj Is Nothing Then DriverFail "group_01", "DriverAddHorizontalDimension", "width 60"
Set dimObj = DriverAddVerticalDimension(model, Array(l2), 60, 38, 0)
If dimObj Is Nothing Then DriverFail "group_01", "DriverAddVerticalDimension", "height 60"
DriverLog "GROUP=group_01|STAGE=rectangle_dimensions_done"

DriverLog "GROUP=group_02|STAGE=create_holes_start"
Set c1 = DriverCreateCircleLocal(model, -20, -20, 4)
Set c2 = DriverCreateCircleLocal(model, 20, -20, 4)
Set c3 = DriverCreateCircleLocal(model, -20, 20, 4)
Set c4 = DriverCreateCircleLocal(model, 20, 20, 4)
If c1 Is Nothing Or c2 Is Nothing Or c3 Is Nothing Or c4 Is Nothing Then DriverFail "group_02", "DriverCreateCircleLocal", "four holes"
DriverLog "GROUP=group_02|STAGE=create_holes_done"

DriverLog "GROUP=group_02|STAGE=hole_centers_start"
Set cp1 = DriverCenterPoint(c1)
Set cp2 = DriverCenterPoint(c2)
Set cp3 = DriverCenterPoint(c3)
Set cp4 = DriverCenterPoint(c4)
If cp1 Is Nothing Or cp2 Is Nothing Or cp3 Is Nothing Or cp4 Is Nothing Then DriverFail "group_02", "DriverCenterPoint", "hole centers"
DriverLog "GROUP=group_02|STAGE=hole_centers_done"

DriverLog "GROUP=group_02|STAGE=hole_center_relations_start"
If Not DriverAddRelation(model, Array(cp1, cp2), "sgHORIZPOINTS") Then DriverFail "group_02", "DriverAddRelation", "cp1 cp2 horizontal"
If Not DriverAddRelation(model, Array(cp3, cp4), "sgHORIZPOINTS") Then DriverFail "group_02", "DriverAddRelation", "cp3 cp4 horizontal"
If Not DriverAddRelation(model, Array(cp1, cp3), "sgVERTPOINTS") Then DriverFail "group_02", "DriverAddRelation", "cp1 cp3 vertical"
If Not DriverAddRelation(model, Array(cp2, cp4), "sgVERTPOINTS") Then DriverFail "group_02", "DriverAddRelation", "cp2 cp4 vertical"
DriverLog "GROUP=group_02|STAGE=hole_center_relations_done"

DriverLog "GROUP=group_02|STAGE=hole_dimensions_start"
Set dimObj = DriverAddDiameterDimension(model, Array(c1), 8, -25, -25)
If dimObj Is Nothing Then DriverFail "group_02", "DriverAddDiameterDimension", "hole diameter 1"
If Not DriverAddRelation(model, Array(c1, c2), "sgEQUAL") Then DriverFail "group_02", "DriverAddRelation", "equal c1 c2"
If Not DriverAddRelation(model, Array(c1, c3), "sgEQUAL") Then DriverFail "group_02", "DriverAddRelation", "equal c1 c3"
If Not DriverAddRelation(model, Array(c1, c4), "sgEQUAL") Then DriverFail "group_02", "DriverAddRelation", "equal c1 c4"

Set dimObj = DriverAddHorizontalDimension(model, Array(cp1, cp2), 40, 0, -28)
If dimObj Is Nothing Then DriverFail "group_02", "DriverAddHorizontalDimension", "hole x pitch"
Set dimObj = DriverAddVerticalDimension(model, Array(cp1, cp3), 40, -28, 0)
If dimObj Is Nothing Then DriverFail "group_02", "DriverAddVerticalDimension", "hole y pitch"
Set dimObj = DriverAddHorizontalDimension(model, Array(cp1, p1), 10, -24, -34)
If dimObj Is Nothing Then DriverFail "group_02", "DriverAddHorizontalDimension", "hole from corner x"
Set dimObj = DriverAddVerticalDimension(model, Array(cp1, p1), 10, -34, -24)
If dimObj Is Nothing Then DriverFail "group_02", "DriverAddVerticalDimension", "hole from corner y"
DriverLog "GROUP=group_02|STAGE=hole_dimensions_done"

sketchName = "qualification_constraints_sketch"
DriverLog "GROUP=group_03|STAGE=close_sketch_start"
If Not DriverCloseCoordinateSketchAndRename(model, sketchName) Then DriverFail "group_03", "DriverCloseCoordinateSketchAndRename", sketchName
If Not DriverSelectAllSketchRegions(model, sketchName) Then DriverFail "group_03", "DriverSelectAllSketchRegions", "coordinate sketch regions"
DriverPass "group_03", "sketch=" & sketchName & "|mode=coordinate_driven"
If Not DriverSetInputDimValueDialog(app, originalInputDimValOnCreate) Then DriverFail "group_99", "DriverSetInputDimValueDialog", "restore dimension input dialog"
DriverClearInputDimValueDialogRestore
DriverPass "group_99", "input_dim_dialog_restored=" & CStr(originalInputDimValOnCreate)
If Len(createdDocTitle) > 0 Then
  app.CloseDoc createdDocTitle
  DriverPass "group_99", "closed_temp_doc=True"
End If
DriverLog "QUALIFICATION_PASS=True"
