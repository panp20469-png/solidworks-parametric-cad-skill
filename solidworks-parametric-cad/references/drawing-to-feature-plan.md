# Drawing to Feature Plan

## Intake Checklist

Extract:

- File type, scale, units, projection standard, sheet count, and title block notes.
- All orthographic, section, auxiliary, detail, and isometric views.
- Overall envelope dimensions and primary datum references.
- Base shape, wall thicknesses, holes, slots, threads, countersinks, counterbores, fillets, chamfers, draft, bends, ribs, bosses, grooves, and cutouts.
- Pattern rules: linear spacing, circular pitch, equal spacing, mirror symmetry, and instance counts.
- Material, finish, tolerance class, and any manufacturing process notes.

## Feature Plan Format

Use this concise plan before generating code. Keep the complete ledger in a local file. In the conversation, report the compact gate summary before script generation so the user can see how the drawing was understood. Show the full table only when the drawing is complex, ambiguous, or the user asks for it.

```text
Gate status: CONFIRMED | BLOCKED | APPROXIMATE_ALLOWED
permission_to_generate_code: yes | no
Units:
Output:
Part or assembly:
Recognized views and sections:
Evidence disposition:
Assumptions:
Unresolved blockers:
Parameters:
Reference geometry:
Dimension usage ledger:
Local view anchor ledger:
Geometric relation ledger:
Topology relation ledger:
Sketch constraint ledger:
Per-feature construction checklist:
Evidence coverage audit:
Feature sequence:
Verification:
```

The `Dimension usage ledger` is mandatory for every drawing-derived model. Each row must state the dimension/callout, source view, owning feature/sketch, datum or start entity, end entity, measurement direction or axis, cross-view formula, exact modeling use, related positional relations, and verification row. If any feature-critical dimension is unused, double-counted, visually estimated, missing a start/end/direction, or missing a verification row, keep `permission_to_generate_code: no`.

For every local/detail/end/section view used by a feature, the `Local view anchor ledger` must state the parent view, parent feature or datum, anchor center point, plane normal, local X/Y axes, depth or thickness direction, evidence source, and status. If the anchor is unresolved, keep `permission_to_generate_code: no`. For each inferred or explicit relation, the `Geometric relation ledger` must state the entities, evidence view or section, evidence level, intended SolidWorks relation, and the sketch or verification check that uses it. The `Topology relation ledger` must state which solids, cavities, passages, holes, bosses, flanges, ribs, and bases must be merged, intersecting, tangent, separate, through-cut, blind, or internally connected, together with the proving view and verification method. For each feature-driving sketch, the `Sketch constraint ledger` must state the sketch plane or face, datum references, dimensions, geometric relations, relation evidence, definition mode, and verification check. Use `coordinate_driven` when code parameters already define coordinates, radii, angles, depths, and topology; verify those computed values and feature results instead of adding display dimensions only to force `ISketch::GetConstrainedStatus() = 3`. Use `constraint_driven` only when the sketch intentionally depends on SolidWorks dimensions/relations, and then require `swFullyConstrained = 3`.

For every drawing, prepare a `Per-feature construction checklist` before code generation. Keep the full checklist in a local file. In the conversation, expose the compact checklist summary; show the full table only when the drawing is complex, ambiguous, or the user asks for it. Use this row format:

```text
Feature:
Sketch plane or datum:
Evidence IDs:
Explicit source dimensions:
Dimension start/end/direction:
Derived values:
Geometric relations:
Relation evidence:
Local view anchor:
Topology intent:
SolidWorks operation:
Depth or end condition:
Verification check:
```

Include unmarked but required position relations such as tangency, coincident endpoints, concentricity, collinearity, symmetry, parallelism, and perpendicularity. Mark drafting-convention-supported inferences separately from explicit dimensions. Wait for user confirmation only when an inference, assumption, missing dimension, or multiple plausible interpretation can change topology, fit, mating, passage continuity, manufacturing intent, or feature placement. If the gate is `CONFIRMED`, all feature-critical evidence is closed, and the user asked for implementation, `permission_to_generate_code` may be `yes` without another confirmation round.

The `Evidence coverage audit` must assign an evidence ID to every visible drawing item and link it to a checklist row, relation ledger item, topology verification, or explicit non-geometry classification. Run the audit in both directions: no drawing item may remain unused, and no checklist parameter may lack drawing evidence, cross-view arithmetic, drafting-convention-supported inference, or user confirmation. If the audit fails, reread the drawing and keep `permission_to_generate_code: no`.

Every visible dimension, diameter, radius, angle, tolerance, section callout, surface note, and manufacturing note must appear in `Evidence disposition` as one of:

- used by a sketch, feature, datum, or validation check;
- classified as manufacturing-only metadata;
- classified as duplicate evidence from another view;
- blocked because its role is unresolved.

Do not open SolidWorks or generate modeling code while `permission_to_generate_code` is `no`.

## Post-Run Drawing Match Gate

For every drawing-derived model, run this gate after the modeling script finishes and before reporting the model as complete. Save the full table next to the model/log. A valid final answer must distinguish execution success from drawing match success.

```text
Execution result: EXECUTION_PASS | EXECUTION_FAIL
Geometry result: GEOMETRY_PASS | GEOMETRY_FAIL | GEOMETRY_UNVERIFIED
Drawing match result: DRAWING_MATCH_PASS | DRAWING_MATCH_FAIL | DRAWING_MATCH_UNVERIFIED
Model file:
Log file:
Failed or unverified rows:
```

Use one row per driving view, section, local view, feature group, and topology relation:

```text
Check item:
Drawing evidence:
Expected value or relation:
Model evidence:
Result: PASS | FAIL | UNVERIFIED
If FAIL: clean checkpoint to return to:
If FAIL: affected feature group:
```

Mandatory row categories:

- Overall classification: part vs assembly, single body/multi-body expectation, unit, material/manufacturing-only notes.
- Each primary, section, local/detail, end, and auxiliary view used in the drawing gate.
- Every feature-critical dimension, radius, angle, count, hole pattern, thickness, depth, datum offset, and derived value.
- Every feature-critical positional relation, including concentricity, tangency, collinearity, coplanarity, symmetry, parallelism, perpendicularity, and endpoint/axis anchoring.
- Every topology relation, including merged bodies, local-only cuts, through cuts, blind cuts, internal passages, side branches, front bosses, flanges, ribs, shells, and wall thicknesses.
- Every cosmetic or finish feature that can alter topology, such as fillet, chamfer, shell, or through-all cuts. Verify that it affects only the intended drawing region.
- Every section, half-section, auxiliary section, or local section in the drawing. The model evidence must come from the matching section plane, orientation, and position recorded in the drawing gate. If the section cannot be generated or inspected, mark it `UNVERIFIED`.

If any feature-critical row is `FAIL` or `UNVERIFIED`, do not report `DRAWING_MATCH_PASS` and do not call the model complete. Return to the last clean checkpoint and rebuild only the affected feature group. Do not use a later broad cut, global fillet, or unrelated cosmetic operation to mask a failed view-match row.

## Ambiguity Rules

- Ask for missing dimensions that change topology or fit: hole diameter, center distance, thickness, mate-critical offsets, thread size, shaft diameter, gear/module data, bearing seats.
- Estimate only cosmetic or non-fit dimensions when the user explicitly allows approximation.
- If a drawing has multiple valid interpretations, state the unresolved evidence, present the plausible feature-plan options, explain which features and dimensions change, and ask the user to confirm before generating code.
- Do not select a convenient interpretation and continue modeling. Do not hide assumptions inside the script.

## Assembly Drawings

For assemblies:

1. Identify each part, quantity, and material from the BOM or callouts.
2. Decide whether to model every component or simplify purchased/standard parts.
3. Create/load components first, then build mates from fixed base to moving or dependent parts.
4. Validate degrees of freedom and interference where possible.
5. Save both native assembly and neutral exports if requested.

Hard assemblies are feasible when the drawing contains enough dimensions, views, BOM data, and mate intent. Without those, set `Gate status: BLOCKED`, set `permission_to_generate_code: no`, and ask for the missing evidence. Produce an approximate part or assembly only when the user explicitly requests a rough model, and record `Gate status: APPROXIMATE_ALLOWED`.
