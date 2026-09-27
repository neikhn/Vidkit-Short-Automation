# Vidkit

Vidkit produces short product explainers from researched sources. An agent handles editorial work; Python tracks revisions and validates handoffs; ElevenLabs supplies narration, word-level transcription, sound effects and background music; Remotion renders a 1080×1920 video.

For an overview of the complete project, read the [English project report](docs/project-report.md).

## Setup

Requires Python 3.11+, Node.js, and npm.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
cd renderer
npm install
cd ..
vidkit doctor
```

Set `ELEVENLABS_API_KEY` and `VIDKIT_VOICE_VI` / `VIDKIT_VOICE_EN` in a local `.env`. Paid ElevenLabs calls occur when you run `tts`, `transcribe`, `sfx generate` or `music generate`. Sound generation uses the same API key; no budget guard is configured.

## Produce a video

Create a job. New jobs use workflow v4 and default to `review`; existing jobs keep their original workflow.

```powershell
vidkit create "Product name" --languages vi --source-url https://example.com
vidkit next <job-id> --language vi --json
```

Ask Codex or Antigravity to use `vidkit-pipeline` with the job ID. The agent researches claims and references, writes the script, designs the visual explanation, then chooses existing components or writes a new TSX visual. A v4 brief includes two approaches to the main explanation, narrative beats, provisional scenes, and a motion sample. If a product screenshot is unavailable, use a sourced substitute and identify it accurately.

```powershell
vidkit add-source <job-id> source-pack.json
vidkit add-script <job-id> vi script-vi.json
vidkit add-brief <job-id> vi brief-vi.json
vidkit preview <job-id> vi --stage concept
vidkit approve <job-id> vi concept --reviewer "Your name"
vidkit tts <job-id> vi
vidkit transcribe <job-id> vi
vidkit add-asset <job-id> image.png --type artwork --description "Official product artwork" --usage-basis "official media" --source-url https://example.com/media
vidkit add-storyboard <job-id> vi storyboard-vi.json
vidkit timeline <job-id> vi
vidkit preview <job-id> vi
vidkit qa <job-id> vi
```

Inspect the MP4 in the video's `previews/` directory. The QA report distinguishes automated validation, media probing, frame inspection, transition review, full playback, and audio listening. Unperformed checks are marked `not-run`. To record inspection, supply a QA JSON file to `vidkit qa <job-id> vi qa-review.json` with `checks.frameInspection`, `checks.transitionReview`, `checks.fullPlayback`, and `checks.audioListening`; each has `status` (`pass`, `fail`, or `not-run`) and an `evidence` list. A passing check needs evidence.

```powershell
vidkit approve <job-id> vi export --reviewer "Your name"
vidkit render <job-id> vi
```

`render` writes the tracked MP4 to `exports/`. Approval is bound to the current script/brief or timeline/preview/QA checksum. A generic “continue” does not approve either gate. In `automatic` mode the video gates do not wait, but validation failures still block export, and new library candidates stay candidates. A successful encode alone does not mean full playback and audio have been reviewed.

## Open one video in Remotion Studio

The job needs a compiled timeline before Studio can open it. Find the job ID and check its next step:

```powershell
vidkit list
vidkit next <job-id> --language en --json
```

If the timeline is missing or stale, compile it first, then start Studio from the repository root:

```powershell
vidkit timeline <job-id> en
vidkit studio <job-id> en
```

Use `vi` instead of `en` for a Vietnamese video. Vidkit prepares job-specific Remotion props and copies the tracked narration and assets into `renderer/public/jobs/<job-id>/<language>/`. Remotion Studio opens in the browser; select the `VidkitShort` composition. Keep the PowerShell process running while using Studio and press `Ctrl+C` when finished.

Rendering from Studio writes to the video's `exports/` directory with a `.studio.mp4` suffix. A Studio render is not automatically tracked or approved. Register it as the current review preview with the exact path printed by Studio:

```powershell
vidkit import-render <job-id> en "<path-to-studio.mp4>"
vidkit qa <job-id> en
```

For a tracked preview without opening Studio, run `vidkit preview <job-id> en`; its MP4 is saved under the job's `previews/` directory.

## Captions and visuals

Captions use the final STT word timing. Automatic grouping considers pauses, punctuation, phrase endings and measured Noto Sans width. An optional `add-caption-plan` JSON selects explicit contiguous `startWord` / `endWord` groups. A group may include `displayTokens` with `text`, `startWord`, `endWord`, and exact `spokenText` to display a number or unit without losing its spoken-word mapping. The same cues feed burned-in captions and SRT/VTT.

The built-in themes are `dark-grid`, `dark-contours`, and `light-editorial`. V4 adds `custom` scenes backed by a job visual or shared component. Storyboard word anchors determine narration timing; motion events may depend on earlier events and reserve time for reading. Crop coordinates refer to the original image.

```powershell
vidkit library search "api" --kind component
vidkit library show api-response
vidkit library preview api-response
vidkit library search "bits" --kind bit
vidkit library preview bit-chat-conversation
vidkit library add candidate.json
vidkit library preview candidate-id
vidkit library approve candidate-id --reviewer "Your name"
```

Approved built-ins live in `renderer/library/`. Candidate manifests, code and assets live in ignored `workspace/library/`. A component candidate may wrap a tested base component or provide its own TSX entrypoint. The fixture must exercise the component; a code candidate also needs a motion preview. A theme fixture must use the exact candidate theme tokens. Video approval and library promotion are separate.
`library approve` copies a checked component, its code and fixture into `renderer/library/approved/`; no manual drag is needed. Shared image assets remain in `workspace/library/assets/` when their usage is job-specific. Commit approved files to share them through Git.

For a visual used by one video, keep its TSX source in a package with a JSON manifest and Remotion props fixture. Use `vidkit add-visual <job-id> vi <manifest.json>` and `vidkit preview-visual <job-id> vi <visual-id>`. The manifest fields are `kind: component`, lowercase `id`, semantic `version`, `description`, `propsSchema`, `entrypoint` and `fixture`. Vidkit copies local imports into `workspace/videos/<video>/vi/visuals/`. A shared custom component uses `vidkit library add` with the same `entrypoint` and a `preview` fixture.

The library now includes article highlighting, token reveal, branching flow, typed output, range/log chart and continuity handoff. `library preview` returns a still and a motion clip for code components. These primitives accept topic-specific data; the agent can still code a different visual when the explanation needs it.

Concept scenes can specify `audioStartMs` to reuse a segment of existing narration. Otherwise their original `startMs` selects the source range when it fits the recording. Out-of-range unmapped scenes remain silent and are recorded in concept metadata; an explicit invalid range fails. Concept timing remains provisional until checked against STT.

The library includes 23 requested [Remotion Bits](https://remotion-bits.dev/docs/getting-started/) examples in `renderer/library/bits.json`. `library preview <bit-id>` renders the original packaged example to `workspace/library/previews/`; `library show` gives its source path in the pinned package. They are marked `example` because their sample text, data, layout and aspect ratio need adaptation before production use. They cannot be selected directly as Vidkit storyboard components. The already integrated `AnimatedText`, `AnimatedCounter` and `GradientTransition` effects remain usable in Vidkit scenes. Provenance is recorded in [renderer/library/THIRD_PARTY.md](renderer/library/THIRD_PARTY.md).

## Sound effects and background music

Ask the agent to use `vidkit-sfx` and `vidkit-music`, adapters for the official ElevenLabs [sound-effects](.agents/skills/sound-effects/SKILL.md) and [music](.agents/skills/music/SKILL.md) skills. Music defaults to `music_v2_5`; SFX defaults to `eleven_text_to_sound_v2`. Explicit sound-plan `modelId` overrides remain supported. See [upstream revision and license](.agents/skills/elevenlabs-upstream.md). Include sound direction in the creative brief's optional `soundDirection` object and review it at concept approval. After narration/STT and storyboard are ready, import a sound plan, generate or reuse the assets, then compile the timeline. See the [sound-plan contract and JSON example](.agents/skills/vidkit-pipeline/references/sound-design.md).

```powershell
vidkit add-sound-plan <job-id> vi sound-plan.json
vidkit sfx generate <job-id> vi --cue result-ping
vidkit music generate <job-id> vi
vidkit timeline <job-id> vi
vidkit audio preview <job-id> vi
vidkit preview <job-id> vi
vidkit qa <job-id> vi
```

Narration stays clean for STT. Music and SFX are separate tracks with gain, trim and fades. Cues align to a transcript word or motion event, including the audible impact position within the source file. Music is instrumental by default, covers the video and ducks during speech. Looping is explicit and supports crossfade; inspect joins before export. Studio, WAV preview and video share the same compiled mix.

`audio import` accepts WAV/MP3 with description, source and usage basis; it detects actual format even when the original extension is wrong. Audio originals live under `workspace/videos/<video>/audio-assets/`; per-language sound plans, request records and WAV previews live under `<language>/audio/`. Music/SFX edits retain narration/STT while invalidating timing/mix/preview/QA/export approval. Old jobs without a sound plan keep their legacy sound path; an empty plan removes its fixed whooshes.

Generation reuses identical results. `--new-take` explicitly requests another take, but unresolved requests still block repeats. Inspect `vidkit audio requests <job-id> vi` and recover a returned file with `vidkit audio recover <job-id> vi <request-id> <file>`; a timeout does not prove that no charge occurred.

To share a reusable sound, run `vidkit audio share <job-id> <asset-id> --purpose "UI confirmations"`. Find it with `vidkit library search sfx --kind asset`, inspect `library show/preview`, then use `vidkit audio reuse <job-id> <library-id> --asset-id <name>`. Files remain in ignored `workspace/library/audio/` by checksum; `vidkit audio reindex` rebuilds the SQLite index from manifests. Sharing is explicit and does not promote a candidate into Git.

QA adds measured `audioLevels` and separately recorded `soundDesign`/`audioListening`. Sample peak/RMS does not establish voice intelligibility or count as listening. Run `.\.venv\Scripts\python.exe tests/smoke_sound.py` for a new synthetic fixture that checks real WAV/MP4 output, cue presence and measured ducking without paid calls. It uses test tones, not production narration/music.

## Find and resume work

```powershell
vidkit list
vidkit show <job-id>
vidkit open <job-id>
vidkit next <job-id> --language vi --json
```

Job files are under ignored `workspace/videos/<date>_<title>_<id>/`. Editing visuals or captions reuses matching narration and transcript. Replacing audio invalidates transcript-based timing. `vidkit studio` opens an interactive preview; a direct Studio export can be registered with `vidkit import-render`, which records it as a preview in v3 and does not grant approval.

Before resuming a v4 job, inspect `vidkit diff <job-id> vi`. `vidkit checkpoint <job-id> vi` saves a copy of the job data and renderer dependencies; Studio, preview and export also record the checkpoint they used. `vidkit add-feedback <job-id> vi feedback.json` records scene-specific review notes against the current timeline. Feedback observations use `sceneId`, `category` (`layout`, `explanation`, `timing`, `visual`, `caption`, `transition`), `scope` (`video` or `general-proposal`) and `observation`; `reviewMinutes` is optional. `vidkit metrics <job-id> vi` summarizes preview rounds, revision requests and recorded review time. A general proposal is reviewed before it becomes a shared rule.

Agent JSON contracts and examples: [.agents/skills/vidkit-pipeline/references/cli-workflow.md](.agents/skills/vidkit-pipeline/references/cli-workflow.md). Antigravity guidance: [docs/antigravity.md](docs/antigravity.md).
The [v4 audit](docs/v4-audit.md) records the read-only findings from the earlier Jev workflow. Run `.\.venv\Scripts\python.exe tests/smoke_v4.py` to create three synthetic validation jobs; their WAV audio is intentionally silent, so they demonstrate pipeline wiring rather than editorial quality.

Current QA automates dependency/event checks, chart unit/source checks and overlap with declared caption focus regions. DOM overflow, visual clarity, transition review, full playback and listening require explicit inspection evidence; they are not inferred from successful rendering. Fixture results do not establish improved creativity or reduced review time. Record real review feedback and minutes with `add-feedback` before comparing those outcomes.
