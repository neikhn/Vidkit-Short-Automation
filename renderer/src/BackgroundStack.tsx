import React from 'react';
import {AbsoluteFill} from 'remotion';

export type LayerTheme = {background: string; surface: string; text: string; muted: string; accent: string};
export type LayerSettings = {density?: number; lineWidth?: number; opacity?: number; motionIntensity?: number; color?: string};
export type LayerProps = {theme: LayerTheme; phase: number; settings?: LayerSettings};
export type BackgroundLayer = {
  id: string; kind: 'background-pattern' | 'background-effect'; version: string; sha256: string;
  loopSeconds: number; settings?: LayerSettings;
};
export type BackgroundRegistry = Record<string, React.ComponentType<LayerProps>>;

export const BackgroundStack: React.FC<{
  layers: BackgroundLayer[]; registry?: BackgroundRegistry; theme: LayerTheme; frame: number; fps: number;
}> = ({layers, registry, theme, frame, fps}) => {
  if (layers[0]?.kind !== 'background-pattern' || layers.slice(1).some((layer) => layer.kind !== 'background-effect')) {
    throw new Error('Background stack requires one pattern followed by optional effects');
  }
  return <AbsoluteFill style={{pointerEvents: 'none'}}>{layers.map((layer) => {
    const Component = registry?.[layer.id];
    if (!Component) throw new Error(`Background source is unavailable: ${layer.id}`);
    const period = Math.max(1, Math.round(layer.loopSeconds * fps));
    return <Component key={layer.id} theme={theme} phase={((frame % period) + period) % period / period} settings={layer.settings} />;
  })}</AbsoluteFill>;
};
