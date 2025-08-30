'use client';

import { useCachedData } from '@dotmac/headless';
import { DocumentManager as UniversalDocumentManager } from '@dotmac/file-system';
import type { Document, DocumentCategory } from '@dotmac/file-system';

// Convert mock data to Document format
const mockDocumentData = {
  documents: [
    {
      id: 'DOC-2024-001',
      name: 'January 2024 Invoice',
      type: 'application/pdf',
      category: 'billing',
      size: 159744, // 156 KB
      createdAt: new Date('2024-01-15T00:00:00Z'),
      updatedAt: new Date('2024-01-15T00:00:00Z'),
      description: 'Monthly service invoice for January 2024',
      downloadUrl: '/documents/invoices/2024-01.pdf',
      viewUrl: '/documents/view/2024-01',
      status: 'completed' as const,
      permissions: {
        read: true,
        write: false,
        delete: false,
        share: true
      }
    },
    {
      id: 'DOC-2024-002',
      name: 'Service Agreement',
      type: 'application/pdf',
      category: 'legal',
      size: 2202009, // 2.1 MB
      createdAt: new Date('2024-01-01T00:00:00Z'),
      updatedAt: new Date('2024-01-01T00:00:00Z'),
      description: 'Customer service agreement and terms of service',
      downloadUrl: '/documents/contracts/service-agreement.pdf',
      viewUrl: '/documents/view/service-agreement',
      status: 'completed' as const,
      permissions: {
        read: true,
        write: false,
        delete: false,
        share: false
      }
    },
    {
      id: 'DOC-2023-012',
      name: 'December 2023 Invoice',
      type: 'application/pdf',
      category: 'billing',
      size: 151552, // 148 KB
      createdAt: new Date('2023-12-15T00:00:00Z'),
      updatedAt: new Date('2023-12-15T00:00:00Z'),
      description: 'Monthly service invoice for December 2023',
      downloadUrl: '/documents/invoices/2023-12.pdf',
      viewUrl: '/documents/view/2023-12',
      status: 'completed' as const,
      permissions: {
        read: true,
        write: false,
        delete: false,
        share: true
      }
    },
    {
      id: 'DOC-2024-003',
      name: 'Installation Report',
      type: 'application/pdf',
      category: 'service',
      size: 911360, // 890 KB
      createdAt: new Date('2024-01-15T00:00:00Z'),
      updatedAt: new Date('2024-01-15T00:00:00Z'),
      description: 'Technical installation and equipment setup report',
      downloadUrl: '/documents/technical/installation-report.pdf',
      viewUrl: '/documents/view/installation-report',
      status: 'completed' as const,
      permissions: {
        read: true,
        write: false,
        delete: false,
        share: true
      }
    },
    {
      id: 'DOC-2024-004',
      name: 'Welcome Package',
      type: 'application/pdf',
      category: 'general',
      size: 3355443, // 3.2 MB
      createdAt: new Date('2024-01-01T00:00:00Z'),
      updatedAt: new Date('2024-01-01T00:00:00Z'),
      description: 'New customer welcome package with service information',
      downloadUrl: '/documents/info/welcome-package.pdf',
      viewUrl: '/documents/view/welcome-package',
      status: 'completed' as const,
      permissions: {
        read: true,
        write: false,
        delete: false,
        share: true
      }
    },
    {
      id: 'DOC-2024-005',
      name: '2023 Tax Statement',
      type: 'application/pdf',
      category: 'billing',
      size: 250880, // 245 KB
      createdAt: new Date('2024-01-31T00:00:00Z'),
      updatedAt: new Date('2024-01-31T00:00:00Z'),
      description: 'Annual tax statement for 2023 services',
      downloadUrl: '/documents/tax/2023-statement.pdf',
      viewUrl: '/documents/view/2023-tax',
      status: 'completed' as const,
      permissions: {
        read: true,
        write: false,
        delete: false,
        share: true
      }
    },
  ] as Document[],
  categories: [
    { id: 'all', name: 'All Documents', count: 6 },
    { id: 'billing', name: 'Billing & Invoices', count: 3 },
    { id: 'legal', name: 'Legal Documents', count: 1 },
    { id: 'service', name: 'Service Records', count: 1 },
    { id: 'general', name: 'General Information', count: 1 },
  ] as DocumentCategory[]
};

export function DocumentManager() {
  const { data: documentData, isLoading } = useCachedData(
    'customer-documents',
    async () => mockDocumentData,
    { ttl: 10 * 60 * 1000 }
  );

  const handleDocumentClick = (document: Document) => {
    // Open document viewer or navigate to document page
    if (document.viewUrl) {
      window.open(document.viewUrl, '_blank');
    }
  };

  const handleDocumentDownload = (document: Document) => {
    if (document.downloadUrl) {
      const link = document.createElement('a');
      link.href = document.downloadUrl;
      link.download = document.name;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  const handleDocumentDelete = (documentId: string) => {
    // Handle document deletion
    console.log('Delete document:', documentId);
  };

  const handleUpload = () => {
    // Handle document upload
    console.log('Upload documents');
  };

  if (isLoading || !documentData) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-blue-600 border-b-2" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="font-bold text-2xl text-gray-900">Documents & Statements</h1>
      </div>

      {/* Universal Document Manager */}
      <UniversalDocumentManager
        documents={documentData.documents}
        categories={documentData.categories}
        onDocumentClick={handleDocumentClick}
        onDocumentDownload={handleDocumentDownload}
        onDocumentDelete={handleDocumentDelete}
        onUpload={handleUpload}
        loading={isLoading}
        className="bg-white rounded-lg border border-gray-200"
      />
    </div>
  );
}
