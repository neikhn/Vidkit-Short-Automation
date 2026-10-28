# Video production checklist

Checklist version: 1. Read at job start, when resuming, and before each handoff. This is an agent-facing checklist, not a new CLI stage, database record or workflow version. The [handoff contract](handoff-contract.md) and [CLI workflow](cli-workflow.md) remain authoritative.

## Flow and progress

Topic → research → localized script + estimated duration + creative brief → concept approval in review mode → final narration → word-level STT → assets + captions + timed storyboard → requested music/SFX + mix → full preview + QA → export approval in review mode → MP4.

Use `vidkit doctor`, `vidkit show <id>` and `vidkit next <id> --language <lang> --json`. On an existing checkpointed job, inspect `vidkit diff` before edits. Read current revisions, checksums and approval evidence; resume the first missing or stale step instead of regenerating everything.

Evaluate every checkbox for each requested language. Shared research/assets can be reused with provenance, but script, narration, timing, captions, mix and approvals are checked separately. Do not create an unrequested language or mark a bilingual job complete when only one language is ready.

Report progress in a VI/EN table derived from actual CLI/artifact state; use not-requested for an absent language. Suggested row labels:

| Stage | VI | EN | Evidence / next action |
|---|---|---|---|
| Research, script and duration | | | |
| Brief and concept review | | | |
| Final narration and STT | | | |
| Assets, captions and storyboard | | | |
| Sound plan and mix / explicit silence | | | |
| Full preview and QA | | | |
| Export review and MP4 | | | |
| SEO, if requested | | | |

Use done, pending, waiting-review, blocked or not-requested as presentation labels, not new stored statuses. For evidence, give real file paths, revisions/checksums and unresolved issues. QA uses pass/fail/not-run separately; a progress label is not a quality verdict.

## Preparation and concept

- [ ] Confirm topic/source URL, viewer, requested languages, target duration, review/automatic mode and who supplies missing assets. Default duration is 45–75 seconds per language unless specified; existing job settings take precedence.
- [ ] Research claims and sources; list actual assets and collection needs. If a product screenshot is inaccessible, continue with a sourced substitute and record its true type/limitation; never invent a screenshot.
- [ ] Write natural VI/EN scripts preserving factual meaning, numbers and uncertainty. Include a clear hook, explanation and topic-specific CTA under the job's existing contract. VI displays HCDB AI and speaks Hãy Cùng Bắt Đầu AI; EN uses AI Lens.
- [ ] Estimate duration independently for each script, including CTA. Label estimates explicitly; they are not measured audio lengths or final timing.
- [ ] Design how each beat explains its claim before choosing components. Specify visual development, assets, theme, background, motion and music/SFX direction in the creative brief. Use new visuals when existing components do not explain the content.
- [ ] Render concept frames/motion from the proposed visuals; inspect phone readability, alignment, hook and CTA. Record provisional timing and reused audio ranges if audio already exists.
- [ ] In review mode, obtain concept approval for the current script/brief/concept revisions before new production narration. “Continue” does not approve. Automatic skips this wait, not data checks.

## Audio, timing and video

- [ ] Prepare Eleven v3 input and generate or reuse final clean narration per language with the configured voice. Keep editorial text, expected speech and tagged TTS input distinct; recover uncertain requests instead of blindly repeating them.
- [ ] Check pronunciation, names, numbers, CTA and actual audio duration. Report deviation from the target and resolve it before final timing; do not disguise missing speech with captions or cut the ending to meet an estimate. A script change requires the appropriate renewed concept review.
- [ ] Reuse matching STT or transcribe final narration alone with ElevenLabs word-level STT. Validate content against expected speech and timing against the correct audio checksum. Do not transcribe a music/SFX mix.
- [ ] Localize storyboard, assets and captions against that language's checked transcript. Verify word anchors, full audio coverage, semantic caption groups, font/diacritics, crop, horizontal visual-group centering, continuity and subtitle safe areas.
- [ ] When sound is requested, follow the [sound contract](sound-design.md): generate/reuse music/SFX, anchor audible impacts to that language's words/motion events, set gain/ducking/fades and deliberate loops. Source tracks may be shared, but timestamps/envelopes are compiled separately for VI/EN. Record explicit silence or an empty plan when chosen; do not generate audio just to tick a checkbox.
- [ ] Compile the timeline including sound; create an audio mix preview when used and a full MP4 preview. Include music/SFX before the final review preview. A visual-only draft or short concept clip is not the preview used to approve export.

## Review and handoff

- [ ] Inspect representative full/phone-sized frames, captions, foreground/background, every transition and CTA ending. Check duration and visual-to-narration agreement for each language.
- [ ] Watch the full preview and listen to its actual voice/music/SFX mix if claiming these checks. Verify intelligibility, cue sync, levels, loop joins and fades. Record pass/fail/not-run with scene/frame or file evidence in QA; metadata/audio-level analysis is not listening.
- [ ] If full playback/listening cannot run, leave not-run and explicitly transfer that review to the user in review mode. Automatic never reports unperformed checks as passed or full quality acceptance.
- [ ] In review mode, obtain export approval for the current timeline/preview/QA revision, then render. Automatic may export only when required data checks pass, with incomplete human QA still disclosed. A Studio export does not grant approval.
- [ ] If SEO was requested, use [vidkit-seo](../../vidkit-seo/SKILL.md) per language: current approved script, titles, one description including hashtags, useful tags and three real A/B/C thumbnails by default (or explicit text-only). SEO review is independent and does not block the video.
- [ ] Hand off actual MP4/thumbnail paths or inline media, language-specific durations, revisions, review state and unfinished checks. Do not build a custom web review page or launch its server unless requested. Existing Remotion Studio remains available for requested editing/review.

## Resume and missing-data scenarios

Visual/caption/music/SFX edits preserve unchanged narration/STT, but invalidate affected timing/mix/preview/QA/export approval. Audio changes require matching STT and timing to be rebuilt; source music/SFX may be retained for deliberate reuse. A theme/background change follows the existing concept gate. Do not silently switch or migrate an old job's workflow.

| Situation | Required handling |
|---|---|
| VI and EN durations differ | Report measured durations separately; build separate anchors/timelines and sound envelopes. Equal duration is not required unless requested. |
| One language's TTS fails | Mark that language blocked at narration; preserve valid artifacts and continue permitted work in the other language. The requested bilingual package remains incomplete. Recover uncertain requests before retrying. |
| Valid audio/STT already exists | Check revision/checksum/content and reuse; no TTS/STT call merely to follow stage order. |
| Product screenshot unavailable | Continue with a verified, accurately labeled alternative; record collection needs/limitations in brief and QA. |
| Music changes after preview | Retain narration/STT; rebuild mix/timeline/full preview/QA and obtain fresh export approval in review mode. |
| Playback or listening unavailable | Record not-run and the limitation; technical probe/frame sampling never fills this gap. |

No extra approval gate, budget guard, scheduler, upload service, CLI command or SQLite state is introduced by this checklist.
