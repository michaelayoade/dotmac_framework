'use client';

import React, { useState, useMemo } from 'react';
import {
  Search,
  Filter,
  SortAsc,
  SortDesc,
  Grid,
  List,
  Calendar,
  Download,
  Eye,
  MoreHorizontal,
  FolderOpen,
  Tag,
  X,
  Plus,
  Archive,
  Trash2
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { Document, DocumentFilters, DocumentSortOptions, DocumentCategory } from '../../types';
import { FilePreview } from '../FilePreview/FilePreview';
import { formatFileSize } from '../../utils/fileUtils';

interface DocumentManagerProps {
  documents: Document[];
  categories?: DocumentCategory[];
  onDocumentClick?: (document: Document) => void;
  onDocumentDownload?: (document: Document) => void;
  onDocumentDelete?: (documentId: string) => void;
  onUpload?: () => void;
  loading?: boolean;
  error?: string;
  className?: string;
}

export function DocumentManager({
  documents,
  categories = [],
  onDocumentClick,
  onDocumentDownload,
  onDocumentDelete,
  onUpload,
  loading = false,
  error,
  className = ''
}: DocumentManagerProps) {
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('list');
  const [filters, setFilters] = useState<DocumentFilters>({});
  const [sortOptions, setSortOptions] = useState<DocumentSortOptions>({
    field: 'date',
    direction: 'desc'
  });
  const [selectedDocuments, setSelectedDocuments] = useState<string[]>([]);
  const [showFilters, setShowFilters] = useState(false);

  // Filter and sort documents
  const processedDocuments = useMemo(() => {
    let filtered = [...documents];

    // Apply category filter
    if (filters.category && filters.category !== 'all') {
      filtered = filtered.filter(doc => doc.category === filters.category);
    }

    // Apply type filter
    if (filters.type && filters.type.length > 0) {
      filtered = filtered.filter(doc =>
        filters.type!.some(type => doc.type.includes(type))
      );
    }

    // Apply search filter
    if (filters.search) {
      const searchTerm = filters.search.toLowerCase();
      filtered = filtered.filter(doc =>
        doc.name.toLowerCase().includes(searchTerm) ||
        (doc.description && doc.description.toLowerCase().includes(searchTerm)) ||
        (doc.tags && doc.tags.some(tag => tag.toLowerCase().includes(searchTerm)))
      );
    }

    // Apply date range filter
    if (filters.dateRange) {
      filtered = filtered.filter(doc => {
        const docDate = new Date(doc.createdAt);
        const start = filters.dateRange!.start;
        const end = filters.dateRange!.end;

        if (start && docDate < start) return false;
        if (end && docDate > end) return false;
        return true;
      });
    }

    // Apply tags filter
    if (filters.tags && filters.tags.length > 0) {
      filtered = filtered.filter(doc =>
        doc.tags && filters.tags!.some(tag => doc.tags!.includes(tag))
      );
    }

    // Sort documents
    filtered.sort((a, b) => {
      let comparison = 0;

      switch (sortOptions.field) {
        case 'name':
          comparison = a.name.localeCompare(b.name);
          break;
        case 'date':
          comparison = new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
          break;
        case 'size':
          comparison = a.size - b.size;
          break;
        case 'type':
          comparison = a.type.localeCompare(b.type);
          break;
      }

      return sortOptions.direction === 'asc' ? comparison : -comparison;
    });

    return filtered;
  }, [documents, filters, sortOptions]);

  const handleDocumentSelect = (documentId: string) => {
    setSelectedDocuments(prev =>
      prev.includes(documentId)
        ? prev.filter(id => id !== documentId)
        : [...prev, documentId]
    );
  };

  const handleSelectAll = () => {
    if (selectedDocuments.length === processedDocuments.length) {
      setSelectedDocuments([]);
    } else {
      setSelectedDocuments(processedDocuments.map(doc => doc.id));
    }
  };

  const handleBulkAction = (action: 'download' | 'delete' | 'archive') => {
    selectedDocuments.forEach(docId => {
      const document = documents.find(d => d.id === docId);
      if (!document) return;

      switch (action) {
        case 'download':
          onDocumentDownload?.(document);
          break;
        case 'delete':
          onDocumentDelete?.(docId);
          break;
        case 'archive':
          // Handle archive action
          break;
      }
    });
    setSelectedDocuments([]);
  };

  const clearFilters = () => {
    setFilters({});
  };

  const formatDate = (date: Date) => {
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    }).format(date);
  };

  if (loading) {
    return (
      <div className={`${className} flex items-center justify-center py-12`}>
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className={`${className} text-center py-12`}>
        <div className="text-red-600 mb-2">Error loading documents</div>
        <p className="text-gray-500 text-sm">{error}</p>
      </div>
    );
  }

  return (
    <div className={className}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900">Documents</h2>
          <p className="text-sm text-gray-600 mt-1">
            {processedDocuments.length} of {documents.length} documents
          </p>
        </div>

        <div className="flex items-center space-x-2">
          {onUpload && (
            <button
              onClick={onUpload}
              className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Plus className="w-4 h-4 mr-2" />
              Upload
            </button>
          )}
        </div>
      </div>

      {/* Search and Filters */}
      <div className="space-y-4 mb-6">
        <div className="flex items-center space-x-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <input
              type="text"
              placeholder="Search documents..."
              value={filters.search || ''}
              onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Filter Toggle */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`
              px-3 py-2 border border-gray-300 rounded-lg flex items-center space-x-2 transition-colors
              ${showFilters ? 'bg-blue-50 border-blue-300 text-blue-700' : 'hover:bg-gray-50'}
            `}
          >
            <Filter className="w-4 h-4" />
            <span className="text-sm">Filters</span>
          </button>

          {/* View Mode */}
          <div className="flex border border-gray-300 rounded-lg overflow-hidden">
            <button
              onClick={() => setViewMode('list')}
              className={`
                p-2 ${viewMode === 'list' ? 'bg-gray-100 text-gray-900' : 'text-gray-500 hover:text-gray-700'}
              `}
            >
              <List className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('grid')}
              className={`
                p-2 border-l border-gray-300 ${viewMode === 'grid' ? 'bg-gray-100 text-gray-900' : 'text-gray-500 hover:text-gray-700'}
              `}
            >
              <Grid className="w-4 h-4" />
            </button>
          </div>

          {/* Sort */}
          <div className="flex items-center space-x-1">
            <select
              value={sortOptions.field}
              onChange={(e) => setSortOptions(prev => ({
                ...prev,
                field: e.target.value as DocumentSortOptions['field']
              }))}
              className="text-sm border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="date">Date</option>
              <option value="name">Name</option>
              <option value="size">Size</option>
              <option value="type">Type</option>
            </select>

            <button
              onClick={() => setSortOptions(prev => ({
                ...prev,
                direction: prev.direction === 'asc' ? 'desc' : 'asc'
              }))}
              className="p-1 text-gray-500 hover:text-gray-700 rounded"
            >
              {sortOptions.direction === 'asc' ? (
                <SortAsc className="w-4 h-4" />
              ) : (
                <SortDesc className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>

        {/* Advanced Filters */}
        <AnimatePresence>
          {showFilters && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="bg-gray-50 border border-gray-200 rounded-lg p-4 space-y-4"
            >
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Category Filter */}
                {categories.length > 0 && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Category
                    </label>
                    <select
                      value={filters.category || 'all'}
                      onChange={(e) => setFilters(prev => ({
                        ...prev,
                        category: e.target.value === 'all' ? undefined : e.target.value
                      }))}
                      className="w-full text-sm border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="all">All Categories</option>
                      {categories.map(category => (
                        <option key={category.id} value={category.id}>
                          {category.name}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                {/* Date Range Filter */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Date Range
                  </label>
                  <div className="flex space-x-2">
                    <input
                      type="date"
                      value={filters.dateRange?.start?.toISOString().split('T')[0] || ''}
                      onChange={(e) => setFilters(prev => ({
                        ...prev,
                        dateRange: {
                          ...prev.dateRange,
                          start: e.target.value ? new Date(e.target.value) : undefined
                        }
                      }))}
                      className="flex-1 text-sm border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <input
                      type="date"
                      value={filters.dateRange?.end?.toISOString().split('T')[0] || ''}
                      onChange={(e) => setFilters(prev => ({
                        ...prev,
                        dateRange: {
                          ...prev.dateRange,
                          end: e.target.value ? new Date(e.target.value) : undefined
                        }
                      }))}
                      className="flex-1 text-sm border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-end">
                  <button
                    onClick={clearFilters}
                    className="text-sm text-blue-600 hover:text-blue-800 flex items-center"
                  >
                    <X className="w-4 h-4 mr-1" />
                    Clear Filters
                  </button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Bulk Actions */}
      {selectedDocuments.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <span className="text-sm text-blue-800">
              {selectedDocuments.length} document(s) selected
            </span>

            <div className="flex items-center space-x-2">
              <button
                onClick={() => handleBulkAction('download')}
                className="text-sm text-blue-600 hover:text-blue-800 flex items-center"
              >
                <Download className="w-4 h-4 mr-1" />
                Download
              </button>

              <button
                onClick={() => handleBulkAction('archive')}
                className="text-sm text-blue-600 hover:text-blue-800 flex items-center"
              >
                <Archive className="w-4 h-4 mr-1" />
                Archive
              </button>

              <button
                onClick={() => handleBulkAction('delete')}
                className="text-sm text-red-600 hover:text-red-800 flex items-center"
              >
                <Trash2 className="w-4 h-4 mr-1" />
                Delete
              </button>
            </div>
          </div>

          <button
            onClick={() => setSelectedDocuments([])}
            className="text-blue-600 hover:text-blue-800"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Document List/Grid */}
      {processedDocuments.length === 0 ? (
        <div className="text-center py-12">
          <FolderOpen className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No documents found</h3>
          <p className="text-gray-500">
            {documents.length === 0
              ? "You haven't uploaded any documents yet."
              : "No documents match your current filters."
            }
          </p>
        </div>
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {processedDocuments.map((document) => (
            <div key={document.id} className="relative">
              {/* Selection Checkbox */}
              <div className="absolute top-2 left-2 z-10">
                <input
                  type="checkbox"
                  checked={selectedDocuments.includes(document.id)}
                  onChange={() => handleDocumentSelect(document.id)}
                  className="w-4 h-4 text-blue-600 bg-white border-gray-300 rounded focus:ring-blue-500"
                />
              </div>

              <FilePreview
                file={document}
                variant="grid"
                showActions={true}
                showMetadata={true}
                onClick={() => onDocumentClick?.(document)}
                onDownload={() => onDocumentDownload?.(document)}
                onRemove={() => onDocumentDelete?.(document.id)}
              />
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          {/* Table Header */}
          <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
            <div className="flex items-center">
              <input
                type="checkbox"
                checked={selectedDocuments.length === processedDocuments.length && processedDocuments.length > 0}
                onChange={handleSelectAll}
                className="w-4 h-4 text-blue-600 bg-white border-gray-300 rounded focus:ring-blue-500 mr-4"
              />
              <div className="flex-1 grid grid-cols-12 gap-4 text-xs font-medium text-gray-500 uppercase tracking-wide">
                <div className="col-span-5">Name</div>
                <div className="col-span-2">Category</div>
                <div className="col-span-1">Size</div>
                <div className="col-span-2">Modified</div>
                <div className="col-span-2">Actions</div>
              </div>
            </div>
          </div>

          {/* Document Rows */}
          <div className="divide-y divide-gray-200">
            {processedDocuments.map((document) => (
              <div
                key={document.id}
                className="px-4 py-3 hover:bg-gray-50 transition-colors cursor-pointer"
                onClick={() => onDocumentClick?.(document)}
              >
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    checked={selectedDocuments.includes(document.id)}
                    onChange={(e) => {
                      e.stopPropagation();
                      handleDocumentSelect(document.id);
                    }}
                    className="w-4 h-4 text-blue-600 bg-white border-gray-300 rounded focus:ring-blue-500 mr-4"
                  />

                  <div className="flex-1 grid grid-cols-12 gap-4 items-center">
                    {/* Name */}
                    <div className="col-span-5 flex items-center space-x-3">
                      <FilePreview
                        file={document}
                        variant="list"
                        showActions={false}
                        showMetadata={false}
                        size="sm"
                      />
                    </div>

                    {/* Category */}
                    <div className="col-span-2">
                      {document.category && (
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                          {document.category}
                        </span>
                      )}
                    </div>

                    {/* Size */}
                    <div className="col-span-1 text-sm text-gray-500">
                      {formatFileSize(document.size)}
                    </div>

                    {/* Modified Date */}
                    <div className="col-span-2 text-sm text-gray-500">
                      {formatDate(document.updatedAt)}
                    </div>

                    {/* Actions */}
                    <div className="col-span-2 flex items-center space-x-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onDocumentClick?.(document);
                        }}
                        className="p-1 text-gray-400 hover:text-blue-600 rounded transition-colors"
                        title="Preview"
                      >
                        <Eye className="w-4 h-4" />
                      </button>

                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onDocumentDownload?.(document);
                        }}
                        className="p-1 text-gray-400 hover:text-green-600 rounded transition-colors"
                        title="Download"
                      >
                        <Download className="w-4 h-4" />
                      </button>

                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          // Handle more actions
                        }}
                        className="p-1 text-gray-400 hover:text-gray-600 rounded transition-colors"
                        title="More actions"
                      >
                        <MoreHorizontal className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
