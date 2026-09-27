# Shared handoff contract
Contract version: 4. Reviewed: 2026-09-26.

The Python CLI stores immutable artifact revisions and checksums in SQLite, with readable files under ignored `workspace/videos/`. Existing workflow v2/v3 jobs remain readable; new jobs use v4. Agents use the CLI, never direct SQLite writes. Publishing remains a prepared handoff; no uploader or scheduler is implemented.

Every handoff identifies job ID, language, revision, checksum, upstream revisions, actual path, producing provider/model or component/theme version, completed checks, and unresolved issues. Prepared, generated, checked, needs-review, blocked, approved, published and invalidated are distinct states. Never claim an unperformed API call, visual inspection, listening pass or upload.

## Artifacts

| Artifact | Key content |
|---|---|
| Source | Claim IDs, statements, URLs, dates, uncertainty and visual candidates |
| Script | Editorial text, expected spoken text, Eleven v3 TTS input and claim mapping |
| Creative brief | Angle, theme, hook, reference observations mapped to beats, two main-explanation approaches, visual strategy and rendered concept frames/clip |
| Concept approval | Reviewer, time, exact script and brief revisions/checksums |
| Audio | Final MP3 or imported audio, voice/model/settings and checksum |
| Transcript | Raw provider response and normalized word timing tied to audio checksum, plus validation findings |
| Assets | Local checksum, actual MIME/extension, evidence type, dimensions, source, date, usage basis and description |
| Caption plan | Optional contiguous word-index groups and verified display-token mapping |
| Sound plan | Optional music direction and SFX purposes, source trims/impacts, gain/fades, word or motion-event anchors |
| Sound assets | Shared job WAV/MP3 files with real format/duration, checksum, provenance, prompt/model/settings and request identity |
| Audio mix | Actual preview WAV tied to timeline revision; listening remains a separate check |
| Storyboard | Semantic scene development, component ID/version, entities, timed event dependencies, continuity, theme, claim/reference IDs, assets and word anchors |
| Timeline | Derived scene/caption timings, component/theme locks, claim-to-scene mapping and validation findings |
| Preview | Actual MP4 for the current timeline |
| QA | Automatic checks, media probe, frame inspection, transition review, full playback and audio listening, each pass/fail/not-run with evidence |
| Export approval | Reviewer, time, exact timeline, preview and QA revisions/checksums |
| Render | Actual export path, input revisions, component/theme/source locks, checkpoint revision, claim-to-scene mapping and QA reference |

Job-specific TSX visuals live under each job's `visuals/` directory. Checkpoints keep source copies and checksums; `vidkit diff` reports edits since the latest checkpoint. A concept clip uses provisional timing and does not count as the final video preview.

Eleven v3 narration → final audio → ElevenLabs STT word-level is the default. Word timing drives scenes, captions and subtitle highlighting; it does not measure music beats. SRT/VTT share cue groups and timing but have no animated styling.

## Revisions and gates

Changing a script invalidates concept approval and spoken downstream work. Changing brief/theme requires new concept approval but preserves audio if spoken text is unchanged. Changing audio invalidates transcript and timed outputs. Changing visual, caption plan, component or storyboard invalidates timeline, preview, QA and export approval while preserving unchanged audio/transcript. Only exact current approval records unlock their gates. “Continue” is never approval.

Review mode stops at concept and export approvals. Automatic mode skips those waits but still blocks on failed source, transcript, asset, timeline, media or render validation. Library candidate promotion is independent from video approval; automatic mode never promotes candidates.

A missing product screenshot is not automatically blocking. Use a sourced official artwork, API example, chart or clear diagram where appropriate, label its true evidence type and note the limitation in brief and QA. Never present a replacement as an actual console screenshot.

Do not repeat an uncertain paid TTS/STT request. If a check cannot run, record `not-run`; audio-level analysis does not count as listening, and frame sampling does not count as full playback.

Music/SFX generation follows the same no-blind-retry rule, with persisted requests and file recovery. Read the [sound contract](sound-design.md) when sound is requested. STT consumes narration alone. Sound-plan/assets invalidate timeline, mix, preview, QA and export approval while retaining narration/transcript; source tracks survive narration edits for intentional reuse.
