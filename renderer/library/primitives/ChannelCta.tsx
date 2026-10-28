import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Scene, Theme} from '../../src/VidkitShort';

type Labels = {
  channelLabel: string;
  likeLabel: string;
  likedLabel: string;
  subscribeLabel: string;
  subscribedLabel: string;
};

const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};
const blend = (from: number, to: number, progress: number) => from + (to - from) * progress;

const ChannelCta: React.FC<{scene: Scene; theme: Theme}> = ({scene, theme}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const labels = scene.componentProps as Partial<Labels> | undefined;
  if (!labels?.channelLabel || !labels.likeLabel || !labels.likedLabel ||
      !labels.subscribeLabel || !labels.subscribedLabel) {
    throw new Error('Channel CTA needs channel and button labels from the workflow');
  }
  const duration = Math.max(1, Math.round((scene.endMs - scene.startMs) * fps / 1000));
  const sceneStart = scene.absoluteStartFrame ?? Math.round(scene.startMs * fps / 1000);
  const likeFrame = (scene.events?.find((event) => event.id === 'like-click')?.atFrame ??
    (sceneStart + Math.round(duration * 0.35))) - sceneStart;
  const subscribeFrame = (scene.events?.find((event) => event.id === 'subscribe-click')?.atFrame ??
    (sceneStart + Math.round(duration * 0.66))) - sceneStart;
  const reveal = interpolate(frame, [0, 15], [0, 1], clamp);
  const likeReveal = interpolate(frame, [2, 16], [0, 1], clamp);
  const subscribeReveal = interpolate(frame, [9, 23], [0, 1], clamp);
  const likeApproach = interpolate(frame, [Math.max(0, likeFrame - 14), likeFrame], [0, 1], clamp);
  const subscribeApproach = interpolate(frame, [likeFrame + 8, subscribeFrame], [0, 1], clamp);
  const cursorX = frame < likeFrame + 8 ? blend(450, 195, likeApproach) : blend(195, 645, subscribeApproach);
  const cursorY = frame < likeFrame + 8 ? blend(205, 73, likeApproach) : 73;
  const likePressed = frame >= likeFrame + 4;
  const subscribePressed = frame >= subscribeFrame + 4;
  const pressScale = (at: number) => frame >= at && frame < at + 8
    ? 1 - 0.12 * Math.sin(Math.PI * (frame - at) / 8) : 1;
  const buttonBase: React.CSSProperties = {height: 134, borderRadius: 32, display: 'flex', alignItems: 'center',
    justifyContent: 'center', gap: 18, fontWeight: 800, fontSize: 38,
    boxShadow: '0 18px 48px #0003', border: `2px solid ${theme.accent}66`};

  return <AbsoluteFill style={{padding: '220px 100px 440px', justifyContent: 'center', alignItems: 'center',
    color: theme.text, textAlign: 'center'}}>
    <div style={{width: 840, maxWidth: '100%', opacity: reveal,
      transform: `translateY(${(1 - reveal) * 36}px)`}}>
      <div style={{fontSize: 38, fontWeight: 800, letterSpacing: 2, color: theme.accent}}>
        {labels.channelLabel.normalize('NFC')}
      </div>
      <div style={{fontSize: scene.title.length > 64 ? 54 : 65, fontWeight: 900, lineHeight: 1.16,
        marginTop: 28, overflowWrap: 'anywhere'}}>{scene.title.normalize('NFC')}</div>
      {scene.body ? <div style={{fontSize: 32, lineHeight: 1.3, marginTop: 20, color: theme.muted}}>
        {scene.body.normalize('NFC')}
      </div> : null}
      <div style={{position: 'relative', width: 840, height: 235, marginTop: 64}}>
        <div style={{display: 'flex', gap: 24}}>
          <div style={{...buttonBase, width: 390, opacity: likeReveal,
            transform: `translateY(${(1 - likeReveal) * 28}px) scale(${pressScale(likeFrame)})`,
            color: likePressed ? theme.background : theme.text,
            background: likePressed ? theme.accent : theme.surface}}>
            <svg aria-hidden="true" width="45" height="45" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M7 10v11H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3ZM7 10l5-7a2 2 0 0 1 3 2v3h4.5a2.5 2.5 0 0 1 2.4 3.2l-2.3 8A2.5 2.5 0 0 1 17.2 21H7" />
            </svg>
            {likePressed ? labels.likedLabel : labels.likeLabel}
          </div>
          <div style={{...buttonBase, width: 426, opacity: subscribeReveal,
            transform: `translateY(${(1 - subscribeReveal) * 28}px) scale(${pressScale(subscribeFrame)})`,
            color: subscribePressed ? theme.background : theme.text,
            background: subscribePressed ? theme.accent : theme.surface}}>
            {subscribePressed ? '✓' : '+'} {subscribePressed ? labels.subscribedLabel : labels.subscribeLabel}
          </div>
        </div>
        <svg aria-hidden="true" width="68" height="68" viewBox="0 0 40 40"
          style={{position: 'absolute', left: cursorX, top: cursorY, opacity: frame < 8 ? 0 : 1,
            filter: 'drop-shadow(3px 5px 5px #0008)', pointerEvents: 'none'}}>
          <path d="M3 2 L3 33 L12 25 L20 39 L27 35 L19 22 L32 21 Z"
            fill={theme.text} stroke={theme.background} strokeWidth="2.5" strokeLinejoin="round" />
        </svg>
      </div>
    </div>
  </AbsoluteFill>;
};

export default ChannelCta;
