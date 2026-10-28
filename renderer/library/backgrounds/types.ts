export type BackgroundTheme = {
  background: string;
  surface: string;
  text: string;
  muted: string;
  accent: string;
};

export type BackgroundProps = {theme: BackgroundTheme; phase: number};

export const tint = (color: string, opacity: number) =>
  `color-mix(in srgb, ${color} ${opacity}%, transparent)`;
