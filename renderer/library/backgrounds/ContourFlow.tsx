import React from 'react';
import {AbsoluteFill} from 'remotion';
import {BackgroundProps, tint} from './types';

const ContourFlow: React.FC<BackgroundProps> = ({theme, phase}) => {
  const tile = 420;
  const offset = phase * tile;
  return <AbsoluteFill style={{backgroundColor: theme.background, backgroundImage:
    `repeating-radial-gradient(ellipse at center, transparent 0 28px, ${tint(theme.accent, 15)} 30px 32px, transparent 34px 58px)`,
    backgroundSize: `${tile}px ${tile}px`, backgroundPosition: `${offset}px ${offset}px`}}>
    <AbsoluteFill style={{background: `linear-gradient(180deg, ${tint(theme.background, 15)}, ${tint(theme.background, 58)})`}} />
  </AbsoluteFill>;
};

export default ContourFlow;
