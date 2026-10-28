import React from 'react';
import {AbsoluteFill} from 'remotion';
import {BackgroundProps, tint} from './types';

// Adapted from the Radial Gradient example in remotion-bits 0.2.1.
const RadialGlow: React.FC<BackgroundProps> = ({theme, phase}) => {
  const angle = phase * Math.PI * 2;
  const x1 = 50 + 27 * Math.cos(angle);
  const y1 = 38 + 21 * Math.sin(angle);
  const x2 = 50 - 24 * Math.cos(angle);
  const y2 = 52 - 25 * Math.sin(angle);
  return <AbsoluteFill style={{backgroundColor: theme.background,
    backgroundImage: `radial-gradient(ellipse at ${x1}% ${y1}%, ${tint(theme.accent, 24)}, transparent 57%), radial-gradient(ellipse at ${x2}% ${y2}%, ${tint(theme.surface, 65)}, transparent 68%)`}} />;
};

export default RadialGlow;
