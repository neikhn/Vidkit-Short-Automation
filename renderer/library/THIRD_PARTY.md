# Third-party visual sources

Checked 2026-10-09.

Vidkit uses [Remotion Bits](https://remotion-bits.dev/docs/getting-started/) package version `0.2.1` for `AnimatedText`, `AnimatedCounter`, and `GradientTransition`. The [package manifest](https://github.com/av/remotion-bits/blob/master/package.json) declares MIT; the dependency and resolved version are pinned in `renderer/package.json` and `renderer/package-lock.json`. `culori` version `4.0.1` is pinned because the gradient utility imports it at runtime.

`bits.json` lists 23 requested upstream examples with their source paths and original aspect ratios. `BitsGallery` imports these examples from the pinned npm package and renders local previews; the examples are not Vidkit storyboard components. Their demo copy, charts and images must be replaced with verified job data and checked on a portrait frame before production use. Cursor Flyover uses an MIT upstream copy in `renderer/src/vendor/CursorFlyover.tsx` with its image URL adapted to Remotion's `staticFile`; its gallery preview uses the synthetic fixture at `renderer/public/gallery.png`.

The library manifest also retains catalog references for agent discovery. A reference is not an installed Vidkit component. To turn a bit into a reusable production scene, implement a parameterized wrapper and fixture, check the current upstream license and API, and record source/version in its manifest.

`radial-glow` and `fireflies` are deterministic, seamless-loop adaptations of the Radial Gradient and Fireflies concepts in pinned `remotion-bits@0.2.1` (MIT). They use Vidkit theme colors and Remotion frames rather than the examples' one-shot transition and random particle spawning. Source attribution and limits are recorded in `manifest.json`; these backgrounds are implemented under `backgrounds/` and are not copies of the demo source.

The Noto Sans font used for caption measurement is bundled in `fonts/`; its OFL text is at `fonts/OFL.txt`.

The CTA hand cursor uses `Pointer` from `lucide-react@1.54.0` (ISC); see the package's `LICENSE`. CTA click, confirmation and bell audio was generated once using ElevenLabs `eleven_text_to_sound_v2`. Reusable trimmed WAVs and their prompts, source checksums and usage basis are under `renderer/public/sfx/cta/`. These audio files are subject to the generating account's ElevenLabs terms, rather than the visual component's MIT license.
