"use client";
import React, { useEffect, useState } from 'react';
import { UniversalDataTable, type TableColumn } from '@dotmac/data-tables';
import { Card } from '@dotmac/primitives';

interface FileItem { id: string; name: string; type: string; size: number; owner: string; lastAccessed: string; shared?: boolean }

export function FilesDataTable() {
  const [data, setData] = useState<FileItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const res = await fetch('/api/customer/files');
      const json = await res.json();
      setData(json.files || []);
      setLoading(false);
    })();
  }, []);

  const columns: TableColumn<FileItem>[] = [
    { key: 'name', label: 'Name', sortable: true },
    { key: 'type', label: 'Type', sortable: true, filterable: true },
    { key: 'owner', label: 'Owner', filterable: true },
    { key: 'lastAccessed', label: 'Last Accessed', formatter: (v) => new Date(v).toLocaleDateString() },
    { key: 'shared', label: 'Shared', formatter: (v) => (v ? 'Yes' : 'No') }
  ];

  return (
    <Card className="p-4">
      <UniversalDataTable<FileItem>
        data={data}
        columns={columns}
        enableSorting
        enableFiltering
        enableGlobalFilter
        enablePagination
        enableVirtualization
        virtualizationConfig={{ enabled: true, estimateSize: 42, overscan: 8 }}
        pageSize={25}
        loading={loading}
        caption="Your files"
        ariaLabel="Files table"
      />
    </Card>
  );
}

