# SEO output and counting contract

Read when writing, revising, reviewing or handing off SEO. Contract version: 2. Reviewed: 2026-10-12. Agent-maintained files only; no production CLI/schema/SQLite support is implied.

## Files and copy

Resolve `vidkit workdir <id> --language <lang>` first. Inside its returned directory:

```text
seo/
  seo.md
  metadata.json
  cover-prompts.md              # default images mode
  references/                  # local copies of actual generation references
  thumbnails/
    thumbnail-A.<actual-format>
    thumbnail-B.<actual-format>
    thumbnail-C.<actual-format>
  history/
    r0001/                     # complete prior package, including images
```

Current preparation root is `workspace/workbench/by-video/<id>/<lang>/`; the command is authoritative. Use actual file format/extensions, not an assumed PNG. Explicit text-only mode creates only copy/metadata, not new prompts/references/images.

`seo.md` identifies job/language/revision/status, market/channel, input approval, keywords, three labeled titles/counts/rationales, recommended/selected variant, ONE full copyable description containing 3–5 hashtags, one comma-separated tag list/count, shortfall reason if needed, thumbnail previews/statuses, research evidence/limitations and next review action. Do not duplicate hashtags in a separate Markdown block. Research notes are outside upload text.

JSON and Markdown upload strings match exactly, including punctuation, accents and LF newlines. Code-fence delimiters do not count. Preview links refer to real saved images; use absolute paths when displaying them in chat, and paths relative to the SEO directory in package files. Prompts are not image previews.

## metadata.json version 2

This table documents a handoff, not executable schema code.

| Field | Content |
|---|---|
| `version`, `jobId`, `language`, `revision` | `2`, exact job ID, `vi` or `en`, positive revision |
| `status` | `draft` or `reviewed`; changed packages require fresh review |
| `market`, `channel` | Actual market; HCDB AI for VI, AI Lens for EN |
| `primaryKeyword`, `secondaryKeywords` | One phrase and supporting phrase array |
| `defaultVariant`, `selectedVariant` | Default `A`; selected A/B/C, initially A |
| `scriptApproval` | Direct user or valid concept approval, reviewer/time, exact script revision/hash, evidence reference |
| `research` | UTC `researchedAt` or null offline, `marketResearchPerformed`, `limitations`, `sources` |
| `research.sources[]` | URL/local reference, access date, supported observation and separate inference; disclose inaccessible sources |
| `inputs[]` | Role, workspace-relative path or explicit external reference, revision if present, SHA-256 of each actual local input used |
| `variants[]` | Exactly A/B/C in order: `id`, `angle` (clear/question/result), `title`, `titleCharacters`, `rationale`, claim/source references |
| `description`, `descriptionCharacters` | Exact shared upload string including CTA, URLs and hashtags; computed code-point length |
| `hashtags` | 3–5 distinct strings matching the description's final hashtag line, in order |
| `tags`, `tagCharacters` | Trimmed relevant tag array and computed YouTube total |
| `tagShortfallReason` | Null for 450–500; concrete missing-coverage reason below 450, not filler justification |
| `thumbnailMode`, `coverRequested` | `images` and true by default; explicit `text-only` and false |
| `covers` | Three A/B/C records in images mode; empty array in text-only |
| `approval` | Null for draft; explicit reviewer/time/evidence, semantic package hash and reviewed file hashes |

Each version 2 `covers[]` record contains:

- `variantId`, `visualIdea`, `labels`, `promptRef` (such as `cover-prompts.md#A`).
- `references[]`: actual local `file` relative to SEO root, `sha256`, original source/asset ID and role (identity/product/style). Preserve provenance; empty is allowed with a documented missing-assets limitation.
- `generationStatus`: `pending`, `generated` or `failed`; `tool` actual capability used or null; `failureReason` null or concrete failure.
- `actualFile`, `sha256`, `width`, `height`, `mimeType`: real decoded output, null before a valid saved file exists. Record dimensions as measured; do not invent 1080×1920 from a prompt.
- `qa`: `content`, `text`, `identity`, `mobileReadability`, `safeArea`, each with `status` (pass/fail/not-run) and evidence such as inspected file/frame size, reviewer observation or a specific defect.

Relevant script/research/brief inputs are fingerprinted; transcript/render only when actually used. Direct approval cites a real user message/time (null time with evidence when unavailable). No fabricated timestamps, file hashes, observed tool calls or credentials.

## Counting

Normalize upload strings to Unicode NFC. Count code points, not bytes, UTF-16 units or graphemes. Include punctuation/spaces; LF newlines each count once. An emoji may consume several code points.

- Titles: 1–100 code points.
- Description: 1–1,000 including every CTA, URL, newline and hashtag. This is Vidkit's project cap.
- Hashtags: 3–5 distinct relevant hashtag tokens; each appears once in the final description, with no appended duplicate list.
- Tags: trim/NFC, remove empty/case-insensitive duplicates, reject embedded commas/quotes/line breaks that make the upload list ambiguous.
- Tag total = sum(tag lengths) + max(tag count minus 1, 0) + 2 for each tag containing a space. Do not add decorative spaces after separator commas.
- Total must be at most 500. Aim for 450–500 with relevant coverage; below 450 needs `tagShortfallReason`. Never add unrelated/redundant terms to fill the limit.

`AI,AI Lens` counts 2 + 7 + 1 separator + 2 implicit quotes = 12. A temporary calculation can verify counts; do not add a maintained validator or CLI. See [copywriting guidance](copywriting.md) for relevance, description shape and examples.

## History, reuse and approval

Before modifying current package files, copy the entire active package into `history/rNNNN/` at its existing revision, excluding history itself. Include metadata, Markdown, prompts, reference images, all thumbnail images and review evidence; preserve bytes and relative layout. Identical archives can be reused; conflicting archives get a unique timestamp suffix, never overwritten. Preserve unrecognized files/media.

Increment revision when input fingerprints, copy, selection, thumbnail mode, prompts, references, images or QA change. Preserve the former package, then set the current package to draft with `approval: null`. Removing images from the active package for an explicit text-only request means archiving them, not destroying them. Unchanged reads/audits and identical reruns do not create revisions or tool calls.

Reuse verified existing thumbnails when their title angle, labels, visual idea, prompt, theme and reference fingerprints remain suitable. A tags-only edit can keep the same image bytes but still needs SEO review. Changed visual requirements require affected variants to be regenerated or explicitly reused with a reason; do not blindly generate all images on every revision.

Show exact revision, selected title, full copy and all A/B/C images for review. Explicit SEO approval is independent of concept/export and automatic mode. Missing/unreadable/wrong-aspect images or failed image QA leave images mode incomplete/draft; do not describe a partial package as approved and complete. Unperformed visual checks remain not-run and are presented for human review; do not infer a pass from explicit package selection.

For version 2 approval, finalize reviewed Markdown/prompts first. Hash `seo.md`, `cover-prompts.md` when present, every referenced thumbnail and copied reference image; store hashes keyed by SEO-relative path in `approval.files`. No nonexistent files or recursive history entries. Compute `packageSha256` from UTF-8 canonical metadata excluding only `status` and `approval` (sorted keys, compact separators, Unicode preserved, no trailing newline). Save reviewer/time/evidence and those hashes in `approval`, then metadata with reviewed status. Avoid self-referential metadata hashing.

Approval remains valid only while semantic package hash, every reviewed file hash and current input fingerprints match. Before reuse, detect altered/missing images as well as edited text. Do not retain approval after changing any reviewed bytes. Version 1 uses its original approval/checksum rules; reading/publishing it does not generate images or upgrade it. A user-requested revision becomes version 2 with preserved version 1 history.

## Version 1 compatibility

A read-only version 1 handoff keeps its stored strings, selection, approval and original checksums. Verify its original title/description/tag caps and recorded Markdown/optional prompt hashes plus the semantic metadata hash when present. Do not require new fields, 3–5 hashtags, a 450-character minimum/shortfall reason, thumbnail images or version 2 QA on a legacy package.

If a legacy record has only prompts, identify them as prompts rather than images; absence of images does not retroactively invalidate its original approval. Never reinterpret a missing legacy mode as permission to generate. A requested revision first archives the complete original bytes, then creates a draft version 2 package with the current default images mode unless the user explicitly chooses text-only.

## Review checklist

Check distinct supported titles, specific description opening, correct channel, embedded hashtags, useful tag coverage, exact counts and Markdown/JSON agreement. Confirm input approval/evidence, thumbnail A/B/C mapping, actual format/dimensions/checksums, readable local files and honestly recorded QA. Text-only has no missing-image failure; unavailable generation leaves requested images pending/failed.

No rendered video, prompts, tool return or source research alone proves image readability, user SEO approval, A/B-test outcomes or upload success.

Primary sources checked 2026-10-12: [metadata limits/counting](https://developers.google.com/youtube/v3/docs/videos#snippet), [description guidance](https://support.google.com/youtube/answer/12948449?hl=en), [tags](https://support.google.com/youtube/answer/146402?hl=en).
