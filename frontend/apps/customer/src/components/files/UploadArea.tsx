"use client";
import React, { useCallback, useState } from 'react';
import { Button, Card } from '@dotmac/primitives';
import { trackAction } from '@dotmac/monitoring/observability';

export function UploadArea() {
  const [drag, setDrag] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  const onDrop = useCallback(async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setStatus('Uploading...');
    trackAction('upload', 'files', { count: files.length });
    const form = new FormData();
    Array.from(files).forEach((f) => form.append('file', f));
    await fetch('/api/customer/files/upload', { method: 'POST', body: form });
    setStatus('Uploaded');
  }, []);

  return (
    <Card
      className={"p-4 border-dashed " + (drag ? 'border-primary' : 'border-muted')}
      onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => { e.preventDefault(); setDrag(false); onDrop(e.dataTransfer.files); }}
      data-testid="upload-area"
    >
      <div className="flex items-center justify-between">
        <div>
          <div className="font-semibold">Upload files</div>
          <div className="text-sm text-muted-foreground">Drag and drop or select from device</div>
        </div>
        <label className="inline-block">
          <input type="file" multiple className="hidden" onChange={(e) => onDrop(e.target.files)} />
          <Button asChild>
            <span>Select Files</span>
          </Button>
        </label>
      </div>
      {status && <div className="text-xs text-muted-foreground mt-2">{status}</div>}
    </Card>
  );
}

