# Three portrait thumbnails

Read in default images mode when creating or revising SEO. Version 2 behavior, reviewed 2026-10-12. This produces actual A/B/C images using available agent tools; no new API/service is added. Explicit text-only skips this reference and image generation.

## Design and inputs

Use A/B/C titles, approved script/brief, video theme/typography and real job assets. Inspect reference images before generation. Assign each reference a role: exact identity/logo, product/evidence image or style. Preserve those roles in the prompt and metadata.

Design three distinct focal ideas, with consistent recognition of the video's subject:
- A: immediate subject recognition tied to the clear title.
- B: a visual question/contrast the video answers.
- C: a supported outcome/event/limitation, using numbers only with evidence.

Use portrait 9:16, one strong focal point, brief localized labels and safe spacing for phone/UI cropping. Reuse video colors/style, not a universal halftone/newspaper template. Avoid shrinking a whole webpage into a thumbnail. Do not synthesize a fake logo, product UI, measurements or source screenshot. Missing identity assets can be replaced by accurate product text plus an illustrative graphic, with the limitation recorded.

## Prepare and generate

1. Save `seo/cover-prompts.md` with sections `## A`, `## B`, `## C`. Each specifies the idea, exact localized labels, real references with roles, final standalone prompt and generation/QA status. Reference paths are local; retain original provenance.
2. Copy actual used reference images into `seo/references/` without overwriting unrelated files; fingerprint them. Do not claim an asset was supplied if the image tool did not receive it. Distinguish inspected supporting research from images actually passed to generation.
3. Use an available image-generation tool. In Codex, load `imagegen` when available and use its built-in tool; issue one distinct request per A/B/C concept. Follow that tool's real reference-input contract, not invented parameters. If local images must first be made visible, inspect them with `view_image`. Request the complete thumbnail with correct text, rather than delivering code/vector placeholders as generated art.
4. Record the actual tool/model when exposed, prompt and inputs. Resolve returned output paths/data; copy every completed final into `seo/thumbnails/thumbnail-<A|B|C>.<actual-format>`. Keep project images inside the handoff; do not leave them only in a global generated-image directory. Never rename a JPEG to PNG or record an imagined save path.
5. Decode outputs to verify file/format and measured dimensions. Verify 9:16 (allow one-pixel rounding); if the tool returned another ratio, request a supported correction without distorting or cutting important content. Do not mark wrong-ratio images complete.
6. Inspect each full-resolution image and its appearance at 360×640: correct content/claims, exact VI diacritics/EN spelling, product identity, meaningful differences across variants, label readability, uncluttered focus and safe edges. Record pass/fail/not-run with evidence per image. A file-format check is not a visual review.
7. Fix observed defects with a targeted revision using the image tool. Preserve history and references; do not silently redraw authentic identity elements. If a generation attempt returns an uncertain result, recover/check it before retrying. Routine tool failure does not authorize an API fallback.
8. Display all three saved images inline, labeled A/B/C beside the matching titles, and recommend A unless another option has a concrete editorial advantage. Ask for the selected variant and exact-package review; do not run a platform A/B test.

## Reuse, failures and review

A copy/tags-only edit may reuse unchanged verified images; check their stored hashes, visual suitability and reference/theme fingerprints first. Changes to a title's visual promise, labels, theme or references trigger review of affected thumbnails, not blind regeneration of every variant.

Unavailable tool: keep prompts/copy, mark generation pending and actual image fields null. Failed generation: record failed with the real error; completed variants retain their actual files and checks. Corrupt output or bad text fails the appropriate check. Do not present partial output as three completed thumbnails or claim mobile review from metadata.

Do not automatically add API keys, choose a paid fallback, replace the provider, upload media or re-render the video. Explicit fallback authorization, if later provided, is separate work. Text-only is an explicit user override; a tool failure must not silently convert images mode to text-only.

SEO review includes all current A/B/C files, prompts, references and their hashes under the [output contract](output.md). Human review can supply missing observations with evidence; never invent checks. Reading an old approved package or preparing a publishing handoff alone does not generate thumbnails.

Before giving upload instructions, verify current account/app cover eligibility; these are saved image deliverables, not a promise of a YouTube feature.
