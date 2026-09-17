# Elbow Replay Evidence (2026-09-13)

Case paths below are relative to the original project root, not to the installed skill. Do not treat missing local case artifacts on another machine as a validated installation.

- Normal entry: `elbow_clean_rebuild/elbow_delivery_20260913/working/elbow_clean_rebuild/run_elbow.py`.
- Frozen prior chain: `elbow_clean_rebuild/elbow_delivery_20260913/legacy_two_stage/`.
- Source inventory: `elbow_clean_rebuild/elbow_delivery_20260913/working_code_manifest.json`.
- Logs under the normal entry's `output/`: `elbow_436_from_zero_20260913_154850.json` and `elbow_436_from_zero_20260913_160201.json`; corresponding native parts and recording logs accompany them.

The recorded complete builds took 103.7 and 111.11 seconds. Both reached `BASIC_CHECK_PASS`, one body, zero reported geometry errors, rebuild and native save success. Local fillets and cosmetic threads were included. These are a reproducible known-case result, not independent full drawing acceptance or evidence of arbitrary-drawing competence. Detailed acceptance remains human review unless separately recorded.

The repeated top-profile failure occurred while constructing a planar profile through world-space 3D-sketch three-point arcs. An intended R5 was read back as approximately 8.54724576 mm. Reconnecting alone did not resolve it; local repair success did not prove fresh replay. The successful replacement used an explicit reference plane, 2D sketch, actual world-to-sketch transform, center-defined arcs and radius readback. The deepest SW inference/solver cause was not independently isolated. Earlier wrong positions and excessive cuts were separate drawing/datum/termination errors, not explained away by this API fix.

The recorded runner uses Python/COM helpers directly. Do not label these recordings as verification of the newly updated MCP arc wrapper. Preserve the verified delivery copy when updating the active server; validate the changed wrapper separately.
