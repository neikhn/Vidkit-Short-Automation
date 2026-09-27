---
name: vidkit-render
description: Preview and export Vidkit Remotion timelines with explicit QA coverage and revision-bound approval.
---
# Vidkit render

Read the [CLI workflow](../vidkit-pipeline/references/cli-workflow.md) and [handoff contract](../vidkit-pipeline/references/handoff-contract.md). Confirm `vidkit doctor`, current timeline, assets, theme/component locks and final narration. The target is 1080×1920, 30 fps, H.264 and AAC.

For a v4 brief, render the provisional hook and main explanation with `vidkit preview <id> <language> --stage concept`; inspect the three rendered hook/evidence/takeaway frames. This clip uses provisional timing and does not satisfy final export review. When continuing an existing job, check `vidkit diff` and save a checkpoint before broad visual edits.

Run `vidkit preview <job-id> <language>` to create a tracked MP4 under `previews/`. Inspect representative phone-sized frames for crop, Vietnamese glyphs, caption centering/line balance, hook identity and visual-claim match. Review every transition and listen through the final video if those checks are claimed. Run `vidkit qa` and record each check as pass/fail/not-run with evidence. An audio-level measurement is not listening; a few frames are not full playback.

In review mode, request explicit export approval for the current timeline, preview and QA revision. Only then run `vidkit render`. Automatic mode may export when validation passes, but unperformed human checks remain not-run and candidate components remain candidates. A direct Studio export registered with `vidkit import-render` is a preview in v3, not an approval.

An encoded MP4 is not quality acceptance. Report what was actually inspected and any screenshot alternative or other limitation. If narration changes, return to STT and rebuild timing. If only visuals or captions change, reuse the audio and transcript.

For music/SFX, read the [sound contract](../vidkit-pipeline/references/sound-design.md). `vidkit audio preview` creates a WAV from the current timeline's mix; Studio, preview and export use those same tracks. Inspect cue sync, voice intelligibility, loop joins and fades. `audioLevels` is automated sample-peak/RMS evidence, while `soundDesign` and `audioListening` need actual review. New sound assets or gain/envelope changes invalidate preview/QA/export approval without calling TTS/STT.
