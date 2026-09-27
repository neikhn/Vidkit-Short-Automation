# V4 validation — 2026-09-26

## Verified

- 36 Python tests pass; renderer TypeScript compiles; Git whitespace checks pass.
- Eight skill frontmatters and local Markdown links checked.
- Custom TSX fixture runs through generated registry, concept, full preview and export without adding a product branch to the shared renderer. Studio server started and built this composition; browser interaction was not inspected.
- Three synthetic jobs rendered with current dependencies:

| Type | Job | Export |
| --- | --- | --- |
| Product / custom TSX | `f5d0309ddfad` | `workspace/videos/2026-09-25_v4-fixture-product-introduction_f5d0309ddfad/exports/v4-fixture-product-introduction.en.r4.mp4` |
| Mechanism / branch flow | `5d37e02b4f41` | `workspace/videos/2026-09-25_v4-fixture-mechanism-explanation_5d37e02b4f41/exports/v4-fixture-mechanism-explanation.en.r5.mp4` |
| Numeric comparison / log chart | `05917ccc306e` | `workspace/videos/2026-09-25_v4-fixture-numeric-comparison_05917ccc306e/exports/v4-fixture-numeric-comparison.en.r5.mp4` |

- Tests cover snapshots/diff, import dependencies including CSS resources, local code packages, candidate promotion, anchored/after event ordering and errors, continuity frame origins, feedback metrics and concept audio segment selection.
- Candidate promotion uses mocked rendering in its unit test. Local custom code and the approved branch-flow primitive were also rendered using actual Remotion.
- Representative concept stills were inspected. This is not full playback, transition inspection or audio listening. QA reports retain `not-run` for checks without supplied evidence.

## Remaining validation and implementation limits

- Fixtures use silent WAVs. They do not test narration quality or establish that videos are more engaging.
- Automatic DOM overflow measurement is not implemented; `layoutOverflow` requires explicit inspection evidence. Caption/focus intersection uses declared normalized geometry.
- No human review time or revision requests were collected. Preview counts include technical verification; they are not a creativity metric. Record actual feedback with `add-feedback` before comparing review effort.
- Dependency tracing supports literal local imports, CSS resource references and literal `staticFile` paths. Computed runtime paths must be declared through job assets or package files; arbitrary computed imports are not discoverable statically.
- Dependency versions are locked by package lock; restoring an executable environment still requires installing those versions.

The existing Jev job was not changed, migrated or rendered. Its prior local code and assets were preserved. No paid service was called.
