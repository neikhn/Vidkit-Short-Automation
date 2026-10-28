import React from 'react';
import {AbsoluteFill} from 'remotion';
import {BackgroundProps, tint} from './types';

const GridDrift: React.FC<BackgroundProps> = ({theme, phase}) => {
  const tile = 96;
  const offset = phase * tile;
  return <AbsoluteFill style={{backgroundColor: theme.background, backgroundImage:
    `linear-gradient(${tint(theme.accent, 27)} 2px, transparent 2px), linear-gradient(90deg, ${tint(theme.accent, 27)} 2px, transparent 2px)`,
    backgroundSize: `${tile}px ${tile}px`, backgroundPosition: `${offset}px ${offset}px`}}>
    <AbsoluteFill style={{background: `radial-gradient(circle at 50% 42%, transparent 14%, ${tint(theme.background, 45)} 80%)`}} />
  </AbsoluteFill>;
};

export default GridDrift;
