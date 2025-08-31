'use client';

import React, { useState } from 'react';
import { ManagementPageTemplate } from '@dotmac/primitives/templates/ManagementPageTemplate';
import { 
  DocumentIcon, 
  PhotoIcon, 
  PlusIcon, 
  EyeIcon,
  ArrowDownTrayIcon,
  TrashIcon 
} from '@heroicons/react/24/outline';

interface FileItem {
  id: string;
  name: string;
  type: 'document' | 'photo' | 'video' | 'other';
  size: number;
  uploadDate: string;
  category: 'installation' | 'maintenance' | 'repair' | 'inspection' | 'other';
  workOrderId?: string;
  customerId?: string;
  description?: string;
  tags: string[];
  url: string;
}

const mockFiles: FileItem[] = [
  {
    id: '1',
    name: 'Installation_Photos_Site_A_20231201.zip',
    type: 'photo',
    size: 15680000,
    uploadDate: '2023-12-01T10:30:00Z',
    category: 'installation',
    workOrderId: 'WO-2023-001',
    customerId: 'CUST-001',
    description: 'Before, during, and after installation photos',
    tags: ['installation', 'documentation', 'photos'],
    url: '/api/files/1'
  },
  {
    id: '2',
    name: 'Service_Agreement_Signed.pdf',
    type: 'document',
    size: 2450000,
    uploadDate: '2023-12-01T14:15:00Z',
    category: 'installation',
    workOrderId: 'WO-2023-001',
    customerId: 'CUST-001',
    description: 'Signed service agreement and installation checklist',
    tags: ['agreement', 'signature', 'legal'],
    url: '/api/files/2'
  },
  {
    id: '3',
    name: 'Network_Diagram_Updated.png',
    type: 'photo',
    size: 890000,
    uploadDate: '2023-11-30T16:45:00Z',
    category: 'maintenance',
    workOrderId: 'WO-2023-002',
    description: 'Updated network topology diagram',
    tags: ['diagram', 'network', 'topology'],
    url: '/api/files/3'
  }
];

export const FilesManagement: React.FC = () => {
  const [files, setFiles] = useState<FileItem[]>(mockFiles);
  const [filteredFiles, setFilteredFiles] = useState<FileItem[]>(mockFiles);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<FileItem[]>([]);

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
        return <DocumentIcon className="w-5 h-5 text-green-600" />;
      default:
        return <DocumentIcon className="w-5 h-5 text-gray-600" />;
    }
  };

  const columns = [
    {
      key: 'name' as keyof FileItem,
      label: 'File Name',
      render: (value: string, item: FileItem) => (
        <div className="flex items-center space-x-3">
          {getFileIcon(item.type)}
          <div>
            <div className="font-medium text-gray-900">{value}</div>
            <div className="text-sm text-gray-500">{formatFileSize(item.size)}</div>
          </div>
        </div>
      )
    },
    {
      key: 'category' as keyof FileItem,
      label: 'Category',
      render: (value: string) => (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize bg-blue-100 text-blue-800">
          {value}
        </span>
      )
    },
    {
      key: 'uploadDate' as keyof FileItem,
      label: 'Upload Date',
      render: (value: string) => new Date(value).toLocaleDateString()
    },
    {
      key: 'workOrderId' as keyof FileItem,
      label: 'Work Order',
      render: (value: string | undefined) => value || '-'
    },
    {
      key: 'tags' as keyof FileItem,
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
      key: 'id' as keyof FileItem,
      label: 'Actions',
      render: (value: string, item: FileItem) => (
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
    
    setFilteredFiles(filtered);
  };

  const handleViewFile = (file: FileItem) => {
    // Open file in modal or new tab
    window.open(file.url, '_blank');
  };

  const handleDownloadFile = (file: FileItem) => {
    // Trigger download
    const link = document.createElement('a');
    link.href = file.url;
    link.download = file.name;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleDeleteFile = (file: FileItem) => {
    if (confirm(`Are you sure you want to delete "${file.name}"?`)) {
      setFiles(prev => prev.filter(f => f.id !== file.id));
      setFilteredFiles(prev => prev.filter(f => f.id !== file.id));
    }
  };

  const handleBulkDelete = () => {
    if (selectedFiles.length === 0) return;
    
    const fileNames = selectedFiles.map(f => f.name).join(', ');
    if (confirm(`Are you sure you want to delete ${selectedFiles.length} files?\n\n${fileNames}`)) {
      const selectedIds = selectedFiles.map(f => f.id);
      setFiles(prev => prev.filter(f => !selectedIds.includes(f.id)));
      setFilteredFiles(prev => prev.filter(f => !selectedIds.includes(f.id)));
      setSelectedFiles([]);
    }
  };

  const actions = [
    {
      label: 'Upload Files',
      onClick: () => setShowUploadModal(true),
      variant: 'primary' as const,
      icon: PlusIcon
    },
    ...(selectedFiles.length > 0 ? [{
      label: `Delete ${selectedFiles.length} Files`,
      onClick: handleBulkDelete,
      variant: 'danger' as const,
      icon: TrashIcon
    }] : [])
  ];

  const filters = [
    {
      key: 'type',
      label: 'File Type',
      options: [
        { value: 'document', label: 'Documents' },
        { value: 'photo', label: 'Photos' },
        { value: 'video', label: 'Videos' },
        { value: 'other', label: 'Other' }
      ]
    },
    {
      key: 'category',
      label: 'Category',
      options: [
        { value: 'installation', label: 'Installation' },
        { value: 'maintenance', label: 'Maintenance' },
        { value: 'repair', label: 'Repair' },
        { value: 'inspection', label: 'Inspection' },
        { value: 'other', label: 'Other' }
      ]
    }
  ];

  return (
    <>
      <ManagementPageTemplate
        title="File Management"
        subtitle={`${files.length} files • ${filteredFiles.reduce((sum, file) => sum + file.size, 0) / 1024 / 1024 | 0} MB total`}
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
  onUpload: (files: FileItem[]) => void;
}> = ({ onClose, onUpload }) => {
  const [uploadData, setUploadData] = useState({
    category: 'installation',
    workOrderId: '',
    customerId: '',
    description: '',
    tags: ''
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
    
    const newFiles: FileItem[] = selectedFiles.map((file, index) => ({
      id: `upload-${Date.now()}-${index}`,
      name: file.name,
      type: file.type.startsWith('image/') ? 'photo' : 'document',
      size: file.size,
      uploadDate: new Date().toISOString(),
      category: uploadData.category as FileItem['category'],
      workOrderId: uploadData.workOrderId || undefined,
      customerId: uploadData.customerId || undefined,
      description: uploadData.description || undefined,
      tags: uploadData.tags.split(',').map(tag => tag.trim()).filter(Boolean),
      url: URL.createObjectURL(file) // Temporary URL for demo
    }));

    onUpload(newFiles);
    onClose();
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
                  />
                </label>
                <p className="text-gray-600 mt-2">or drag and drop files here</p>
                <p className="text-sm text-gray-500 mt-1">
                  PDF, PNG, JPG, ZIP up to 50MB each
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
                        {getFileIcon(file.type)}
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

            {/* Metadata Form */}
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
                  <option value="installation">Installation</option>
                  <option value="maintenance">Maintenance</option>
                  <option value="repair">Repair</option>
                  <option value="inspection">Inspection</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div>
                <label htmlFor="workOrderId" className="block text-sm font-medium text-gray-700 mb-1">
                  Work Order ID
                </label>
                <input
                  id="workOrderId"
                  type="text"
                  value={uploadData.workOrderId}
                  onChange={(e) => setUploadData({...uploadData, workOrderId: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="WO-2023-001"
                />
              </div>

              <div>
                <label htmlFor="customerId" className="block text-sm font-medium text-gray-700 mb-1">
                  Customer ID
                </label>
                <input
                  id="customerId"
                  type="text"
                  value={uploadData.customerId}
                  onChange={(e) => setUploadData({...uploadData, customerId: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="CUST-001"
                />
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
                  placeholder="installation, photos, documentation"
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

// Helper function for file icons (outside component to avoid re-definition)
const getFileIcon = (type: string) => {
  if (type.startsWith('image/')) {
    return <PhotoIcon className="w-4 h-4 text-blue-600" />;
  }
  return <DocumentIcon className="w-4 h-4 text-green-600" />;
};