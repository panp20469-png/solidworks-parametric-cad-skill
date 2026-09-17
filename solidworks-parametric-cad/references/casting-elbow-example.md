# Casting Elbow and Manifold Reading Example

Use this reference only for cast elbows, manifolds, pipe joints, and similar one-piece passage parts. It is a drawing-reading aid, not a normal-use regression requirement. Numeric examples and B/C view labels below belong to the illustrated elbow case; do not use them as defaults for another drawing.

## Core Rule

Treat the flow passage as the model spine. Resolve external shape, internal bores, branch connections, flange faces, wall thickness, and proving section views before writing SolidWorks code.

A single casting drawing normally represents one physical part, not an assembly. Temporary multi-bodies are allowed only as construction; the final model must be one solid body.

## Cross-View Reading Pattern

For a cast elbow drawing:

1. Use the largest primary view to infer the main passage path and external silhouette.
2. Use section views to verify bore diameter, wall thickness, flange depth, boss depth, and internal passage continuity.
3. Use end views to define flange outlines, bolt-hole counts, and hole distribution.
4. Use auxiliary or local views to locate side branches, bosses, and datum planes.
5. Use the isometric view only as a sanity check, not as the driving source.

Do not model from one view alone. Every major feature must be traced to the relevant views before automation.

## Base Example

For the known elbow-style example:

- The base is a square plate controlled by the plan/section view.
- Base thickness comes from the section view.
- Rounded corners and mounting holes come from the A-A/plan evidence.
- Mounting holes must be through-cut and coplanar with the base, not floating above it.

## Main Passage Example

For the main curved tube, combine the section view with the main half-section:

- Start from the base-top datum, not the bottom datum, when the section gives base thickness.
- Use the vertical straight segment, the tangent arc, and the inclined straight segment as separate constrained path entities.
- Use the arc radius, included angle, tangent relations, and endpoint height together. Do not replace this with an arbitrary three-point arc.
- Before sketching, solve and record the line endpoints, arc center, tangent points, sweep direction, and final endpoint.

## Branches, Flanges, and Bosses

- For a top three-ear flange, use the end view for the outline and bolt pattern, then the main or section view for thickness.
- For a top end view such as B on the known elbow drawing, the end-view center is the endpoint of the main inclined tube axis, the end-view plane normal is the inclined tube axis direction, and the flange thickness direction follows that axis. Do not place the B outline, center hole, or 3-hole pattern on an arbitrary global plane or at an independent offset.
- End-view ear radii and base corner radii are local outline features, not global finishing operations. Build the top flange ears in the B end-view sketch and build the base corner `R10` in the base sketch or a base-thickness-only operation. Do not add a late global fillet, chamfer, or through-all corner cut after the branches and top flange exist, because it can damage unrelated views and still look like a script success.
- For a side branch, first establish its centerline from height, angle, and length stackup. Create a datum plane normal to that centerline. Use local end-view and section evidence together for the boss and bore scope.
- For the illustrated side-branch stack `25` plus flange thickness `6`, first identify each dimension's start and end references and direction. If they are consecutive axial segments, their total is `25 + 6 = 31`; do not model a 31 mm segment followed by another 6 mm flange. If either dimension is a projection or uses a different datum, derive the endpoint from those references instead. Do not add main-pipe radius, wall thickness, or visual overlap without drawing evidence.
- For a front boss, locate it from the main half-section and the proving section. Verify that its bore reaches the main passage.
- Treat branch and boss bores as functional internal connections. An exterior opening is insufficient; a section or internal check must prove connection to the intended passage.
- In sectioned elbows, read hatch and voids as topology. Hatched material is solid; unhatched enclosed regions are bores or cavities. For the known elbow drawing, `D40` outside with `D30` inner passage proves a `5 mm` tube wall, and `D24` outside with `D12` bore proves a `6 mm` boss wall. A side or front local bore may connect to the main `D30` passage, but it must not be cut through the whole casting unless the drawing explicitly marks a through-cut.

## Validation Focus

- Main passage follows the solved path.
- Branch passage and front-boss bore are internally connected to the main passage.
- Flange and mounting holes match their drawing counts and locations.
- Section-view wall relationships are checked.
- Final solid body count is one.

If the user explicitly asks to compare a manual `.SLDPRT`, use it only as optional QA evidence after the drawing-derived feature plan exists.
