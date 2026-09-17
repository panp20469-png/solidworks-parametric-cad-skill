# Drawing-to-API Handoff

## Transferable construction rules

Read the existing drawing ledger first; do not create a second independent dimension table. For each feature, trace source view and dimension -> datum/start/end/direction -> geometric frame and extent -> native operation and selection -> measured result. A numerical length without its two anchors is incomplete. Detail views belong to the parent part, not to a disconnected object.

For sections, identify the cutting plane and material hatching before classifying passages. A bore reaching an internal cavity is not automatically a through-all cut through the opposite wall. Record the intended termination surface and affected body. Restrict local fillets/chamfers to the owning contour or selected edges.

For a planar outline:

1. Resolve its world origin, normal and local axes from the parent feature, not screen coordinates.
2. Create/select the reference plane and a 2D sketch. Use its actual `ModelToSketchTransform` for world-to-sketch conversion; verify transformed points are on the sketch plane. Convert millimeters to API meters once at the boundary.
3. Preserve handedness when converting arc directions. For center/radius-defined arcs, use center/start/end/direction construction. In coordinate-driven construction, temporarily disable inference with `AddToDB` and restore its prior value in `finally`.
4. Read back actual arc radii and relevant endpoints/centers; check closure and intended regions before the dependent feature. A successful API return or mathematically closed input does not prove the created sketch matches it. Stop on the first mismatch; repair that sketch, not a later feature.

3D sketches remain appropriate for spatial paths and independently validated spatial profiles. The recorded planar-profile failure does not prove all 3D arc APIs are defective. Do not silently convert every sketch type or apply global fixing constraints.

## Failure attribution and repair retention

- Drawing interpretation: wrong dimension anchors, section material/void, connectivity, or parent/detail relationship. Correct the ledger and contract first.
- Geometry translation: ledger is correct but frame, units, arc direction, selection, or feature termination is wrong. Correct the shared native-operation helper or drawing-local mapping.
- Runtime construction: intended parameters are correct but measured SW entities differ. Record the first API, expected/actual geometry and state. Do not blame the drawing without evidence. Preserve uncertainty about the underlying solver/COM mechanism.
- Environment: attachment, active-document changes, saves and recording failures are separate from geometry. Do not retry by launching another SW instance.

After a local repair, replace the defective construction in the normal entrypoint; do not retain a normal workflow of intentional failure followed by a repair script. Preserve the last working model and a versioned entrypoint, contract, dependencies and execution log. From-zero verification requires an authorized fresh part, no manual edits or hidden retries. Record replay and drawing acceptance separately.

## Skill and MCP boundary

The skill derives the drawing plan; Codex chooses native tools and supplies complete parameters. MCP validates and dispatches those operations to SW. The server does not infer drawing intent. Keep generic sketch/plane/extrude/cut/sweep/fillet tools in MCP; keep part-specific sequences in the case runner. Do not add elbow/flange/base object tools.

Verify the configured server path and tool schema before use. Updating disk code does not update an already-imported MCP process: reconnect/restart the MCP host and validate the affected tool before declaring it live. A direct Python/COM build proves that route, not that every step traveled over MCP. Keep both validation claims separate.

For the known case and evidence limits, see `elbow-replay-evidence.md`. For maintenance tests, see `dev-validation.md`.
