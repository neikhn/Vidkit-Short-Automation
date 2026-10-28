import React from 'react';
import {AbsoluteFill} from 'remotion';
import {BackgroundProps, tint} from './types';

const LightEditorial: React.FC<BackgroundProps> = ({theme, phase}) => {
  const angle = phase * Math.PI * 2;
  const x = 50 + 20 * Math.cos(angle);
  const y = 38 + 12 * Math.sin(angle);
  const tile = 120;
  return <AbsoluteFill style={{backgroundColor: theme.background, backgroundImage:
    `linear-gradient(${tint(theme.accent, 8)} 1px, transparent 1px)`,
    backgroundSize: `${tile}px ${tile}px`, backgroundPosition: `0 ${phase * tile}px`}}>
    <AbsoluteFill style={{background:
      `radial-gradient(ellipse at ${x}% ${y}%, ${tint(theme.accent, 12)}, transparent 64%)`}} />
  </AbsoluteFill>;
};

export default LightEditorial;
