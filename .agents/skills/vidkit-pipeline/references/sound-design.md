# Sound design contract

Reviewed 2026-09-26. Music/SFX are separate from narration. Transcribe clean narration only. Sound design is optional for existing jobs; an explicit empty plan removes legacy whooshes. Concept approval covers audio direction; export approval covers the current mix. Do not introduce a budget guard or another approval stage.

## Plan

Import JSON using `vidkit add-sound-plan <id> <language> <file>`:

```json
{
  "schemaVersion": 1,
  "music": {
    "id": "underscore",
    "purpose": "Support a calm technical explanation",
    "prompt": "Sparse electronic documentary underscore, gentle pulse, room for speech, resolved ending",
    "forceInstrumental": true,
    "gainDb": -22,
    "duckDb": -10,
    "fadeInMs": 600,
    "fadeOutMs": 800
  },
  "sfx": [
    {
      "id": "result-ping",
      "purpose": "Mark the output becoming visible",
      "prompt": "A short soft electronic confirmation ping, dry quick decay, no voices",
      "durationSeconds": 1,
      "sceneId": "explanation",
      "eventId": "output-reveal",
      "gainDb": -16,
      "impactMs": 0,
      "fadeInMs": 15,
      "fadeOutMs": 40
    }
  ]
}
```

Replace `sceneId`/`eventId` with `wordIndex` to anchor to narration. Word anchors are zero-based transcript indexes; motion event IDs are scoped by scene. Cue IDs are unique, lowercase and hyphenated. `assetId` selects imported/reused audio; otherwise generation registers the cue ID. A cue may retain both prompt and assetId for generation provenance.

Optional cue fields: `offsetMs` (signed), `trimStartMs`, `impactMs` (position inside the original file), `durationMs`, `gainDb`, `fadeInMs`, `fadeOutMs`. Audible impact is aligned to the anchor plus offset. A negative start or overlong cue fails; edit trim/duration/anchor intentionally.

Generation defaults: Music `music_v2_5`, SFX `eleven_text_to_sound_v2`; explicit `modelId` overrides remain supported. Existing assets are not regenerated when the default changes.

Music defaults to the whole video. `trimStartMs` selects its source start, `offsetMs` delays its entrance, `loop` enables repeated segments and `crossfadeMs` controls their overlap. Non-loop music must cover its intended range. Fade duration must fit the segment. `lengthMs`, `modelId`, `forceInstrumental` affect generation; `duckDb` changes the local envelope.

Music ducking joins transcript words separated by at most 400ms, ramps down over 100ms and releases over 220ms. It is a timing-based envelope, not acoustic voice detection or mastering. Refine gain after listening. Short silences intentionally retain the lower gain to avoid pumping.

Sound-assets `checked` means the manifest and media passed technical import checks, not that anyone listened. Narration paths are unchanged. A creative brief may include `soundDirection: {"music": "...", "sfx": "..."}`; then `next` and timeline compilation require an explicit sound plan. Use an empty plan to choose silence deliberately.

## Files and operations

- Job audio assets: `workspace/videos/<video>/audio-assets/{sfx,music}/<checksum>.<actual-extension>` and immutable sound-assets manifests.
- Per-language sound-plan/request/mix revisions: `<language>/audio/`. Existing narration paths remain compatible.
- `vidkit audio import <id> <file> --asset-id <name> --kind sfx|music --description "..." --source "..." --usage-basis "..."` registers WAV/MP3 by contents, not the supplied suffix.
- `vidkit sfx generate <id> <language> --cue <cue-id>` and `vidkit music generate <id> <language>` reuse identical generated content. `--new-take` explicitly requests another take; unresolved requests still block.
- `vidkit audio requests <id> <language>` lists persisted attempts. `vidkit audio recover <id> <language> <request-id> <file>` registers a returned file without another API call. Do not assume a timeout means no charge occurred.
- `vidkit timeline <id> <language>` compiles cues; `vidkit audio preview <id> <language>` renders a WAV with the same tracks as Studio/video. `preview` and `render` use the same mix data.
- `vidkit audio share <id> <asset-id> --purpose "..."` explicitly copies a reusable sound into checksum storage under `workspace/library/audio/`. Search with `vidkit library search music --kind asset`, inspect `library show/preview`, and register it in another job with `vidkit audio reuse <id> <library-id> --asset-id <name>`.

`vidkit audio reindex` rebuilds its SQLite index and discoverable candidate manifests from checksum folders. Generated source files stay outside Git; sharing is separate from approving the video.

Requests record prompt, settings, state and local output; API keys are excluded. Persist original files. Import requires provenance; generated usageBasis records account terms as needing publication verification, not a blanket rights guarantee.

## Dependency and QA

Changing sound-plan/assets invalidates timeline, mix, preview, QA and export approval, retaining narration/STT. New narration invalidates transcription/timing while retaining sound-plan and sound source files. Storyboard changes recalculate event anchors. Compiled timelines lock the plan revision and referenced asset checksums.

QA `audioLevels` measures decoded sample peak/RMS when ffmpeg is available. It is not true-peak metering or listening. `soundDesign` and `audioListening` remain pass/fail/not-run with actual evidence. Inspect voice intelligibility, cue synchronization, loop joins, fades, emotional framing and noise/clicks in the complete preview. Unchecked items stay not-run.
