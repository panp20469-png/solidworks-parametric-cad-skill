' SW_DRIVER_LIBRARY_VERSION=2
' Shared late-bound SolidWorks COM helpers. Keep this file ASCII-only.

Const swdSaveAsCurrentVersion = 0
Const swdSaveAsOptionsSilent = 1
Const swdEndCondBlind = 0
Const swdEndCondThroughAll = 1
Const swdFullyConstrained = 3
Const swdInputDimValOnCreate = 10
Const swdPi = 3.141592653589793

Dim swdFso, swdLogPath, swdFeatureAliases
Dim swdInputDimDialogRestoreKnown, swdInputDimDialogOriginalValue, swdInputDimDialogRestoreApp
Set swdFso = CreateObject("Scripting.FileSystemObject")
Set swdFeatureAliases = CreateObject("Scripting.Dictionary")
swdLogPath = ""
swdInputDimDialogRestoreKnown = False
Set swdInputDimDialogRestoreApp = Nothing

Sub DriverConfigure(ByVal logPath)
  swdLogPath = logPath
End Sub

Sub DriverLog(ByVal text)
  Dim stream
  WScript.Echo text
  If Len(swdLogPath) = 0 Then Exit Sub
  Set stream = swdFso.OpenTextFile(swdLogPath, 8, True)
  stream.WriteLine text
  stream.Close
End Sub

Sub DriverPass(ByVal groupName, ByVal detail)
  DriverLog "GROUP=" & groupName & "|RESULT=PASS|" & detail
End Sub

Sub DriverFail(ByVal groupName, ByVal apiCall, ByVal detail)
  DriverLog "GROUP=" & groupName & "|RESULT=FAIL|API_CALL=" & apiCall & "|DETAIL=" & detail & "|ERROR=" & Hex(Err.Number) & " " & Err.Description
  DriverFailureCleanup
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

Function DriverTopPlaneName()
  DriverTopPlaneName = U(Array(&H4E0A, &H89C6, &H57FA, &H51C6, &H9762))
End Function

Function DriverFrontPlaneName()
  DriverFrontPlaneName = U(Array(&H524D, &H89C6, &H57FA, &H51C6, &H9762))
End Function

Function DriverOriginName()
  DriverOriginName = U(Array(&H539F, &H70B9))
End Function

Function DriverAttachSolidWorks(ByVal visible)
  Dim app
  On Error Resume Next
  Err.Clear
  Set app = GetObject(, "SldWorks.Application")
  WScript.Echo "ATTACH_RUNNING_SERVER=" & CStr(IsObject(app)) & "|ERROR=" & Hex(Err.Number) & " " & Err.Description
  If Err.Number <> 0 Or Not IsObject(app) Then
    Err.Clear
    Set app = CreateObject("SldWorks.Application")
    WScript.Echo "ATTACH_CREATE_SERVER=" & CStr(IsObject(app)) & "|ERROR=" & Hex(Err.Number) & " " & Err.Description
  End If
  If Err.Number <> 0 Or Not IsObject(app) Then
    Err.Clear
    Exit Function
  End If
  Err.Clear
  app.Visible = visible
  app.UserControl = True
  Err.Clear
  Set DriverAttachSolidWorks = app
  WScript.Echo "ATTACH_RETURN_SERVER=" & CStr(IsObject(DriverAttachSolidWorks))
End Function

Function DriverGetInputDimValueDialog(ByVal app)
  On Error Resume Next
  DriverGetInputDimValueDialog = False
  If Not IsObject(app) Then Exit Function
  Err.Clear
  DriverGetInputDimValueDialog = CBool(app.GetUserPreferenceToggle(swdInputDimValOnCreate))
  If Err.Number <> 0 Then
    Err.Clear
    DriverGetInputDimValueDialog = False
  End If
End Function

Function DriverSetInputDimValueDialog(ByVal app, ByVal enabled)
  On Error Resume Next
  DriverSetInputDimValueDialog = False
  If Not IsObject(app) Then Exit Function
  Err.Clear
  app.SetUserPreferenceToggle swdInputDimValOnCreate, CBool(enabled)
  DriverSetInputDimValueDialog = (Err.Number = 0)
  Err.Clear
End Function

Sub DriverRegisterInputDimValueDialogRestore(ByVal app, ByVal originalValue)
  On Error Resume Next
  If Not IsObject(app) Then Exit Sub
  Set swdInputDimDialogRestoreApp = app
  swdInputDimDialogOriginalValue = CBool(originalValue)
  swdInputDimDialogRestoreKnown = True
End Sub

Sub DriverClearInputDimValueDialogRestore()
  On Error Resume Next
  swdInputDimDialogRestoreKnown = False
  Set swdInputDimDialogRestoreApp = Nothing
End Sub

Sub DriverFailureCleanup()
  On Error Resume Next
  If swdInputDimDialogRestoreKnown And IsObject(swdInputDimDialogRestoreApp) Then
    swdInputDimDialogRestoreApp.SetUserPreferenceToggle swdInputDimValOnCreate, swdInputDimDialogOriginalValue
  End If
End Sub

Function DriverPartTemplate(ByVal app)
  Dim path
  On Error Resume Next
  path = ""
  Err.Clear
  path = app.GetUserPreferenceStringValue(8)
  Err.Clear
  If Len(path) > 0 And swdFso.FileExists(path) Then
    DriverPartTemplate = path
    Exit Function
  End If
  path = "C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2024\templates\gb_part.prtdot"
  If swdFso.FileExists(path) Then
    DriverPartTemplate = path
    Exit Function
  End If
  path = "C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2024\templates\Part.prtdot"
  If swdFso.FileExists(path) Then
    DriverPartTemplate = path
    Exit Function
  End If
  DriverPartTemplate = ""
End Function

Function DriverNewPart(ByVal app)
  Dim templatePath, model
  On Error Resume Next
  templatePath = DriverPartTemplate(app)
  If Len(templatePath) = 0 Then
    Set DriverNewPart = Nothing
    Exit Function
  End If
  Err.Clear
  Set model = app.NewDocument(templatePath, 0, 0, 0)
  If Err.Number <> 0 Then
    Err.Clear
    Set DriverNewPart = Nothing
  Else
    Set DriverNewPart = model
  End If
End Function

Function DriverOpenPart(ByVal app, ByVal path)
  Dim model
  On Error Resume Next
  Set model = Nothing
  If Not swdFso.FileExists(path) Then
    Set DriverOpenPart = Nothing
    Exit Function
  End If
  Err.Clear
  Set model = app.GetOpenDocumentByName(path)
  If model Is Nothing Then Set model = app.OpenDoc(path, 1)
  If Err.Number <> 0 Then
    Err.Clear
    Set DriverOpenPart = Nothing
  Else
    Set DriverOpenPart = model
  End If
End Function

Function DriverSelectPlaneFallback(ByVal model, ByVal chineseName, ByVal englishName)
  Dim selected
  On Error Resume Next
  model.ClearSelection2 True
  Err.Clear
  selected = model.Extension.SelectByID2(chineseName, "PLANE", 0, 0, 0, False, 0, Nothing, 0)
  If Not selected Then
    model.ClearSelection2 True
    Err.Clear
    selected = model.Extension.SelectByID2(englishName, "PLANE", 0, 0, 0, False, 0, Nothing, 0)
  End If
  Err.Clear
  DriverSelectPlaneFallback = selected
End Function

Function DriverSelectPlaneByName(ByVal model, ByVal planeName)
  Dim actualName
  On Error Resume Next
  actualName = DriverActualFeatureName(planeName)
  model.ClearSelection2 True
  Err.Clear
  DriverSelectPlaneByName = model.Extension.SelectByID2(actualName, "PLANE", 0, 0, 0, False, 0, Nothing, 0)
  Err.Clear
End Function

Function DriverActualFeatureName(ByVal featureName)
  If swdFeatureAliases.Exists(CStr(featureName)) Then
    DriverActualFeatureName = swdFeatureAliases(CStr(featureName))
  Else
    DriverActualFeatureName = featureName
  End If
End Function

Function DriverFeatureByName(ByVal model, ByVal featureName)
  Dim feature, actualName
  On Error Resume Next
  actualName = DriverActualFeatureName(featureName)
  Set feature = model.FeatureByName(actualName)
  If feature Is Nothing And actualName <> featureName Then
    Set feature = model.FeatureByName(featureName)
  End If
  Set DriverFeatureByName = feature
End Function

Sub DriverRenameLastFeature(ByVal model, ByVal featureName)
  Dim feature
  On Error Resume Next
  Set feature = model.FeatureByPositionReverse(0)
  If Not feature Is Nothing Then
    If swdFeatureAliases.Exists(CStr(featureName)) Then
      swdFeatureAliases(CStr(featureName)) = feature.Name
    Else
      swdFeatureAliases.Add CStr(featureName), feature.Name
    End If
    DriverLog "FEATURE_ALIAS=" & CStr(featureName) & "|ACTUAL=" & feature.Name
  End If
End Sub

Function DriverAliasNewestFeatureOfType(ByVal model, ByVal featureName, ByVal typeName)
  Dim feature, candidate, actualType
  On Error Resume Next
  Set candidate = Nothing
  Set feature = model.FirstFeature
  Do While Not feature Is Nothing
    actualType = feature.GetTypeName2()
    If Err.Number = 0 Then
      If CStr(actualType) = CStr(typeName) Then Set candidate = feature
    Else
      Err.Clear
    End If
    Set feature = feature.GetNextFeature
  Loop
  If candidate Is Nothing Then
    DriverAliasNewestFeatureOfType = False
    Exit Function
  End If
  If swdFeatureAliases.Exists(CStr(featureName)) Then
    swdFeatureAliases(CStr(featureName)) = candidate.Name
  Else
    swdFeatureAliases.Add CStr(featureName), candidate.Name
  End If
  DriverLog "FEATURE_ALIAS=" & CStr(featureName) & "|ACTUAL=" & candidate.Name & "|TYPE=" & CStr(typeName)
  DriverAliasNewestFeatureOfType = True
End Function

Function DriverFeatureExists(ByVal model, ByVal featureName)
  Dim feature
  On Error Resume Next
  Set feature = DriverFeatureByName(model, featureName)
  DriverFeatureExists = Not feature Is Nothing
End Function

Function DriverSelectSketchByName(ByVal model, ByVal sketchName, ByVal mark)
  Dim actualName
  On Error Resume Next
  actualName = DriverActualFeatureName(sketchName)
  model.ClearSelection2 True
  Err.Clear
  DriverSelectSketchByName = model.Extension.SelectByID2(actualName, "SKETCH", 0, 0, 0, False, mark, Nothing, 0)
  Err.Clear
End Function

Function DriverBodyCount(ByVal model)
  Dim bodies
  On Error Resume Next
  Err.Clear
  bodies = model.GetBodies2(0, False)
  If Err.Number <> 0 Then
    Err.Clear
    DriverBodyCount = -1
  ElseIf IsEmpty(bodies) Then
    DriverBodyCount = 0
  ElseIf IsArray(bodies) Then
    DriverBodyCount = UBound(bodies) - LBound(bodies) + 1
  Else
    DriverBodyCount = 1
  End If
End Function

Function DriverSaveCheckpoint(ByVal model, ByVal path)
  Dim saveResult, savedFile
  On Error Resume Next
  Err.Clear
  saveResult = model.SaveAs3(path, swdSaveAsCurrentVersion, swdSaveAsOptionsSilent)
  If Err.Number <> 0 Or Not swdFso.FileExists(path) Then
    Err.Clear
    DriverSaveCheckpoint = False
    Exit Function
  End If
  Set savedFile = swdFso.GetFile(path)
  DriverSaveCheckpoint = (savedFile.Size > 0)
  Err.Clear
End Function

Function DriverExportStep(ByVal model, ByVal path)
  On Error Resume Next
  Err.Clear
  model.SaveAs3 path, swdSaveAsCurrentVersion, swdSaveAsOptionsSilent
  DriverExportStep = (Err.Number = 0 And swdFso.FileExists(path))
  Err.Clear
End Function

Function DriverActiveSketch(ByVal model)
  On Error Resume Next
  Set DriverActiveSketch = model.SketchManager.ActiveSketch
End Function

Function DriverRad(ByVal degreeValue)
  DriverRad = CDbl(degreeValue) * swdPi / 180.0
End Function

Function DriverSelectObjects(ByVal model, ByVal objects)
  Dim i, selectedCount, selectedOk
  On Error Resume Next
  model.ClearSelection2 True
  Err.Clear
  selectedCount = model.Extension.MultiSelect2(objects, False, Nothing)
  If Err.Number = 0 And selectedCount > 0 Then
    DriverSelectObjects = True
    Exit Function
  End If

  Err.Clear
  selectedCount = 0
  For i = 0 To UBound(objects)
    selectedOk = False
    If IsObject(objects(i)) Then selectedOk = objects(i).Select4((i > 0), Nothing)
    If Err.Number <> 0 Or Not selectedOk Then
      Err.Clear
      model.ClearSelection2 True
      DriverSelectObjects = False
      Exit Function
    End If
    selectedCount = selectedCount + 1
  Next
  DriverSelectObjects = (selectedCount = UBound(objects) - LBound(objects) + 1)
  Err.Clear
End Function

Function DriverAddRelation(ByVal model, ByVal objects, ByVal relationName)
  On Error Resume Next
  If Not DriverSelectObjects(model, objects) Then
    DriverAddRelation = False
    Exit Function
  End If
  Err.Clear
  model.SketchAddConstraints relationName
  DriverAddRelation = (Err.Number = 0)
  Err.Clear
End Function

Function DriverSetDisplayDimensionValue(ByVal displayDimension, ByVal systemValue)
  Dim dimension, setErrors
  On Error Resume Next
  DriverSetDisplayDimensionValue = False
  If Not IsObject(displayDimension) Then Exit Function

  Err.Clear
  displayDimension.SystemValue = systemValue
  If Err.Number = 0 Then
    DriverSetDisplayDimensionValue = True
    Exit Function
  End If

  Err.Clear
  Set dimension = displayDimension.GetDimension2(0)
  If Err.Number = 0 And IsObject(dimension) Then
    Err.Clear
    setErrors = dimension.SetSystemValue3(systemValue, 1, Empty)
    If Err.Number = 0 Then
      DriverSetDisplayDimensionValue = True
    Else
      Err.Clear
      dimension.SystemValue = systemValue
      DriverSetDisplayDimensionValue = (Err.Number = 0)
    End If
  End If
  Err.Clear
End Function

Function DriverAddHorizontalDimension(ByVal model, ByVal objects, ByVal valueMm, ByVal xMm, ByVal yMm)
  Dim displayDimension
  On Error Resume Next
  If Not DriverSelectObjects(model, objects) Then
    Set DriverAddHorizontalDimension = Nothing
    Exit Function
  End If
  Err.Clear
  Set displayDimension = model.AddHorizontalDimension2(Mm(xMm), Mm(yMm), 0)
  If Err.Number <> 0 Or Not IsObject(displayDimension) Then
    Err.Clear
    Set DriverAddHorizontalDimension = Nothing
    Exit Function
  End If
  If Not DriverSetDisplayDimensionValue(displayDimension, Mm(valueMm)) Then
    Set DriverAddHorizontalDimension = Nothing
    Exit Function
  End If
  Set DriverAddHorizontalDimension = displayDimension
End Function

Function DriverAddVerticalDimension(ByVal model, ByVal objects, ByVal valueMm, ByVal xMm, ByVal yMm)
  Dim displayDimension
  On Error Resume Next
  If Not DriverSelectObjects(model, objects) Then
    Set DriverAddVerticalDimension = Nothing
    Exit Function
  End If
  Err.Clear
  Set displayDimension = model.AddVerticalDimension2(Mm(xMm), Mm(yMm), 0)
  If Err.Number <> 0 Or Not IsObject(displayDimension) Then
    Err.Clear
    Set DriverAddVerticalDimension = Nothing
    Exit Function
  End If
  If Not DriverSetDisplayDimensionValue(displayDimension, Mm(valueMm)) Then
    Set DriverAddVerticalDimension = Nothing
    Exit Function
  End If
  Set DriverAddVerticalDimension = displayDimension
End Function

Function DriverAddDiameterDimension(ByVal model, ByVal objects, ByVal valueMm, ByVal xMm, ByVal yMm)
  Dim displayDimension
  On Error Resume Next
  If Not DriverSelectObjects(model, objects) Then
    Set DriverAddDiameterDimension = Nothing
    Exit Function
  End If
  Err.Clear
  Set displayDimension = model.AddDiameterDimension2(Mm(xMm), Mm(yMm), 0)
  If Err.Number <> 0 Or Not IsObject(displayDimension) Then
    Err.Clear
    Set DriverAddDiameterDimension = Nothing
    Exit Function
  End If
  If Not DriverSetDisplayDimensionValue(displayDimension, Mm(valueMm)) Then
    Set DriverAddDiameterDimension = Nothing
    Exit Function
  End If
  Set DriverAddDiameterDimension = displayDimension
End Function

Function DriverAddDimension(ByVal model, ByVal objects, ByVal valueMm, ByVal xMm, ByVal yMm)
  Dim displayDimension
  On Error Resume Next
  If Not DriverSelectObjects(model, objects) Then
    Set DriverAddDimension = Nothing
    Exit Function
  End If
  Err.Clear
  Set displayDimension = model.AddDimension2(Mm(xMm), Mm(yMm), 0)
  If Err.Number <> 0 Or Not IsObject(displayDimension) Then
    Err.Clear
    Set DriverAddDimension = Nothing
    Exit Function
  End If
  If Not DriverSetDisplayDimensionValue(displayDimension, Mm(valueMm)) Then
    Set DriverAddDimension = Nothing
    Exit Function
  End If
  Set DriverAddDimension = displayDimension
End Function

Function DriverAddAngleDimension(ByVal model, ByVal objects, ByVal valueDeg, ByVal xMm, ByVal yMm)
  Dim displayDimension
  On Error Resume Next
  If Not DriverSelectObjects(model, objects) Then
    Set DriverAddAngleDimension = Nothing
    Exit Function
  End If
  Err.Clear
  Set displayDimension = model.AddDimension2(Mm(xMm), Mm(yMm), 0)
  If Err.Number <> 0 Or Not IsObject(displayDimension) Then
    Err.Clear
    Set DriverAddAngleDimension = Nothing
    Exit Function
  End If
  If Not DriverSetDisplayDimensionValue(displayDimension, DriverRad(valueDeg)) Then
    Set DriverAddAngleDimension = Nothing
    Exit Function
  End If
  Set DriverAddAngleDimension = displayDimension
End Function

Function DriverSegmentPoint(ByVal segment, ByVal endpointName)
  On Error Resume Next
  If LCase(endpointName) = "start" Then
    Set DriverSegmentPoint = segment.GetStartPoint2()
  Else
    Set DriverSegmentPoint = segment.GetEndPoint2()
  End If
  If Err.Number <> 0 Then
    Err.Clear
    Set DriverSegmentPoint = Nothing
  End If
End Function

Function DriverCenterPoint(ByVal sketchEntity)
  On Error Resume Next
  Set DriverCenterPoint = sketchEntity.GetCenterPoint2()
  If Err.Number <> 0 Then
    Err.Clear
    Set DriverCenterPoint = Nothing
  End If
End Function

Function DriverSketchOriginPoint(ByVal model)
  Dim selected
  On Error Resume Next
  model.ClearSelection2 True
  Err.Clear
  selected = model.Extension.SelectByID2("Point1@Origin", "EXTSKETCHPOINT", 0, 0, 0, False, 0, Nothing, 0)
  If Err.Number <> 0 Or Not selected Then
    Err.Clear
    model.ClearSelection2 True
    selected = model.Extension.SelectByID2("Point1@" & DriverOriginName(), "EXTSKETCHPOINT", 0, 0, 0, False, 0, Nothing, 0)
  End If
  If Err.Number <> 0 Or Not selected Then
    Err.Clear
    model.ClearSelection2 True
    selected = model.Extension.SelectByID2("", "EXTSKETCHPOINT", 0, 0, 0, False, 0, Nothing, 0)
  End If
  If Err.Number <> 0 Or Not selected Then
    Err.Clear
    model.ClearSelection2 True
    selected = model.Extension.SelectByID2(DriverOriginName(), "EXTSKETCHPOINT", 0, 0, 0, False, 0, Nothing, 0)
  End If
  If Err.Number <> 0 Or Not selected Then
    Err.Clear
    Set DriverSketchOriginPoint = Nothing
    Exit Function
  End If
  Set DriverSketchOriginPoint = model.SelectionManager.GetSelectedObject6(1, -1)
  model.ClearSelection2 True
  If Err.Number <> 0 Then
    Err.Clear
    Set DriverSketchOriginPoint = Nothing
  End If
End Function

Function DriverSetConstructionGeometry(ByVal sketchSegment, ByVal isConstruction)
  On Error Resume Next
  DriverSetConstructionGeometry = False
  If Not IsObject(sketchSegment) Then Exit Function
  Err.Clear
  sketchSegment.ConstructionGeometry = isConstruction
  DriverSetConstructionGeometry = (Err.Number = 0)
  Err.Clear
End Function

Function DriverFixActiveSketchForQualification(ByVal model)
  Dim sketch, segments, selectedCount, status
  On Error Resume Next
  Set sketch = DriverActiveSketch(model)
  If sketch Is Nothing Then
    DriverFixActiveSketchForQualification = False
    Exit Function
  End If
  Err.Clear
  segments = sketch.GetSketchSegments()
  If Err.Number <> 0 Or IsEmpty(segments) Then
    DriverLog "QUALIFY_SKETCH_FIX=segments_error|ERROR=" & Hex(Err.Number) & " " & Err.Description
    Err.Clear
    DriverFixActiveSketchForQualification = False
    Exit Function
  End If
  model.ClearSelection2 True
  selectedCount = model.Extension.MultiSelect2(segments, False, Nothing)
  DriverLog "QUALIFY_SKETCH_FIX=selected|COUNT=" & CStr(selectedCount)
  If selectedCount <= 0 Then
    DriverFixActiveSketchForQualification = False
    Exit Function
  End If
  Err.Clear
  model.SketchAddConstraints "sgFIXED"
  If Err.Number <> 0 Then
    Err.Clear
    DriverFixActiveSketchForQualification = False
    Exit Function
  End If
  status = sketch.GetConstrainedStatus()
  DriverLog "QUALIFY_SKETCH_FIX=status|VALUE=" & CStr(status) & "|ERROR=" & Hex(Err.Number) & " " & Err.Description
  DriverFixActiveSketchForQualification = (Err.Number = 0 And status = swdFullyConstrained)
  Err.Clear
End Function

Function DriverFixActiveSketchPointsForQualification(ByVal model)
    On Error Resume Next
    DriverFixActiveSketchPointsForQualification = False

    Dim sketch
    Set sketch = model.SketchManager.ActiveSketch
    If Not IsObject(sketch) Then Exit Function

    Dim points
    points = sketch.GetSketchPoints2()
    If Err.Number <> 0 Or Not IsArray(points) Then
        DriverLog "QUALIFY_POINT_FIX=points|ERROR=" & Err.Number
        Err.Clear
        Exit Function
    End If

    model.ClearSelection2 True

    Dim selectedCount
    selectedCount = model.Extension.MultiSelect2(points, False, Nothing)
    DriverLog "QUALIFY_POINT_FIX=selected|COUNT=" & selectedCount
    If Err.Number <> 0 Or selectedCount <= 0 Then
        DriverLog "QUALIFY_POINT_FIX=select|ERROR=" & Err.Number
        Err.Clear
        Exit Function
    End If

    model.SketchAddConstraints "sgFIXED"
    If Err.Number <> 0 Then
        DriverLog "QUALIFY_POINT_FIX=constraint|ERROR=" & Err.Number
        Err.Clear
        Exit Function
    End If

    Dim status
    status = sketch.GetConstrainedStatus()
    DriverLog "QUALIFY_POINT_FIX=status|VALUE=" & status & "|ERROR=" & Err.Number
    If Err.Number <> 0 Then
        Err.Clear
        Exit Function
    End If

    DriverFixActiveSketchPointsForQualification = (status = 3)
End Function

Function DriverRequireFullyDefinedSketch(ByVal model, ByVal sketchName)
  Dim sketchFeature, sketch, status
  On Error Resume Next
  Set sketchFeature = DriverFeatureByName(model, sketchName)
  If sketchFeature Is Nothing Then
    DriverRequireFullyDefinedSketch = False
    Exit Function
  End If
  Set sketch = sketchFeature.GetSpecificFeature2()
  If sketch Is Nothing Then
    DriverRequireFullyDefinedSketch = False
    Exit Function
  End If
  Err.Clear
  status = sketch.GetConstrainedStatus()
  DriverLog "SKETCH_STATUS=" & sketchName & "|" & CStr(status)
  DriverRequireFullyDefinedSketch = (Err.Number = 0 And status = swdFullyConstrained)
  Err.Clear
End Function

Function DriverCloseSketchAndRename(ByVal model, ByVal sketchName)
  On Error Resume Next
  Err.Clear
  model.SketchManager.InsertSketch True
  If Err.Number <> 0 Then
    Err.Clear
    DriverCloseSketchAndRename = False
    Exit Function
  End If
  DriverRenameLastFeature model, sketchName
  DriverCloseSketchAndRename = DriverRequireFullyDefinedSketch(model, sketchName)
End Function

Function DriverCloseCoordinateSketchAndRename(ByVal model, ByVal sketchName)
  Dim sketchFeature, sketch, status
  On Error Resume Next
  Err.Clear
  model.SketchManager.InsertSketch True
  If Err.Number <> 0 Then
    Err.Clear
    DriverCloseCoordinateSketchAndRename = False
    Exit Function
  End If
  DriverRenameLastFeature model, sketchName
  Set sketchFeature = DriverFeatureByName(model, sketchName)
  If sketchFeature Is Nothing Then
    DriverCloseCoordinateSketchAndRename = False
    Exit Function
  End If
  Set sketch = sketchFeature.GetSpecificFeature2()
  If sketch Is Nothing Then
    DriverCloseCoordinateSketchAndRename = False
    Exit Function
  End If
  Err.Clear
  status = sketch.GetConstrainedStatus()
  DriverLog "SKETCH_STATUS=" & sketchName & "|" & CStr(status) & "|MODE=coordinate_driven"
  DriverCloseCoordinateSketchAndRename = (Err.Number = 0)
  Err.Clear
End Function

Function DriverSelectAllSketchRegions(ByVal model, ByVal sketchName)
  Dim sketchFeature, sketch, regions, regionCount, selectData, selectedCount
  On Error Resume Next
  model.ClearSelection2 True
  Set sketchFeature = DriverFeatureByName(model, sketchName)
  If sketchFeature Is Nothing Then
    DriverSelectAllSketchRegions = False
    Exit Function
  End If
  Set sketch = sketchFeature.GetSpecificFeature2()
  If sketch Is Nothing Then
    DriverSelectAllSketchRegions = False
    Exit Function
  End If
  Err.Clear
  regionCount = sketch.GetSketchRegionCount()
  regions = sketch.GetSketchRegions()
  If Err.Number <> 0 Or regionCount <= 0 Or IsEmpty(regions) Then
    Err.Clear
    DriverSelectAllSketchRegions = False
    Exit Function
  End If
  Set selectData = model.SelectionManager.CreateSelectData
  selectData.Mark = 4
  model.ClearSelection2 True
  selectedCount = model.Extension.MultiSelect2(regions, False, selectData)
  DriverSelectAllSketchRegions = (selectedCount = regionCount)
  Err.Clear
End Function

Function DriverBossExtrude(ByVal model, ByVal depthMm, ByVal mergeResult)
  Dim feature
  On Error Resume Next
  Err.Clear
  Set feature = model.FeatureManager.FeatureExtrusion2(True, False, False, swdEndCondBlind, swdEndCondBlind, Mm(depthMm), Mm(depthMm), False, False, False, False, 0.01745329251994, 0.01745329251994, False, False, False, False, mergeResult, True, True, 0, 0, False)
  If Err.Number <> 0 Then Err.Clear
  Set DriverBossExtrude = feature
End Function

Function DriverCutThroughAll(ByVal model)
  Dim feature
  On Error Resume Next
  Err.Clear
  Set feature = model.FeatureManager.FeatureCut3(False, False, False, swdEndCondThroughAll, swdEndCondThroughAll, Mm(200), Mm(200), False, False, False, False, 0.01745329251994, 0.01745329251994, False, False, False, False, False, True, True, False, False, False, swdEndCondBlind, 0, False)
  If Err.Number <> 0 Then Err.Clear
  Set DriverCutThroughAll = feature
End Function

Function DriverCutBlindBoth(ByVal model, ByVal depthMm)
  Dim feature
  On Error Resume Next
  Err.Clear
  Set feature = model.FeatureManager.FeatureCut3(False, False, False, swdEndCondBlind, swdEndCondBlind, Mm(depthMm), Mm(depthMm), False, False, False, False, 0.01745329251994, 0.01745329251994, False, False, False, False, False, True, True, False, False, False, swdEndCondBlind, 0, False)
  If Err.Number <> 0 Then Err.Clear
  Set DriverCutBlindBoth = feature
End Function

Function DriverSweepBossCircular(ByVal model, ByVal sketchName, ByVal diameterMm)
  Dim selected, feature, actualName
  On Error Resume Next
  model.ClearSelection2 True
  actualName = DriverActualFeatureName(sketchName)
  selected = model.Extension.SelectByID2(actualName, "SKETCH", 0, 0, 0, False, 4, Nothing, 0)
  If Not selected Then
    Set DriverSweepBossCircular = Nothing
    Exit Function
  End If
  Err.Clear
  Set feature = model.FeatureManager.InsertProtrusionSwept4(False, False, 0, False, True, 0, 0, False, 0, 0, 0, 0, True, False, True, 0, True, True, Mm(diameterMm), 0)
  If Err.Number <> 0 Then Err.Clear
  Set DriverSweepBossCircular = feature
End Function

Function DriverSweepCutCircular(ByVal model, ByVal sketchName, ByVal diameterMm)
  Dim selected, feature, actualName
  On Error Resume Next
  model.ClearSelection2 True
  actualName = DriverActualFeatureName(sketchName)
  selected = model.Extension.SelectByID2(actualName, "SKETCH", 0, 0, 0, False, 4, Nothing, 0)
  If Not selected Then
    Set DriverSweepCutCircular = Nothing
    Exit Function
  End If
  Err.Clear
  Set feature = model.FeatureManager.InsertCutSwept5(False, False, 0, False, True, 0, 0, False, 0, 0, 0, 0, False, True, 0, True, False, True, False, True, Mm(diameterMm), 0)
  If Err.Number <> 0 Then Err.Clear
  Set DriverSweepCutCircular = feature
End Function

Function DriverCreateFixedPlane(ByVal model, ByVal planeName, ByVal ox, ByVal oy, ByVal oz, ByVal ax, ByVal ay, ByVal az, ByVal bx, ByVal by, ByVal bz)
  Dim p1(2), p2(2), p3(2)
  On Error Resume Next
  p1(0) = Mm(ox)
  p1(1) = Mm(oy)
  p1(2) = Mm(oz)
  p2(0) = Mm(ox + ax)
  p2(1) = Mm(oy + ay)
  p2(2) = Mm(oz + az)
  p3(0) = Mm(ox + bx)
  p3(1) = Mm(oy + by)
  p3(2) = Mm(oz + bz)
  Err.Clear
  model.CreatePlaneFixed2 p1, p2, p3, False
  If Err.Number <> 0 Then
    Err.Clear
    DriverCreateFixedPlane = False
    Exit Function
  End If
  DriverRenameLastFeature model, planeName
  If Not DriverFeatureExists(model, planeName) Then
    DriverCreateFixedPlane = DriverAliasNewestFeatureOfType(model, planeName, "RefPlane")
  Else
    DriverCreateFixedPlane = True
  End If
End Function

Function DriverCreateLineLocal(ByVal model, ByVal x1, ByVal y1, ByVal x2, ByVal y2)
  On Error Resume Next
  Err.Clear
  Set DriverCreateLineLocal = model.SketchManager.CreateLine(Mm(x1), Mm(y1), 0, Mm(x2), Mm(y2), 0)
  If Err.Number <> 0 Then
    Err.Clear
    Set DriverCreateLineLocal = Nothing
  End If
End Function

Function DriverCreateArcLocal(ByVal model, ByVal cx, ByVal cy, ByVal x1, ByVal y1, ByVal x2, ByVal y2, ByVal direction)
  On Error Resume Next
  Err.Clear
  Set DriverCreateArcLocal = model.SketchManager.CreateArc(Mm(cx), Mm(cy), 0, Mm(x1), Mm(y1), 0, Mm(x2), Mm(y2), 0, direction)
  If Err.Number <> 0 Then
    Err.Clear
    Set DriverCreateArcLocal = Nothing
  End If
End Function

Function DriverCreateCircleLocal(ByVal model, ByVal x, ByVal y, ByVal radius)
  On Error Resume Next
  Err.Clear
  Set DriverCreateCircleLocal = model.SketchManager.CreateCircleByRadius(Mm(x), Mm(y), 0, Mm(radius))
  If Err.Number <> 0 Then
    Err.Clear
    Set DriverCreateCircleLocal = Nothing
  End If
End Function

Sub DriverLineLocal(ByVal model, ByVal x1, ByVal y1, ByVal x2, ByVal y2)
  Dim ignored
  Set ignored = DriverCreateLineLocal(model, x1, y1, x2, y2)
End Sub

Sub DriverArcLocal(ByVal model, ByVal cx, ByVal cy, ByVal x1, ByVal y1, ByVal x2, ByVal y2, ByVal direction)
  Dim ignored
  Set ignored = DriverCreateArcLocal(model, cx, cy, x1, y1, x2, y2, direction)
End Sub

Sub DriverCircleLocal(ByVal model, ByVal x, ByVal y, ByVal radius)
  Dim ignored
  Set ignored = DriverCreateCircleLocal(model, x, y, radius)
End Sub
