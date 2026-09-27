import React from 'react';
import {SoundTracks, type SoundTrack} from './SoundTracks';
import {Audio} from '@remotion/media';
import {AnimatedCounter, AnimatedText, GradientTransition} from 'remotion-bits';
import libraryManifest from '../library/manifest.json';
import {JevVisual} from './JevVisuals';
import {
  AbsoluteFill,
  continueRender,
  delayRender,
  Img,
  interpolate,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

type CaptionToken = {text: string; start_ms?: number; end_ms?: number; startMs?: number; endMs?: number};
type Caption = {text: string; startMs: number; endMs: number; tokens: CaptionToken[]; lines?: string[]};
type Asset = {id: string; src?: string; description?: string; width?: number; height?: number};
type Crop = {x: number; y: number; width: number; height: number};
type Callout = {text?: string; x?: number; y?: number};
type SafeArea = {top: number; right: number; bottom: number; left: number};
export type Scene = {
  id: string;
  layout: 'custom' | 'hook' | 'screenshot' | 'steps' | 'takeaway' | 'brand-hook' | 'screenshot-focus' | 'api-response' | 'diagram-flow' | 'metric-breakdown';
  purpose?: string;
  title: string;
  body: string;
  startMs: number;
  endMs: number;
  status?: string;
  asset?: Asset | null;
  supportAssets?: Asset[];
  assetRequired?: boolean;
  crop?: Crop;
  callout?: Callout | null;
  component?: string;
  componentId?: string;
  componentProps?: Record<string, unknown>;
  absoluteStartFrame?: number;
  events?: Array<{id: string; entityId: string; atFrame: number; endFrame: number}>;
  entities?: Array<{id: string; label?: string}>;
  continuityGroup?: string;
  continuityStartFrame?: number;
  componentVersion?: string;
  claimIds?: string[];
  motion?: {cues?: Array<{atMs: number; type?: string}>; zoomTo?: number; mode?: string};
};

const labels = {
  en: {hook: 'Worth knowing', screenshot: 'Product evidence', steps: 'How it works', takeaway: 'Takeaway'},
  vi: {hook: 'Điểm đáng chú ý', screenshot: 'Demo sản phẩm', steps: 'Cách hoạt động', takeaway: 'Kết luận'},
};

export type VidkitShortProps = {
  schemaVersion: number;
  language: string;
  title: string;
  audioSrc: string;
  soundTracks?: SoundTrack[];
  audioSegments?: Array<{startMs: number; endMs: number; sourceStartMs: number}>;
  durationSeconds: number;
  captions: Caption[];
  scenes: Scene[];
  safeArea?: SafeArea;
  theme?: string;
  themeData?: Theme;
  sfx?: Array<{type: 'whoosh'; atMs: number}>;
  visualRegistry?: Record<string, React.ComponentType<{scene: Scene; theme: Theme}>>;
};

const defaultSafeArea: SafeArea = {top: 88, right: 150, bottom: 260, left: 64};
const nfc = (value: string | undefined) => (value ?? '').normalize('NFC');

export type Theme = {
  background: string; surface: string; text: string; muted: string; accent: string; pattern: string;
  typography: {headlineSize: number; captionSize: number};
  motionIntensity: number;
  captionStyle: {width: number; outline: string; shadow: string};
};
const themes = Object.fromEntries(libraryManifest.themes.map((entry) => [entry.id, entry.style])) as Record<string, Theme>;

const captionFontSize = (text: string, maxWidth = 820) => {
  if (typeof document === 'undefined') return text.length > 32 ? 43 : 49;
  const context = document.createElement('canvas').getContext('2d');
  if (!context) return 43;
  for (const size of [49, 46, 43, 40, 38]) {
    context.font = `800 ${size}px "Noto Sans"`;
    let lines = 1;
    let width = 0;
    for (const word of text.split(/\s+/)) {
      const wordWidth = context.measureText(`${width ? ' ' : ''}${word}`).width;
      if (width && width + wordWidth > maxWidth) {
        lines += 1;
        width = context.measureText(word).width;
      } else {
        width += wordWidth;
      }
    }
    if (lines <= 2) return size;
  }
  return 38;
};

const revealStyle = (frame: number, fps: number, intensity = 1): React.CSSProperties => {
  const enter = spring({frame, fps, config: {damping: 18, stiffness: 120}});
  return {
    opacity: enter,
    transform: `translateY(${interpolate(enter, [0, 1], [42 * intensity, 0])}px)`,
  };
};

const Eyebrow: React.FC<{children: React.ReactNode}> = ({children}) => (
  <div style={{fontSize: 25, fontWeight: 800, color: '#1677ff', letterSpacing: 1.2, textTransform: 'uppercase'}}>
    {children}
  </div>
);

const Title: React.FC<{children: React.ReactNode; compact?: boolean}> = ({children, compact}) => {
  const length = String(children ?? '').length;
  const fontSize = compact ? (length > 34 ? 60 : 68) : length > 34 ? 72 : 90;
  return (
    <div
      style={{
        fontSize,
        lineHeight: 1.08,
        fontWeight: 900,
        color: '#10233f',
        letterSpacing: -2.4,
        marginTop: 18,
        display: '-webkit-box',
        WebkitBoxOrient: 'vertical',
        WebkitLineClamp: 2,
        overflow: 'hidden',
      }}
    >
      {children}
    </div>
  );
};

const Body: React.FC<{children: React.ReactNode}> = ({children}) => (
  <div style={{fontSize: 38, lineHeight: 1.35, fontWeight: 600, color: '#526176', marginTop: 24}}>{children}</div>
);

const AssetPanel: React.FC<{scene: Scene}> = ({scene}) => {
  const asset = scene.asset;
  const crop = scene.crop ?? {x: 0, y: 0, width: 1, height: 1};
  if (!asset?.src) {
    return (
      <div
        style={{
          height: 790,
          borderRadius: 38,
          background: '#e8edf5',
          border: '3px dashed #9aa8ba',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          textAlign: 'center',
          padding: 72,
          color: '#607087',
          fontSize: 34,
          fontWeight: 700,
        }}
      >
        Cần bổ sung ảnh minh họa cho cảnh này
      </div>
    );
  }
  const imageStyle: React.CSSProperties = {
    position: 'absolute',
    width: `${100 / crop.width}%`,
    height: `${100 / crop.height}%`,
    left: `${(-crop.x / crop.width) * 100}%`,
    top: `${(-crop.y / crop.height) * 100}%`,
    objectFit: 'contain',
  };
  return (
    <div style={{height: 790, borderRadius: 38, background: '#fff', overflow: 'hidden', position: 'relative', boxShadow: '0 24px 80px rgba(35, 60, 90, .18)', border: '1px solid #dfe6ef'}}>
      <Img src={staticFile(asset.src)} style={imageStyle} />
      {scene.callout?.text ? (
        <div
          style={{
            position: 'absolute',
            left: `${(scene.callout.x ?? 0.08) * 100}%`,
            top: `${(scene.callout.y ?? 0.74) * 100}%`,
            transform: 'translate(-5%, -50%)',
            maxWidth: 660,
            padding: '16px 24px',
            borderRadius: 20,
            background: '#1677ff',
            color: '#fff',
            fontSize: 28,
            lineHeight: 1.25,
            fontWeight: 800,
            boxShadow: '0 12px 35px rgba(22, 119, 255, .35)',
          }}
        >
          {nfc(scene.callout.text)}
        </div>
      ) : null}
    </div>
  );
};

const HookScene: React.FC<{scene: Scene; language: string}> = ({scene, language}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return (
    <AbsoluteFill
      style={{padding: '300px 84px 420px', justifyContent: 'center', ...revealStyle(frame, fps)}}
      from={-1}
    >
      <Eyebrow>{language === 'vi' ? labels.vi.hook : labels.en.hook}</Eyebrow>
      <Title>{nfc(scene.title)}</Title>
      {scene.body ? <Body>{nfc(scene.body)}</Body> : null}
      <div style={{width: 120, height: 10, borderRadius: 99, background: '#1677ff', marginTop: 38}} />
    </AbsoluteFill>
  );
};

const ScreenshotScene: React.FC<{scene: Scene; language: string}> = ({scene, language}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return (
    <AbsoluteFill style={{padding: '150px 66px 350px', ...revealStyle(frame, fps)}}>
      <Eyebrow>{language === 'vi' ? labels.vi.screenshot : labels.en.screenshot}</Eyebrow>
      <Title compact>{nfc(scene.title)}</Title>
      <div style={{marginTop: 34}}><AssetPanel scene={scene} /></div>
    </AbsoluteFill>
  );
};

const StepsScene: React.FC<{scene: Scene; language: string}> = ({scene, language}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return (
    <AbsoluteFill style={{padding: '220px 76px 390px', justifyContent: 'center', ...revealStyle(frame, fps)}}>
      <div style={{display: 'flex', alignItems: 'center', gap: 22}}>
        <div style={{width: 62, height: 62, borderRadius: 18, background: '#1677ff', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 30, fontWeight: 900}}>→</div>
        <Eyebrow>{language === 'vi' ? labels.vi.steps : labels.en.steps}</Eyebrow>
      </div>
      <Title compact>{nfc(scene.title)}</Title>
      {scene.body ? <Body>{nfc(scene.body)}</Body> : null}
      {scene.asset ? <div style={{marginTop: 38, transform: 'scale(.86)', transformOrigin: 'top center'}}><AssetPanel scene={scene} /></div> : null}
    </AbsoluteFill>
  );
};

const TakeawayScene: React.FC<{scene: Scene; language: string}> = ({scene, language}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return (
    <AbsoluteFill style={{padding: '300px 82px 430px', justifyContent: 'center', ...revealStyle(frame, fps)}}>
      <div style={{padding: '54px 48px', borderRadius: 42, background: '#10233f', boxShadow: '0 30px 90px rgba(16, 35, 63, .28)'}}>
        <Eyebrow>{language === 'vi' ? labels.vi.takeaway : labels.en.takeaway}</Eyebrow>
        <div style={{fontSize: scene.title.length > 34 ? 62 : 72, lineHeight: 1.12, fontWeight: 900, color: '#fff', marginTop: 20, display: '-webkit-box', WebkitBoxOrient: 'vertical', WebkitLineClamp: 2, overflow: 'hidden'}}>{nfc(scene.title)}</div>
        {scene.body ? <div style={{fontSize: 36, lineHeight: 1.38, fontWeight: 600, color: '#cbd7e8', marginTop: 24}}>{nfc(scene.body)}</div> : null}
      </div>
    </AbsoluteFill>
  );
};

const FocusImage: React.FC<{scene: Scene; theme: Theme; height?: number}> = ({scene, theme, height = 800}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const asset = scene.asset;
  if (!asset?.src) {
    return <div style={{height, border: `2px dashed ${theme.muted}`, borderRadius: 36, display: 'grid', placeItems: 'center', color: theme.muted, fontSize: 28}}>Visual needed for this scene</div>;
  }
  const crop = scene.crop ?? {x: 0, y: 0, width: 1, height: 1};
  const panelWidth = 948;
  const sourceWidth = asset.width ?? 1200;
  const sourceHeight = asset.height ?? 900;
  const scale = Math.max(panelWidth / (crop.width * sourceWidth), height / (crop.height * sourceHeight));
  const cropWidth = crop.width * sourceWidth * scale;
  const cropHeight = crop.height * sourceHeight * scale;
  const zoomAt = scene.motion?.cues?.find((cue) => cue.type === 'zoom')?.atMs ?? scene.startMs;
  const zoomFrame = Math.max(0, ((zoomAt - scene.startMs) / 1000) * fps);
  const zoom = interpolate(frame, [zoomFrame, zoomFrame + fps * 2], [1, scene.motion?.zoomTo ?? 1 + .065 * theme.motionIntensity],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return <div style={{width: panelWidth, height, borderRadius: 36, overflow: 'hidden', position: 'relative', border: `2px solid ${theme.muted}55`, boxShadow: '0 28px 90px #0006', background: theme.surface}}>
    <div style={{position: 'absolute', inset: 0, transform: `scale(${zoom})`}}>
      <Img src={staticFile(asset.src)} style={{position: 'absolute', width: sourceWidth * scale, height: sourceHeight * scale,
        left: (panelWidth - cropWidth) / 2 - crop.x * sourceWidth * scale,
        top: (height - cropHeight) / 2 - crop.y * sourceHeight * scale}} />
    </div>
    {scene.callout?.text ? <div style={{position: 'absolute', left: `${(scene.callout.x ?? .08) * 100}%`, top: `${(scene.callout.y ?? .74) * 100}%`,
      background: theme.accent, color: theme.background, padding: '12px 20px', borderRadius: 18, fontSize: 28, fontWeight: 800, maxWidth: 650}}>{nfc(scene.callout.text)}</div> : null}
  </div>;
};

const V3Scene: React.FC<{scene: Scene; theme: Theme}> = ({scene, theme}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const reveal = revealStyle(frame, fps, theme.motionIntensity);
  const titleStyle: React.CSSProperties = {fontSize: theme.typography.headlineSize, lineHeight: 1.1, fontWeight: 900, color: theme.text,
    letterSpacing: -1.6, maxWidth: 940, overflowWrap: 'break-word'};
  const bodyStyle: React.CSSProperties = {fontSize: 35, lineHeight: 1.35, fontWeight: 600, color: theme.muted, maxWidth: 900};
  const layout = scene.component ?? scene.layout;
  const revealAt = (index: number, total: number) => {
    const cue = scene.motion?.cues?.[index];
    const durationFrames = Math.max(1, (scene.endMs - scene.startMs) / 1000 * fps);
    return cue ? Math.max(0, (cue.atMs - scene.startMs) / 1000 * fps) :
      index * Math.min(10, durationFrames * .62 / Math.max(1, total - 1));
  };
  if (scene.motion?.mode?.startsWith('jev-')) return <JevVisual scene={scene} theme={theme} />;
  if (layout === 'brand-hook') {
    return <AbsoluteFill style={{padding: '250px 70px 410px', justifyContent: 'center', ...reveal}}>
      {scene.asset?.src ? <div style={{width: 300, height: 300, marginBottom: 55, borderRadius: 48, overflow: 'hidden', background: theme.surface,
        display: 'grid', placeItems: 'center'}}><Img src={staticFile(scene.asset.src)} style={{maxWidth: 270, maxHeight: 270, objectFit: 'contain'}} /></div>
        : <div style={{position: 'relative', width: 520, height: 330, marginBottom: 65, display: 'grid', placeItems: 'center'}}>
          {[300, 230, 155].map((size, index) => <div key={index} style={{position: 'absolute', width: size, height: size,
            borderRadius: '50%', border: `2px solid ${theme.accent}`, opacity: .2 + index * .16,
            transform: `rotate(${frame * (index + 1) * .2}deg)`}} />)}
          <div style={{width: 155, height: 155, borderRadius: 42, background: theme.surface, display: 'grid',
            placeItems: 'center', color: theme.accent, fontSize: 70, fontWeight: 900,
            boxShadow: `0 0 85px ${theme.accent}55`}}>✦</div>
        </div>}
      <AnimatedText transition={{split: 'word', y: [24, 0], opacity: [0, 1], splitStagger: 3, duration: 18}}
        style={{...titleStyle, fontSize: 86}}>{nfc(scene.title)}</AnimatedText>
      {scene.body ? <div style={{...bodyStyle, marginTop: 32}}>{nfc(scene.body)}</div> : null}
    </AbsoluteFill>;
  }
  if (layout === 'screenshot-focus') {
    return <AbsoluteFill style={{padding: '145px 66px 390px', ...reveal}}>
      <div style={titleStyle}>{nfc(scene.title)}</div>
      <div style={{marginTop: 45}}><FocusImage scene={scene} theme={theme} height={890} /></div>
    </AbsoluteFill>;
  }
  if (layout === 'api-response') {
    const fields = scene.body.split(/[,\n]/).map((part) => part.trim()).filter(Boolean).slice(0, 5);
    return <AbsoluteFill style={{padding: '210px 75px 410px', justifyContent: 'center', ...reveal}}>
      <div style={titleStyle}>{nfc(scene.title)}</div>
      <div style={{marginTop: 55, minHeight: 600, borderRadius: 34, background: theme.surface, padding: '65px 48px', border: `2px solid ${theme.accent}55`,
        boxShadow: `0 24px 85px ${theme.accent}19`}}>
        {fields.map((field, index) => <div key={index} style={{fontSize: 39, lineHeight: 1.45, fontWeight: 700, color: theme.text,
          opacity: interpolate(frame, [revealAt(index, fields.length), revealAt(index, fields.length) + 7], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
          padding: '29px 0', borderBottom: index < fields.length - 1 ? `1px solid ${theme.muted}44` : 'none'}}>
          <span style={{color: theme.accent, marginRight: 20}}>{'{ }'}</span>{nfc(field)}
        </div>)}
      </div>
    </AbsoluteFill>;
  }
  if (layout === 'diagram-flow') {
    const steps = scene.body.split(/(?:→|\n)/).map((part) => part.trim()).filter(Boolean).slice(0, 4);
    if (scene.motion?.mode === 'parallel') {
      return <AbsoluteFill style={{padding: '195px 65px 390px', justifyContent: 'center', ...reveal}}>
        <div style={titleStyle}>{nfc(scene.title)}</div>
        <div style={{marginTop: 50, padding: '28px 32px', borderRadius: 24, border: `2px solid ${theme.accent}`, color: theme.text,
          background: theme.surface, fontSize: 37, fontWeight: 800, textAlign: 'center'}}>ONE EMAIL</div>
        <div style={{height: 68, width: 3, background: theme.accent, margin: '0 auto'}} />
        <div style={{display: 'grid', gap: 20}}>{steps.map((step, index) => <div key={index} style={{display: 'flex', gap: 16, alignItems: 'center',
          opacity: interpolate(frame, [revealAt(index, steps.length), revealAt(index, steps.length) + 7], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>
          <div style={{width: 44, height: 3, background: theme.accent}} />
          <div style={{flex: 1, borderRadius: 22, background: theme.surface, padding: '30px 28px', fontSize: 38, fontWeight: 750,
            borderLeft: `7px solid ${theme.accent}`}}>{nfc(step)}</div>
        </div>)}</div>
        <div style={{fontSize: 26, color: theme.muted, marginTop: 28, textAlign: 'center'}}>PARALLEL PASS</div>
      </AbsoluteFill>;
    }
    if (scene.motion?.mode === 'token-chain') {
      return <AbsoluteFill style={{padding: '235px 70px 390px', justifyContent: 'center', ...reveal}}>
        <div style={titleStyle}>{nfc(scene.title)}</div>
        <div style={{marginTop: 90, display: 'flex', alignItems: 'center', gap: 12}}>{steps.map((step, index) => <React.Fragment key={index}>
          {index > 0 ? <div style={{fontSize: 40, color: theme.accent}}>→</div> : null}
          <div style={{minWidth: 0, flex: 1, padding: '30px 9px', borderRadius: 19, background: theme.surface, color: theme.text,
            textAlign: 'center', fontSize: 27, fontWeight: 800, opacity: interpolate(frame,
              [revealAt(index, steps.length), revealAt(index, steps.length) + 7], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>{nfc(step)}</div>
        </React.Fragment>)}</div>
        <div style={{marginTop: 55, color: theme.muted, fontSize: 30}}>Each token waits on the previous one.</div>
      </AbsoluteFill>;
    }
    return <AbsoluteFill style={{padding: '180px 70px 390px', justifyContent: 'center', ...reveal}}>
      <div style={titleStyle}>{nfc(scene.title)}</div>
      <div style={{marginTop: 60, display: 'grid', gap: 34}}>{steps.map((step, index) =>
        <div key={index} style={{display: 'flex', alignItems: 'center', gap: 30,
          opacity: interpolate(frame, [revealAt(index, steps.length), revealAt(index, steps.length) + 7], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>
          <div style={{width: 68, height: 68, borderRadius: 20, background: theme.accent, color: theme.background,
            display: 'grid', placeItems: 'center', fontSize: 31, fontWeight: 900}}>{index + 1}</div>
          <div style={{background: theme.surface, color: theme.text, borderRadius: 24, padding: '34px 34px', flex: 1, fontSize: 41, fontWeight: 700}}>{nfc(step)}</div>
        </div>)}</div>
    </AbsoluteFill>;
  }
  if (layout === 'metric-breakdown') {
    const metric = scene.title.match(/[\d,.]+\s?(?:%|ms|s|tokens|million|billion)?/i)?.[0];
    const range = /\d\s*[–-]\s*\d/.test(scene.title) || scene.title.includes('$');
    return <AbsoluteFill style={{padding: '220px 76px 405px', justifyContent: 'center', ...reveal}}>
      {range ? <div style={{fontSize: 112, fontWeight: 900, color: theme.accent, lineHeight: 1.1}}>{nfc(scene.title)}</div> : metric ? <div style={{fontSize: 132, fontWeight: 900, color: theme.accent, lineHeight: 1}}>
        <AnimatedCounter transition={{values: [0, Number.parseFloat(metric.replace(/,/g, ''))], duration: 34}}
          toFixed={metric.includes('.') ? metric.split('.')[1].match(/^\d+/)?.[0].length ?? 0 : 0}
          postfix={metric.match(/[^\d,.].*$/)?.[0] ?? ''} />
      </div> : null}
      {!range && !metric ? <div style={{...titleStyle, marginTop: 35}}>{nfc(scene.title)}</div> : null}
      {scene.body ? <div style={{...bodyStyle, marginTop: 30}}>{nfc(scene.body)}</div> : null}
      {scene.asset?.src ? <div style={{marginTop: 45}}><FocusImage scene={scene} theme={theme} height={500} /></div> : null}
    </AbsoluteFill>;
  }
  return <AbsoluteFill style={{padding: '240px 78px 420px', justifyContent: 'center', ...reveal}}>
    <div style={{padding: '70px 62px', background: theme.surface, borderRadius: 42, boxShadow: '0 28px 90px #0005',
      border: `2px solid ${theme.accent}44`}}>
      <div style={{height: 9, width: 125, borderRadius: 9, background: theme.accent, marginBottom: 42}} />
      <div style={titleStyle}>{nfc(scene.title)}</div>
      {scene.body ? <div style={{...bodyStyle, marginTop: 32}}>{nfc(scene.body)}</div> : null}
    </div>
  </AbsoluteFill>;
};

const SceneView: React.FC<{scene: Scene; language: string; theme: Theme; isV3: boolean}> = ({scene, language, theme, isV3}) => {
  if (isV3) return <V3Scene scene={scene} theme={theme} />;
  if (scene.layout === 'screenshot') return <ScreenshotScene scene={scene} language={language} />;
  if (scene.layout === 'steps') return <StepsScene scene={scene} language={language} />;
  if (scene.layout === 'takeaway') return <TakeawayScene scene={scene} language={language} />;
  return <HookScene scene={scene} language={language} />;
};

const captionText = (tokens: CaptionToken[]) => tokens.map((token) => token.text).join(' ')
  .replace(/\s+([,.;:!?…%])/g, '$1').normalize('NFC');

const captionLines = (cue: Caption, width: number, fontSize: number): CaptionToken[][] => {
  if (typeof document === 'undefined') return [cue.tokens];
  const ctx = document.createElement('canvas').getContext('2d');
  if (!ctx) return [cue.tokens];
  ctx.font = `700 ${fontSize}px "Noto Sans"`;
  if (ctx.measureText(captionText(cue.tokens)).width <= width) return [cue.tokens];
  const weak = new Set(['at', 'the', 'a', 'an', 'of', 'to', 'with', 'for', 'and', 'or', 'in', 'on', 'và', 'là', 'của', 'ở', 'với']);
  const options = cue.tokens.slice(2, -1).map((_, offset) => {
    const pivot = offset + 2;
    const left = cue.tokens.slice(0, pivot);
    const right = cue.tokens.slice(pivot);
    const a = ctx.measureText(captionText(left)).width;
    const b = ctx.measureText(captionText(right)).width;
    const penalty = Math.abs(a - b) + (weak.has(left[left.length - 1].text.toLowerCase()) ? 600 : 0) + (right.length === 1 ? 900 : 0);
    return {left, right, a, b, penalty};
  }).filter((item) => item.a <= width && item.b <= width);
  options.sort((a, b) => a.penalty - b.penalty);
  if (!options.length) throw new Error(`Caption exceeds two lines at 48px: ${cue.text}`);
  return [options[0].left, options[0].right];
};

const Captions: React.FC<{captions: Caption[]; safeArea: SafeArea; theme: Theme; isV3: boolean}> = ({captions, safeArea, theme, isV3}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const now = (frame / fps) * 1000;
  const cue = captions.find((caption) => now >= caption.startMs && now <= caption.endMs);
  if (!cue) return null;
  if (!isV3) {
    const size = captionFontSize(cue.text);
    return <div style={{position: 'absolute', left: safeArea.left + 12, right: safeArea.right + 12, bottom: safeArea.bottom, textAlign: 'center'}}>
      <div style={{display: 'inline-block', maxWidth: 820, borderRadius: 24, padding: '18px 24px 20px', background: 'rgba(16,35,63,.92)', fontSize: size, lineHeight: 1.22, fontWeight: 800, color: '#fff'}}>
        {cue.text}
      </div>
    </div>;
  }
  const lines = captionLines(cue, theme.captionStyle.width, theme.typography.captionSize);
  return (
    <div style={{position: 'absolute', width: theme.captionStyle.width, left: '50%', transform: 'translateX(-50%)', bottom: safeArea.bottom,
      textAlign: 'center', fontSize: theme.typography.captionSize, lineHeight: 1.23, fontWeight: 700, color: '#fff',
      WebkitTextStroke: `3px ${theme.captionStyle.outline}`, paintOrder: 'stroke fill',
      textShadow: theme.captionStyle.shadow}}>
      {lines.map((line, lineIndex) => <div key={lineIndex} style={{whiteSpace: 'nowrap'}}>
        {line.map((token, index) => {
          const start = token.startMs ?? token.start_ms ?? 0;
          const end = token.endMs ?? token.end_ms ?? start;
          const active = now >= start && now <= end;
          return (
            <React.Fragment key={`${start}-${index}`}>
              {index > 0 ? ' ' : ''}
              <span style={{color: active ? theme.accent : '#fff'}}>{nfc(token.text)}</span>
            </React.Fragment>
          );
        })}
      </div>)}
    </div>
  );
};

export const VidkitShort: React.FC<VidkitShortProps> = (props) => {
  const {fps} = useVideoConfig();
  const safeArea = props.safeArea ?? defaultSafeArea;
  const isV3 = props.schemaVersion >= 3;
  const theme = props.themeData ?? themes[props.theme ?? 'dark-grid'] ?? themes['dark-grid'];
  const [fontHandle] = React.useState(() => delayRender('Loading bundled Noto Sans fonts'));
  React.useEffect(() => {
    let finished = false;
    const finish = () => {
      if (!finished) {
        finished = true;
        continueRender(fontHandle);
      }
    };
    Promise.all([
      document.fonts.load('400 32px "Noto Sans"'),
      document.fonts.load('600 32px "Noto Sans"'),
      document.fonts.load('700 32px "Noto Sans"'),
      document.fonts.load('800 32px "Noto Sans"'),
      document.fonts.load('900 32px "Noto Sans"'),
      document.fonts.ready,
    ]).then(finish, finish);
    return finish;
  }, [fontHandle]);
  return (
    <AbsoluteFill style={{background: isV3 ? theme.background : 'linear-gradient(145deg, #f8fafc 0%, #edf3f9 65%, #e7eef8 100%)',
      color: isV3 ? theme.text : '#10233f', fontFamily: 'Noto Sans, sans-serif', overflow: 'hidden'}}>
      {isV3 ? <GradientTransition
        gradient={[
          `linear-gradient(145deg, ${theme.background}, ${theme.surface})`,
          `linear-gradient(190deg, ${theme.surface}, ${theme.background})`,
        ]}
        frames={[0, Math.max(1, props.durationSeconds * fps)]}
        style={{position: 'absolute', inset: 0, opacity: .6}}
      /> : null}
      <AbsoluteFill style={isV3 ? {backgroundImage: theme.pattern, backgroundSize: '76px 76px', opacity: .75} :
        {opacity: 0.45, backgroundImage: 'radial-gradient(circle at 12% 10%, rgba(22,119,255,.12), transparent 28%), radial-gradient(circle at 90% 60%, rgba(80,145,255,.10), transparent 32%)'}} />
      {props.audioSrc ? props.audioSegments ? props.audioSegments.map((segment, index) =>
        <Sequence key={`audio-${index}`} from={Math.round(segment.startMs * fps / 1000)}
          durationInFrames={Math.max(1, Math.round((segment.endMs - segment.startMs) * fps / 1000))}>
          <Audio src={staticFile(props.audioSrc)} trimBefore={Math.round(segment.sourceStartMs * fps / 1000)} />
        </Sequence>) : <Audio src={staticFile(props.audioSrc)} volume={props.soundTracks?.some((track) => (track.src?.includes('jobs/0e00e47bb788/') || track.src?.includes('jobs/e5fb0399b313/')) && track.id.startsWith('editorial-underscore')) ? 0.8 : 1} /> : null}
      {props.soundTracks ? <SoundTracks tracks={props.soundTracks} /> : null}
      {props.sfx?.filter((cue) => cue.type === 'whoosh').map((cue, index) => <Sequence
        key={`sfx-${index}`}
        from={Math.max(0, Math.round(cue.atMs / 1000 * fps))}
        durationInFrames={Math.round(fps * .36)}
      >
        <Audio src={staticFile('sfx/whoosh.wav')} volume={.16} />
      </Sequence>)}
      {props.scenes.map((scene) => {
        const from = Math.max(0, Math.floor((scene.startMs / 1000) * fps));
        const duration = Math.max(1, Math.ceil(((scene.endMs - scene.startMs) / 1000) * fps));
        const Custom = props.visualRegistry?.[scene.componentId ?? scene.component ?? ''];
        return <Sequence key={scene.id} from={from} durationInFrames={duration} premountFor={Math.min(fps, from)}>
          {Custom ? <Custom scene={scene} theme={theme} /> : <SceneView scene={scene} language={props.language} theme={theme} isV3={isV3} />}
        </Sequence>;
      })}
      <Captions captions={props.captions} safeArea={safeArea} theme={theme} isV3={isV3} />
      {!isV3 ? <div style={{position: 'absolute', top: safeArea.top, left: safeArea.left, fontSize: 22, fontWeight: 800, letterSpacing: 1.4, color: '#718096'}}>VIDKIT · {props.language.toUpperCase()}</div> : null}
    </AbsoluteFill>
  );
};
