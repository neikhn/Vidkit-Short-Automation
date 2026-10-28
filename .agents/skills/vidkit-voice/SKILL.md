---
name: vidkit-voice
description: Prepare Vidkit narration for ElevenLabs eleven_v3 with clear, selectively emphasized delivery, pronunciation mappings and audio handoff. Use for TTS preparation or authorized narration generation.
---
# Voice

## Input and output
Input: localized script, language and voice configuration if generating.
Output: TTS-ready input and expected spoken/display mappings; an audio record only when audio was actually generated.
Read the [contract](../vidkit-pipeline/references/handoff-contract.md) and [Eleven v3 guide](references/eleven-v3.md).

## Workflow
1. Preserve clean editorial narration. Prepare the expected spoken version for numbers, abbreviations and difficult names while retaining their display spellings.
   For v9 CTA, speak “Hãy Cùng Bắt Đầu AI” in Vietnamese while displaying HCDB AI; speak and display “AI Lens” in English. Invite viewers to follow and interact for an episode-specific reason. The on-screen Like, Subscribe and bell clicks do not require those button names in the narration. Preserve the older CTA wording for existing jobs.
2. Add restrained delivery tags and punctuation for clear, emphasized technology explanation. Keep visual instructions outside the TTS input.
3. Use eleven_v3; start with Natural delivery unless configured otherwise. Use the supplied language-appropriate voice ID, never an invented example ID.
4. If the ElevenLabs client is configured, generate a coherent narration take. Otherwise deliver prepared text and required configuration only.
5. Finish narration edits/joins before transcription. Record the final audio identity and duration when measurable.
6. Hand off final MP3 to [transcript](../vidkit-transcript/SKILL.md); do not replace the agreed STT stage with TTS timestamps.
7. Generate with `vidkit tts <job-id> <language>`. The CLI loads the configured voice and API key from `.env` and records the actual model/voice revision.

## Completion and missing inputs
Text preparation can complete without a voice ID or API client; generation cannot. Label these states separately. Missing credentials are configuration dependencies, not content to paste into a document.

If narration is wrong, preserve the faulty take and findings. Do not automatically retry an uncertain API result or conceal spoken mistakes by altering captions. Music/SFX remain separate tracks.
