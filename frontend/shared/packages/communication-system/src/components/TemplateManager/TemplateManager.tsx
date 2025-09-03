'use client';

import React, { useState, useCallback, useMemo } from 'react';
import {
  Plus,
  Search,
  Edit3,
  Trash2,
  Copy,
  Filter,
  MoreVertical,
  Eye,
  Send,
  Clock,
  Tag,
  User,
  Mail,
  MessageSquare,
  Smartphone,
  Bell,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { CommunicationTemplate } from '../../types';
import { useCommunicationSystem } from '../../hooks/useCommunicationSystem';

interface TemplateManagerProps {
  tenantId?: string;
  userId?: string;
  onTemplateSelect?: (template: CommunicationTemplate) => void;
  onTemplateCreate?: (template: CommunicationTemplate) => void;
  onTemplateUpdate?: (template: CommunicationTemplate) => void;
  onTemplateDelete?: (templateId: string) => void;
  className?: string;
  compact?: boolean;
  showActions?: boolean;
  filterByChannel?: string;
  filterByCategory?: string;
}

const channelIcons = {
  email: Mail,
  sms: Smartphone,
  chat: MessageSquare,
  push: Bell,
  websocket: MessageSquare,
  webhook: Send,
  whatsapp: MessageSquare,
};

const priorityColors = {
  low: 'text-gray-500',
  medium: 'text-yellow-500',
  high: 'text-orange-500',
  critical: 'text-red-500',
};

const statusColors = {
  true: 'bg-green-100 text-green-800',
  false: 'bg-gray-100 text-gray-800',
};

export function TemplateManager({
  tenantId,
  userId,
  onTemplateSelect,
  onTemplateCreate,
  onTemplateUpdate,
  onTemplateDelete,
  className = '',
  compact = false,
  showActions = true,
  filterByChannel,
  filterByCategory,
}: TemplateManagerProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState(filterByCategory || 'all');
  const [selectedChannel, setSelectedChannel] = useState(filterByChannel || 'all');
  const [selectedPriority, setSelectedPriority] = useState('all');
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [showFilters, setShowFilters] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<CommunicationTemplate | null>(null);
  const [previewTemplate, setPreviewTemplate] = useState<CommunicationTemplate | null>(null);

  const communication = useCommunicationSystem({
    tenantId,
    userId,
    enableRealtime: true,
  });

  const filteredTemplates = useMemo(() => {
    return communication.templates.filter((template) => {
      const matchesSearch =
        !searchTerm ||
        template.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        template.body.toLowerCase().includes(searchTerm.toLowerCase()) ||
        template.subject?.toLowerCase().includes(searchTerm.toLowerCase());

      const matchesCategory = selectedCategory === 'all' || template.category === selectedCategory;
      const matchesChannel = selectedChannel === 'all' || template.channel === selectedChannel;
      const matchesPriority = selectedPriority === 'all' || template.priority === selectedPriority;
      const matchesStatus =
        selectedStatus === 'all' ||
        (selectedStatus === 'active' && template.isActive) ||
        (selectedStatus === 'inactive' && !template.isActive);

      return matchesSearch && matchesCategory && matchesChannel && matchesPriority && matchesStatus;
    });
  }, [
    communication.templates,
    searchTerm,
    selectedCategory,
    selectedChannel,
    selectedPriority,
    selectedStatus,
  ]);

  const categories = useMemo(() => {
    const cats = new Set(communication.templates.map((t) => t.category));
    return Array.from(cats);
  }, [communication.templates]);

  const channels = useMemo(() => {
    const chans = new Set(communication.templates.map((t) => t.channel));
    return Array.from(chans);
  }, [communication.templates]);

  const handleCreateTemplate = useCallback(
    async (templateData: Omit<CommunicationTemplate, 'id' | 'createdAt' | 'updatedAt'>) => {
      try {
        const template = await communication.createTemplate(templateData);
        onTemplateCreate?.(template);
        setIsCreateModalOpen(false);
      } catch (error) {
        console.error('Failed to create template:', error);
      }
    },
    [communication, onTemplateCreate]
  );

  const handleUpdateTemplate = useCallback(
    async (templateId: string, updates: Partial<CommunicationTemplate>) => {
      try {
        const template = await communication.updateTemplate(templateId, updates);
        onTemplateUpdate?.(template);
        setEditingTemplate(null);
      } catch (error) {
        console.error('Failed to update template:', error);
      }
    },
    [communication, onTemplateUpdate]
  );

  const handleDuplicateTemplate = useCallback(
    async (template: CommunicationTemplate) => {
      const duplicateData = {
        ...template,
        name: `${template.name} (Copy)`,
        isActive: false,
        version: 1,
      };
      delete (duplicateData as any).id;
      delete (duplicateData as any).createdAt;
      delete (duplicateData as any).updatedAt;

      await handleCreateTemplate(duplicateData);
    },
    [handleCreateTemplate]
  );

  const handleDeleteTemplate = useCallback(
    async (templateId: string) => {
      if (confirm('Are you sure you want to delete this template?')) {
        try {
          // TODO: Implement delete API call
          onTemplateDelete?.(templateId);
        } catch (error) {
          console.error('Failed to delete template:', error);
        }
      }
    },
    [onTemplateDelete]
  );

  const TemplateCard = ({ template }: { template: CommunicationTemplate }) => {
    const ChannelIcon =
      channelIcons[template.channel as keyof typeof channelIcons] || MessageSquare;

    return (
      <motion.div
        layout
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        className={`bg-white rounded-lg border border-gray-200 hover:border-gray-300 hover:shadow-md transition-all ${
          compact ? 'p-3' : 'p-4'
        }`}
      >
        <div className='flex items-start justify-between'>
          <div className='flex-1 min-w-0'>
            <div className='flex items-center space-x-2 mb-2'>
              <ChannelIcon className='w-4 h-4 text-gray-500' />
              <h3 className={`font-medium truncate ${compact ? 'text-sm' : 'text-base'}`}>
                {template.name}
              </h3>
              <span
                className={`px-2 py-1 text-xs rounded-full ${statusColors[template.isActive.toString() as keyof typeof statusColors]}`}
              >
                {template.isActive ? 'Active' : 'Inactive'}
              </span>
            </div>

            <div className='flex items-center space-x-4 text-xs text-gray-500 mb-2'>
              <div className='flex items-center space-x-1'>
                <Tag className='w-3 h-3' />
                <span>{template.category}</span>
              </div>
              <div className={`flex items-center space-x-1 ${priorityColors[template.priority]}`}>
                <Clock className='w-3 h-3' />
                <span className='capitalize'>{template.priority}</span>
              </div>
              <div className='flex items-center space-x-1'>
                <User className='w-3 h-3' />
                <span>v{template.version}</span>
              </div>
            </div>

            {template.subject && !compact && (
              <p className='text-sm text-gray-600 mb-1 font-medium'>Subject: {template.subject}</p>
            )}

            <p className={`text-gray-600 line-clamp-2 ${compact ? 'text-xs' : 'text-sm'}`}>
              {template.body.substring(0, compact ? 80 : 120)}
              {template.body.length > (compact ? 80 : 120) && '...'}
            </p>

            {template.variables.length > 0 && (
              <div className='flex flex-wrap gap-1 mt-2'>
                {template.variables.slice(0, compact ? 3 : 5).map((variable, index) => (
                  <span key={index} className='px-2 py-1 text-xs bg-blue-50 text-blue-600 rounded'>
                    {variable}
                  </span>
                ))}
                {template.variables.length > (compact ? 3 : 5) && (
                  <span className='px-2 py-1 text-xs bg-gray-50 text-gray-500 rounded'>
                    +{template.variables.length - (compact ? 3 : 5)} more
                  </span>
                )}
              </div>
            )}
          </div>

          {showActions && (
            <div className='flex items-center space-x-1 ml-2'>
              <button
                onClick={() => setPreviewTemplate(template)}
                className='p-1 hover:bg-gray-100 rounded transition-colors'
                title='Preview'
              >
                <Eye className='w-4 h-4 text-gray-500' />
              </button>
              <button
                onClick={() => onTemplateSelect?.(template)}
                className='p-1 hover:bg-gray-100 rounded transition-colors'
                title='Use Template'
              >
                <Send className='w-4 h-4 text-blue-600' />
              </button>
              <div className='relative group'>
                <button className='p-1 hover:bg-gray-100 rounded transition-colors'>
                  <MoreVertical className='w-4 h-4 text-gray-500' />
                </button>
                <div className='absolute right-0 top-full mt-1 w-32 bg-white rounded-md shadow-lg border border-gray-200 py-1 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10'>
                  <button
                    onClick={() => setEditingTemplate(template)}
                    className='w-full text-left px-3 py-1 text-sm hover:bg-gray-50 flex items-center space-x-2'
                  >
                    <Edit3 className='w-3 h-3' />
                    <span>Edit</span>
                  </button>
                  <button
                    onClick={() => handleDuplicateTemplate(template)}
                    className='w-full text-left px-3 py-1 text-sm hover:bg-gray-50 flex items-center space-x-2'
                  >
                    <Copy className='w-3 h-3' />
                    <span>Duplicate</span>
                  </button>
                  <button
                    onClick={() => handleDeleteTemplate(template.id)}
                    className='w-full text-left px-3 py-1 text-sm hover:bg-gray-50 text-red-600 flex items-center space-x-2'
                  >
                    <Trash2 className='w-3 h-3' />
                    <span>Delete</span>
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </motion.div>
    );
  };

  return (
    <div className={`w-full ${className}`}>
      {/* Header */}
      <div className='flex items-center justify-between mb-6'>
        <div>
          <h2 className={`font-semibold text-gray-900 ${compact ? 'text-lg' : 'text-xl'}`}>
            Communication Templates
          </h2>
          <p className='text-sm text-gray-500 mt-1'>
            {filteredTemplates.length} of {communication.templates.length} templates
          </p>
        </div>

        {showActions && (
          <div className='flex items-center space-x-2'>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`p-2 rounded-lg border transition-colors ${
                showFilters ? 'bg-blue-50 border-blue-200' : 'border-gray-300 hover:border-gray-400'
              }`}
              title='Toggle Filters'
            >
              <Filter className='w-4 h-4' />
            </button>
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className='flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors'
            >
              <Plus className='w-4 h-4' />
              <span>New Template</span>
            </button>
          </div>
        )}
      </div>

      {/* Search and Filters */}
      <div className='space-y-4 mb-6'>
        <div className='relative'>
          <Search className='absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400' />
          <input
            type='text'
            placeholder='Search templates...'
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className='w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
          />
        </div>

        <AnimatePresence>
          {showFilters && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className='grid grid-cols-1 md:grid-cols-4 gap-4 p-4 bg-gray-50 rounded-lg'
            >
              <div>
                <label className='block text-sm font-medium text-gray-700 mb-1'>Category</label>
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className='w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
                >
                  <option value='all'>All Categories</option>
                  {categories.map((category) => (
                    <option key={category} value={category}>
                      {category}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className='block text-sm font-medium text-gray-700 mb-1'>Channel</label>
                <select
                  value={selectedChannel}
                  onChange={(e) => setSelectedChannel(e.target.value)}
                  className='w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
                >
                  <option value='all'>All Channels</option>
                  {channels.map((channel) => (
                    <option key={channel} value={channel} className='capitalize'>
                      {channel}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className='block text-sm font-medium text-gray-700 mb-1'>Priority</label>
                <select
                  value={selectedPriority}
                  onChange={(e) => setSelectedPriority(e.target.value)}
                  className='w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
                >
                  <option value='all'>All Priorities</option>
                  <option value='low'>Low</option>
                  <option value='medium'>Medium</option>
                  <option value='high'>High</option>
                  <option value='critical'>Critical</option>
                </select>
              </div>

              <div>
                <label className='block text-sm font-medium text-gray-700 mb-1'>Status</label>
                <select
                  value={selectedStatus}
                  onChange={(e) => setSelectedStatus(e.target.value)}
                  className='w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
                >
                  <option value='all'>All</option>
                  <option value='active'>Active</option>
                  <option value='inactive'>Inactive</option>
                </select>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Templates Grid */}
      {communication.isLoading ? (
        <div className='flex items-center justify-center py-12'>
          <div className='animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600'></div>
        </div>
      ) : filteredTemplates.length === 0 ? (
        <div className='text-center py-12'>
          <MessageSquare className='w-12 h-12 text-gray-400 mx-auto mb-4' />
          <p className='text-gray-500'>No templates found</p>
          {showActions && (
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className='mt-4 text-blue-600 hover:text-blue-700'
            >
              Create your first template
            </button>
          )}
        </div>
      ) : (
        <div
          className={`grid gap-4 ${
            compact ? 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3' : 'grid-cols-1 lg:grid-cols-2'
          }`}
        >
          <AnimatePresence>
            {filteredTemplates.map((template) => (
              <TemplateCard key={template.id} template={template} />
            ))}
          </AnimatePresence>
        </div>
      )}

      {communication.error && (
        <div className='mt-4 p-4 bg-red-50 border border-red-200 rounded-lg'>
          <p className='text-red-600 text-sm'>{communication.error}</p>
        </div>
      )}
    </div>
  );
}
