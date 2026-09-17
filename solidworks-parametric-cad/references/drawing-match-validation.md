# Drawing Match Validation

Use this reference for the drawing contract and acceptance reporting. Detailed automated measurements, section capture, and proving-view loops in this reference apply only to user-requested `full_drawing_match` mode. Default `basic_plus_human_review` mode performs one basic check and hands detailed drawing comparison to the user; an earlier mismatch does not automatically authorize a full validation loop.

- Basic checks retain detection of failed features, known sketch-value mismatches, rebuild errors, unexpected body count, and obvious shape errors. Stop on an actual error; never continue merely because final review is manual.
- Report `AWAITING_USER_REVIEW` until the user accepts the model, then `USER_ACCEPTED`. Keep automated drawing-match status unverified unless the full checks really passed.
- Record from-zero reproducibility independently: `NOT_RUN`, `PASS`, or `FAIL`, with the executed entrypoint and result log. Local repair success does not establish replay success.

## Separate generation from acceptance

Coordinate-driven construction is valid. If a line is computed from `(0, 0)` to `(100, 0)`, do not add a redundant display dimension merely to force the line to 100 mm. Qualify the millimetre conversion and primitive helper once, then reuse it.

The independent validator exists to catch different failures:

- the generator used a value that does not match the drawing contract;
- a dimension chain was double-counted or assigned to the wrong physical segment;
- the correct size was created on the wrong plane, datum, direction, or local axis;
- correct individual features produced the wrong topology or passage connectivity;
- the requested proving view or section was not actually activated;
- a successful API call produced a valid but drawing-inaccurate model.

Do not use generator inputs as proof of model output. `PASS BY CONSTRUCTION` is not a drawing-match result. Each acceptance row must cite an actual model measurement or inspected proving view, its expected result, and the comparison outcome. Missing evidence is `UNVERIFIED`; a measured mismatch is `FAIL`, even when the script and geometry checks pass.

## Single-source drawing contract

For a non-trivial part, compile the confirmed drawing ledger into one JSON or YAML contract before generating code. Record at least:

```text
schema_version
part_id
units
source drawing and scale
gate status and permission_to_generate_code
unresolved items
coordinate-system origin and global axes
per-feature evidence IDs
per-feature datum or local frame:
  origin
  normal
  local_x
  local_y
dimensions with start entity, end entity, and measurement direction
derived formulas with physical segment meanings
geometric relations
topology requirements
verification checks and tolerances
required proving views and sections
```

Rules:

- Generate every feature-critical numeric input from the contract. Do not maintain a second handwritten parameter table in the script.
- Record the contract content hash in the execution log.
- Record which contract paths were consumed. Missing required paths block generation.
- Store each physical segment separately with its start and end references. Compute total lengths from those segments; never use a total length as a component length and then add an already included segment again.
- If a local view lacks an anchored origin, normal, local X/Y axes, or depth direction, keep the gate `BLOCKED`.
- If feature-critical drawing evidence remains unresolved, the run may proceed only as `APPROXIMATE_ALLOWED` after explicit user approval and cannot claim `DRAWING_MATCH_PASS`.

## Verification layers

### Primitive qualification

Run once per helper/API signature or after the helper changes:

- millimetre-to-metre conversion;
- sketch plane and local-coordinate conversion;
- line, arc, circle, and rectangle coordinates;
- boss/cut depth and direction;
- sweep profile/path selection;
- standard view activation;
- section-view creation;
- screenshot refresh and file output.

Normal production runs do not need to remeasure every low-level line after these helpers pass qualification.

### Per-feature checks

After each feature group, independently reload the drawing contract and inspect the resulting model:

- owning sketch/feature exists;
- expected body count and merge state;
- feature center, axis, plane normal, and local X/Y directions;
- critical diameters, radii, thicknesses, lengths, angles, counts, and pitch values;
- dimension-chain endpoint, not just each input term;
- intended through/blind/internal-connectivity relation;
- matching orthographic, local, or section proving view.

Stop on the first failed row and return to the owning feature group.

### Whole-part checks

Before final delivery, require:

- rebuild success and no SolidWorks geometry errors;
- expected body/component count;
- overall envelope and datum-relative feature positions;
- functional passage connectivity and absence of destructive unintended cuts;
- all required orthographic, local, and section comparisons;
- native save and requested neutral exports;
- no unresolved feature-critical evidence.

## Proving-view integrity

For each requested image, record:

```text
requested view
activated standard/custom view identifier
section plane and section creation result when applicable
output path
image hash
```

Front, top, isometric, local-end, and section images must be demonstrably different when their orientations or section states differ. If two required views unexpectedly have the same hash, treat the capture chain as failed and do not use those images as drawing-match evidence.

For SolidWorks standard views, call `ShowNamedView2("", view_id)` with the matching `swStandardViews_e` identifier instead of using a generic `-1` custom-view identifier. Verify `ActiveView.Orientation3.ArrayData` against `GetStandardViewRotation(view_id)`, then force a graphics redraw before saving the bitmap.

Before capturing ordinary views, explicitly remove any active model section view. Standard-view rotation verification proves camera orientation, but it does not prove that section visualization is off.

## Result levels

- `EXECUTION_PASS`: the script completed and produced the expected files.
- `GEOMETRY_PASS`: rebuild, geometry checks, and body/component counts passed.
- `DRAWING_MATCH_UNVERIFIED`: required measurements, local frames, topology, views, or sections were not completed.
- `DRAWING_MATCH_FAIL`: at least one drawing-contract row differs from the model.
- `DRAWING_MATCH_PASS`: every feature-critical contract row and proving view passed and no unresolved item remains.

Human inspection is the final audit, not the first mechanism that discovers gross drawing mismatches.
