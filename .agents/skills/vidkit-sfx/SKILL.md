---
name: vidkit-sfx
description: Connect the official ElevenLabs sound-effects skill to Vidkit tracked generation, sound plans, mixing and review.
---
# Vidkit adapter

Use for sound-effects in a Vidkit job. Read the official [sound-effects skill](../sound-effects/SKILL.md) for provider prompting and parameters, and the [sound contract](../vidkit-pipeline/references/sound-design.md) for Vidkit fields and commands. Do not duplicate vendor guidance here.

Input: script, creative direction, sound plan and available audio/storyboard. Output: registered assets, sound plan and explicit mix review findings.

1. Include sound direction in the creative brief; follow the existing concept/export gates. Preserve other tracks in the current plan and reuse suitable audio when available.
2. Import with `vidkit add-sound-plan <id> <language> <file>`. When generation is authorized, run `vidkit sfx generate <id> <language> --cue <cue-id>`. Use this tracked command for Vidkit production jobs instead of standalone upstream SDK/CLI examples; no additional SDK/CLI installation is needed.
3. Generation uses `ELEVENLABS_API_KEY` and incurs usage. Inspect `vidkit audio requests` after uncertain results and recover files instead of repeating requests. `--new-take` is explicit, not an automatic retry.
4. Keep original audio, settings, provenance and checksums. Set anchors, trims, fades, gain and narration ducking in the plan. Compile `vidkit timeline`, then create `vidkit audio preview` and a full video preview.
5. Record alignment, voice masking and listening coverage separately. Measurements do not prove listening. Shared-library promotion is independent of video approval.

Complete when assets/timing validate and actual review coverage is recorded. Report missing configuration or provider failures accurately. Upstream streaming, composition plans, finetuning and inpainting are not implemented by the current Vidkit CLI. No budget guard or music beat detection is added.
