---
name: vidkit-storyboard
description: Turn Vidkit scripts and word-level transcripts into meaning-driven scenes, caption groups, motion cues, and theme-locked timelines.
---
# Vidkit storyboard

Read [visual style](references/visual-style.md), [subtitle treatment](references/subtitles.md), and the [CLI workflow](../vidkit-pipeline/references/cli-workflow.md). Input: approved creative brief in review mode, final audio identity, normalized transcript, source claims, and asset inventory. Output: storyboard JSON and optional caption plan imported through the CLI.

Start with the narrative beat: what must become clear, which object appears, what it does, what changes visibly and how it leads to the next beat. Then search `vidkit library search` and inspect previews. Reuse or compose when that fits; otherwise write a job visual under `visuals/` and register it with `vidkit add-visual`. A code candidate can stand on its own, with TSX entrypoint, props schema, fixture and motion preview; it need not wrap a built-in component. Preserve component ID/version/checksum and theme lock in the compiled timeline.

For new v6 jobs, name the primary visual group in each beat and center that group horizontally in the visual area. Keep title, heading and source left-aligned; card contents can also be left-aligned. A custom visual should group its related objects before positioning them, then check the composition with captions at phone size. The compiled timeline marks this contract with `visualAlignment: "centered"`; do not add it to an existing job.

For v7-v9 jobs, copy the approved brief's `backgroundId` into the storyboard exactly. The compiled timeline locks its ID, version and checksum; the background is global, not repeated per scene. Do not add an opaque full-frame fill to a custom visual unless deliberately hiding the background. Check readability and the loop seam at phone size with main visuals and captions.

For v4, give scenes a `development` object with understanding/object/action/result/connection, `entities` with stable IDs, and `events` anchored to a word or to `after` another event. Set duration and hold frames so the viewer can read the result. Use the same entity ID and `continuityGroup` for intended cross-scene continuity; custom components derive display state from the current frame so scrubbing is deterministic. Reference observations belong to specific beats, not a generic mood board.

Scenes must partition transcript word indexes exactly. Copy anchor text; Python derives milliseconds. Motion cues use word indexes in their scene, never invented timestamps. Use source claim IDs, accurate asset IDs and crop coordinates from the original image. If no product screenshot exists, continue with a sourced substitute and call it by its true type.

For v5–v8 jobs, retain the final CTA scene required by that job's workflow. For new v9 jobs, end with exactly one `role: "cta"` custom scene using `channel-cta-strip`, at least five seconds long. The component displays the channel wordmark plus Like, Subscribe and bell controls. Omit click events: the three cursor clicks are sequenced within the scene duration, while transcript words set the scene boundaries and captions. Check each click, all three activated states, caption clearance at 360×640 and the final frame before audio ends. Existing jobs do not acquire this CTA automatically.

Propose caption groups by meaning. Use contiguous word-index ranges; optional display tokens must cover every spoken word and carry exact spokenText. Let Python validate the plan and Noto Sans width. Keep captions to two lines, avoid orphan words and split boundaries at short connectors or between numbers and units. Subtitles and animated captions share timing; music beat analysis is outside this workflow.

Run `vidkit add-storyboard`, optional `vidkit add-caption-plan`, and `vidkit timeline`. If timing, assets, claims or library components fail validation, revise the inputs and compile again. Visual and caption edits retain unchanged audio/transcript; new audio invalidates both.

When sound design is requested, use the [sound contract](../vidkit-pipeline/references/sound-design.md). Anchor SFX to the visible motion event or a narrated word, accounting for the audible impact position inside its source file. Describe the cue purpose before picking a sound. Register all required sounds before compiling the timeline; timing is derived locally. Sound-plan edits preserve clean narration/STT.

Remotion Bits: `vidkit library search bits --kind effect` lists the three integrated effects; `vidkit library search bits --kind bit` lists 23 upstream examples. Use `library preview <bit-id>` to render a gallery sample and `library show <bit-id>` to find its source in the pinned package. A `bit` entry is an example with sample data, not a storyboard component; adapt and test a parameterized wrapper before using it in a video. See renderer/library/THIRD_PARTY.md for provenance.


For v10 jobs, copy the approved brief's full `background` configuration, including effect order and settings. Read [layered background design](../vidkit-pipeline/references/background-design.md). The compiled timeline locks every layer; the optional overlays are transparent. Prefer a simple pattern when it supports the explanation.
