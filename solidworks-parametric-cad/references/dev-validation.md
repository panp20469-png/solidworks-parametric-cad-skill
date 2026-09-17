# Skill Development Validation

Use this file only when maintaining, debugging, or evaluating the skill itself. Do not run these regressions during normal user modeling unless the user explicitly asks to test or improve the skill.

## Regression Order

Separate helper tests, recorded case replay, and unfamiliar-drawing evaluation. See `geometry-handoff.md` and `elbow-replay-evidence.md`; the existing basic replay is not the full acceptance defined below. Do not repeat the recorded build just to edit documentation.

For an updated planar arc wrapper, test local units, both directions, finite positive radii, coincident endpoints, 2D-only context, state restoration on failure, and measured-radius rejection. Mock tests validate dispatch logic only; live MCP feature acceptance remains a separate check after server reload. For generalization, evaluate a changed parameter set and an unfamiliar drawing without copying the elbow dimensions or feature sequence, and record interventions and drawing acceptance.

1. First pass the known cast-elbow regression from the drawing alone.
2. Only after that regression passes, test an unfamiliar medium-complexity single-part drawing.
3. Treat blind testing before the known regression passes as skill-development noise, not normal production modeling.

## Cast-Elbow Regression Acceptance

The cast-elbow regression passes only when:

1. The part is built from the drawing alone in one SolidWorks instance.
2. Every feature-driving sketch passes its recorded definition mode: coordinate/parameter-driven sketches match computed geometry and feature checks; constraint-driven sketches report `swFullyConstrained = 3`.
3. The final model contains one solid body.
4. The main tube follows the two straight segments plus tangent `R35` arc and reaches the specified endpoint height.
5. The branch bore and front-boss bore are internally connected to the main passage.
6. The base holes, top three-ear flange holes, and branch-flange holes match their drawing counts and locations.
7. Non-destructive section comparisons match the proving drawing sections.
8. The result reaches `EXECUTION_PASS`, `GEOMETRY_PASS`, and `DRAWING_MATCH_PASS`.
9. The run records one machine-readable drawing contract and its hash; every required feature-critical contract path is consumed by the generator and checked by the independent validator.
10. Front, isometric, local, and section proving images record the activated view/section state and do not collapse to identical hashes.
11. The completed regression can be repeated three times from a clean part document without manual geometry edits and produces the same contract checks, body count, key measurements, and topology result.

## Normal-Use Boundary

For ordinary user requests, do not require this regression before modeling a new drawing. Use the drawing gate and automation rules in `SKILL.md` and the drawing references instead.
