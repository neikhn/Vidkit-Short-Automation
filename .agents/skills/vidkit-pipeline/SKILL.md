---
name: vidkit-pipeline
description: Coordinate Vidkit research, script, creative brief, concept approval, ElevenLabs narration, timed storyboard, preview QA, and export. Use for multi-stage requests and resuming jobs.
---
# Vidkit pipeline

Read [handoff contract](references/handoff-contract.md) and [CLI workflow](references/cli-workflow.md). Use `vidkit doctor`, `vidkit show <job-id>`, `vidkit diff <job-id> <language>` when a checkpoint exists, and `vidkit next <job-id> --language <language> --json` before acting. Existing jobs keep their workflow; new jobs use v4. Do not edit SQLite or assume a missing stage is complete.

For each language, follow: research → script → creative brief with theme, hook, visual strategy, sourced assets and three frame previews → concept approval in review mode → final Eleven v3 narration → ElevenLabs STT word-level transcript → assets and caption plan → storyboard and motion → preview MP4 → QA report → export approval in review mode → render. Use `vidkit next` after every handoff.

In review mode, “continue” means continue non-gated preparation only. Require explicit `vidkit approve ... concept` and `vidkit approve ... export` for the current revisions. In automatic mode, skip waits for video approval but never ignore validation failures; candidate library entries remain candidates. Do not promote a library candidate while approving a video unless the user separately chooses to do so.

Design how the viewer will understand each claim before searching the library. Analyze supplied references into observable editing choices and map each choice to a narrative beat. Compare two visual approaches for the main explanation, then select reuse, composition or new TSX code. A component may be job-specific; do not force content into an existing layout. Render a concept motion preview with `vidkit preview <id> <language> --stage concept` before concept approval. If a product screenshot is inaccessible, continue with sourced official artwork, an API example, chart or explanatory diagram. Label the evidence type and limitations accurately in brief and QA. Do not invent UI screenshots or logos.

Before modifying an existing video, inspect its current files, uncommitted changes and `vidkit diff`; preserve code already revised through Studio feedback. Use `vidkit checkpoint` for a named safe copy before broad edits. If regeneration would discard revised code, show the concrete diff first. A successful render or passing probe is not proof of visual clarity.

Research and editorial work are agent tasks imported through the CLI. TTS and STT are paid API steps; do not send requests speculatively or repeat an uncertain result. No embedded LLM API, scheduler, automatic publishing, music beat detector, or budget guard exists.

When sound design is requested, include music/SFX direction in the creative brief and route to [sound effects](../vidkit-sfx/SKILL.md) and [background music](../vidkit-music/SKILL.md). The adapters load the official ElevenLabs [sound-effects](../sound-effects/SKILL.md) and [music](../music/SKILL.md) skills for provider guidance. Read the [sound contract](references/sound-design.md) for CLI/data. Generate/reuse sound assets after concept approval, then compile them with the timed storyboard before preview. Keep clean narration for STT. Sound generation is paid; unresolved attempts are recovered, not blindly retried. Music/SFX edits preserve narration/transcript and require a fresh mix/video review. The existing concept/export gates cover audio direction and final mix.

Route to [research](../vidkit-research/SKILL.md), [script](../vidkit-script/SKILL.md), [voice](../vidkit-voice/SKILL.md), [transcript](../vidkit-transcript/SKILL.md), [storyboard](../vidkit-storyboard/SKILL.md), [render](../vidkit-render/SKILL.md), and [publish](../vidkit-publish/SKILL.md) only as needed. Report actual artifact paths, revisions and unperformed QA checks.
