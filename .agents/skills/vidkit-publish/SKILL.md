---
name: vidkit-publish
description: Prepare a Vidkit publication handoff from an independently reviewed Shorts SEO package and exact render revision, verify content and approval evidence, and interpret reported performance. Use for publication preparation; no uploader or scheduler is implemented.
---
# Publish

## Input and output

Input: explicit job ID/language, exact render revision, source pack, check results, destination, and the current manual SEO package prepared by [vidkit-seo](../vidkit-seo/SKILL.md).
Output: a publication handoff with the selected title, shared description, hashtags/tags, render path, source/QA limitations and approval evidence under the [contract](../vidkit-pipeline/references/handoff-contract.md). No upload is implied.

## Workflow

1. Resolve `vidkit workdir <id> --language <lang>` and read `seo/seo.md` and `metadata.json`. If absent, invoke SEO preparation when requested; an unapproved script needs confirmation first. Follow the [SEO output contract](../vidkit-seo/references/output.md); do not silently rewrite reviewed copy.
2. Verify job/language/channel, current input revisions/checksums, Markdown/JSON agreement and exact SEO package approval, including actual image/reference hashes for version 2. Draft, stale or incomplete requested thumbnails may be presented for review, not as a complete approved publication package. Explicit text-only packages have no image requirement. SEO approval is independent of concept/export approval and remains explicit in automatic mode.
3. Use `selectedVariant` from that reviewed package and its single shared description. Verify that the actual render supports its claims and retain source links/qualifications. Changing copy, selected variant, thumbnail mode, prompts, references or image bytes archives the package, increments revision and requires fresh SEO review. Description already includes hashtags; do not append them again.
4. Check content, asset, transcript and render findings, including playback/listening coverage. Verify render/export approval where the job's review workflow requires it. A directly exported Studio file is not automatically approved. Apply current platform/account requirements only after checking authoritative guidance.
5. Give the user the actual MP4, approved copy and selected A/B/C thumbnail path for manual publishing. Distinguish real images from unfinished prompts; note an explicit text-only choice. Keep version 1 packages readable under their original contract, without generating images or silently upgrading them. Read-only publishing preparation does not invoke generation. Skills, SEO approval and export approval do not authorize an upload or schedule.
6. If the user supplies publishing results, record only verified upload ID, destination, visibility and evidence in a manual handoff note. Never infer success or retry an uncertain upload. If they ask for performance analysis, compare equivalent ages and separate topic/language/duration; use reported Studio/API evidence and distinguish observations from editorial inference.

## Completion and missing capabilities

No uploader or scheduler is implemented. Complete file preparation and report anything awaiting review; never mark a draft package as uploaded/published. Do not add an API, change SQLite or change `next` to fill this gap.

Check current [YouTube video metadata requirements](https://developers.google.com/youtube/v3/docs/videos) and [Shorts analytics](https://support.google.com/youtube/answer/12942217) when platform-specific behavior is requested. Metadata guidance checked 2026-10-12; analytics/account behavior needs fresh verification when used. No metadata choice guarantees reach or monetization.
