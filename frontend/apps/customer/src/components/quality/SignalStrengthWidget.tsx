"use client";
import React from 'react';
import { Card, Progress } from '@dotmac/primitives';

export function SignalStrengthWidget({ strengthDbm = -55, qualityPct = 0.92 }: { strengthDbm?: number; qualityPct?: number }) {
  const pct = Math.round(qualityPct * 100);
  const label = strengthDbm > -60 ? 'Excellent' : strengthDbm > -70 ? 'Good' : strengthDbm > -80 ? 'Fair' : 'Weak';
  return (
    <Card className="p-4 space-y-2" data-testid="signal-strength-widget">
      <div className="flex items-center justify-between">
        <div className="font-semibold">Signal Strength</div>
        <div className="text-sm text-muted-foreground">{strengthDbm} dBm</div>
      </div>
      <Progress value={pct} />
      <div className="text-sm">Quality: {pct}% · {label}</div>
    </Card>
  );
}

