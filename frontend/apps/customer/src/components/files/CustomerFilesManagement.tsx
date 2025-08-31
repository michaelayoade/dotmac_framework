'use client';

import React, { useState } from 'react';
import { ManagementPageTemplate } from '@dotmac/primitives/templates/ManagementPageTemplate';
import { 
  DocumentIcon, 
  PhotoIcon, 
  PlusIcon, 
  EyeIcon,
  ArrowDownTrayIcon,
  ShareIcon,
  TrashIcon,
  FolderIcon
} from '@heroicons/react/24/outline';

interface CustomerFile {
  id: string;
  name: string;
  type: 'document' | 'photo' | 'video' | 'invoice' | 'contract' | 'other';
  size: number;
  uploadDate: string;
  category: 'installation' | 'billing' | 'support' | 'contracts' | 'personal';
  description?: string;
  tags: string[];
  url: string;
  shared: boolean;
  sharedWith?: string[];
  downloadCount: number;
  lastAccessed?: string;
}

const mockFiles: CustomerFile[] = [
  {
    id: '1',
    name: 'Service_Agreement_2023.pdf',
    type: 'contract',
    size: 2450000,
    uploadDate: '2023-01-15T10:30:00Z',
    category: 'contracts',
    description: 'Original service agreement and terms',
    tags: ['agreement', 'contract', '2023'],
    url: '/api/customer-files/1',
    shared: false,
    downloadCount: 3,
    lastAccessed: '2023-11-15T14:22:00Z'
  },
  {
    id: '2',
    name: 'Installation_Photos.zip',
    type: 'photo',
    size: 15680000,
    uploadDate: '2023-01-18T14:15:00Z',
    category: 'installation',
    description: 'Photos from equipment installation',
    tags: ['installation', 'photos', 'equipment'],
    url: '/api/customer-files/2',
    shared: true,
    sharedWith: ['support@example.com'],
    downloadCount: 1,
    lastAccessed: '2023-01-20T09:15:00Z'
  },
  {
    id: '3',
    name: 'November_2023_Invoice.pdf',
    type: 'invoice',
    size: 890000,
    uploadDate: '2023-11-01T08:00:00Z',
    category: 'billing',
    description: 'Monthly service invoice',
    tags: ['invoice', 'november', 'billing'],
    url: '/api/customer-files/3',
    shared: false,
    downloadCount: 2,
    lastAccessed: '2023-11-05T16:45:00Z'
  },
  {
    id: '4',
    name: 'Support_Ticket_Screenshots.png',
    type: 'photo',
    size: 1250000,
    uploadDate: '2023-10-28T16:45:00Z',
    category: 'support',
    description: 'Screenshots for support ticket #12345',
    tags: ['support', 'screenshots', 'troubleshooting'],
    url: '/api/customer-files/4',
    shared: true,
    sharedWith: ['support@example.com', 'tech@example.com'],
    downloadCount: 5,
    lastAccessed: '2023-11-01T11:30:00Z'
  }
];

export const CustomerFilesManagement: React.FC = () => {
  const [files, setFiles] = useState<CustomerFile[]>(mockFiles);
  const [filteredFiles, setFilteredFiles] = useState<CustomerFile[]>(mockFiles);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<CustomerFile[]>([]);
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('list');

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getFileIcon = (type: string) => {
    switch (type) {
      case 'photo':
        return <PhotoIcon className="w-5 h-5 text-blue-600" />;
      case 'document':
      case 'contract':
      case 'invoice':
        return <DocumentIcon className="w-5 h-5 text-green-600" />;
      default:
        return <DocumentIcon className="w-5 h-5 text-gray-600" />;
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'installation': return 'bg-blue-100 text-blue-800';
      case 'billing': return 'bg-green-100 text-green-800';
      case 'support': return 'bg-yellow-100 text-yellow-800';
      case 'contracts': return 'bg-purple-100 text-purple-800';
      case 'personal': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const columns = [
    {
      key: 'name' as keyof CustomerFile,
      label: 'File Name',
      render: (value: string, item: CustomerFile) => (
        <div className="flex items-center space-x-3">
          {getFileIcon(item.type)}
          <div>
            <div className="font-medium text-gray-900">{value}</div>
            <div className="text-sm text-gray-500">
              {formatFileSize(item.size)} • {item.downloadCount} downloads
            </div>
          </div>
        </div>
      )
    },
    {
      key: 'category' as keyof CustomerFile,
      label: 'Category',
      render: (value: string) => (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${getCategoryColor(value)}`}>
          {value}
        </span>
      )
    },
    {
      key: 'uploadDate' as keyof CustomerFile,
      label: 'Upload Date',
      render: (value: string) => new Date(value).toLocaleDateString()
    },
    {
      key: 'shared' as keyof CustomerFile,
      label: 'Sharing',
      render: (value: boolean, item: CustomerFile) => (
        <div className="flex items-center space-x-2">
          {value ? (
            <>
              <ShareIcon className="w-4 h-4 text-blue-600" />
              <span className="text-sm text-blue-600">
                Shared with {item.sharedWith?.length || 0}
              </span>
            </>
          ) : (
            <span className="text-sm text-gray-500">Private</span>
          )}
        </div>
      )
    },
    {
      key: 'tags' as keyof CustomerFile,
      label: 'Tags',
      render: (value: string[]) => (
        <div className="flex flex-wrap gap-1">
          {value.slice(0, 2).map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-800"
            >
              {tag}
            </span>
          ))}
          {value.length > 2 && (
            <span className="text-xs text-gray-500">+{value.length - 2} more</span>
          )}
        </div>
      )
    },
    {
      key: 'id' as keyof CustomerFile,
      label: 'Actions',
      render: (value: string, item: CustomerFile) => (
        <div className="flex items-center space-x-2">
          <button
            onClick={() => handleViewFile(item)}
            className="text-blue-600 hover:text-blue-800"
            aria-label={`View ${item.name}`}
          >
            <EyeIcon className="w-4 h-4" />
          </button>
          <button
            onClick={() => handleDownloadFile(item)}
            className="text-green-600 hover:text-green-800"
            aria-label={`Download ${item.name}`}
          >
            <ArrowDownTrayIcon className="w-4 h-4" />
          </button>
          <button
            onClick={() => handleShareFile(item)}
            className="text-purple-600 hover:text-purple-800"
            aria-label={`Share ${item.name}`}
          >
            <ShareIcon className="w-4 h-4" />
          </button>
          <button
            onClick={() => handleDeleteFile(item)}
            className="text-red-600 hover:text-red-800"
            aria-label={`Delete ${item.name}`}
          >
            <TrashIcon className="w-4 h-4" />
          </button>
        </div>
      )
    }
  ];

  const handleSearch = (query: string) => {
    const filtered = files.filter(file => 
      file.name.toLowerCase().includes(query.toLowerCase()) ||
      file.description?.toLowerCase().includes(query.toLowerCase()) ||
      file.tags.some(tag => tag.toLowerCase().includes(query.toLowerCase()))
    );
    setFilteredFiles(filtered);
  };

  const handleFilter = (filters: Record<string, string>) => {
    let filtered = files;
    
    if (filters.type) {
      filtered = filtered.filter(file => file.type === filters.type);
    }
    if (filters.category) {
      filtered = filtered.filter(file => file.category === filters.category);
    }
    if (filters.shared) {
      if (filters.shared === 'shared') {
        filtered = filtered.filter(file => file.shared);
      } else if (filters.shared === 'private') {
        filtered = filtered.filter(file => !file.shared);
      }
    }
    
    setFilteredFiles(filtered);
  };

  const handleViewFile = (file: CustomerFile) => {
    // Track access
    setFiles(prev => prev.map(f => 
      f.id === file.id 
        ? { ...f, lastAccessed: new Date().toISOString() }
        : f
    ));
    
    // Open file
    window.open(file.url, '_blank');
  };

  const handleDownloadFile = (file: CustomerFile) => {
    // Track download
    setFiles(prev => prev.map(f => 
      f.id === file.id 
        ? { 
            ...f, 
            downloadCount: f.downloadCount + 1,
            lastAccessed: new Date().toISOString() 
          }
        : f
    ));
    
    // Trigger download
    const link = document.createElement('a');
    link.href = file.url;
    link.download = file.name;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleShareFile = (file: CustomerFile) => {
    // Open sharing modal
    const email = prompt('Enter email address to share with:');
    if (email) {
      setFiles(prev => prev.map(f => 
        f.id === file.id 
          ? { 
              ...f, 
              shared: true,
              sharedWith: [...(f.sharedWith || []), email]
            }
          : f
      ));
    }
  };

  const handleDeleteFile = (file: CustomerFile) => {
    if (confirm(`Are you sure you want to delete "${file.name}"?`)) {
      setFiles(prev => prev.filter(f => f.id !== file.id));
      setFilteredFiles(prev => prev.filter(f => f.id !== file.id));
    }
  };

  const actions = [
    {
      label: 'Upload Files',
      onClick: () => setShowUploadModal(true),
      variant: 'primary' as const,
      icon: PlusIcon
    },
    {
      label: 'Organize',
      onClick: () => {
        // Show organization options
      },
      variant: 'secondary' as const,
      icon: FolderIcon
    }
  ];

  const filters = [
    {
      key: 'type',
      label: 'File Type',
      options: [
        { value: 'document', label: 'Documents' },
        { value: 'photo', label: 'Photos' },
        { value: 'invoice', label: 'Invoices' },
        { value: 'contract', label: 'Contracts' },
        { value: 'other', label: 'Other' }
      ]
    },
    {
      key: 'category',
      label: 'Category',
      options: [
        { value: 'installation', label: 'Installation' },
        { value: 'billing', label: 'Billing' },
        { value: 'support', label: 'Support' },
        { value: 'contracts', label: 'Contracts' },
        { value: 'personal', label: 'Personal' }
      ]
    },
    {
      key: 'shared',
      label: 'Sharing',
      options: [
        { value: 'shared', label: 'Shared Files' },
        { value: 'private', label: 'Private Files' }
      ]
    }
  ];

  const totalSize = files.reduce((sum, file) => sum + file.size, 0);
  const storageUsed = (totalSize / 1024 / 1024).toFixed(1);
  const storageLimit = '1000'; // 1GB limit

  return (
    <>
      <ManagementPageTemplate
        title="My Files"
        subtitle={`${files.length} files • ${storageUsed} MB of ${storageLimit} MB used`}
        data={filteredFiles}
        columns={columns}
        onSearch={handleSearch}
        onFilter={handleFilter}
        onItemSelect={setSelectedFiles}
        actions={actions}
        filters={filters}
        selectable={true}
        searchPlaceholder="Search files by name, description, or tags..."
        emptyMessage="No files found"
        className="h-full"
      />

      {/* File Upload Modal */}
      {showUploadModal && (
        <FileUploadModal
          onClose={() => setShowUploadModal(false)}
          onUpload={(newFiles) => {
            setFiles(prev => [...prev, ...newFiles]);
            setFilteredFiles(prev => [...prev, ...newFiles]);
          }}
        />
      )}
    </>
  );
};

// File Upload Modal Component
const FileUploadModal: React.FC<{
  onClose: () => void;
  onUpload: (files: CustomerFile[]) => void;
}> = ({ onClose, onUpload }) => {
  const [uploadData, setUploadData] = useState({
    category: 'personal',
    description: '',
    tags: '',
    makePrivate: true
  });
  const [dragActive, setDragActive] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const files = Array.from(e.dataTransfer.files);
    setSelectedFiles(prev => [...prev, ...files]);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files);
      setSelectedFiles(prev => [...prev, ...files]);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    const newFiles: CustomerFile[] = selectedFiles.map((file, index) => ({
      id: `upload-${Date.now()}-${index}`,
      name: file.name,
      type: getFileType(file),
      size: file.size,
      uploadDate: new Date().toISOString(),
      category: uploadData.category as CustomerFile['category'],
      description: uploadData.description || undefined,
      tags: uploadData.tags.split(',').map(tag => tag.trim()).filter(Boolean),
      url: URL.createObjectURL(file),
      shared: !uploadData.makePrivate,
      sharedWith: uploadData.makePrivate ? undefined : [],
      downloadCount: 0
    }));

    onUpload(newFiles);
    onClose();
  };

  const getFileType = (file: File): CustomerFile['type'] => {
    if (file.type.startsWith('image/')) return 'photo';
    if (file.type.startsWith('video/')) return 'video';
    if (file.name.toLowerCase().includes('invoice')) return 'invoice';
    if (file.name.toLowerCase().includes('contract') || file.name.toLowerCase().includes('agreement')) return 'contract';
    return 'document';
  };

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      role="dialog"
      aria-labelledby="upload-title"
      aria-modal="true"
    >
      <div className="bg-white rounded-lg w-full max-w-2xl max-h-[90vh] overflow-auto">
        <div className="p-6">
          <h2 id="upload-title" className="text-xl font-semibold mb-6">Upload Files</h2>
          
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* File Drop Zone */}
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              className={`
                border-2 border-dashed rounded-lg p-8 text-center transition-colors
                ${dragActive ? 'border-blue-400 bg-blue-50' : 'border-gray-300'}
              `}
            >
              <DocumentIcon className="mx-auto h-12 w-12 text-gray-400 mb-4" />
              <div>
                <label htmlFor="file-upload" className="cursor-pointer">
                  <span className="text-lg font-medium text-blue-600 hover:text-blue-700">
                    Choose files to upload
                  </span>
                  <input
                    id="file-upload"
                    type="file"
                    multiple
                    className="sr-only"
                    onChange={handleFileSelect}
                    accept=".pdf,.png,.jpg,.jpeg,.gif,.doc,.docx,.txt,.zip"
                  />
                </label>
                <p className="text-gray-600 mt-2">or drag and drop files here</p>
                <p className="text-sm text-gray-500 mt-1">
                  PDF, Images, Documents up to 10MB each
                </p>
              </div>
            </div>

            {/* Selected Files List */}
            {selectedFiles.length > 0 && (
              <div className="space-y-2">
                <h3 className="font-medium text-gray-900">Selected Files ({selectedFiles.length})</h3>
                <div className="max-h-32 overflow-y-auto space-y-1">
                  {selectedFiles.map((file, index) => (
                    <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                      <div className="flex items-center space-x-2">
                        <DocumentIcon className="w-4 h-4 text-gray-600" />
                        <span className="text-sm">{file.name}</span>
                        <span className="text-xs text-gray-500">
                          ({(file.size / 1024 / 1024).toFixed(2)} MB)
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => setSelectedFiles(prev => prev.filter((_, i) => i !== index))}
                        className="text-red-600 hover:text-red-800 text-sm"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* File Metadata */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="category" className="block text-sm font-medium text-gray-700 mb-1">
                  Category *
                </label>
                <select
                  id="category"
                  value={uploadData.category}
                  onChange={(e) => setUploadData({...uploadData, category: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                >
                  <option value="personal">Personal</option>
                  <option value="billing">Billing</option>
                  <option value="support">Support</option>
                  <option value="contracts">Contracts</option>
                  <option value="installation">Installation</option>
                </select>
              </div>

              <div>
                <label htmlFor="tags" className="block text-sm font-medium text-gray-700 mb-1">
                  Tags (comma separated)
                </label>
                <input
                  id="tags"
                  type="text"
                  value={uploadData.tags}
                  onChange={(e) => setUploadData({...uploadData, tags: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="important, backup, 2023"
                />
              </div>
            </div>

            <div>
              <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                id="description"
                value={uploadData.description}
                onChange={(e) => setUploadData({...uploadData, description: e.target.value})}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Brief description of the files..."
              />
            </div>

            <div className="flex items-center">
              <input
                id="makePrivate"
                type="checkbox"
                checked={uploadData.makePrivate}
                onChange={(e) => setUploadData({...uploadData, makePrivate: e.target.checked})}
                className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <label htmlFor="makePrivate" className="ml-2 text-sm text-gray-700">
                Keep files private (not shared with support)
              </label>
            </div>

            <div className="flex space-x-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 px-4 py-2 text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-500"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={selectedFiles.length === 0}
                className="flex-1 px-4 py-2 text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Upload {selectedFiles.length > 0 ? `${selectedFiles.length} Files` : ''}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};