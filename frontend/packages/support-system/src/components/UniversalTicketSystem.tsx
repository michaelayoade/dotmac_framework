/**
 * Universal Ticket System
 * DRY component that works across all portals with portal-specific features
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  AlertCircle,
  CheckCircle,
  Clock,
  ChevronRight,
  MessageCircle,
  Paperclip,
  Plus,
  Search,
  Send,
  Star,
  XCircle,
  Filter,
  Download,
  MoreHorizontal,
  User,
  Calendar,
  Tag,
  Users,
  Eye,
  Edit3,
  Archive,
  AlertTriangle
} from 'lucide-react';
import { useSupportTicketing, useSupport } from '../providers/SupportProvider';
import type { SupportTicket, TicketStatus, TicketPriority, TicketCategory, SearchFilters } from '../types';

export interface UniversalTicketSystemProps {
  variant?: 'customer' | 'agent' | 'admin' | 'compact';
  showCreateButton?: boolean;
  showSearch?: boolean;
  showFilters?: boolean;
  showBulkActions?: boolean;
  maxHeight?: string;
  onTicketSelect?: (ticket: SupportTicket) => void;
  initialFilters?: SearchFilters;
  className?: string;
}

interface TicketListItem extends SupportTicket {
  isSelected?: boolean;
}

export function UniversalTicketSystem({
  variant = 'customer',
  showCreateButton = true,
  showSearch = true,
  showFilters = true,
  showBulkActions = false,
  maxHeight = '600px',
  onTicketSelect,
  initialFilters = {},
  className = ''
}: UniversalTicketSystemProps) {
  const { portalConfig, features, preferences, utils } = useSupport();
  const ticketing = useSupportTicketing();

  // Local state
  const [selectedTicket, setSelectedTicket] = useState<SupportTicket | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showFiltersPanel, setShowFiltersPanel] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState<SearchFilters>(initialFilters);
  const [selectedTickets, setSelectedTickets] = useState<Set<string>>(new Set());
  const [tickets, setTickets] = useState<TicketListItem[]>([]);
  const [newTicketData, setNewTicketData] = useState({
    subject: '',
    description: '',
    category: 'general' as TicketCategory,
    priority: 'medium' as TicketPriority
  });
  const [replyMessage, setReplyMessage] = useState('');

  // Fetch tickets on mount and filter changes
  useEffect(() => {
    const fetchTickets = async () => {
      try {
        const response = await ticketing.list({ ...filters, query: searchQuery });
        if (response.success && response.data?.data) {
          setTickets(response.data.data);
        }
      } catch (error) {
        console.error('[UniversalTicketSystem] Failed to fetch tickets:', error);
      }
    };

    fetchTickets();
  }, [filters, searchQuery, ticketing]);

  // Portal-specific configurations
  const canCreateTickets = useMemo(() => {
    return portalConfig.allowedActions.includes('create_ticket');
  }, [portalConfig]);

  const canManageTickets = useMemo(() => {
    return portalConfig.allowedActions.includes('manage_tickets');
  }, [portalConfig]);

  const canViewInternalNotes = useMemo(() => {
    return preferences.tickets.showInternalNotes;
  }, [preferences]);

  // Event handlers
  const handleTicketClick = useCallback((ticket: SupportTicket) => {
    setSelectedTicket(ticket);
    onTicketSelect?.(ticket);
  }, [onTicketSelect]);

  const handleCreateTicket = useCallback(async () => {
    if (!newTicketData.subject.trim() || !newTicketData.description.trim()) {
      return;
    }

    try {
      const ticketNumber = utils.generateTicketNumber();
      const response = await ticketing.create({
        ticketNumber,
        subject: newTicketData.subject,
        description: newTicketData.description,
        category: newTicketData.category,
        priority: newTicketData.priority,
        status: 'open' as TicketStatus,
        source: 'web',
        customerId: portalConfig.type === 'customer' ? 'current-user' : '',
        customerEmail: 'current-user@example.com', // This would come from auth context
        customerName: 'Current User', // This would come from auth context
        tags: [],
        escalationLevel: 0,
        relatedTickets: [],
        attachments: [],
        watchers: [],
        slaBreached: false,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        id: '',
        metadata: {}
      });

      if (response.success) {
        setShowCreateModal(false);
        setNewTicketData({
          subject: '',
          description: '',
          category: 'general',
          priority: 'medium'
        });
        // Refresh ticket list
        const ticketsResponse = await ticketing.list(filters);
        if (ticketsResponse.success && ticketsResponse.data?.data) {
          setTickets(ticketsResponse.data.data);
        }
      }
    } catch (error) {
      console.error('[UniversalTicketSystem] Failed to create ticket:', error);
    }
  }, [newTicketData, ticketing, utils, portalConfig, filters]);

  const handleReplyToTicket = useCallback(async () => {
    if (!selectedTicket || !replyMessage.trim()) return;

    try {
      await ticketing.addMessage(selectedTicket.id, replyMessage);
      setReplyMessage('');
      // Refresh the selected ticket to show new message
      const response = await ticketing.get(selectedTicket.id);
      if (response.success && response.data) {
        setSelectedTicket(response.data);
      }
    } catch (error) {
      console.error('[UniversalTicketSystem] Failed to reply to ticket:', error);
    }
  }, [selectedTicket, replyMessage, ticketing]);

  const handleBulkAction = useCallback(async (action: string) => {
    if (selectedTickets.size === 0) return;

    const ticketIds = Array.from(selectedTickets);

    try {
      switch (action) {
        case 'close':
          for (const ticketId of ticketIds) {
            await ticketing.close(ticketId, 'Bulk closure');
          }
          break;
        case 'assign':
          // This would show an assignment modal
          console.log('Bulk assign not implemented');
          break;
        case 'export':
          // This would trigger export
          console.log('Bulk export not implemented');
          break;
      }

      setSelectedTickets(new Set());
      // Refresh tickets
      const response = await ticketing.list(filters);
      if (response.success && response.data?.data) {
        setTickets(response.data.data);
      }
    } catch (error) {
      console.error('[UniversalTicketSystem] Bulk action failed:', error);
    }
  }, [selectedTickets, ticketing, filters]);

  // Utility functions
  const getStatusIcon = (status: TicketStatus) => {
    const iconProps = { className: "h-4 w-4" };
    switch (status) {
      case 'open':
      case 'in_progress':
        return <AlertCircle {...iconProps} className="h-4 w-4 text-blue-600" />;
      case 'pending':
      case 'waiting_customer':
        return <Clock {...iconProps} className="h-4 w-4 text-yellow-600" />;
      case 'resolved':
        return <CheckCircle {...iconProps} className="h-4 w-4 text-green-600" />;
      case 'closed':
        return <XCircle {...iconProps} className="h-4 w-4 text-gray-600" />;
      default:
        return <AlertCircle {...iconProps} className="h-4 w-4 text-gray-600" />;
    }
  };

  const getStatusColor = (status: TicketStatus) => {
    switch (status) {
      case 'open':
      case 'in_progress':
        return 'text-blue-600 bg-blue-50 border-blue-200';
      case 'pending':
      case 'waiting_customer':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'resolved':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'closed':
        return 'text-gray-600 bg-gray-50 border-gray-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getPriorityColor = (priority: TicketPriority) => {
    switch (priority) {
      case 'critical':
        return 'text-red-800 bg-red-100';
      case 'high':
        return 'text-red-600 bg-red-50';
      case 'medium':
        return 'text-yellow-600 bg-yellow-50';
      case 'low':
        return 'text-green-600 bg-green-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  const formatDate = useCallback((dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  }, []);

  // Render ticket detail view
  if (selectedTicket) {
    return (
      <div className={`space-y-6 ${className}`}>
        {/* Header */}
        <div className="flex items-center justify-between">
          <button
            onClick={() => setSelectedTicket(null)}
            className="text-blue-600 hover:text-blue-800 font-medium text-sm flex items-center"
          >
            ← Back to Tickets
          </button>
          <div className="flex items-center space-x-2">
            {getStatusIcon(selectedTicket.status)}
            <span className={`px-2 py-1 text-xs font-medium rounded-full border ${getStatusColor(selectedTicket.status)}`}>
              {selectedTicket.status.toUpperCase()}
            </span>
          </div>
        </div>

        {/* Ticket Details */}
        <div className="bg-white rounded-lg border p-6">
          <div className="border-b pb-4 mb-4">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h1 className="text-xl font-semibold text-gray-900">{selectedTicket.subject}</h1>
                <p className="text-sm text-gray-600">Ticket #{selectedTicket.ticketNumber}</p>
              </div>
              <span className={`px-2 py-1 text-xs font-medium rounded ${getPriorityColor(selectedTicket.priority)}`}>
                {selectedTicket.priority.toUpperCase()} PRIORITY
              </span>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-gray-600">Created:</span>
                <p className="font-medium">{formatDate(selectedTicket.createdAt)}</p>
              </div>
              <div>
                <span className="text-gray-600">Updated:</span>
                <p className="font-medium">{formatDate(selectedTicket.updatedAt)}</p>
              </div>
              <div>
                <span className="text-gray-600">Category:</span>
                <p className="font-medium capitalize">{selectedTicket.category}</p>
              </div>
              <div>
                <span className="text-gray-600">Assigned:</span>
                <p className="font-medium">{selectedTicket.assignedTo || 'Unassigned'}</p>
              </div>
            </div>
          </div>

          <div className="mb-6">
            <h3 className="font-medium text-gray-900 mb-2">Description</h3>
            <p className="text-gray-700 whitespace-pre-wrap">{selectedTicket.description}</p>
          </div>

          {/* Messages would go here in a real implementation */}

          {/* Reply Form */}
          {selectedTicket.status !== 'closed' && (
            <div className="border-t pt-4">
              <h4 className="font-medium text-gray-900 mb-3">Reply</h4>
              <div className="space-y-3">
                <textarea
                  value={replyMessage}
                  onChange={(e) => setReplyMessage(e.target.value)}
                  placeholder="Type your reply..."
                  rows={4}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <div className="flex items-center justify-between">
                  <button
                    type="button"
                    className="flex items-center text-gray-600 text-sm hover:text-gray-800"
                  >
                    <Paperclip className="mr-1 h-4 w-4" />
                    Attach File
                  </button>
                  <button
                    onClick={handleReplyToTicket}
                    disabled={!replyMessage.trim() || ticketing.isLoading('addMessage')}
                    className="flex items-center rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700 disabled:bg-gray-300"
                  >
                    <Send className="mr-2 h-4 w-4" />
                    {ticketing.isLoading('addMessage') ? 'Sending...' : 'Send Reply'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Render ticket list view
  return (
    <div className={`space-y-6 ${className}`} style={{ maxHeight }}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Support Tickets</h2>
        <div className="flex items-center space-x-3">
          {showBulkActions && selectedTickets.size > 0 && (
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-600">
                {selectedTickets.size} selected
              </span>
              <button
                onClick={() => handleBulkAction('close')}
                className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded"
              >
                Close
              </button>
              <button
                onClick={() => handleBulkAction('assign')}
                className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded"
              >
                Assign
              </button>
            </div>
          )}

          {showFilters && (
            <button
              onClick={() => setShowFiltersPanel(!showFiltersPanel)}
              className="flex items-center px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              <Filter className="mr-2 h-4 w-4" />
              Filters
            </button>
          )}

          {canCreateTickets && showCreateButton && (
            <button
              onClick={() => setShowCreateModal(true)}
              className="flex items-center bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
            >
              <Plus className="mr-2 h-4 w-4" />
              New Ticket
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar */}
        <div className="space-y-4">
          {/* Search */}
          {showSearch && (
            <div className="bg-white rounded-lg border p-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search tickets..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          )}

          {/* Quick Stats */}
          <div className="bg-white rounded-lg border p-4">
            <h3 className="font-medium text-gray-900 text-sm mb-3">Quick Stats</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span>Open</span>
                <span className="font-medium">{tickets.filter(t => t.status === 'open').length}</span>
              </div>
              <div className="flex justify-between">
                <span>Pending</span>
                <span className="font-medium">{tickets.filter(t => t.status === 'pending').length}</span>
              </div>
              <div className="flex justify-between">
                <span>Resolved</span>
                <span className="font-medium">{tickets.filter(t => t.status === 'resolved').length}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Ticket List */}
        <div className="lg:col-span-3">
          <div className="bg-white rounded-lg border divide-y divide-gray-200">
            {ticketing.isLoading() ? (
              <div className="p-8 text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4" />
                <p className="text-gray-600">Loading tickets...</p>
              </div>
            ) : tickets.length === 0 ? (
              <div className="p-8 text-center">
                <MessageCircle className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">No tickets found</h3>
                <p className="text-gray-600">
                  {searchQuery ? 'No tickets match your search.' : "You haven't created any tickets yet."}
                </p>
              </div>
            ) : (
              tickets.map((ticket) => (
                <div
                  key={ticket.id}
                  onClick={() => handleTicketClick(ticket)}
                  className="p-6 hover:bg-gray-50 cursor-pointer transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-2">
                        {showBulkActions && (
                          <input
                            type="checkbox"
                            checked={selectedTickets.has(ticket.id)}
                            onChange={(e) => {
                              e.stopPropagation();
                              const newSelected = new Set(selectedTickets);
                              if (e.target.checked) {
                                newSelected.add(ticket.id);
                              } else {
                                newSelected.delete(ticket.id);
                              }
                              setSelectedTickets(newSelected);
                            }}
                            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                          />
                        )}
                        {getStatusIcon(ticket.status)}
                        <span className={`px-2 py-1 text-xs font-medium rounded-full border ${getStatusColor(ticket.status)}`}>
                          {ticket.status.toUpperCase()}
                        </span>
                        <span className={`px-2 py-1 text-xs font-medium rounded ${getPriorityColor(ticket.priority)}`}>
                          {ticket.priority.toUpperCase()}
                        </span>
                      </div>

                      <h3 className="text-lg font-medium text-gray-900 mb-1">{ticket.subject}</h3>
                      <p className="text-gray-600 text-sm line-clamp-2 mb-2">{ticket.description}</p>

                      <div className="flex items-center space-x-4 text-gray-500 text-xs">
                        <span>#{ticket.ticketNumber}</span>
                        <span>Created {formatDate(ticket.createdAt)}</span>
                        <span>Updated {formatDate(ticket.updatedAt)}</span>
                        {canManageTickets && ticket.assignedTo && (
                          <span>Assigned to {ticket.assignedTo}</span>
                        )}
                      </div>
                    </div>

                    <ChevronRight className="ml-4 h-5 w-5 text-gray-400 flex-shrink-0" />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Create Ticket Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="border-b p-6">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-gray-900">Create Support Ticket</h2>
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <XCircle className="h-6 w-6" />
                </button>
              </div>
            </div>

            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                  <select
                    value={newTicketData.category}
                    onChange={(e) => setNewTicketData(prev => ({ ...prev, category: e.target.value as TicketCategory }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="technical">Technical Support</option>
                    <option value="billing">Billing</option>
                    <option value="sales">Sales</option>
                    <option value="general">General</option>
                    <option value="account">Account</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
                  <select
                    value={newTicketData.priority}
                    onChange={(e) => setNewTicketData(prev => ({ ...prev, priority: e.target.value as TicketPriority }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    {canManageTickets && <option value="urgent">Urgent</option>}
                    {canManageTickets && <option value="critical">Critical</option>}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Subject</label>
                <input
                  type="text"
                  value={newTicketData.subject}
                  onChange={(e) => setNewTicketData(prev => ({ ...prev, subject: e.target.value }))}
                  placeholder="Brief description of your issue"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  value={newTicketData.description}
                  onChange={(e) => setNewTicketData(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Please provide detailed information about your issue..."
                  rows={6}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div className="flex justify-end space-x-3 border-t bg-gray-50 p-6">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateTicket}
                disabled={!newTicketData.subject.trim() || !newTicketData.description.trim() || ticketing.isLoading('create')}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300"
              >
                {ticketing.isLoading('create') ? 'Creating...' : 'Create Ticket'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
