import React from 'react';
import {AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

type Asset = {src?: string; width?: number; height?: number};
type Cue = {type?: string; atMs: number};
export type JevScene = {
  id: string;
  title: string;
  body: string;
  startMs: number;
  endMs: number;
  asset?: Asset | null;
  supportAssets?: Asset[];
  motion?: {mode?: string; cues?: Cue[]};
};
export type JevTheme = {background: string; surface: string; text: string; muted: string; accent: string};

const pink = '#EB43B4';
const lime = '#63D6A0';
const amber = '#F2BE63';
const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};

export const JevVisual: React.FC<{scene: JevScene; theme: JevTheme}> = ({scene, theme}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const at = (type: string, fallback = 0) => {
    const cue = scene.motion?.cues?.find((item) => item.type === type);
    return cue ? Math.max(0, (cue.atMs - scene.startMs) / 1000 * fps) : fallback;
  };
  const appear = (start: number, duration = 10) => interpolate(frame, [start, start + duration], [0, 1], clamp);
  const pop = (start: number) => spring({frame: frame - start, fps, config: {damping: 16, stiffness: 180}});
  const card: React.CSSProperties = {background: theme.surface, border: `2px solid ${theme.accent}55`, borderRadius: 28,
    boxShadow: '0 24px 70px #0005', color: theme.text};
  const heading: React.CSSProperties = {fontSize: 64, fontWeight: 900, letterSpacing: -1.5, lineHeight: 1.1, color: theme.text};

  if (scene.motion?.mode === 'jev-banner') {
    return <AbsoluteFill style={{display: 'flex', justifyContent: 'center', alignItems: 'center', paddingBottom: 260}}>
      <div style={{width: 948, height: 390, overflow: 'hidden', borderRadius: 34, border: `3px solid ${pink}AA`,
        boxShadow: `0 0 80px ${pink}2E, 0 28px 85px #0009`, opacity: appear(0, 12),
        transform: `scale(${interpolate(frame, [0, 85], [0.94, 1.035], clamp)})`}}>
        {scene.asset?.src ? <Img src={staticFile(scene.asset.src)} style={{width: '100%', height: '100%', objectFit: 'cover'}} /> : null}
      </div>
    </AbsoluteFill>;
  }

  if (scene.motion?.mode === 'jev-article-tour') {
    const dateAt = at('date');
    const founderAt = at('founder');
    const systemAt = at('system');
    const scroll = interpolate(frame, [0, dateAt, founderAt, systemAt + 12], [0, 0, 100, 270], clamp);
    const stage = frame >= systemAt ? 2 : frame >= founderAt ? 1 : frame >= dateAt ? 0 : -1;
    const highlights = [
      {x: 405, y: 350, w: 145, h: 34},
      {x: 190, y: 650, w: 290, h: 41},
      {x: 185, y: 805, w: 590, h: 63},
    ];
    const labels = ['SEP 15, 2026', 'DIOGO ALMEIDA', 'SYSTEM ONE MODEL'];
    return <AbsoluteFill>
      <div style={{position: 'absolute', top: 92, left: 80, ...heading, fontSize: 48}}>TYPESAFE · OFFICIAL ARTICLE</div>
      <div style={{position: 'absolute', left: 80, top: 190, width: 920, height: 1030, overflow: 'hidden', borderRadius: 32,
        border: `2px solid ${pink}88`, boxShadow: '0 28px 80px #0008', background: '#c0cecf'}}>
        <div style={{position: 'absolute', width: 920, height: 1406, top: -scroll}}>
          {scene.asset?.src ? <Img src={staticFile(scene.asset.src)} style={{width: 920, height: 1406}} /> : null}
          {highlights.map((box, index) => <div key={index} style={{position: 'absolute', left: box.x, top: box.y,
            width: box.w, height: box.h, background: index === stage ? `${pink}55` : 'transparent',
            border: index === stage ? `4px solid ${pink}` : '4px solid transparent', borderRadius: 8,
            boxShadow: index === stage ? `0 0 32px ${pink}88` : 'none'}} />)}
        </div>
        {stage === 1 && scene.supportAssets?.[0]?.src ? <div style={{position: 'absolute', right: 24, bottom: 45,
          width: 275, padding: 8, background: theme.background, borderRadius: 22, border: `3px solid ${pink}`,
          opacity: appear(founderAt), transform: `scale(${0.88 + .12 * pop(founderAt)})`, boxShadow: '0 20px 50px #0008'}}>
          <Img src={staticFile(scene.supportAssets[0].src)} style={{width: 253, height: 248, objectFit: 'cover', borderRadius: 14}} />
          <div style={{fontSize: 29, fontWeight: 900, textAlign: 'center', padding: '8px 0'}}>Diogo Almeida</div>
        </div> : null}
      </div>
      {stage >= 0 ? <div style={{position: 'absolute', left: 120, top: 1260, width: 840, padding: '28px 38px', textAlign: 'center',
        borderRadius: 22, background: pink, color: '#170C18', fontSize: 52, fontWeight: 900,
        boxShadow: `0 15px 45px ${pink}55`, opacity: appear(stage === 0 ? dateAt : stage === 1 ? founderAt : systemAt)}}>{labels[stage]}</div> : null}
    </AbsoluteFill>;
  }

  if (scene.motion?.mode === 'jev-llm-example') {
    const one = at('token-one'), two = at('token-two'), three = at('token-three'), skip = at('skip');
    const starts = [one, two, three, three + 7];
    return <AbsoluteFill>
      <div style={{position: 'absolute', left: 75, top: 240, ...heading}}>CHAT MODEL</div>
      <div style={{position: 'absolute', left: 75, top: 405, width: 930, padding: '38px 42px', ...card,
        fontSize: 37, fontWeight: 600}}><span style={{color: theme.accent, fontWeight: 900}}>INPUT EMAIL</span><br />“I was charged twice. Can someone help?”</div>
      <div style={{position: 'absolute', left: 75, top: 700, fontSize: 32, fontWeight: 800, color: theme.muted}}>GENERATED REPLY · ONE TOKEN AT A TIME</div>
      <div style={{position: 'absolute', left: 75, top: 785, display: 'flex', alignItems: 'center', gap: 13}}>
        {['I', 'can', 'help', 'you.'].map((token, index) => <React.Fragment key={token}>
          {index > 0 ? <span style={{fontSize: 40, color: theme.accent, opacity: appear(starts[index])}}>→</span> : null}
          <div style={{...card, padding: '25px 22px', minWidth: index === 2 ? 165 : 125, textAlign: 'center', fontSize: 42,
            fontWeight: 850, opacity: appear(starts[index]), transform: `translateY(${(1 - pop(starts[index])) * 28}px)`}}>{token}</div>
        </React.Fragment>)}
      </div>
      <div style={{position: 'absolute', left: 75, top: 1030, width: 920, borderTop: `7px solid ${pink}`,
        transformOrigin: 'left', transform: `scaleX(${appear(skip, 10)})`, opacity: appear(skip)}} />
      <div style={{position: 'absolute', left: 75, top: 1100, width: 930, padding: '30px 38px', ...card,
        borderColor: `${pink}AA`, opacity: appear(skip), fontSize: 40, fontWeight: 900}}>
        <span style={{color: pink}}>JEV</span> skips the paragraph → <span style={{color: lime}}>billing</span>
      </div>
    </AbsoluteFill>;
  }

  if (scene.motion?.mode === 'jev-workflow') {
    const questions = [at('team'), at('urgency'), at('review')];
    const evaluate = at('evaluate'), answer = at('answer'), probability = at('probability');
    const results = [{name: 'billing', p: '0.86', width: 194}, {name: 'high', p: '0.72', width: 160}, {name: 'yes', p: '0.94', width: 210}];
    return <AbsoluteFill>
      <div style={{position: 'absolute', left: 75, top: 105, ...heading, fontSize: 58}}>HOW JEV WORKS</div>
      <div style={{position: 'absolute', left: 75, top: 285, width: 430, height: 360, padding: '30px 34px', ...card,
        borderColor: `${pink}AA`, opacity: appear(0)}}>
        <div style={{fontSize: 32, fontWeight: 900, color: pink}}>STATE · EMAIL</div>
        <div style={{fontSize: 39, lineHeight: 1.22, marginTop: 25, fontWeight: 700}}>“I was charged twice. Can someone call me?”</div>
      </div>
      <div style={{position: 'absolute', left: 535, top: 285, width: 470, height: 360, padding: '30px 32px', ...card}}>
        <div style={{fontSize: 32, fontWeight: 900, color: theme.accent}}>TYPED QUESTIONS</div>
        {['Pick a team', 'Score urgency', 'Needs review?'].map((label, index) => <div key={label} style={{fontSize: 34,
          fontWeight: 750, marginTop: 25, padding: '10px 12px', borderRadius: 10, background: `${theme.accent}16`,
          opacity: appear(questions[index], 8), transform: `translateX(${(1 - pop(questions[index])) * 25}px)`}}>{label}</div>)}
      </div>
      <svg style={{position: 'absolute', left: 0, top: 0}} width="1080" height="1350" viewBox="0 0 1080 1350">
        <path d="M290 655 L485 790 M790 655 L595 790" fill="none" stroke={theme.accent} strokeWidth="7"
          strokeDasharray="360" strokeDashoffset={360 * (1 - appear(evaluate, 12))} />
        <path d="M540 940 L210 1075 M540 940 L540 1075 M540 940 L870 1075" fill="none" stroke={lime} strokeWidth="7"
          strokeDasharray="410" strokeDashoffset={410 * (1 - appear(answer, 11))} />
      </svg>
      <div style={{position: 'absolute', left: 390, top: 760, width: 300, height: 175, borderRadius: 32,
        display: 'grid', placeItems: 'center', background: `${pink}EE`, border: '4px solid #FFD0F0',
        boxShadow: `0 0 ${20 + 25 * Math.sin(frame / 4) ** 2}px ${pink}88`, color: '#180D1B',
        fontSize: 77, fontWeight: 950, opacity: appear(evaluate), transform: `scale(${.87 + .13 * pop(evaluate)})`}}>Jev</div>
      {results.map((item, index) => <div key={item.name} style={{position: 'absolute', top: 1070, left: 75 + index * 315,
        width: 285, height: 250, padding: '23px 24px', ...card, borderColor: `${lime}99`,
        opacity: appear(answer + index * 5), transform: `translateY(${(1 - pop(answer + index * 5)) * 30}px)`}}>
        <div style={{fontSize: 40, fontWeight: 900}}>{item.name}</div>
        <div style={{height: 24, marginTop: 30, background: '#314654', borderRadius: 14}}><div style={{width: item.width,
          height: 24, borderRadius: 14, background: lime, transformOrigin: 'left',
          transform: `scaleX(${appear(probability + index * 4, 12)})`}} /></div>
        <div style={{fontSize: 32, color: lime, fontWeight: 850, marginTop: 22}}>p = {item.p}</div>
      </div>)}
    </AbsoluteFill>;
  }

  if (scene.motion?.mode === 'jev-choice-limit') {
    const options = at('options'), caution = at('caution');
    return <AbsoluteFill>
      <div style={{position: 'absolute', left: 75, top: 265, ...heading}}>DEFINED ANSWERS ONLY</div>
      <div style={{position: 'absolute', left: 75, top: 455, fontSize: 32, fontWeight: 850, color: theme.muted}}>TEAM · PICK ONE</div>
      <div style={{position: 'absolute', left: 75, top: 550, display: 'flex', gap: 25}}>{['billing', 'technical', 'sales'].map((item, index) => <div key={item}
        style={{width: 290, padding: '37px 15px', textAlign: 'center', ...card, fontSize: 36, fontWeight: 850,
          borderColor: index === 0 ? lime : `${theme.accent}55`, background: index === 0 ? '#123A34' : theme.surface,
          opacity: appear(options + index * 5), transform: `translateY(${(1 - pop(options + index * 5)) * 45}px)`}}>{item}</div>)}</div>
      <div style={{position: 'absolute', left: 75, top: 790, width: 925, padding: '32px 42px', ...card, borderColor: `${lime}99`,
        fontSize: 42, fontWeight: 850, opacity: appear(options + 12)}}>Jev chooses <span style={{color: lime}}>billing</span> ✓</div>
      <div style={{position: 'absolute', left: 75, top: 1030, width: 925, padding: '35px 40px', borderRadius: 28,
        border: `3px solid ${amber}`, background: '#3D3021', color: amber, fontSize: 43, fontWeight: 900,
        opacity: appear(caution), transform: `translateY(${(1 - pop(caution)) * 40}px)`}}>⚠ Valid format ≠ correct decision</div>
    </AbsoluteFill>;
  }

  if (scene.motion?.mode === 'jev-speed-chart') {
    const bars = appear(at('range'), 16);
    return <AbsoluteFill>
      <div style={{position: 'absolute', left: 75, top: 185, ...heading}}>HOW FAST?</div>
      <div style={{position: 'absolute', left: 75, top: 300, fontSize: 31, color: theme.muted}}>TypeSafe-reported comparison · per call · log scale</div>
      <div style={{position: 'absolute', left: 75, top: 455, width: 930, height: 770, ...card, padding: 40}}>
        <div style={{fontSize: 31, fontWeight: 850, color: lime}}>JEV <span style={{color: theme.text}}>70–500 ms</span></div>
        <div style={{position: 'relative', marginTop: 25, height: 68, background: '#263C47', borderRadius: 16}}>
          <div style={{position: 'absolute', left: 25, top: 0, width: 165 * bars, height: 68, background: lime, borderRadius: 16}} />
        </div>
        <div style={{fontSize: 31, fontWeight: 850, color: pink, marginTop: 75}}>FRONTIER LLMS <span style={{color: theme.text}}>3–329 s</span></div>
        <div style={{position: 'relative', marginTop: 25, height: 68, background: '#263C47', borderRadius: 16}}>
          <div style={{position: 'absolute', left: 320, top: 0, width: 430 * bars, height: 68, background: pink, borderRadius: 16}} />
        </div>
        <div style={{display: 'flex', justifyContent: 'space-between', marginTop: 55, color: theme.muted, fontSize: 24}}>
          <span>0.1s</span><span>1s</span><span>10s</span><span>100s</span><span>300s</span>
        </div>
        <div style={{height: 2, background: theme.muted, marginTop: 15}} />
        <div style={{marginTop: 55, fontSize: 30, color: theme.muted}}>Ranges from TypeSafe's published table</div>
      </div>
    </AbsoluteFill>;
  }

  if (scene.motion?.mode === 'jev-price') {
    const price = at('price'), output = at('output');
    return <AbsoluteFill>
      <div style={{position: 'absolute', left: 75, top: 195, ...heading}}>INPUT TOKENS</div>
      <div style={{position: 'absolute', left: 75, top: 300, fontSize: 31, color: theme.muted}}>TypeSafe-reported pricing</div>
      <div style={{position: 'absolute', left: 75, top: 465, width: 925, height: 240, ...card, padding: '40px 52px'}}>
        <div style={{fontSize: 38, fontWeight: 850}}>1,000,000 tokens</div>
        <div style={{display: 'flex', gap: 10, marginTop: 36}}>{Array.from({length: 18}, (_, index) => <div key={index}
          style={{height: 30, width: 33, borderRadius: 7, background: theme.accent,
            opacity: appear(price - 8 + index * 1.5, 5)}} />)}</div>
      </div>
      <div style={{position: 'absolute', left: 510, top: 725, color: theme.accent, fontSize: 86,
        opacity: appear(price)}}>↓</div>
      <div style={{position: 'absolute', left: 75, top: 850, width: 925, height: 220, padding: '26px 48px', ...card,
        borderColor: `${lime}AA`, opacity: appear(price), transform: `scale(${.9 + .1 * pop(price)})`}}>
        <span style={{fontSize: 120, color: lime, fontWeight: 950}}>$0.042</span><span style={{fontSize: 31, marginLeft: 30}}>INPUT</span>
      </div>
      <div style={{position: 'absolute', left: 75, top: 1135, width: 925, padding: '30px 48px', ...card,
        opacity: appear(output), fontSize: 42, fontWeight: 850}}>OUTPUT <span style={{color: lime, float: 'right'}}>NO SEPARATE CHARGE</span></div>
    </AbsoluteFill>;
  }

  if (scene.motion?.mode === 'jev-email-test') {
    const accuracy = at('accuracy'), cost = at('cost'), caveat = at('caveat');
    return <AbsoluteFill>
      <div style={{position: 'absolute', left: 75, top: 185, ...heading}}>ONE EMAIL TEST</div>
      <div style={{position: 'absolute', left: 75, top: 290, fontSize: 28, color: theme.muted}}>A developer's result, reported by TechCrunch</div>
      <div style={{position: 'absolute', left: 75, top: 440, width: 925, height: 325, ...card, padding: '35px 42px',
        opacity: appear(accuracy)}}>
        <div style={{fontSize: 33, fontWeight: 850, color: theme.accent}}>ACCURACY</div>
        <div style={{fontSize: 47, fontWeight: 900, marginTop: 45}}>Gemini <span style={{color: lime}}>slightly higher</span></div>
        <div style={{fontSize: 28, color: theme.muted, marginTop: 20}}>No exact accuracy scores claimed here</div>
      </div>
      <div style={{position: 'absolute', left: 75, top: 810, width: 925, height: 360, ...card, padding: '35px 42px',
        opacity: appear(cost)}}>
        <div style={{fontSize: 33, fontWeight: 850, color: theme.accent}}>RELATIVE COST</div>
        <div style={{display: 'flex', alignItems: 'center', gap: 22, marginTop: 42, fontSize: 30, fontWeight: 900}}>
          <span style={{width: 130}}>Jev</span><div style={{width: 48, height: 35, background: lime, borderRadius: 8}} /> 1×
        </div>
        <div style={{display: 'flex', alignItems: 'center', gap: 22, marginTop: 30, fontSize: 30, fontWeight: 900}}>
          <span style={{width: 130}}>Gemini</span><div style={{width: 480 * appear(cost, 16), height: 35, background: pink, borderRadius: 8}} /> 10–20×
        </div>
      </div>
      <div style={{position: 'absolute', left: 75, top: 1220, width: 925, borderRadius: 22, padding: '23px 35px',
        background: '#3D3021', color: amber, fontSize: 31, fontWeight: 850, opacity: appear(caveat)}}>
        One task, not a universal benchmark
      </div>
    </AbsoluteFill>;
  }

  if (scene.motion?.mode === 'jev-pairing') {
    const jev = at('jev'), decisions = at('decisions'), prose = at('prose');
    const nodes = [
      {top: 340, label: 'SUPPORT EMAIL', note: 'unstructured state', color: theme.accent, start: 0},
      {top: 660, label: 'JEV', note: 'quick typed decisions', color: pink, start: jev},
      {top: 990, label: 'CHAT MODEL', note: 'writes the reply', color: lime, start: prose},
    ];
    return <AbsoluteFill>
      <div style={{position: 'absolute', left: 75, top: 170, ...heading}}>WORK TOGETHER</div>
      {nodes.map((node, index) => <React.Fragment key={node.label}>
        {index > 0 ? <div style={{position: 'absolute', left: 520, top: node.top - 93, width: 8, height: 82,
          background: node.color, opacity: appear(node.start), transformOrigin: 'top',
          transform: `scaleY(${appear(node.start, 10)})`}} /> : null}
        <div style={{position: 'absolute', left: 75, top: node.top, width: 925, height: 215, padding: '38px 50px', ...card,
          borderColor: node.color, opacity: appear(node.start), transform: `translateY(${(1 - pop(node.start)) * 35}px)`}}>
          <div style={{fontSize: 49, fontWeight: 950, color: node.color}}>{node.label}</div>
          <div style={{fontSize: 33, marginTop: 20, color: theme.muted}}>{node.note}</div>
        </div>
      </React.Fragment>)}
      <div style={{position: 'absolute', left: 690, top: 745, padding: '12px 20px', borderRadius: 18,
        background: pink, color: '#1C1020', fontSize: 27, fontWeight: 900, opacity: appear(decisions)}}>billing · urgent</div>
    </AbsoluteFill>;
  }

  if (scene.motion?.mode === 'jev-cta') {
    const question = at('question'), follow = at('follow');
    return <AbsoluteFill>
      <div style={{position: 'absolute', left: 170, top: 280, width: 740, height: 740, borderRadius: '50%',
        border: `4px solid ${pink}77`, boxShadow: `0 0 100px ${pink}22`,
        transform: `scale(${interpolate(frame, [0, 160], [0.92, 1.08], clamp)})`}} />
      <div style={{position: 'absolute', left: 90, top: 540, width: 900, textAlign: 'center', ...heading,
        fontSize: 81, opacity: appear(question)}}>WHERE WOULD<br />JEV HELP YOU?</div>
      <div style={{position: 'absolute', left: 0, right: 0, top: 900, display: 'flex', justifyContent: 'center', gap: 16,
        opacity: appear(question + 8)}}>{['TRIAGE', 'ROUTING', 'REVIEW'].map((item, index) =>
          <div key={item} style={{padding: '20px 25px', borderRadius: 18, ...card, borderColor: index === 1 ? pink : theme.accent,
            fontSize: 30, fontWeight: 850}}>{item}</div>)}</div>
      <div style={{position: 'absolute', left: 140, top: 1140, width: 800, padding: '30px 35px', borderRadius: 28,
        background: pink, color: '#180F1D', textAlign: 'center', fontSize: 43, fontWeight: 900,
        opacity: appear(follow), transform: `translateY(${(1 - pop(follow)) * 40}px)`}}>Comment your use case · Follow</div>
    </AbsoluteFill>;
  }

  return null;
};
