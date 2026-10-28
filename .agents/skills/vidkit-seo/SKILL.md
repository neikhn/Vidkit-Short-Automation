---
name: vidkit-seo
description: Create or revise a YouTube Shorts SEO package for a Vidkit job and language, with three titles, engaging description including hashtags, researched tags and three generated portrait thumbnails for HCDB AI or AI Lens. Use for SEO or publication metadata requests; support explicit text-only output.
---
# YouTube Shorts SEO

## Scope and inputs

Prepare a manual file handoff, not a CLI stage or publishing service. Read the [handoff contract](../vidkit-pipeline/references/handoff-contract.md). SEO never blocks preview/export, changes `next`, or upgrades a job's workflow.

Require an explicit job ID and language. Read `vidkit show <id>`, current clean script, research/source pack and creative brief. Use `editorial_text` for meaning and `expected_spoken_text` for promised narration; ElevenLabs `tts_input` with audio tags is not canonical copy. Use existing transcript/render evidence when available and record what was actually inspected.

The current clean script needs explicit user approval or still-valid concept approval for its exact revision/checksum. If absent, request confirmation before writing SEO copy. “Continue,” automatic mode and export approval do not replace script or SEO approval.

Defaults: `vi` targets Vietnam and **HCDB AI**; `en` targets English-speaking viewers and **AI Lens**. Honor explicit market overrides. Creating/revising SEO includes three actual A/B/C thumbnails unless the user explicitly requests `text-only`; reading, auditing or publishing an existing package does not generate images.

## Workflow

1. Inspect the existing package. Read [output and counting](references/output.md) and [copywriting and tags](references/copywriting.md). Resolve `vidkit workdir <id> --language <lang>`; prepare files inside its `seo/` directory.
2. Identify the real viewer question and primary/supporting keywords. Research current language/market terminology when web access exists. Prefer primary evidence for product claims; separate dated observations from editorial inference. Do not invent search volume, competition, rankings or performance forecasts.
3. Write exactly three distinct titles: A clearly names the subject (default), B asks a curiosity the video answers, C presents a supported result/event/limitation. Retain product/model names and qualifiers.
4. Write a specific hook with the primary keyword, then what the viewer will understand and the topic's meaningful detail. Finish with a topic-specific channel CTA, useful source links and 3–5 relevant hashtags. Save one complete copyable description, hashtags included once; no separate Markdown hashtag block to append. Avoid boilerplate openings, script repetition and claims beyond the video.
5. Build tags from entity names, topic, demonstrated features, viewer intent and genuine market-language variants. Put specific terms first; deduplicate and remove unrelated terms. Aim for 450–500 characters only when useful coverage supports it; explain a shorter list briefly, never pad.
6. Normalize NFC and compute exact title/description/tag counts, including URLs, hashtags, newlines and YouTube tag comma/quote overhead. Caps: 100/1,000/500 respectively. Compare Markdown and JSON before review.
7. In default images mode, read [thumbnail creation](references/covers.md), prepare three paired concepts/prompts and generate A/B/C using the available image tool with real video assets as references. Preserve identity/evidence; inspect and save every image locally with its checksum and QA. Reuse an unchanged verified image rather than generating it again. In explicit text-only mode, skip thumbnail generation and its reference.
8. Before replacing current files, preserve the previous package, prompts, references and images in revision history. Save version 2 metadata and Markdown as draft; show the three titles, full description, tags/counts and all three actual thumbnail previews (or the precise incomplete status). Record approval only for the exact current package and selected variant, following the output contract.
9. Before handoff to [publish](../vidkit-publish/SKILL.md), recheck input revisions, approved file bytes and image hashes. Changed inputs/copy/images/selection invalidate SEO approval. Keep video/audio/transcript unchanged.

## Completion and missing capabilities

Complete copy requires distinct supported titles, engaging description with embedded hashtags, relevant tags, accurate counts and matching Markdown/JSON. Complete images mode additionally requires three real readable portrait images and recorded checks; prompts alone do not complete thumbnails. Text-only has no thumbnail obligation.

Missing research/brief: request material or record an explicit user-approved omission. Offline: prepare a content-grounded draft with `marketResearchPerformed: false` and a “market research not performed” limitation. Missing transcript/render does not require creating them; conflicting actual narration must be resolved before promising that content.

Use the agent's available image-generation capability; in Codex, follow `imagegen` when available and prefer the built-in tool. Missing/failing tools leave copy and prompts in draft with thumbnail status pending/failed. Do not silently switch to a paid API, add keys/services, retry an unresolved result blindly, or claim generated/inspected images that do not exist. Recover identifiable outputs first.

No SEO API, new CLI, SQLite writes, maintained validator, upload or scheduler is added. Existing version 1 packages remain readable and unchanged until the user requests a revision.

## Sources

Adapted from `vox-youtube-seo` in Voxel-Long-form-Automation; retain evidence/history discipline, not long-form chapters, automated tests or halftone defaults. Checked 2026-10-12: [YouTube descriptions](https://support.google.com/youtube/answer/12948449?hl=en), [metadata limits and tag counting](https://developers.google.com/youtube/v3/docs/videos#snippet), [role of tags](https://support.google.com/youtube/answer/146402?hl=en). Target tag length is a project preference, not a promise of reach.
