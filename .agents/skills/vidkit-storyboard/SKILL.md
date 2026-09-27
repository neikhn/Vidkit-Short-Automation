---
name: vidkit-storyboard
description: Turn Vidkit scripts and word-level transcripts into meaning-driven scenes, caption groups, motion cues, and theme-locked timelines.
---
# Vidkit storyboard

Read [visual style](references/visual-style.md), [subtitle treatment](references/subtitles.md), and the [CLI workflow](../vidkit-pipeline/references/cli-workflow.md). Input: approved creative brief in review mode, final audio identity, normalized transcript, source claims, and asset inventory. Output: storyboard JSON and optional caption plan imported through the CLI.

Start with the narrative beat: what must become clear, which object appears, what it does, what changes visibly and how it leads to the next beat. Then search `vidkit library search` and inspect previews. Reuse or compose when that fits; otherwise write a job visual under `visuals/` and register it with `vidkit add-visual`. A code candidate can stand on its own, with TSX entrypoint, props schema, fixture and motion preview; it need not wrap a built-in component. Preserve component ID/version/checksum and theme lock in the compiled timeline.

For v4, give scenes a `development` object with understanding/object/action/result/connection, `entities` with stable IDs, and `events` anchored to a word or to `after` another event. Set duration and hold frames so the viewer can read the result. Use the same entity ID and `continuityGroup` for intended cross-scene continuity; custom components derive display state from the current frame so scrubbing is deterministic. Reference observations belong to specific beats, not a generic mood board.

Scenes must partition transcript word indexes exactly. Copy anchor text; Python derives milliseconds. Motion cues use word indexes in their scene, never invented timestamps. Use source claim IDs, accurate asset IDs and crop coordinates from the original image. If no product screenshot exists, continue with a sourced substitute and call it by its true type.

Propose caption groups by meaning. Use contiguous word-index ranges; optional display tokens must cover every spoken word and carry exact spokenText. Let Python validate the plan and Noto Sans width. Keep captions to two lines, avoid orphan words and split boundaries at short connectors or between numbers and units. Subtitles and animated captions share timing; music beat analysis is outside this workflow.

Run `vidkit add-storyboard`, optional `vidkit add-caption-plan`, and `vidkit timeline`. If timing, assets, claims or library components fail validation, revise the inputs and compile again. Visual and caption edits retain unchanged audio/transcript; new audio invalidates both.

When sound design is requested, use the [sound contract](../vidkit-pipeline/references/sound-design.md). Anchor SFX to the visible motion event or a narrated word, accounting for the audible impact position inside its source file. Describe the cue purpose before picking a sound. Register all required sounds before compiling the timeline; timing is derived locally. Sound-plan edits preserve clean narration/STT.

Remotion Bits: `vidkit library search bits --kind effect` lists the three integrated effects; `vidkit library search bits --kind bit` lists 23 upstream examples. Use `library preview <bit-id>` to render a gallery sample and `library show <bit-id>` to find its source in the pinned package. A `bit` entry is an example with sample data, not a storyboard component; adapt and test a parameterized wrapper before using it in a video. See renderer/library/THIRD_PARTY.md for provenance.
