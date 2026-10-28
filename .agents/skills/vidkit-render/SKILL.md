---
name: vidkit-render
description: Preview and export Vidkit Remotion timelines with explicit QA coverage and revision-bound approval.
---
# Vidkit render

Read the [CLI workflow](../vidkit-pipeline/references/cli-workflow.md) and [handoff contract](../vidkit-pipeline/references/handoff-contract.md). Confirm `vidkit doctor`, current timeline, assets, theme/component locks and final narration. The target is 1080×1920, 30 fps, H.264 and AAC.

For a v4+ brief, render the provisional hook and main explanation with `vidkit preview <id> <language> --stage concept`; inspect hook/evidence/takeaway frames and the CTA frame on v5 jobs. This clip uses provisional timing and does not satisfy final export review. When continuing an existing job, check `vidkit diff` and save a checkpoint before broad visual edits.

Run `vidkit preview <job-id> <language>` to create a tracked MP4 under `previews/`. Inspect representative phone-sized frames for crop, Vietnamese glyphs, caption centering/line balance, hook identity and visual-claim match. Review every transition and listen through the final video if those checks are claimed. Run `vidkit qa` and record each check as pass/fail/not-run with evidence. An audio-level measurement is not listening; a few frames are not full playback.

For v6 scenes, inspect the apparent horizontal center of the entire logo/card/chart/diagram group at the beginning and end of motion in 1080×1920 and 360×640 frames, including a frame with captions. Title, heading and source stay left-aligned. Record `checks.visualAlignment` as pass only after visual inspection, especially for custom TSX. For a failure, give an evidence item with `sceneId`, absolute `frame`, and `note`; leave it `not-run` when no frame was inspected.

For v7+ jobs, verify the selected background runs continuously through scene cuts, joins cleanly after each loop and remains legible beneath titles, imagery and captions at both output and phone size. Record `checks.backgroundMotion` as pass/fail/not-run with scene and frame evidence. A custom visual may obscure the global background; report that instead of assuming it passes.

On v5–v8 jobs, inspect the CTA required by that job's workflow. On v9+ jobs, inspect the channel wordmark, Like → Subscribe → bell cursor targets, pressed states and final hold. The voice should invite following and interaction with the spoken channel name, without needing to name the buttons. Check the final frame and caption clearance at 360×640. Do not accept a corrective disclaimer strip as a substitute for an honest explanatory visual; retain sourcing and limitations in the handoff/QA record.

In review mode, request explicit export approval for the current timeline, preview and QA revision. Only then run `vidkit render`. Automatic mode may export when validation passes, but unperformed human checks remain not-run and candidate components remain candidates. A direct Studio export registered with `vidkit import-render` is a preview in v3, not an approval.

An encoded MP4 is not quality acceptance. Report what was actually inspected and any screenshot alternative or other limitation. If narration changes, return to STT and rebuild timing. If only visuals or captions change, reuse the audio and transcript.

For music/SFX, read the [sound contract](../vidkit-pipeline/references/sound-design.md). `vidkit audio preview` creates a WAV from the current timeline's mix; Studio, preview and export use those same tracks. Inspect cue sync, voice intelligibility, loop joins and fades. `audioLevels` is automated sample-peak/RMS evidence, while `soundDesign` and `audioListening` need actual review. New sound assets or gain/envelope changes invalidate preview/QA/export approval without calling TTS/STT.


For v10 backgrounds, follow [layered background design](../vidkit-pipeline/references/background-design.md). New candidates require image review before motion preview; `library preview --still-only` is not motion evidence. Check the pattern remains visible through optional effects and inspect each loop across scene cuts.
