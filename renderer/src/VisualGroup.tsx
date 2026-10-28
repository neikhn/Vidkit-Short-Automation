import React from 'react';

type Props = {children: React.ReactNode; enabled?: boolean; maxWidth: number};

export const VisualGroup: React.FC<Props> = ({children, enabled, maxWidth}) => {
  if (!enabled) return <>{children}</>;
  return <div data-vidkit-visual-group="centered" style={{display: 'flex', justifyContent: 'center', width: '100%', minWidth: 0}}>
    <div style={{width: '100%', maxWidth, minWidth: 0}}>{children}</div>
  </div>;
};
