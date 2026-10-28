import React from 'react';
import {AbsoluteFill} from 'remotion';
import {BackgroundProps, tint} from './types';

// Adapted from the Fireflies concept in remotion-bits 0.2.1. All positions
// are deterministic and periodic so scrubbing and the loop seam agree.
const seeds = Array.from({length: 24}, (_, index) => ({
  x: 8 + ((index * 47 + 17) % 84),
  y: 8 + ((index * 71 + 13) % 83),
  radius: 2 + (index % 4),
  offset: index * 2.399963229728653,
}));

const Fireflies: React.FC<BackgroundProps> = ({theme, phase}) => {
  const angle = phase * Math.PI * 2;
  return <AbsoluteFill style={{backgroundColor: theme.background,
    backgroundImage: `radial-gradient(ellipse at 50% 42%, ${tint(theme.surface, 62)}, transparent 72%)`}}>
    {seeds.map((seed, index) => {
      const x = seed.x + 4 * Math.sin(angle + seed.offset);
      const y = seed.y + 3 * Math.cos(angle + seed.offset);
      const opacity = 0.12 + 0.36 * (1 + Math.sin(angle * (index % 3 + 1) + seed.offset)) / 2;
      return <div key={index} style={{position: 'absolute', left: `${x}%`, top: `${y}%`,
        width: seed.radius * 2, height: seed.radius * 2, borderRadius: '50%',
        backgroundColor: theme.accent, opacity,
        boxShadow: `0 0 ${seed.radius * 9}px ${seed.radius * 2}px ${tint(theme.accent, 30)}`}} />;
    })}
  </AbsoluteFill>;
};

export default Fireflies;
