# SolidWorks Automation Notes

## Environment Checks

- Before a formal modeling run, check the `SLDWORKS` process and call `sw_get_status`. Reuse the responsive connected instance and configure the generated script with auto-launch disabled. If no usable instance exists, stop and ask before launching SolidWorks so the run cannot silently create a duplicate application process.
- The Windows COM ProgID is usually `SldWorks.Application`.
- A non-invasive check is `Test-Path Registry::HKEY_CLASSES_ROOT\SldWorks.Application`.
- Creating `New-Object -ComObject SldWorks.Application` may launch SolidWorks and should be treated as a visible desktop automation step.
- If COM calls fail, first distinguish attachment permissions/session visibility from dispatch errors. Inspect registration read-only only when relevant. Do not prescribe `/regserver` on this installation; it has not been a supported repair path here. Installation repair requires separate evidence and authorization.

## Script Shape

Use a generated script with these sections:

1. Input parameters and output paths.
2. Unit conversion helpers, usually `mm -> m` for API geometry coordinates.
3. Attach to the user-opened SolidWorks instance and select the target document/template; do not auto-launch.
4. Named parameter/equation setup.
5. Sketch construction validation, then feature creation in dependency order.
6. Rebuild, save, export, and verification logging.

Keep all source dimensions in millimeters in variable names and comments. Convert at API boundaries.

For interactive Codex use, separate complete local evidence from compact model input:

1. Write the complete execution log to disk.
2. Print one stable status line per feature group, for example `GROUP=group_01|RESULT=PASS`.
3. On failure, print `GROUP`, `API_CALL`, and the first error only, then stop.
4. Inspect only those compact status lines by default. Read a short surrounding window from the complete log only when the first error is insufficient.
5. Do not reread the full generated script, full log, or multiple screenshots after every run.

When opening a file that may already be loaded, do not assume `OpenDoc6` changes `ActiveDoc`. Call `ActivateDoc3` with the returned document title and verify that both the active title and path match the requested target before modeling or capturing evidence.

For non-trivial parts, make the generated script idempotent and resumable:

1. Attach to the existing SolidWorks application first. Create a new document only when no usable target document or checkpoint exists.
2. Keep the complete feature sequence in one script. Split it into ordered neutral groups such as `group_01`, `group_02`, `group_03`, and `final_verify`. Keep engineering names such as base, flange, branch, or boss in the drawing checklist only, not as MCP/server tool names or visible SolidWorks feature names.
3. Before each group, inspect the expected feature and body count. Skip the group only when its output already exists and passes its local check.
4. After each successful group, rebuild and save the same native checkpoint file.
5. If a group fails, stop immediately. Patch that group or a shared helper, then rerun the same script so completed groups are skipped.
6. Use small diagnostic scripts only when a specific SolidWorks API call needs isolation. Do not replace the complete script with a growing collection of one-off feature scripts.

For drawing-driven work, treat the drawing ledger as the modeling source. Do not open or reverse-engineer a user's manual `.SLDPRT` unless the user explicitly requests a comparison. When comparison is requested, use the reference part only after the drawing-derived plan exists and only as QA evidence.

During one normal modeling invocation, create or attach `swApp` once and keep the same `swApp` and model references alive until the script ends. Feature groups are functions inside that process. Do not use `Shell.Run`, a new `cscript`, or a new PowerShell child process to execute each group. A separate resume invocation is appropriate only after the previous invocation has stopped and saved a checkpoint.

For the VBScript route only, use `scripts/single-instance-base-smoke.vbs` as its lifecycle baseline. Do not rerun it or switch drivers when a Python/MCP runner is already qualified for the task.

When developing the VBScript route, use `scripts/lib/solidworks-com-driver.vbs` and qualify that driver once. This qualification is not a prerequisite for the separately validated Python/MCP route. Keep drawing-specific parameters separate from shared COM helpers.

## Feature Mapping

- Rectangular plates, brackets, housings: base sketch plus boss extrude, then cuts, holes, patterns, fillets, chamfers.
- Shafts, bushings, pulleys, knobs: revolved base, then keyways, threads, grooves, holes.
- Sheet metal: base flange, edge flanges, bends, reliefs, flat pattern, K-factor or bend radius from drawing notes.
- Tubes and frames: weldment or sweep profiles along 3D sketches when centerlines are known.
- Organic transitions: loft/sweep with guide curves only when the drawing gives enough sections.
- Assemblies: create/load parts, insert into assembly, fix or mate the primary component, then mate secondary components by datums, axes, faces, and hole centers.

## Generated Script Guidance

- Prefer the task's verified runner. Python/pywin32 has completed the recorded elbow replay; VBScript remains an alternative, not a mandatory intermediary inside MCP. Connection-only success is weaker evidence than a complete build.
- Use PowerShell only as a process/log wrapper when possible. PowerShell/.NET COM dispatch may fail with `TYPE_E_ELEMENTNOTFOUND` even when VBScript automation works.
- Use C# when the task needs stronger typing, large scripts, or repeatable production automation.
- Use VBA macros only when SolidWorks-native macro workflows are specifically useful.
- If Python is used, check for `pywin32` first; do not assume it is installed.
- Check every important return value. In late-bound VBScript, failed SolidWorks API calls often return `Nothing`, `False`, or a non-zero `Err.Number` without a useful stack trace. For native saves, also verify that the expected file exists and is non-empty. On this machine, `ModelDoc2.SaveAs3` can return `False` or `0` while the `.SLDPRT` file is still written successfully, so the return value alone is not a sufficient save-failure test.
- Log after each major feature group with stable keys such as `GROUP_01_OK`, `CUT_OK`, `PATTERN_OK`, `SAVE_OK`, and `EXPORT_STEP_OK`. This makes retry decisions local instead of requiring full script reconstruction.
- Keep console output compact. Full diagnostics belong in the on-disk log; stdout should contain group start, group result, first failure, checkpoint path, and final verification only.
- Before launching a generated formal script, inspect it for accidental `Shell.Run`, nested `cscript`, repeated `CreateObject("SldWorks.Application")`, blanket `sgFIXED` / `ConstrainAll` / `FullyDefineSketch` calls, and face-sketch geometry created from unconverted world coordinates.
- Run `scripts/validate-solidworks-vbs.ps1` through `scripts/run-solidworks-vbs.ps1` before launching an external VBS file. Formal scripts call the shared driver instead of `FeatureExtrusion2`, `FeatureCut3`, sweep APIs, or `CreateCircleByRadius` directly. Qualification scripts may use `sgFIXED` only to isolate helper lifecycle behavior; formal scripts may not.
- Keep template paths discoverable. Try SolidWorks default template preferences first; if the template is missing, log `TEMPLATE_ERROR` and ask for or infer a valid template path before creating geometry.
- Save native SolidWorks files before neutral exports. STEP export failures are easier to debug when the SLDPRT or SLDASM already exists and rebuilds successfully.
- Maintain a small catalog of verified helpers for fragile operations such as sketch-region selection, boss extrusion, cut extrusion, sweep creation, datum-plane creation, body combine, native save, and section verification. Reuse a helper only after it has passed a real feature check or a targeted smoke test. Preserve its known-good API signature and selection marks; do not silently generalize an unverified helper during a formal drawing run.

### Sketch Definition Gate

For every sketch that drives a boss, cut, sweep, loft, rib, hole, pattern, or another dependent feature, check that the sketch is explicitly defined by the drawing plan before calling the feature API. This applies to sketches on default planes, datum planes, faces, and 3D paths.

There are two accepted modes:

1. Coordinate/parameter-driven mode. Use this by default for automation-created rectangles, circles, arcs, bolt circles, profiles, and paths whose coordinates, radii, depths, angles, and topology have already been calculated from the drawing ledger. In this mode, the API call parameters are the definition. Log and verify the source parameters and feature-critical distances/radii/angles/region counts. Do not add SolidWorks display dimensions only to turn an otherwise correct coordinate sketch from `swUnderConstrained = 2` into `swFullyConstrained = 3`.
2. Constraint-driven mode. Use this when a sketch intentionally depends on SolidWorks dimensions or relations for editability, user manipulation, or unresolved coordinate derivation. In this mode, use `ISketch::GetConstrainedStatus()` and require `swFullyConstrained = 3`. If the status is not `3`, log the sketch name and status, stop the current feature group, and repair the sketch dimensions or relations before continuing.

For a formal drawing-driven model, do not call blanket `sgFIXED`, `ConstrainAll`, or `FullyDefineSketch` operations to hide missing constraints or missing drawing understanding. If coordinate-driven construction is used, validate the computed geometry directly. If constraint-driven construction is used, add explicit dimensions and geometric relations from the drawing ledger, exit the sketch, rebuild, and read `GetConstrainedStatus()` again. Blanket fixing is acceptable only in an isolated lifecycle smoke test where geometry fidelity is intentionally out of scope.

```vbscript
Const swFullyConstrained = 3

Function RequireFullyDefinedSketch(ByVal model, ByVal sketchName)
  Dim sketchFeature, sketch, status
  Set sketchFeature = model.FeatureByName(sketchName)
  If sketchFeature Is Nothing Then
    WScript.Echo "SKETCH_NOT_FOUND=" & sketchName
    RequireFullyDefinedSketch = False
    Exit Function
  End If

  Set sketch = sketchFeature.GetSpecificFeature2()
  If sketch Is Nothing Then
    WScript.Echo "SKETCH_OBJECT_ERROR=" & sketchName
    RequireFullyDefinedSketch = False
    Exit Function
  End If

  status = sketch.GetConstrainedStatus()
  WScript.Echo "SKETCH_STATUS=" & sketchName & "|" & CStr(status)
  RequireFullyDefinedSketch = (status = swFullyConstrained)
End Function
```

Call this function immediately before selecting sketch regions or invoking the dependent feature API only for constraint-driven sketches. For coordinate/parameter-driven sketches, closure and region checks answer whether a profile can form the intended feature, while the script parameter ledger answers whether its size and position are stable.

### Closed 2D Boss Extrude in Late-bound VBScript

For a closed 2D contour, do not assume that selecting the sketch tree node or each sketch segment is equivalent to the interactive SolidWorks command. A SolidWorks 2024 macro recorded on this machine selected the enclosed contour as a sketch region with selection mark `4`, then called `FeatureExtrusion2`.

For generated scripts, prefer `ISketch::GetSketchRegions()` plus `IModelDocExtension::MultiSelect2()` with `ISelectData::Mark = 4`. This avoids mouse-pick coordinates and works for one enclosed boss region or multiple hole regions:

```vbscript
Set sketchFeature = model.FeatureByName(sketchName)
Set sketch = sketchFeature.GetSpecificFeature2()
regions = sketch.GetSketchRegions()
Set selectData = model.SelectionManager.CreateSelectData
selectData.Mark = 4
selectedCount = model.Extension.MultiSelect2(regions, False, selectData)
Set feat = model.FeatureManager.FeatureExtrusion2(True, False, False, 0, 0, depthM, depthM, False, False, False, False, 0.01745329251994, 0.01745329251994, False, False, False, False, True, True, True, 0, 0, False)
model.SelectionManager.EnableContourSelection = False
```

If the call returns `Nothing`, record a minimal manual macro for that exact feature, compare selection type and mark first, and repair only the shared helper. During local retries, attach to the current SolidWorks document and continue from the last checkpoint instead of creating a new part document.

### Verified Boss and Cut APIs on This Machine

For this SolidWorks 2024 SP0.1 installation, do not treat `FeatureExtrusion3(..., is_cut=True, ...)` as a verified cut path. It can create a feature-like entry without subtracting material. The verified local mapping is:

- Boss/base extrusion: `FeatureExtrusion2(...)`.
- Through-all cut extrusion: `FeatureCut3(False, False, False, swEndCondThroughAll, swEndCondThroughAll, ...)`.
- Cut validation: check volume or mass properties after the feature. A 60 x 60 x 10 mm block has `36000 mm^3`; four through holes of diameter 8 mm reduce it to about `33989.38 mm^3`.

### Sketch Coordinates on Inclined Faces

SolidWorks 2D sketch creation calls use the active sketch plane's local coordinate system. For sketches on an inclined face or datum plane, derive coordinates with the sketch transform or construct geometry directly from that plane's local axes. Do not pass world XYZ values directly into `CreateCircleByRadius`, `CreateLine`, or similar face-sketch calls unless the conversion has been proven. A valid API call can otherwise create detached or visibly floating geometry.

## Failure Triage

Use the first matching symptom:

- `CREATE_ERROR` or COM ProgID not registered: SolidWorks automation is unavailable. Check installation, registry, or launch permissions before writing more geometry code.
- `TYPE_E_ELEMENTNOTFOUND` from PowerShell COM: switch to VBScript for the real automation path; do not treat this alone as proof that SolidWorks is unusable.
- Template path missing or `NewDocument` returns `Nothing`: resolve the part/assembly template before feature creation.
- Sketch selection returns `False`: verify entity names, active document type, active sketch state, whether the target plane or face exists, and whether the sketch passed the appropriate coordinate-driven or constraint-driven definition gate.
- Feature method returns `Nothing`: check units, sketch closure, contour selection, end condition parameters, and rebuild errors before adding later features.
- Save/export reports failure: log the target path, file extension, return value, and returned codes. For a native save, also check whether the expected file exists and is non-empty before retrying. Retry with a simpler native save before STEP export only when the native artifact is actually missing or invalid.
- Assembly opens but contains zero components: reopen saved parts with legacy `OpenDoc(path, 1)` and insert them with `AddComponent4`; then verify `GetComponents(False)`.
- Mate creation fails with ByRef/type mismatch: select the exact faces/axes with `SelectByID2` and use legacy `AssemblyDoc.AddMate` before trying newer mate APIs.

After the first targeted retry for the same symptom, stop and report the failing feature group, API call, and log evidence. Do not generate a chain of speculative probe scripts.

## SolidWorks Feature Names and VBScript Encoding

Default to normal SolidWorks feature-tree names for single-part models. Do not rename features just to make the tree look semantic; default names like `凸台-拉伸1` and `切除-拉伸1` are acceptable and closer to manual SolidWorks output.

Keep generated VBScript file names, output paths, script identifiers, log keys, and internal selection names ASCII. This avoids `cscript` misreading UTF-8 `.vbs` files and producing garbled feature names.

If the user explicitly requests Chinese SolidWorks-visible feature names, do not write raw Chinese literals in `.vbs`. Use an ASCII-safe Unicode helper or write the script as UTF-16LE with BOM, then test it with `cscript //nologo` before using it on a drawing model. Otherwise leave feature names as SolidWorks defaults.
## Verification

After generation:

- Force rebuild.
- Verify every feature-driving sketch with the appropriate gate: coordinate/parameter-driven sketches must match the logged drawing parameters and region/topology checks; constraint-driven sketches must report `ISketch::GetConstrainedStatus() = 3`.
- Save in native format.
- Export STEP/STP only when the user explicitly requests it. Interoperability needs alone do not authorize an export; keep recovery checkpoints in the native working file.
- Capture at least one screenshot when visual verification is needed.
- For standard views, call `ShowNamedView2("", view_id)` with the correct `swStandardViews_e` identifier (`Front=1`, `Back=2`, `Left=3`, `Right=4`, `Top=5`, `Bottom=6`, `Isometric=7`, `Trimetric=8`, `Dimetric=9`), then force `GraphicsRedraw2` before `SaveBMP`. Compare the first nine values of `ActiveView.Orientation3.ArrayData` with `GetStandardViewRotation(view_id)` and retry at most twice if they differ. Record the requested view, verified rotation, attempt count, and image hash. If the rotation is unverified or required views have identical hashes, fail the proving-view check.
- Before capturing normal orthographic or isometric views, call `ModelViewManager.RemoveSectionView()` so a section state left active in another open document cannot contaminate the screenshots. Create model section views through `ModelViewManager.CreateSectionViewData()` plus `CreateSectionView()`. Record the remove result, resolved plane, offset, creation result, and section screenshot hash. A fallback note or selected plane without an active section is not section evidence.
- Report unresolved assumptions, dimensions used, and output paths.
- For assemblies, report expected component count versus `GetComponents(False)` result.
- For parametric parts, report the driving parameter table or the equations that control the main dimensions.
