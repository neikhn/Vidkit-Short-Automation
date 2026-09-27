# Vidkit v4 audit notes

Reviewed on 2026-09-26. The existing TypeSafe Jev job `4e41503a8d71` was read only.

- Its saved storyboards have six revisions: r1–r5 have 13 scenes and r6 has 10. Seven MP4 previews exist. These revisions show iteration but do not identify who requested each change.
- Before v4 work, `renderer/src/JevVisuals.tsx` and product media were untracked, while `renderer/src/VidkitShort.tsx`, `src/vidkit/timeline.py`, `src/vidkit/render.py`, `src/vidkit/workflow.py`, tests and README had local edits. The Jev visual was wired through a product-specific branch in the shared renderer.
- The v3 component registration required a built-in `baseComponent`; the compiler resolved candidate components back to that base. The old code lock covered `VidkitShort.tsx` and package lock but missed imported visual code.
- Studio received generated `props.json`; there was no supported path to turn edits to that copy into the job's source. In the observed workflow, the agent edited code while the user reviewed Studio. V4 checkpoints and diff therefore protect source and job data rather than treating Studio's temporary props as authoritative.

The stored revisions cannot reliably separate user edits from agent edits or prove which visual choices should become general rules. Review notes now record `video` or `general-proposal` scope per scene. Promotion to shared skills or components remains a separate decision.

No Jev job data was migrated, deleted or rendered during this audit.
