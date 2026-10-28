# Layered backgrounds (workflow v10)

Choose the visual explanation first. Select one `background-pattern`; add zero, one or both `background-effect` layers only when they improve the scene. Straight Grid is the neutral fallback, not a required choice. Simpler patterns are valid: Straight Grid, Dot Grid, Diagonal Lines and Editorial Lines. Topography, Wavy Grid and 3D Grid are additional choices inspired by supplied references.

Use `vidkit library search --kind background-pattern` and `--kind background-effect`, then `library show <id>` to inspect status, source and limits. New candidates first use `vidkit library preview <id> --still-only`. This renders a 1080x1920 PNG at a quarter cycle and creates no MP4. Present all requested pattern images, then stop for user feedback before generating motion. Do not interpret approval of the implementation plan as approval of these images.

After the user accepts a candidate's image, run `vidkit library preview <id>` for its two-loop motion clip. Inspect loop joins, the speed of reveal and phone readability before requesting promotion with `library approve`. A still-only preview cannot satisfy motion checks or promotion. Video concept/export approval and library promotion remain independent. An already approved library entry can be reused without repeating candidate image review.

Brief and storyboard use the same configuration:

```json
"background": {
  "patternId": "straight-grid",
  "effectIds": []
}
```

For a composed background, examples of effect IDs are `radial-glow-overlay` and `fireflies-overlay`; effect order is draw order. Optional `patternProps` and `effectProps` adjust `density` (0.5-2), `lineWidth` (0.5-6), `opacity` (0-1), `motionIntensity` (0-1), and `color` (CSS color). Effect props are keyed by selected effect ID. Omitted props use the component presets. The preview's black/white palette is a review fixture, not a requirement for every video.

Pattern presets use 20% line opacity by default. Keep patterns subordinate to foreground visuals; inspect them with title, primary visual and captions, and lower opacity further if they compete. Increase contrast only when the scene requires it.

The timeline contains `backgroundLayers` with each layer's ID, kind, version, source checksum, loopSeconds and settings. Source packages are loaded through the generated job registry. Rendering order is theme background color, pattern, transparent effects, scene visuals, captions. Frame-based phases use the absolute video frame; no scene resets, CSS animation or real-time clocks. Default loops are twelve seconds.

New candidates cannot enter timed video rendering until they have a current motion preview; a creative brief may propose a pending candidate. Changing any layer or its props needs a new concept preview and approval while preserving unchanged narration/STT. Inspect custom scene fills: they may obscure the background. `backgroundMotion` remains not-run until actual motion and seams are inspected; a PNG proves neither.

Candidate packages live in ignored `workspace/library/`; only separately approved source, fixtures and manifests are copied to `renderer/library/approved/`. V7-v9 jobs retain `backgroundId` and their existing components. Do not migrate, rebuild or render old videos for this change.
