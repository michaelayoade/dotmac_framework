'use client';

import { useCachedData } from '@dotmac/headless';
import { Card } from '@dotmac/styled-components/customer';
import {
  Calendar,
  Download,
  ExternalLink,
  Eye,
  FileCheck,
  FileText,
  Filter,
  FolderOpen,
  Mail,
  Receipt,
  Search,
  Shield,
} from 'lucide-react';
import { useState } from 'react';

// Mock document data
const mockDocumentData = {
  documents: [
    {
      id: 'DOC-2024-001',
      name: 'January 2024 Invoice',
      type: 'invoice',
      category: 'billing',
      size: '156 KB',
      createdDate: '2024-01-15T00:00:00Z',
      description: 'Monthly service invoice for January 2024',
      downloadUrl: '/documents/invoices/2024-01.pdf',
      viewUrl: '/documents/view/2024-01',
      status: 'available',
    },
    {
      id: 'DOC-2024-002',
      name: 'Service Agreement',
      type: 'contract',
      category: 'legal',
      size: '2.1 MB',
      createdDate: '2024-01-01T00:00:00Z',
      description: 'Customer service agreement and terms of service',
      downloadUrl: '/documents/contracts/service-agreement.pdf',
      viewUrl: '/documents/view/service-agreement',
      status: 'available',
    },
    {
      id: 'DOC-2023-012',
      name: 'December 2023 Invoice',
      type: 'invoice',
      category: 'billing',
      size: '148 KB',
      createdDate: '2023-12-15T00:00:00Z',
      description: 'Monthly service invoice for December 2023',
      downloadUrl: '/documents/invoices/2023-12.pdf',
      viewUrl: '/documents/view/2023-12',
      status: 'available',
    },
    {
      id: 'DOC-2024-003',
      name: 'Installation Report',
      type: 'technical',
      category: 'service',
      size: '890 KB',
      createdDate: '2024-01-15T00:00:00Z',
      description: 'Technical installation and equipment setup report',
      downloadUrl: '/documents/technical/installation-report.pdf',
      viewUrl: '/documents/view/installation-report',
      status: 'available',
    },
    {
      id: 'DOC-2024-004',
      name: 'Welcome Package',
      type: 'information',
      category: 'general',
      size: '3.2 MB',
      createdDate: '2024-01-01T00:00:00Z',
      description: 'New customer welcome package with service information',
      downloadUrl: '/documents/info/welcome-package.pdf',
      viewUrl: '/documents/view/welcome-package',
      status: 'available',
    },
    {
      id: 'DOC-2024-005',
      name: '2023 Tax Statement',
      type: 'tax',
      category: 'billing',
      size: '245 KB',
      createdDate: '2024-01-31T00:00:00Z',
      description: 'Annual tax statement for 2023 services',
      downloadUrl: '/documents/tax/2023-statement.pdf',
      viewUrl: '/documents/view/2023-tax',
      status: 'available',
    },
  ],
  categories: [
    { id: 'all', name: 'All Documents', count: 6 },
    { id: 'billing', name: 'Billing & Invoices', count: 3 },
    { id: 'legal', name: 'Legal Documents', count: 1 },
    { id: 'service', name: 'Service Records', count: 1 },
    { id: 'general', name: 'General Information', count: 1 },
  ],
  recentActivity: [
    {
      id: 'ACT-001',
      action: 'downloaded',
      document: 'January 2024 Invoice',
      timestamp: '2024-01-29T14:30:00Z',
    },
    {
      id: 'ACT-002',
      action: 'viewed',
      document: 'Service Agreement',
      timestamp: '2024-01-28T10:15:00Z',
    },
    {
      id: 'ACT-003',
      action: 'generated',
      document: '2023 Tax Statement',
      timestamp: '2024-01-31T09:00:00Z',
    },
  ],
};

export function DocumentManager() {
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'date' | 'name' | 'type'>('date');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  const { data: documentData, isLoading } = useCachedData(
    'customer-documents',
    async () => mockDocumentData,
    { ttl: 10 * 60 * 1000 }
  );

  const getDocumentIcon = (type: string) => {
    switch (type) {
      case 'invoice':
        return <Receipt className='h-5 w-5 text-green-600' />;
      case 'contract':
        return <FileCheck className='h-5 w-5 text-blue-600' />;
      case 'technical':
        return <Shield className='h-5 w-5 text-purple-600' />;
      case 'tax':
        return <FileText className='h-5 w-5 text-orange-600' />;
      default:
        return <FileText className='h-5 w-5 text-gray-600' />;
    }
  };

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'invoice':
        return 'Invoice';
      case 'contract':
        return 'Contract';
      case 'technical':
        return 'Technical';
      case 'tax':
        return 'Tax Document';
      case 'information':
        return 'Information';
      default:
        return 'Document';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      return 'Today';
    }
    if (diffDays === 1) {
      return 'Yesterday';
    }
    if (diffDays < 7) {
      return `${diffDays} days ago`;
    }
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const filteredAndSortedDocuments =
    documentData?.documents
      .filter((doc) => {
        const matchesCategory = selectedCategory === 'all' || doc.category === selectedCategory;
        const matchesSearch =
          doc.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          doc.description.toLowerCase().includes(searchQuery.toLowerCase());
        return matchesCategory && matchesSearch;
      })
      .sort((a, b) => {
        let comparison = 0;

        switch (sortBy) {
          case 'date':
            comparison = new Date(a.createdDate).getTime() - new Date(b.createdDate).getTime();
            break;
          case 'name':
            comparison = a.name.localeCompare(b.name);
            break;
          case 'type':
            comparison = a.type.localeCompare(b.type);
            break;
        }

        return sortOrder === 'asc' ? comparison : -comparison;
      }) || [];

  if (isLoading || !documentData) {
    return (
      <div className='flex h-64 items-center justify-center'>
        <div className='h-8 w-8 animate-spin rounded-full border-blue-600 border-b-2' />
      </div>
    );
  }

  return (
    <div className='space-y-6'>
      {/* Header */}
      <div className='flex items-center justify-between'>
        <h1 className='font-bold text-2xl text-gray-900'>Documents & Statements</h1>
        <button
          type='button'
          className='flex items-center rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700'
        >
          <Mail className='mr-2 h-4 w-4' />
          Email Preferences
        </button>
      </div>

      <div className='grid grid-cols-1 gap-6 lg:grid-cols-4'>
        {/* Sidebar */}
        <div className='space-y-4'>
          {/* Search */}
          <Card className='p-4'>
            <div className='relative'>
              <Search className='-translate-y-1/2 absolute top-1/2 left-3 h-4 w-4 transform text-gray-400' />
              <input
                type='text'
                placeholder='Search documents...'
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className='w-full rounded-lg border border-gray-300 py-2 pr-4 pl-10 focus:outline-none focus:ring-2 focus:ring-blue-500'
              />
            </div>
          </Card>

          {/* Categories */}
          <Card className='p-4'>
            <h3 className='mb-3 font-medium text-gray-900 text-sm'>Categories</h3>
            <div className='space-y-1'>
              {documentData.categories.map((category) => (
                <button
                  type='button'
                  key={category.id}
                  onClick={() => setSelectedCategory(category.id)}
                  className={`w-full rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                    selectedCategory === category.id
                      ? 'bg-blue-100 text-blue-900'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  <div className='flex items-center justify-between'>
                    <span>{category.name}</span>
                    <span className='text-gray-500 text-xs'>{category.count}</span>
                  </div>
                </button>
              ))}
            </div>
          </Card>

          {/* Recent Activity */}
          <Card className='p-4'>
            <h3 className='mb-3 font-medium text-gray-900 text-sm'>Recent Activity</h3>
            <div className='space-y-2'>
              {documentData.recentActivity.map((activity) => (
                <div key={activity.id} className='text-gray-600 text-xs'>
                  <p className='font-medium'>
                    {activity.action} {activity.document}
                  </p>
                  <p className='text-gray-500'>{formatTimestamp(activity.timestamp)}</p>
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* Main Content */}
        <div className='space-y-4 lg:col-span-3'>
          {/* Filters */}
          <Card className='p-4'>
            <div className='flex items-center justify-between'>
              <div className='flex items-center space-x-4'>
                <div className='flex items-center space-x-2'>
                  <Filter className='h-4 w-4 text-gray-400' />
                  <span className='text-gray-700 text-sm'>Sort by:</span>
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value as 'date' | 'name' | 'type')}
                    className='rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
                  >
                    <option value='date'>Date</option>
                    <option value='name'>Name</option>
                    <option value='type'>Type</option>
                  </select>
                  <button
                    type='button'
                    onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                    className='text-blue-600 text-sm hover:text-blue-800'
                  >
                    {sortOrder === 'asc' ? '↑' : '↓'}
                  </button>
                </div>
              </div>
              <span className='text-gray-500 text-sm'>
                {filteredAndSortedDocuments.length} documents
              </span>
            </div>
          </Card>

          {/* Document List */}
          {filteredAndSortedDocuments.length === 0 ? (
            <Card className='p-8 text-center'>
              <FolderOpen className='mx-auto mb-4 h-12 w-12 text-gray-400' />
              <h3 className='mb-2 font-medium text-gray-900 text-lg'>No documents found</h3>
              <p className='text-gray-600'>
                {searchQuery
                  ? 'No documents match your search criteria.'
                  : 'No documents available in this category.'}
              </p>
            </Card>
          ) : (
            <div className='space-y-3'>
              {filteredAndSortedDocuments.map((document) => (
                <Card key={document.id} className='p-4 transition-shadow hover:shadow-md'>
                  <div className='flex items-center justify-between'>
                    <div className='flex min-w-0 flex-1 items-center space-x-4'>
                      <div className='flex-shrink-0'>{getDocumentIcon(document.type)}</div>

                      <div className='min-w-0 flex-1'>
                        <div className='mb-1 flex items-center space-x-2'>
                          <h3 className='truncate font-medium text-gray-900 text-sm'>
                            {document.name}
                          </h3>
                          <span className='inline-flex items-center rounded bg-gray-100 px-2 py-0.5 font-medium text-gray-800 text-xs'>
                            {getTypeLabel(document.type)}
                          </span>
                        </div>

                        <p className='mb-1 line-clamp-1 text-gray-600 text-xs'>
                          {document.description}
                        </p>

                        <div className='flex items-center space-x-3 text-gray-500 text-xs'>
                          <span className='flex items-center'>
                            <Calendar className='mr-1 h-3 w-3' />
                            {formatDate(document.createdDate)}
                          </span>
                          <span>{document.size}</span>
                          <span>#{document.id}</span>
                        </div>
                      </div>
                    </div>

                    <div className='ml-4 flex items-center space-x-2'>
                      <button
                        type='button'
                        onClick={() => window.open(document.viewUrl, '_blank')}
                        className='rounded-lg p-2 text-gray-600 transition-colors hover:bg-blue-50 hover:text-blue-600'
                        title='View Document'
                      >
                        <Eye className='h-4 w-4' />
                      </button>
                      <button
                        type='button'
                        onClick={() => {
                          const link = document.createElement('a');
                          link.href = document.downloadUrl;
                          link.download = document.name;
                          link.click();
                        }}
                        className='rounded-lg p-2 text-gray-600 transition-colors hover:bg-green-50 hover:text-green-600'
                        title='Download Document'
                      >
                        <Download className='h-4 w-4' />
                      </button>
                      <button
                        type='button'
                        onClick={() => window.open(document.viewUrl, '_blank')}
                        className='rounded-lg p-2 text-gray-600 transition-colors hover:bg-gray-50 hover:text-gray-800'
                        title='Open in New Tab'
                      >
                        <ExternalLink className='h-4 w-4' />
                      </button>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}

          {/* Quick Actions */}
          <Card className='p-6'>
            <h3 className='mb-4 font-semibold text-gray-900 text-lg'>Quick Actions</h3>
            <div className='grid grid-cols-1 gap-4 md:grid-cols-3'>
              <button
                type='button'
                className='flex items-center justify-center rounded-lg border-2 border-gray-300 border-dashed p-4 transition-colors hover:border-blue-500 hover:bg-blue-50'
              >
                <div className='text-center'>
                  <Receipt className='mx-auto mb-2 h-6 w-6 text-gray-400' />
                  <span className='text-gray-600 text-sm'>Download All Invoices</span>
                </div>
              </button>

              <button
                type='button'
                className='flex items-center justify-center rounded-lg border-2 border-gray-300 border-dashed p-4 transition-colors hover:border-green-500 hover:bg-green-50'
              >
                <div className='text-center'>
                  <FileText className='mx-auto mb-2 h-6 w-6 text-gray-400' />
                  <span className='text-gray-600 text-sm'>Request Tax Documents</span>
                </div>
              </button>

              <button
                type='button'
                className='flex items-center justify-center rounded-lg border-2 border-gray-300 border-dashed p-4 transition-colors hover:border-purple-500 hover:bg-purple-50'
              >
                <div className='text-center'>
                  <Mail className='mx-auto mb-2 h-6 w-6 text-gray-400' />
                  <span className='text-gray-600 text-sm'>Email Preferences</span>
                </div>
              </button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
