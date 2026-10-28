import React from 'react';
import {Pointer} from 'lucide-react';
import {Audio} from '@remotion/media';
import {AbsoluteFill, Easing, interpolate, Sequence, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Scene, Theme} from '../../src/VidkitShort';

type Labels = {
  channelLabel: string;
  likeLabel: string;
  likedLabel: string;
  subscribeLabel: string;
  subscribedLabel: string;
  ctaColor?: string;
  soundEnabled?: boolean;
  soundVolume?: number;
};

const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};
const ease = Easing.bezier(0.2, 0.8, 0.2, 1);
const move = (frame: number, start: number, end: number, from: number, to: number) =>
  interpolate(frame, [start, Math.max(start + 1, end)], [from, to], {...clamp, easing: ease});
const pulse = (frame: number, at: number) =>
  interpolate(frame, [at - 2, at + 3, at + 11], [1, 0.88, 1], clamp);

const Thumb: React.FC<{filled: boolean}> = ({filled}) => <svg width="88" height="88" viewBox="0 0 24 24"
  fill={filled ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="1.8"
  strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
  <path d="M7 10v11H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3ZM7 10l5-7a2 2 0 0 1 3 2v3h4.5a2.5 2.5 0 0 1 2.4 3.2l-2.3 8A2.5 2.5 0 0 1 17.2 21H7" />
</svg>;

const Bell: React.FC<{filled: boolean; rotation: number}> = ({filled, rotation}) => <svg width="90" height="90"
  viewBox="0 0 24 24" fill={filled ? 'currentColor' : 'none'} stroke="currentColor"
  strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"
  style={{transform: `rotate(${rotation}deg)`}}>
  <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9ZM10 21h4" />
</svg>;

const Burst: React.FC<{frame: number; at: number; x: number; color: string}> = ({frame, at, x, color}) => {
  const opacity = interpolate(frame, [at, at + 5, at + 20], [0, 1, 0], clamp);
  const radius = interpolate(frame, [at, at + 20], [74, 124], clamp);
  return <svg width="280" height="280" viewBox="0 0 280 280" aria-hidden="true"
    style={{position: 'absolute', left: x - 140, top: -56, pointerEvents: 'none', opacity}}>
    {Array.from({length: 8}, (_, index) => {
      const angle = index * Math.PI / 4;
      const ax = 140 + Math.cos(angle) * radius;
      const ay = 140 + Math.sin(angle) * radius;
      return <circle key={index} cx={ax} cy={ay} r={index % 2 ? 5 : 7} fill={color} />;
    })}
  </svg>;
};

const ChannelCtaStrip: React.FC<{scene: Scene; theme: Theme}> = ({scene, theme}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const labels = scene.componentProps as Partial<Labels> | undefined;
  if (!labels?.channelLabel || !labels.likeLabel || !labels.likedLabel ||
      !labels.subscribeLabel || !labels.subscribedLabel) {
    throw new Error('Channel CTA needs channel and button labels from the workflow');
  }
  const duration = Math.max(1, Math.round((scene.endMs - scene.startMs) * fps / 1000));
  const likeAt = Math.round(duration * 0.21);
  const subscribeAt = Math.round(duration * 0.46);
  const bellAt = Math.round(duration * 0.67);
  const likeDone = frame >= likeAt + 4;
  const subscribed = frame >= subscribeAt + 4;
  const bellDone = frame >= bellAt + 4;
  const bellRotation = bellDone ? Math.sin((frame - bellAt - 4) * 0.75) *
    Math.exp(-(frame - bellAt - 4) / 15) * 24 : 0;
  const stripOpacity = interpolate(frame, [0, 14], [0, 1], clamp);
  const stripScale = interpolate(frame, [0, 18], [0.92, 1], {...clamp, easing: ease});
  const cursorX = frame < likeAt + 9
    ? move(frame, 8, likeAt, 42, 84)
    : frame < subscribeAt + 9
      ? move(frame, likeAt + 8, subscribeAt, 84, 407)
      : move(frame, subscribeAt + 8, bellAt, 407, 730);
  const cursorY = move(frame, 8, likeAt, 230, 84);
  const cursorOpacity = interpolate(frame, [7, 12, duration - 17, duration - 5], [0, 1, 1, 0], clamp);
  const selectedSurface = '#dfe3e8';
  const selectedInk = '#17202c';
  const subscribeColor = labels.ctaColor || '#ff2636';
  const soundVolume = Math.max(0, Math.min(1, labels.soundVolume ?? 0.32));
  const circle: React.CSSProperties = {width: 168, height: 168, borderRadius: '50%', display: 'flex',
    alignItems: 'center', justifyContent: 'center', flexShrink: 0};

  return <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: '160px 100px 340px',
    color: theme.text, textAlign: 'center'}}>
    {labels.soundEnabled !== false ? <>
      <Sequence from={likeAt + 3} layout="none"><Audio src={staticFile('sfx/cta/like.wav')} volume={soundVolume} /></Sequence>
      <Sequence from={subscribeAt + 3} layout="none"><Audio src={staticFile('sfx/cta/subscribe.wav')} volume={soundVolume} /></Sequence>
      <Sequence from={bellAt + 3} layout="none"><Audio src={staticFile('sfx/cta/bell.wav')} volume={soundVolume * 0.85} /></Sequence>
    </> : null}
    <div style={{width: 850, maxWidth: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
      <div style={{fontSize: 58, fontWeight: 900, color: theme.text, letterSpacing: 1,
        opacity: stripOpacity}}>{labels.channelLabel.normalize('NFC')}</div>
      <div style={{position: 'relative', width: 818, height: 220, marginTop: 66,
        opacity: stripOpacity, transform: `scale(${stripScale})`}}>
        <div style={{display: 'flex', alignItems: 'center', gap: 24}}>
          <div style={{...circle, background: likeDone ? selectedSurface : theme.accent,
            color: likeDone ? selectedInk : '#fff', transform: `scale(${pulse(frame, likeAt)})`}}>
            <Thumb filled={likeDone} />
          </div>
          <div style={{width: 430, height: 168, borderRadius: 100, background: subscribed ? selectedSurface : subscribeColor,
            color: subscribed ? selectedInk : '#fff', fontSize: 47, fontWeight: 900,
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 20,
            whiteSpace: 'nowrap', transform: `scale(${pulse(frame, subscribeAt)})`}}>
            {subscribed ? <span style={{fontSize: 55, lineHeight: 1}}>✓</span> : null}
            {subscribed ? labels.subscribedLabel : labels.subscribeLabel}
          </div>
          <div style={{...circle, background: bellDone ? selectedSurface : theme.accent,
            color: bellDone ? selectedInk : '#fff', transform: `scale(${pulse(frame, bellAt)})`}}>
            <Bell filled={bellDone} rotation={bellRotation} />
          </div>
        </div>
        <Burst frame={frame} at={likeAt + 3} x={84} color={theme.accent} />
        <Burst frame={frame} at={subscribeAt + 3} x={407} color={subscribeColor} />
        <Burst frame={frame} at={bellAt + 3} x={730} color={theme.accent} />
        <div aria-hidden="true"
          style={{position: 'absolute', left: cursorX - 28, top: cursorY - 7, opacity: cursorOpacity,
            width: 84, height: 84,
            filter: 'drop-shadow(3px 5px 3px #0007)', pointerEvents: 'none',
            transformOrigin: '28px 7px',
            transform: `scale(${Math.min(pulse(frame, likeAt), pulse(frame, subscribeAt), pulse(frame, bellAt))})`}}>
          {/* Lucide uses open strokes; a closed underlay keeps the hand opaque. */}
          <svg width="84" height="84" viewBox="0 0 24 24" style={{position: 'absolute', inset: 0}}>
            <path fill="#fff" d="M6 14V4a2 2 0 0 1 4 0v5a2 2 0 0 1 4 0v1a2 2 0 0 1 4 0v1a2 2 0 0 1 4 0v3a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6a2 2 0 0 1 2.83-2.82L7 15Z" />
          </svg>
          <Pointer size={84} strokeWidth={1.7} fill="none" color="#17202c"
            style={{position: 'absolute', inset: 0}} />
        </div>
      </div>
      {scene.title ? <div style={{fontSize: 42, lineHeight: 1.2, fontWeight: 750, maxWidth: 790,
        marginTop: 32, color: theme.text, opacity: stripOpacity}}>{scene.title.normalize('NFC')}</div> : null}
      {scene.body ? <div style={{fontSize: 30, lineHeight: 1.25, maxWidth: 790, marginTop: 16,
        color: theme.muted, opacity: stripOpacity}}>{scene.body.normalize('NFC')}</div> : null}
    </div>
  </AbsoluteFill>;
};

export default ChannelCtaStrip;
