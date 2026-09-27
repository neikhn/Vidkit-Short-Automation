import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Scene, Theme} from '../../src/VidkitShort';

type Props = {scene: Scene; theme: Theme};
type Kind = 'article-highlight' | 'token-sequence' | 'branch-flow' | 'typed-output' | 'range-log-chart' | 'continuity-handoff';
const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};
const asText = (value: unknown) => typeof value === 'string' ? value : '';
const asList = (value: unknown): string[] => Array.isArray(value) ? value.map(String) : [];

export const Explainer: React.FC<Props & {kind?: Kind}> = ({scene, theme, kind: selectedKind}) => {
  const kind = selectedKind ?? scene.componentId as Kind;
  const local = useCurrentFrame();
  const {fps} = useVideoConfig();
  const absolute = (scene.absoluteStartFrame ?? Math.round(scene.startMs / 1000 * fps)) + local;
  const props = scene.componentProps ?? {};
  const eventAt = (id: string, fallback: number) => scene.events?.find((event) => event.entityId === id)?.atFrame ??
    (scene.absoluteStartFrame ?? 0) + fallback;
  const reveal = (id: string, fallback: number) => interpolate(absolute, [eventAt(id, fallback), eventAt(id, fallback) + 12], [0, 1], clamp);
  const card: React.CSSProperties = {background: theme.surface, border: `2px solid ${theme.accent}55`, borderRadius: 26,
    padding: 38, color: theme.text, boxShadow: '0 24px 55px #0005'};
  const heading: React.CSSProperties = {fontSize: 62, fontWeight: 900, lineHeight: 1.12, marginBottom: 46};
  const inner: React.CSSProperties = {padding: '250px 72px 400px', justifyContent: 'center'};

  if (kind === 'article-highlight') {
    const excerpt = asText(props.excerpt);
    const highlight = asText(props.highlight);
    const start = highlight ? excerpt.indexOf(highlight) : -1;
    return <AbsoluteFill style={inner}><div style={heading}>{scene.title}</div><div style={{...card, fontSize: 42, lineHeight: 1.5}}>
      {start >= 0 ? <>{excerpt.slice(0, start)}<span style={{background: theme.accent, color: theme.background,
        borderRadius: 8, opacity: reveal('highlight', 18)}}>{highlight}</span>{excerpt.slice(start + highlight.length)}</> : excerpt}
      <div style={{fontSize: 24, color: theme.muted, marginTop: 38}}>{asText(props.source)}</div>
    </div></AbsoluteFill>;
  }
  if (kind === 'token-sequence') {
    return <AbsoluteFill style={inner}><div style={heading}>{scene.title}</div><div style={{display: 'flex', flexWrap: 'wrap', gap: 18}}>
      {asList(props.tokens).map((token, index) => <div key={index} style={{...card, padding: '22px 28px', fontSize: 42,
        opacity: reveal(`token-${index}`, index * 9), transform: `translateY(${(1 - reveal(`token-${index}`, index * 9)) * 28}px)`}}>{token}</div>)}
    </div></AbsoluteFill>;
  }
  if (kind === 'branch-flow') {
    const branches = asList(props.branches);
    return <AbsoluteFill style={inner}><div style={heading}>{scene.title}</div><div style={{...card, fontSize: 44,
      textAlign: 'center', opacity: reveal('source', 0)}}>{asText(props.sourceNode)}</div>
      <div style={{height: 100, width: 4, margin: '0 auto', background: theme.accent,
        transformOrigin: 'top', transform: `scaleY(${reveal('connector', 15)})`}} />
      <div style={{display: 'flex', gap: 18}}>{branches.map((branch, index) => <div key={index} style={{...card,
        flex: 1, fontSize: 35, textAlign: 'center', opacity: reveal(`branch-${index}`, 24 + index * 8)}}>{branch}</div>)}</div>
    </AbsoluteFill>;
  }
  if (kind === 'typed-output') {
    const fields = Array.isArray(props.fields) ? props.fields as Array<{name: string; type: string; value: string; probability?: number}> : [];
    return <AbsoluteFill style={inner}><div style={heading}>{scene.title}</div><div style={{...card, fontFamily: 'monospace'}}>
      {fields.map((field, index) => <div key={index} style={{display: 'flex', gap: 14, fontSize: 32, padding: '15px 0',
        borderBottom: `1px solid ${theme.muted}44`, opacity: reveal(`field-${index}`, index * 12)}}>
        <span style={{color: theme.accent}}>{field.name}</span><span style={{color: theme.muted}}>:{field.type}</span>
        <span style={{marginLeft: 'auto'}}>{field.value}</span>
        {field.probability !== undefined ? <span>{Math.round(field.probability * 100)}%</span> : null}
      </div>)}</div></AbsoluteFill>;
  }
  if (kind === 'range-log-chart') {
    const values = Array.isArray(props.values) ? props.values as Array<{label: string; value: number}> : [];
    const scale = props.scale === 'log' ? (value: number) => Math.log10(Math.max(1, value)) : (value: number) => value;
    const max = Math.max(1, ...values.map((item) => scale(item.value)));
    return <AbsoluteFill style={inner}><div style={heading}>{scene.title}</div><div style={{...card}}>
      {values.map((item, index) => <div key={index} style={{marginBottom: 32, opacity: reveal(`bar-${index}`, index * 14)}}>
        <div style={{display: 'flex', justifyContent: 'space-between', fontSize: 30}}><span>{item.label}</span><span>{item.value} {asText(props.unit)}</span></div>
        <div style={{height: 25, marginTop: 13, borderRadius: 20, background: theme.background}}><div style={{height: '100%',
          width: `${100 * scale(item.value) / max}%`, borderRadius: 20, background: theme.accent}} /></div>
      </div>)}<div style={{fontSize: 22, color: theme.muted}}>{asText(props.source)} · {props.scale === 'log' ? 'Log scale' : 'Linear scale'}</div>
    </div></AbsoluteFill>;
  }
  const origin = scene.continuityStartFrame ?? scene.absoluteStartFrame ?? 0;
  const position = interpolate(absolute, [origin, origin + Math.max(1, fps)], [0, 1], clamp);
  return <AbsoluteFill style={inner}><div style={heading}>{scene.title}</div><div style={{...card, fontSize: 48,
    transform: `translateX(${(1 - position) * -140}px)`, opacity: position}}>
      {asText(props.label) || scene.body}</div><div style={{fontSize: 30, color: theme.muted, marginTop: 34}}>{asText(props.destination)}</div>
    </AbsoluteFill>;
};

export default Explainer;
