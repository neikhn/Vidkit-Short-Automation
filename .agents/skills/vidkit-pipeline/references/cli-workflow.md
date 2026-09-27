# Vidkit CLI workflow

Runtime contract v4 for new jobs. Workspace paths are relative to `workspace/`; existing v2/v3 jobs keep their workflow. Run `vidkit next <job-id> --language vi --json` for the next missing or blocked stage. `vidkit show` lists revisions and checksums.

## Production sequence

```powershell
vidkit create "Product" --languages vi --mode review --source-url https://example.com
vidkit add-source <id> source-pack.json
vidkit add-script <id> vi script.json
vidkit add-brief <id> vi brief.json
vidkit preview <id> vi --stage concept
vidkit approve <id> vi concept --reviewer "Name"
vidkit tts <id> vi
vidkit transcribe <id> vi
vidkit add-asset <id> official.png --type artwork --description "Product artwork" --usage-basis "official media" --source-url https://example.com/media
vidkit add-caption-plan <id> vi captions.json
vidkit add-storyboard <id> vi storyboard.json
vidkit timeline <id> vi
vidkit preview <id> vi
vidkit qa <id> vi
vidkit approve <id> vi export --reviewer "Name"
vidkit render <id> vi
```

Caption plan is optional; Python creates a semantic fallback. `tts` and `transcribe` call ElevenLabs and can incur cost. `studio` is interactive; `import-render` records its MP4 as a preview in v3. `timeline --draft` is only a technical test.

When sound design is requested, include `soundDirection` in the brief and read the [sound contract](sound-design.md). After narration/transcript/storyboard, import the sound plan and generate/import its required assets before `timeline`. `sfx generate` and `music generate` use paid ElevenLabs APIs. `audio preview` renders a WAV locally; Studio/video use the same tracks. Sound design uses the existing concept/export gates.

## Source and brief

Source pack has non-empty `claims` with unique `id`, `statement`, `sourceUrl`, `publishedAt` (nullable), `retrievedAt`, and `uncertainty` (nullable). Visual descriptions must be checked against the actual asset.

Legacy v3 creative brief example (v4 adds the fields described below):

```json
{
  "angle": "Show the product decision path",
  "theme": "dark-grid",
  "hook": "What does the tool return?",
  "visualStrategy": "One API response and one diagram, each tied to a claim",
  "screenshotUnavailable": true,
  "screenshotAlternative": {
    "type": "api-example",
    "sourceUrl": "https://example.com/docs",
    "reason": "The console requires login"
  },
  "frames": {
    "hook": {"headline": "A useful product hook", "visualNote": "Brand name with generic explanatory graphic"},
    "evidence": {"headline": "The API response", "visualNote": "Enlarge the verified response fields"},
    "takeaway": {"headline": "The practical limit", "visualNote": "One conclusion with supporting source"}
  }
}
```

For v4, `add-brief` requires `beats` with development and approach, two `explanationAlternatives`, `chosenExplanation`, and `conceptPreview.scenes` with hook/evidence/takeaway roles and provisional times. `preview --stage concept` renders a motion clip and three actual frames before audio. v3 retains its static frame behavior. Concept approval checks the current script, brief and preview; changing script or brief requires new approval.

If valid audio exists, concept scenes reuse matching source ranges. Set `audioStartMs` to select the narration segment when provisional scene times differ from the recording. Explicit ranges outside the audio fail validation; unmapped ranges that exceed the recording stay silent and are listed in concept metadata. Timing remains provisional and must be reviewed after STT.

Add a job-specific TSX visual with `vidkit add-visual <id> vi <manifest.json>`, then `vidkit preview-visual <id> vi <visual-id>`. A manifest needs `kind: component`, `id`, semantic `version`, `description`, `propsSchema`, `entrypoint` and `fixture`. The fixture is a Remotion props JSON whose scene uses the component ID. Package local imports with the source; code lives under the job's `visuals/` directory. `vidkit checkpoint <id> vi` copies source and renderer dependencies; `vidkit diff <id> vi` compares the latest copy to current edits.

## Caption plan

```json
{
  "groups": [
    {"startWord": 0, "endWord": 5},
    {"startWord": 6, "endWord": 11}
  ]
}
```

Groups partition all normalized transcript words, with no gap, repeat or reordering. For condensed numeric display, a group may include `displayTokens`: `{"text":"$0.042","startWord":6,"endWord":11,"spokenText":"zero point zero four two dollars"}`. Exact transcript wording is validated.

## Storyboard

Use `schemaVersion: 4` for new jobs, `language`, `theme`, and non-empty `scenes`. Each scene requires `id`, `layout`, `title`, `startAnchor.wordIndex`, `endAnchor.wordIndex`, and `development` with understanding/object/action/result/connection. Word ranges partition the full transcript. Existing layouts remain, and `layout: custom` selects a registered component with `component`, `componentVersion`, and `componentProps`. Optional `entities`, `events`, `continuityGroup`, `referenceIds` and `focusRect` support visual progression. Events use `wordIndex` or `after`, optional `offsetFrames`, `durationFrames` and `holdFrames`; Python computes frames and rejects cycles or overflow.

```json
{
  "schemaVersion": 4,
  "language": "vi",
  "theme": "dark-grid",
  "scenes": [
    {
      "id": "hook",
      "development": {"understanding": "The product promise", "object": "Product artwork", "action": "Reveal one claim", "result": "A visible capability", "connection": "Explain how it works next"},
      "layout": "brand-hook",
      "title": "Tên sản phẩm và lời hứa",
      "body": "Một vấn đề rõ ràng",
      "claimIds": ["claim-1"],
      "assetId": "official-artwork-12345678",
      "assetRequired": false,
      "startAnchor": {"wordIndex": 0},
      "endAnchor": {"wordIndex": 11},
      "motion": {"cues": [{"type": "zoom", "wordIndex": 5}]}
    }
  ]
}
```

The example shows one scene shape; a real storyboard must cover the last word. Crop is `{x,y,width,height}` normalized against the original image, with no region outside it. Python resolves all word anchors and motion cue timestamps. A referenced component/theme must exist in the library; candidate components are allowed in automatic jobs but not promoted by export.

## Library and QA

`vidkit library search/show/preview/add/approve` operates on manifests and source packages. After `library add`, run `library preview <candidate-id>` before using or approving it; a manifest, source or fixture edit requires another preview. Components may declare a TSX `entrypoint` without `baseComponent`, or configure an existing base. Fixtures must exercise the candidate ID and props; themes must use their ID and exact style tokens. Preview includes a motion clip. Approved source and fixtures are Git-versioned under `renderer/library/`; candidates are under ignored `workspace/library/`. Promotion copies the package and remains independent of export approval.

`vidkit qa` writes a report with `automatic`, `mediaProbe`, `frameInspection`, `transitionReview`, `fullPlayback`, and `audioListening`. Each is `pass`, `fail`, or `not-run` with evidence. A review file passed to `vidkit qa <id> vi <file>` supplies the last four checks. An export approval is tied to the current timeline, preview and QA revisions. `render` in review mode requires that explicit approval. Automatic export still blocks on validation failure and never claims that unperformed viewing/listening occurred.
