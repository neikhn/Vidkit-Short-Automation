import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import type {Scene, Theme} from '../../src/VidkitShort';

const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};

const CtaEndCard: React.FC<{scene: Scene; theme: Theme}> = ({scene, theme}) => {
  const frame = useCurrentFrame();
  const progress = interpolate(frame, [0, 16], [0, 1], clamp);
  const title = scene.title.normalize('NFC');
  const follow = scene.body.normalize('NFC');

  return <AbsoluteFill style={{padding: '245px 100px 430px', justifyContent: 'center', textAlign: 'center'}}>
    <div style={{opacity: progress, transform: `translateY(${(1 - progress) * 34}px)`}}>
      <div style={{width: 96, height: 7, margin: '0 auto 48px', borderRadius: 7, background: theme.accent}} />
      <div style={{fontSize: title.length > 62 ? 55 : 66, fontWeight: 900, lineHeight: 1.16,
        color: theme.text, overflowWrap: 'anywhere'}}>{title}</div>
      <div style={{marginTop: 50, fontSize: 44, lineHeight: 1.32, fontWeight: 700,
        color: theme.accent}}>{follow}</div>
    </div>
  </AbsoluteFill>;
};

export default CtaEndCard;
