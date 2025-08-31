"use client";
import React, { useEffect, useState } from 'react';
import { Card } from '@dotmac/primitives';

interface FileItem { id: string; name: string; type: string; size: number; owner: string; lastAccessed: string; category?: string; shared?: boolean }

export function FilesTable() {
  const [files, setFiles] = useState<FileItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch('/api/customer/files');
        const json = await res.json();
        setFiles(json.files || []);
      } catch (e: any) {
        setError('Failed to load files');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <Card className="p-4" data-testid="files-table">
      <div className="font-semibold mb-3">Files</div>
      {loading && <div className="text-sm text-muted-foreground">Loading...</div>}
      {error && <div className="text-sm text-destructive">{error}</div>}
      {!loading && files.length === 0 && <div className="text-sm text-muted-foreground">No files yet</div>}
      {!loading && files.length > 0 && (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-muted-foreground">
              <th className="py-2">Name</th>
              <th>Type</th>
              <th>Owner</th>
              <th>Last Accessed</th>
              <th>Shared</th>
            </tr>
          </thead>
          <tbody>
            {files.map(f => (
              <tr key={f.id} className="border-t">
                <td className="py-2">{f.name}</td>
                <td>{f.type}</td>
                <td>{f.owner}</td>
                <td>{new Date(f.lastAccessed).toLocaleDateString()}</td>
                <td>{f.shared ? 'Yes' : 'No'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}

