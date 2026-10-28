# Shared handoff contract
Contract version: 4. Reviewed: 2026-09-26.

The Python CLI stores immutable artifact revisions and checksums in SQLite, with readable files under ignored `workspace/videos/`. Existing jobs remain readable; new CLI jobs use v10. Agents use the CLI, never direct SQLite writes. Publishing remains a prepared handoff; no uploader or scheduler is implemented.

Every handoff identifies job ID, language, revision, checksum, upstream revisions, actual path, producing provider/model or component/theme version, completed checks, and unresolved issues. Prepared, generated, checked, needs-review, blocked…2 tokens truncated…oved, published and invalidated are distinct states. Never claim an unperformed API call, visual inspection, listening pass or upload.

## Artifacts

| Artifact | Key content |
|---|---|
| Source | Claim IDs, statements, URLs, dates, uncertainty and visual candidates |
| Script | Editorial text, expected spoken text, Eleven v3 TTS input and claim mapping |
| v5–v7 CTA | Final spoken follow-and-comment line and its topic-specific question, reviewed in concept and anchored to the last storyboard scene |
| v8 CTA | Final spoken Like/Subscribe line with action phrases and full spoken channel name; VI displays HCDB AI but says Hãy Cùng Bắt Đầu AI; EN displays and says AI Lens. Review provisional concept clicks and final transcript-anchored clicks separately. |
| v9 CTA | Final spoken follow-and-interact invitation with the full channel name; Like, Subscribe and bell clicks play in sequence within the final scene without being named in narration. |
| Creative brief | Angle, theme, v7-v9 background ID or v10 layered background, hook, reference observations mapped to beats, two main-explanation approaches, visual strategy and rendered concept frames/clip |
| Concept approval | Reviewer, time, exact script and brief revisions/checksums |
| Audio | Final MP3 or imported audio, voice/model/settings and checksum |
| Transcript | Raw provider response and normalized word timing tied to audio checksum, plus validation findings |
| Assets | Local checksum, actual MIME/extension, evidence type, dimensions, source, date, usage basis and description |
| Caption plan | Optional contiguous word-index groups and verified display-token mapping |
| Sound plan | Optional music direction and SFX purposes, source trims/impacts, gain/fades, word or motion-event anchors |
| Sound assets | Shared job WAV/MP3 files with real format/duration, checksum, provenance, prompt/model/settings and request identity |
| Audio mix | Actual preview WAV tied to timeline revision; listening remains a separate check |
| Storyboard | Semantic scene development, component ID/version, entities, timed event dependencies, continuity, theme, v7-v9 background ID or v10 layered background, claim/reference IDs, assets and word anchors |
| Timeline | Derived scene/caption timings, component/theme/background locks, claim-to-scene mapping and validation findings |
| Preview | Actual MP4 for the current timeline |
| QA | Automatic checks, media probe, frame inspection, transition review, full playback and audio listening, each pass/fail/not-run with evidence |
| Export approval | Reviewer, time, exact timeline, preview and QA revisions/checksums |
| Render | Actual export path, input revisions, component/theme/source locks, checkpoint revision, claim-to-scene mapping and QA reference |

Job-specific TSX visuals live under each job's `visuals/` directory. Checkpoints keep source copies and checksums; `vidkit diff` reports edits since the latest checkpoint. A concept clip uses provisional timing and does not count as the final video preview.

Eleven v3 narration → final audio → ElevenLabs STT word-level is the default. Word timing drives scenes, captions and subtitle highlighting; it does not measure music beats. SRT/VTT share cue groups and timing but have no animated styling.

## Revisions and gates

Changing a script invalidates concept approval and spoken downstream work. Changing brief/theme/background requires new concept approval but preserves audio if spoken text is unchanged. Changing audio invalidates transcript and timed outputs. Changing visual, caption plan, component or storyboard invalidates timeline, preview, QA and export approval while preserving unchanged audio/transcript. Only exact current approval records unlock their gates. “Continue” is never approval.

Review mode stops at concept and export approvals. Automatic mode skips those waits but still blocks on failed source, transcript, asset, timeline, media or render validation. Library candidate promotion is independent from video approval; automatic mode never promotes candidates.

A missing product screenshot is not automatically blocking. Use a sourced official artwork, API example, chart or clear diagram where appropriate, label its true evidence type and note the limitation in brief and QA. Never present a replacement as an actual console screenshot.

Avoid corrective disclaimer strips on screen. Preserve evidence type and limitations in source pack/brief/QA; explain a material distinction in narration or redesign the visual. Never depict invented measurements or a fabricated UI as verified output.

Do not repeat an uncertain paid TTS/STT request. If a check cannot run, record `not-run`; audio-level analysis does not count as listening, and frame sampling does not count as full playback.

Music/SFX generation follows the same no-blind-retry rule, with persisted requests and file recovery. Read the [sound contract](sound-design.md) when sound is requested. STT consumes narration alone. Sound-plan/assets invalidate timeline, mix, preview, QA and export approval while retaining narration/transcript; source tracks survive narration edits for intentional reuse.


V10 background handoffs carry the same `background` configuration from creative brief to storyboard, then lock each pattern/effect in timeline `backgroundLayers`. See [layered background design](background-design.md). A still review is not approval of motion or library promotion.

## Optional manual SEO handoff

Reviewed 2026-10-12. [vidkit-seo](../../vidkit-seo/SKILL.md) runs on request for an explicit job ID/language and approved clean script (direct user or still-valid concept approval). Resolve `vidkit workdir <id> --language <lang>`; write `seo/seo.md` and `seo/metadata.json`. New version 2 packages include three generated 9:16 A/B/C thumbnails, saved prompts and real reference copies by default; explicit text-only skips them.

Agent-maintained SEO files are not registered production artifacts or a second SQLite state source. SEO does not change `next`, workflow version or render/export gates. The [output contract](../../vidkit-seo/references/output.md) defines one description with embedded hashtags, useful tags aiming for 450–500 characters, content/image/input fingerprints, complete-package history and exact independent SEO review. Missing thumbnail capabilities remain disclosed incomplete work, not fake deliverables.

Publish uses the selected title, shared complete description and selected real thumbnail from a current reviewed package. Copy, input, selection, prompt, reference or image changes invalidate approval. A text-only override has no image requirement. Version 1 keeps its original meaning; reading/publishing old SEO does not generate images or migrate it. SEO/video approval does not start an A/B test or authorize upload.
