# Drawing Understanding Rules

Use this checklist before generating SolidWorks code from any 2D mechanical drawing, PDF, screenshot, or hand sketch.

## Whole-Drawing Reading

Use the existing ledgers below in this reading order; do not create a second duplicate checklist:

1. Identify the main, projected, section, and local/end views and map them to the same part; do not treat a local view as a detached component without assembly evidence.
2. Trace outer boundaries, section hatching, and hole boundaries across views to identify material and voids. An unhatched region alone is not proof of a hole; establish the section context and connectivity.
3. Establish common datums and centerlines; anchor each local view's origin, plane normal, local axes, and thickness direction to its parent geometry.
4. Assign each dimension to its start/end entities and measurement direction. Distinguish total lengths, partial lengths, radii, and projections before deriving coordinates.
5. Close cross-view relations and topology: concentricity, tangency, symmetry, orientation, wall thickness, hole termination, and passage connectivity.
6. Present the resulting sketch/feature checklist and unresolved points before coding. Reuse recorded user confirmations rather than asking the same question again.

An authorized previous model may corroborate these interpretations, but does not replace drawing evidence. Keep part-specific dimensions and repair examples in the project case files. If the intended values are correct but the created geometry differs, diagnose the script/API execution rather than rewriting the drawing interpretation to fit the faulty result.

- Identify every orthographic view, section, detail, auxiliary view, isometric view, centerline, hidden line, and note.
- Treat every visible dimension and callout as intentional. Map each one to a modeled feature, a verification check, a manufacturing-only note, or an explicit unresolved item.
- Do not discard a drawing item merely because it does not create geometry directly. Material, roughness, tolerance, heat treatment, section marks, centerlines, and title-block data still need an explicit classification.
- Use cross-view arithmetic before sketching. When one view gives a base thickness and another gives an absolute height, calculate the feature length from both values instead of estimating it visually.
- Read the drawing twice: first to infer the part and feature order, then to account for every visible dimension and callout. If the second pass exposes an unused feature-critical item or a contradiction, stop before code generation.
- Stop and ask the user when unresolved information can change topology, passage continuity, fit, mating, or manufacturing intent.
- Treat the drawing as the primary modeling source. Do not open or reverse-engineer a manual `.SLDPRT` unless the user explicitly asks for a reference comparison.

## Dimension Usage and Position Ledger

Before opening SolidWorks for a non-trivial part, record:

```text
Dimension or callout:
Source view:
Target feature:
Role: driving | verification | manufacturing-only | assumption | unresolved
Datum or start entity:
End entity:
Measurement direction or axis:
Cross-view calculation:
Used by feature or check:
Position relations required:
Verification row:
```

Rules:

- Do not start automation while a feature-critical drawing item remains unassigned. If a visible drawing item is intentionally unused, record the reason.
- Every feature-critical linear, angular, radial, diameter, depth, count, or thickness value must state what it measures between. Do not use a dimension as a free length without recording its start entity, end entity, and measurement direction.
- When dimensions are combined, record each term's physical segment, start entity, end entity, and measurement direction. Add lengths only when their segments are consecutive along the same axis; distinguish component lengths, total lengths, and projections to avoid double-counting.
- Do not add a radius, wall thickness, projection offset, or visual extension to a dimension chain unless another drawing item, drafting convention, or user confirmation explicitly supports it.
- If a dimension can be read from a surface, centerline, axis, tangent point, endpoint, or section plane in more than one plausible way and the difference changes feature placement, mark it `unresolved`, set `Gate status: BLOCKED`, and ask before code generation.
- If a feature-critical value is unused, double-counted, used only by visual estimation, or not anchored to a datum, axis, face, centerline, endpoint, tangent point, or section plane, keep `permission_to_generate_code: no`.

## Bidirectional Evidence-Coverage Audit

Before code generation, audit the drawing and checklist in both directions:

1. Drawing to checklist: every visible dimension, diameter, radius, angle, count, thickness, centerline, hidden line, section mark, tolerance, surface note, title-block item, manufacturing note, and positional relation must map to a checklist row, a verification check, or an explicit non-geometry classification.
2. Checklist to drawing: every checklist value, derived coordinate, relation, topology requirement, and assumption must map back to its source view, cross-view calculation, drafting-convention-supported relation, or user confirmation.
3. Unused-item review: if any drawing item is not used or classified, return to the drawing and determine whether it exposes a missing feature, missing constraint, duplicate evidence, manufacturing-only note, or unresolved blocker.
4. Repeat the audit after user corrections. Keep `permission_to_generate_code: no` until the unused and unresolved lists are empty for feature-critical items.

Record:

```text
Evidence ID:
Drawing item:
Source view or section:
Classification: feature-driving | relation-driving | topology-verification | manufacturing-only | title-block | duplicate-evidence | unresolved
Checklist row or ledger item:
Used: yes | no

Evidence coverage audit: PASS | FAIL
Unused drawing items:
Unresolved drawing items:
Checklist values without source:
```

## Geometric Relation Closure

Dimensions alone are not sufficient. Before sketching, identify the geometric relations needed to reproduce the drawing shape and to fully define each sketch.

Record relations such as:

- coincident endpoints for connected contour segments;
- tangency where a straight segment and arc, or two arcs, form a smooth continuous transition;
- concentricity when circles, arcs, bores, or bosses share a centerline;
- collinearity for aligned edges or centerlines;
- symmetry about a centerline or datum;
- horizontal, vertical, parallel, and perpendicular relations;
- equal radius, equal length, circular spacing, and mirror relations when supported by the drawing.

Classify each relation:

```text
Relation:
Entities:
Evidence view or section:
Evidence level: explicit | drafting-convention-supported | user-confirmed | unresolved
SolidWorks relation:
Used by sketch or verification:
```

Use drafting conventions and cross-view evidence, not raster proximity alone. Examples:

- A continuous contour that transitions smoothly from a line into an arc without a drawn corner supports a tangent relation.
- Two contour segments that meet as one boundary support coincident endpoints.
- Circular features crossed by the same centerline support concentricity.
- A repeated pattern about a centerline supports symmetry or equal spacing only when the drawing layout, dimensions, or callouts support it.

Position relations must be recorded before the affected feature is modeled. A local/end/section view can provide shape only after its center, axis, plane normal, and depth direction are tied back to the parent view. For each feature, explicitly list coincidence, tangency, concentricity, collinearity, coplanarity, symmetry, parallelism, perpendicularity, equal spacing, endpoint anchoring, plane normals, and axis sharing when they are visible or required by drafting convention.

If more than one relation set can satisfy the visible drawing and the difference changes topology, passage continuity, fit, or feature placement, mark the relation as `unresolved`, set the gate to `BLOCKED`, and ask the user before generating code.

## Local View Anchor Gate

Detail views, end views, auxiliary views, and section views are not independent modeling sketches. Before using any local view to create geometry, anchor it to the parent view.

Record:

```text
Local view or section:
Parent view:
Parent feature or datum:
Anchor center point:
Plane normal:
Local X/Y axes:
Depth or thickness direction:
Evidence: section mark | centerline | projection relation | shared axis | user-confirmed
Status: confirmed | unresolved
```

Rules:

- End views for tubes, shafts, bosses, and flanges must share the parent feature centerline unless explicit evidence says otherwise.
- A local/end-view sketch plane normal must match the parent axis or section direction before any boss, cut, sweep, or hole pattern is created from that view.
- A section view must define or verify a cut plane tied to the section arrows, datum, centerline, or parent feature. Do not use the section profile as a free-standing side sketch.
- If the local view center, plane normal, local axes, or depth direction is unresolved, set `Gate status: BLOCKED` and `permission_to_generate_code: no`.
- Do not model a convenient approximate position for a local view while hoping to correct it later. Resolve the anchor first.

## Topology Closure

Dimensions and sketch relations do not prove that the resulting 3D part is functionally connected. Before code generation, record the required 3D topology.

## Section Hatching and Void Closure

For section and half-section views, resolve material and voids before choosing any cut depth.

- Hatched regions are solid material. Do not remove hatched material unless another view explicitly shows a cut, bore, slot, or recess passing through that region.
- Unhatched enclosed regions inside a sectioned solid are holes, bores, cavities, or flow passages. Treat them as voids and trace where they start, stop, or connect.
- For a concentric circular bore and outer cylindrical surface, compute radial wall thickness as `(outer diameter - inner diameter) / 2` and record it as a verification item. For eccentric or noncircular sections, determine local wall thickness from the actual boundaries.
- A local bore that connects to a main passage is not automatically a through-all cut through the entire part. Its scope is limited by the section evidence: cut only along the local bore until it opens into the intended passage unless the drawing explicitly marks it as through.
- Do not infer a through-cut from a circular outline alone. Require a through-hole callout, matching section void, hidden-line evidence, or user confirmation.
- If hatch/void evidence conflicts with a planned cut, set `Gate status: BLOCKED` and ask before modeling.
- If the drawing contains a section or half-section, add a post-run section self-check row before code generation. The row must state the section plane, section direction, parent feature or datum, expected solid/void regions, wall thicknesses, and how the generated model will be checked against that section.

```text
Topology item:
Entities or regions:
Required relation: merged | intersecting | tangent | separate | through-cut | internally connected | blind
Evidence view or section:
Verification method:
Status: confirmed | unresolved
```

Examples:

- A branch bore that joins a main passage must be recorded as `internally connected`, not merely as an exterior circular opening.
- A flange, boss, rib, or base that belongs to one casting must be recorded as `merged`.
- A mounting hole labeled as through must be recorded as `through-cut`.
- Separate assembly components must not be merged merely because they touch in one view.

If a topology item cannot be proven from the drawing and the difference changes function, manufacturability, or body count, set the gate to `BLOCKED` and ask the user.

## Sketch Constraint Ledger

For each feature-driving sketch, record:

```text
Sketch name:
Plane or face:
Datum references:
Segments and profiles:
Dimensions:
Relations:
Relation evidence:
Derived coordinates:
Source views:
Expected feature:
```

For paths with arcs, also record the center, radius, start point, end point, sweep direction, included angle, and tangent relations. For a 3D path, constrain every segment and point in all required directions.

## Sketch Definition Gate

Every sketch that drives a boss, cut, sweep, loft, rib, hole, pattern, or other dependent feature must be explicitly defined before the feature is created. This includes sketches on datum planes, faces, and 3D paths.

Choose and record one definition mode for each planned sketch:

- `coordinate_driven`: the drawing dimensions are converted into explicit API coordinates, radii, angles, depths, and topology before sketch creation. In this mode, the code parameters are the definition. Verify the computed geometry, sketch regions, feature result, and required relations. Do not add SolidWorks display dimensions merely to make `ISketch::GetConstrainedStatus()` report `3`.
- `constraint_driven`: the sketch intentionally depends on SolidWorks dimensions or relations for editability or because the geometry is easier to define through relations. In this mode, use `ISketch::GetConstrainedStatus()` and require `swFullyConstrained = 3`. If the status is not `3`, stop at that sketch and repair missing or conflicting dimensions and relations before continuing.

Every formal sketch constraint must be traceable to a drawing dimension, cross-view calculation, datum choice, geometric relation, or explicitly approved assumption. Do not use blanket fixing or automatic full-definition operations to hide missing understanding.

## Gate Status

Record exactly one status in the local feature plan:

- `CONFIRMED`: feature-critical evidence is closed and formal code generation is allowed.
- `BLOCKED`: one or more unresolved items can change geometry or fit; ask the user before generating code.
- `APPROXIMATE_ALLOWED`: the user explicitly requested a rough model and the assumptions are recorded.

Also record:

```text
permission_to_generate_code: yes | no
```

For a non-trivial drawing, do not open SolidWorks or generate modeling code until permission is `yes`.

## Code Handoff Gate

Generate modeling code only after:

1. Every major feature is traced to the relevant views and sections.
2. Feature-critical dimensions have been assigned or explicitly confirmed by the user.
3. The feature order is written in dependency order.
4. Each local/detail/end/section view used by a feature has a confirmed anchor ledger row.
5. Each planned sketch has a constraint ledger.
6. Every functional 3D connection, separation, and through-cut is recorded in the topology ledger.
7. The verification plan includes the selected sketch definition gate, rebuild checks, body count, passage continuity where applicable, and section comparison when the drawing contains sections.
8. Every visible drawing item is assigned an evidence ID and linked to a checklist row, ledger item, verification check, manufacturing note, title-block item, cosmetic detail, or explicit unresolved item.
9. Every checklist parameter traces back to drawing evidence, cross-view arithmetic, drafting-convention-supported inference, or user confirmation.
10. Every feature-critical dimension has a start entity, end entity, direction or axis, formula when derived, modeling use, and verification row.
11. Every feature-critical positional relation is recorded with its evidence source and the sketch/feature/check that uses it.
12. The local feature plan records a gate status and `permission_to_generate_code: yes`.
