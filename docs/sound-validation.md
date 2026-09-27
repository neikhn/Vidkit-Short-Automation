# Sound design validation — 2026-09-26

- 51 Python tests pass, including API payloads, request recovery/reuse, impact alignment, word/event anchors, source formats, crossfades, speech ducking, stale checksums and preservation of narration/STT.
- Renderer TypeScript compiles; both new skills pass the skill validator; all 10 Vidkit skills have valid local links.
- Real Remotion WAV and H.264/AAC MP4 were generated from synthetic 220Hz narration markers, a 440Hz music loop and an 880Hz effect. No ElevenLabs request was sent.
- The music component measured **-10.01 dB** lower during a narration interval than in a quiet interval. The effect appeared at its compiled cue time. These measurements test mix behavior, not musical or editorial quality.
- Automatic QA passed for the exported fixture: decoded PCM16 sample peak **-19.95 dBFS**, RMS **-30.30 dBFS**. Remotion's bundled ffmpeg lacks `astats` and raw float muxing; Vidkit decodes PCM16 WAV and measures every channel locally instead.

Fixture job: `20179467cb82`.

- WAV: `workspace/videos/2026-09-26_sound-mix-regression-fixture_20179467cb82/en/audio/mix/audio-mix.r1.wav`
- MP4: `workspace/videos/2026-09-26_sound-mix-regression-fixture_20179467cb82/exports/sound-mix-regression-fixture.en.r1.mp4`
- QA: `workspace/videos/2026-09-26_sound-mix-regression-fixture_20179467cb82/en/qa/qa-report.r2.json`

The first integration runs exposed the bundled ffmpeg restrictions and correctly blocked export. QA was rerun after adapting the decoder, then export succeeded. `tests/smoke_sound.py` recreates the complete synthetic sound test in a new job.

## Limits

Live API access, account entitlements and the subjective quality of generated music/SFX have not been tested. API settings were checked against official documentation and exercised with mocked responses. Live generation remains an explicitly requested paid operation.

Full playback, audio listening and sound-design review are `not-run`; frequency measurements do not count as listening. Level analysis is quantized sample-peak/RMS, not true-peak metering, loudness normalization or a voice-intelligibility check. Ducking follows transcript intervals rather than acoustic speech detection. Music beat detection, composition-plan generation, stems and mastering are outside this integration.

Existing video data was preserved. Source renderer changes can make older compiled timelines stale; no older job was automatically rebuilt or migrated.
