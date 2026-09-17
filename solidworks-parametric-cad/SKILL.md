---
name: solidworks-parametric-cad
description: Create and automate SolidWorks CAD from drawings, PDFs, sketches, dimension tables, or mechanical requirements, including drawing gates, COM/MCP/VBScript automation, SLDPRT/SLDASM/STEP export, debugging, and validation.
---

# SolidWorks Parametric CAD

## Scope

- Use this skill for SolidWorks part/assembly modeling, drawing-to-CAD interpretation, CAD automation scripts, output export, automation debugging, and geometry validation.
- When the user works in Chinese, answer in Chinese. Use Chinese SolidWorks-visible names only when useful or requested.
- Generate scripts and CAD outputs in the active workspace unless the user requests another folder. Protect user originals and unrelated files. Within an authorized modeling or repair task, update the task-owned script and native working checkpoint in place; resume the target document instead of creating a new version for every retry.
- Export STEP/STP only when the user explicitly requests it. Native working checkpoints support recovery; do not accumulate failed neutral exports.
- Treat the drawing, PDF, image, sketch, dimension table, or textual requirement as the modeling source. Do not open or reverse-engineer a user manual `.SLDPRT` unless the user explicitly asks for reference comparison or QA.
- Do not browse the web for routine SolidWorks modeling. Use local references, known-good scripts, and SolidWorks runtime evidence first.

## Reference Routing

- For simple known parts such as flanges, bushings, shafts, plates, brackets, and bolt circles, use the compact gate in this file plus the output format in `references/drawing-to-feature-plan.md`. Do not load the full drawing rules unless the compact gate exposes ambiguity, missing feature-critical evidence, or conflicting dimensions.
- For non-trivial drawings, multi-view/sectioned parts, castings, shells, manifolds, assemblies, unclear screenshots, or any drawing with topology/fit ambiguity, read `references/drawing-understanding-rules.md` before interpreting geometry or writing code.
- Use `references/drawing-to-feature-plan.md` for the local gate report and feature-plan template.
- Use `references/drawing-match-validation.md` for the single-source drawing contract, independent post-run checks, proving-view capture, and drawing-match result rules.
- For cast elbows, manifolds, pipe joints, or similar internally connected passage parts, also read `references/casting-elbow-example.md`.
- For SolidWorks COM/API/VBScript/PowerShell/C# implementation details, read `references/solidworks-automation.md`.
- For skill maintenance, regression testing, or blind validation, read `references/dev-validation.md`. Do not run development regressions during normal user modeling unless the user asks to maintain or evaluate the skill.

## Drawing Gate

- Hard stop: for any drawing-derived model, do not open SolidWorks, generate code, or create a "rough first" model until the drawing gate has been written and the gate records `CONFIRMED` with `permission_to_generate_code: yes`, unless the user explicitly approves `APPROXIMATE_ALLOWED`.
- Use the whole drawing, not one isolated view. Every feature-critical dimension, radius, angle, count, thickness, centerline, hidden line, section mark, tolerance, note, and positional relation must either drive a feature, verify a feature, be classified as non-geometry/manufacturing/title-block/cosmetic, or be marked unresolved.
- Close dimensions, geometric relations, and topology before code generation. Include cross-view arithmetic and required relations such as coincidence, tangency, concentricity, symmetry, parallelism, perpendicularity, and internal connectivity.
- For every drawing-derived model, maintain a dimension-usage ledger before code generation. Each dimension or callout must state its source view, owning feature/sketch, datum or start entity, end entity, measurement direction or axis, formula if combined with other dimensions, exact modeling use, and verification row. If a feature-critical dimension is unused, double-counted, visually estimated, or not anchored to a datum/axis/face/centerline, set `Gate status: BLOCKED` and `permission_to_generate_code: no`.
- Treat positional relations as first-class drawing evidence, not optional interpretation. The gate must explicitly record required coincidence, tangency, concentricity, collinearity, coplanarity, symmetry, parallelism, perpendicularity, equal spacing, endpoint anchoring, plane normals, and axis sharing before the affected feature is modeled.
- Local/detail/end/section views must be anchored back to the parent view before modeling. Record the parent feature, center point, plane normal, local axes, depth/thickness direction, and evidence source. If a local view center, section plane, or end-face orientation is unresolved, set `Gate status: BLOCKED` and `permission_to_generate_code: no`.
- Before generating any modeling script from a drawing, write the drawing-understanding result first: recognized views, evidence disposition, derived dimensions, geometric relations, topology relations, per-feature construction checklist, unresolved blockers, gate status, and `permission_to_generate_code`. Show the user the compact summary in the conversation; keep the full table on disk for non-trivial drawings.
- For non-trivial drawings, keep the complete evidence ledger, relation ledger, topology ledger, sketch constraint ledger, and per-feature checklist on disk. In the conversation, report only the compact gate summary unless the user asks for the full table.
- For non-trivial drawings, compile the confirmed ledger into exactly one machine-readable drawing contract before code generation. Generated scripts must read feature-critical values from that contract instead of copying numeric literals into a second parameter table. Record the contract path and content hash in the execution log. If a required contract field is missing, unused, or consumed by two incompatible physical segments, set `Gate status: BLOCKED` and `permission_to_generate_code: no`.
- For simple known parts such as flanges, bushings, shafts, plates, brackets, and bolt circles, use a compact gate: identify views, units, datum, critical dimensions, hole pattern, thickness/depth, assumptions, and verification. Do not build the full long evidence table unless the drawing is ambiguous or the part is non-trivial.
- Record exactly one gate status: `CONFIRMED`, `BLOCKED`, or `APPROXIMATE_ALLOWED`, plus `permission_to_generate_code: yes | no`.

## Confirmation Rules

- If the gate is `CONFIRMED`, all feature-critical evidence is closed, and the user has asked for implementation, code generation may proceed without an extra confirmation round.
- Before asking a clarification question, first inspect the current local gate files, evidence ledgers, user-confirmed notes, and previous run summaries in the active workspace. Do not re-ask an item that is already recorded as user-confirmed; restate the recorded answer and proceed, or ask only if a newer drawing/evidence contradicts it.
- Ask the user before code generation only when unresolved evidence can change topology, fit, mating, passage continuity, manufacturing intent, or when multiple plausible interpretations remain.
- `APPROXIMATE_ALLOWED` is valid only when the user explicitly asks for a rough/approximate model or approves recorded assumptions. In that case `permission_to_generate_code` may be `yes`, but the result must be reported as approximate.
- Do not create an approximate model by default. A visually similar draft is not a substitute for drawing understanding.

## Automation Rules

- Before translating a confirmed drawing into API calls, read `references/geometry-handoff.md`. Keep drawing evidence, geometric coordinates, API inputs, and measured outputs traceable; distinguish interpretation defects from construction defects.
- For planar feature profiles, prefer a 2D sketch on an explicit plane. Convert world coordinates through the actual sketch transform; do not assume that an inclined plane's local axes equal world axes. Spatial paths may still use 3D sketches.

- Default acceptance mode is `basic_plus_human_review`: check feature creation, detected sketch-geometry mismatches, rebuild, body count, and obvious appearance errors once; leave detailed drawing/section acceptance to the user. Do not repeat section switching or expand display troubleshooting unless explicitly requested. This mode changes post-run verification effort, not the pre-model drawing-understanding requirements.
- The detailed automated drawing-match, proving-view, and section checks below apply only in `full_drawing_match` mode when the user requests automated full verification. In basic mode report `AWAITING_USER_REVIEW`; explicit user acceptance may be recorded as `USER_ACCEPTED`, never as an automated `DRAWING_MATCH_PASS`. Any known sketch or geometry error still stops the affected operation.
- After a local repair succeeds, incorporate the repair into the executable entrypoint before claiming it can be reproduced. Record model state, from-zero replay, and drawing acceptance separately. A repaired model is not proof of repeatability; do not rerun from zero without user authorization. Preserve the prior good native checkpoint and keep failures separate.

- Classify the part before launching SolidWorks: axisymmetric parts use revolve-first workflows; prismatic parts use extrude/cut workflows; cast shells and manifolds use controlled body, cavity, branch, flange, rib, and hole sequences; assemblies create/load parts first, then add mates.
- Before every formal run, first check both the `SLDWORKS` process and `sw_get_status`. If a responsive instance is already connected, attach to that instance and set generated scripts to disallow auto-launch. If no usable instance is open, report that state and obtain user permission before launching SolidWorks; do not silently create a second application instance.
- Use one SolidWorks application instance and one target document for a normal modeling run. Do not launch a new SolidWorks document, `cscript`, PowerShell child process, or helper process for every feature group.
- Prefer a single idempotent/resumable modeling script organized by feature groups. If a group fails, stop at the first failure, save/checkpoint if possible, patch only that group or shared helper, then rerun the same script from the first incomplete group.
- For drawing-derived models, script success is not completion. After the geometry-altering run, complete a post-run drawing match gate before reporting completion. The gate must compare the generated model against the driving views, sections, local/detail views, dimensions, positional relations, and passage/connectivity requirements recorded in the drawing plan. If any feature-critical row is failed or unverified, report the model as not completed.
- Treat post-run verification as an independent acceptance path, not as a second way to drive the model. Coordinate-driven primitives do not need redundant SolidWorks display dimensions, but the validator must reload the drawing contract independently and compare it with measured feature positions, overall dimension chains, local frames, counts, topology, and proving views. Do not mark a row `PASS BY CONSTRUCTION` merely because the generator received the intended number.
- Stop after the first failed feature group. Save a checkpoint, report the first contract row that differs, and rebuild the owning group only. Do not finish the whole part and defer all drawing comparison to a final human inspection.
- If the drawing contains a section, half-section, auxiliary section, or local section, the post-run gate must include a matching section-view check at the recorded plane, orientation, and position. If the automation cannot create or inspect that section, record `DRAWING_MATCH_UNVERIFIED` instead of `DRAWING_MATCH_PASS`.
- For automated proving screenshots, record the requested view, the activated standard/custom view identifier, the section-view creation result, and the output hash. Required front/top/isometric/local/section images must not collapse to the same hash. Identical hashes are a verification failure, not drawing-match evidence.
- If a post-run drawing match check finds a topology or view-match error, return to the last clean checkpoint and rebuild the affected feature group. Do not hide the error with later cosmetic features, global through-all cuts, or broad fillet/chamfer operations that can damage unrelated geometry.
- Region-specific dimensions, radii, chamfers, fillets, holes, cuts, and local outlines must be scoped to their owning feature, view, face, sketch, or feature group. Do not satisfy a local drawing callout with a late global operation that can modify unrelated geometry.
- Do not repeat generic COM checks, API documentation searches, smoke tests, or unrelated probes after the local environment baseline is known. Debug only the first failing feature group and the first failing API call.
- Formal feature-driving sketches must be explicitly defined by the drawing plan before creating the dependent feature. Prefer coordinate/parameter-driven construction when the drawing dimensions already determine entity coordinates, radii, angles, depths, and topology; in that mode, verify the computed geometry and required relations instead of adding SolidWorks display dimensions only to force `ISketch::GetConstrainedStatus() = 3`. Require `swFullyConstrained = 3` only for constraint-driven sketches whose size or position depends on SolidWorks relations/dimensions. Do not use blanket `sgFIXED`, `ConstrainAll`, or `FullyDefineSketch` to hide missing drawing understanding.
- For one-piece castings, temporary multi-bodies are allowed only as construction. The final deliverable must be merged into one solid body and verified with `BODY_COUNT=1`.
- For mechanisms and assemblies, do not lock every component with global reference-plane mates. Fix only the base/ground component and use functional mates that preserve intended degrees of freedom.
- Do not call `CloseAllDocuments(True)`. Close only documents created by the current script after confirming they are intentionally disposable or saved.

## Local Automation Path

- Prefer available SolidWorks MCP tools for connection/status/document inspection when they are configured. Do not treat MCP status tools as proof that geometry modeling tools exist.
- Treat MCP as a SolidWorks operation/API gateway, not as storage for drawing, part, or manufacturing intent. Permanent MCP tools must be thin parameterized wrappers around native SolidWorks operations/API calls: connection, document open/create/save/export, selection, sketch start/end, sketch entities, sketch dimensions, sketch relations, reference geometry, boss extrude, cut extrude, sweep, loft, revolve, pattern, mirror, fillet, chamfer, shell, combine, rebuild, body count, section view, and status/log inspection.
- Do not make permanent MCP tools for engineering objects, drawing features, or part-specific construction blocks. Forbidden permanent tool names and concepts include `base`, `plate`, `flange`, `lug_flange`, `three_lug_flange`, `boss_with_bore`, `branch_pipe`, `swept_pipe`, `cast_elbow`, `drawing_436`, and similar combinations. If a generated script needs local grouping, use neutral drawing-local names such as `group_01`, keep the geometry meaning in the drawing checklist, and do not copy those groups into the MCP server.
- For geometry automation on this machine, use the verified path documented in `references/solidworks-automation.md`. Preserve an already-qualified Python/MCP implementation; older VBScript connection evidence is not a reason to replace a working model runner. Never launch SolidWorks automatically on this installation; ask the user to open it when attachment fails.
- Use the existing wrappers and shared helpers when generating external scripts. Avoid duplicating fragile COM calls in drawing-specific scripts.
- For generated VBScript, keep file names, output paths, script identifiers, log keys, and default internal feature/sketch names ASCII. Do not write raw Chinese string literals in `.vbs`; `cscript` can misread UTF-8 and create garbled SolidWorks feature names.
- Prefer leaving single-part feature-tree names as SolidWorks defaults. Rename features only when the user explicitly asks for visible semantic names.
- If a Chinese SolidWorks-visible name is required in VBScript, build it with a `ChrW`/`U(Array(...))` helper or write the file as UTF-16LE with BOM and test it before use.

## Naming

- For a single-part `.SLDPRT`, keep the feature tree close to normal manual SolidWorks output. Prefer default feature-type names.
- Do not rename one-piece part regions to component-like names unless the output is a real `.SLDASM` assembly or the user asks for semantic labels.
- For generated VBScript, avoid semantic Chinese renaming by default. Use ASCII stable names only for hidden internal reselection when unavoidable, and do not expose those names as user-facing component names.
- For assemblies, use clear component and mate names that describe function and degrees of freedom.

## Reporting

After a successful or blocked run, report concisely:

- Input interpretation: recognized views, units, feature plan, assumptions, and blockers.
- Gate result: `CONFIRMED`, `BLOCKED`, or `APPROXIMATE_ALLOWED`, plus whether code generation was permitted.
- Files created: scripts, SLDPRT/SLDASM, STEP, screenshots, and logs with absolute paths.
- Verification: coordinate/parameter geometry checks, required sketch relation checks, sketch status when relevant, rebuild, body/component count, save/export, section comparison, passage continuity, drawing-match table, or why a check was skipped.
- Result level: `EXECUTION_PASS`, `GEOMETRY_PASS`, and `DRAWING_MATCH_PASS` when applicable. Report a model as completed only when the required layers pass.
- Report acceptance according to the selected mode: `DRAWING_MATCH_PASS` for completed full automated verification, or `USER_ACCEPTED` after explicit user acceptance in basic mode. Otherwise report `AWAITING_USER_REVIEW` or the actual failure. Missing full verification is not itself evidence that a model is wrong. State from-zero replay as not run, passed, or failed independently of model acceptance.
- Next step: the single highest-value action if the model is blocked or only approximate.

## References

- `references/drawing-understanding-rules.md`: mandatory drawing-reading gate, evidence coverage, relation closure, topology closure, and code-handoff criteria.
- `references/drawing-to-feature-plan.md`: concise feature-plan and checklist template.
- `references/drawing-match-validation.md`: single-source contract, independent feature checks, proving-view integrity, and result-level rules.
- `references/solidworks-automation.md`: COM/API implementation notes, wrappers, known machine-specific behavior, failure triage, and verified script patterns.
- `references/casting-elbow-example.md`: drawing-reading example for cast elbows and manifolds.
- `references/dev-validation.md`: skill maintenance and regression validation only.

## Scripts

- `scripts/check-solidworks-com.ps1`: registry/COM diagnostics. PowerShell COM can expose `TYPE_E_ELEMENTNOTFOUND`; do not treat that alone as fatal if VBScript works.
- `scripts/check-solidworks-vbs.vbs`: minimal direct SolidWorks COM check through `cscript`.
- `scripts/single-instance-base-smoke.vbs`: one-process lifecycle baseline.
- `scripts/lib/solidworks-com-driver.vbs`: shared external-VBScript COM driver.
- `scripts/qualify-solidworks-vbs-driver.vbs`: helper qualification for maintaining the VBScript driver.
- `scripts/validate-solidworks-vbs.ps1`: static preflight for external VBScript.
- `scripts/run-solidworks-script.ps1`: PowerShell automation runner with logging.
- `scripts/run-solidworks-vbs.ps1`: VBScript runner with static preflight, argument forwarding, and logging.
