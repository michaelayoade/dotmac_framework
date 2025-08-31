"use client";
import React, { useEffect, useRef, useState } from 'react';
import { Button, Progress, Card } from '@dotmac/primitives';
import { trackAction } from '@dotmac/monitoring/observability';

export function SpeedTestWidget() {
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<any>(null);
  const timerRef = useRef<any>(null);

  const start = async () => {
    if (running) return;
    trackAction('click', 'speed-test.start');
    setResult(null);
    setRunning(true);
    setProgress(0);

    const durationSec = Number(process.env.NEXT_PUBLIC_SPEED_TEST_SECONDS || 10);
    const interval = 1000;
    let elapsed = 0;
    timerRef.current = setInterval(() => {
      elapsed += 1;
      setProgress(Math.min(100, Math.floor((elapsed / durationSec) * 100)));
      if (elapsed >= durationSec) {
        clearInterval(timerRef.current);
        finish();
      }
    }, interval);
  };

  const finish = async () => {
    try {
      const res = await fetch('/api/customer/quality/speed-test', { method: 'POST' });
      const json = await res.json();
      setResult(json);
    } finally {
      setRunning(false);
      setProgress(100);
    }
  };

  useEffect(() => () => clearInterval(timerRef.current), []);

  return (
    <Card className="p-4 space-y-3" data-testid="speed-test-widget">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">Speed Test</h3>
        {!running && (
          <Button onClick={start} data-testid="speed-test-start">Start Test</Button>
        )}
      </div>
      {running && (
        <div className="space-y-2">
          <Progress value={progress} />
          <div className="text-sm text-muted-foreground">Testing network... {progress}%</div>
        </div>
      )}
      {result && (
        <div className="grid grid-cols-2 gap-3" data-testid="speed-test-result">
          <Card className="p-3"><div className="text-xs text-muted-foreground">Download</div><div className="text-2xl font-bold">{result.downMbps} Mbps</div></Card>
          <Card className="p-3"><div className="text-xs text-muted-foreground">Upload</div><div className="text-2xl font-bold">{result.upMbps} Mbps</div></Card>
          <Card className="p-3"><div className="text-xs text-muted-foreground">Latency</div><div className="text-xl font-semibold">{result.latencyMs} ms</div></Card>
          <Card className="p-3"><div className="text-xs text-muted-foreground">Jitter</div><div className="text-xl font-semibold">{result.jitterMs} ms</div></Card>
        </div>
      )}
    </Card>
  );
}

