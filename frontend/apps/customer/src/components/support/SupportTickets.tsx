'use client';

import { useCachedData } from '@dotmac/headless';
import { Card } from '@dotmac/ui/customer';
import {
  AlertCircle,
  CheckCircle,
  ChevronRight,
  Clock,
  MessageCircle,
  Paperclip,
  Plus,
  Search,
  Send,
  Star,
  XCircle,
} from 'lucide-react';
import { useState } from 'react';

// Mock support ticket data
const mockTicketData = {
  tickets: [
    {
      id: 'TKT-2024-001',
      subject: 'Internet connection keeps dropping',
      status: 'open',
      priority: 'high',
      category: 'technical',
      createdDate: '2024-01-28T10:30:00Z',
      lastUpdated: '2024-01-29T14:20:00Z',
      assignedTo: 'Technical Support Team',
      description:
        'My internet connection has been dropping every few hours for the past 3 days. Speed test shows normal speeds when connected.',
      messages: [
        {
          id: 'MSG-001',
          sender: 'customer',
          senderName: 'You',
          message:
            'My internet connection has been dropping every few hours for the past 3 days. Speed test shows normal speeds when connected.',
          timestamp: '2024-01-28T10:30:00Z',
          attachments: [],
        },
        {
          id: 'MSG-002',
          sender: 'support',
          senderName: 'Tech Support - Sarah',
          message:
            'Thank you for contacting us. I can see some signal fluctuations on your line. Let me schedule a technician to check your equipment. Are you available tomorrow between 2-4 PM?',
          timestamp: '2024-01-29T14:20:00Z',
          attachments: [],
        },
      ],
    },
    {
      id: 'TKT-2024-002',
      subject: 'Billing question about recent charge',
      status: 'resolved',
      priority: 'medium',
      category: 'billing',
      createdDate: '2024-01-25T09:15:00Z',
      lastUpdated: '2024-01-26T16:45:00Z',
      assignedTo: 'Billing Department',
      description: 'I see an unexpected charge on my account and need clarification.',
      resolution: 'Charge was for one-time equipment upgrade. Billing adjusted and credit applied.',
      rating: 5,
      messages: [
        {
          id: 'MSG-003',
          sender: 'customer',
          senderName: 'You',
          message: 'I see an unexpected charge on my account and need clarification.',
          timestamp: '2024-01-25T09:15:00Z',
          attachments: [],
        },
        {
          id: 'MSG-004',
          sender: 'support',
          senderName: 'Billing - Mike',
          message:
            "I can see this charge was for the WiFi 6 router upgrade you requested. However, I notice we forgot to send the confirmation email. I've applied a $10 credit to your account for the inconvenience.",
          timestamp: '2024-01-26T16:45:00Z',
          attachments: [],
        },
      ],
    },
    {
      id: 'TKT-2024-003',
      subject: 'Request for service upgrade information',
      status: 'pending',
      priority: 'low',
      category: 'sales',
      createdDate: '2024-01-27T11:00:00Z',
      lastUpdated: '2024-01-27T11:00:00Z',
      assignedTo: 'Sales Team',
      description:
        'Interested in upgrading to the Fiber 500 plan. What would be the cost difference?',
      messages: [
        {
          id: 'MSG-005',
          sender: 'customer',
          senderName: 'You',
          message:
            'Interested in upgrading to the Fiber 500 plan. What would be the cost difference?',
          timestamp: '2024-01-27T11:00:00Z',
          attachments: [],
        },
      ],
    },
  ],
  categories: [
    { id: 'all', name: 'All Tickets', count: 3 },
    { id: 'technical', name: 'Technical Support', count: 1 },
    { id: 'billing', name: 'Billing', count: 1 },
    { id: 'sales', name: 'Sales', count: 1 },
  ],
};

export function SupportTickets() {
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedTicket, setSelectedTicket] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [showCreateTicket, setShowCreateTicket] = useState(false);
  const [newTicketMessage, setNewTicketMessage] = useState('');

  const { data: ticketData, isLoading } = useCachedData(
    'customer-support-tickets',
    async () => mockTicketData,
    { ttl: 2 * 60 * 1000 }
  );

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'open':
        return <AlertCircle className="h-4 w-4 text-yellow-600" />;
      case 'pending':
        return <Clock className="h-4 w-4 text-blue-600" />;
      case 'resolved':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'closed':
        return <XCircle className="h-4 w-4 text-gray-600" />;
      default:
        return <AlertCircle className="h-4 w-4 text-gray-600" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'open':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'pending':
        return 'text-blue-600 bg-blue-50 border-blue-200';
      case 'resolved':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'closed':
        return 'text-gray-600 bg-gray-50 border-gray-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
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

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));

    if (diffHours < 24) {
      return date.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      });
    }

    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const filteredTickets =
    ticketData?.tickets.filter(ticket => {
      const matchesCategory = selectedCategory === 'all' || ticket.category === selectedCategory;
      const matchesSearch =
        ticket.subject.toLowerCase().includes(searchQuery.toLowerCase()) ||
        ticket.description.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesCategory && matchesSearch;
    }) || [];

  const selectedTicketData = selectedTicket
    ? ticketData?.tickets.find(t => t.id === selectedTicket)
    : null;

  if (isLoading || !ticketData) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-blue-600 border-b-2" />
      </div>
    );
  }

  if (selectedTicketData) {
    return (
      <div className="space-y-6">
        {/* Ticket Header */}
        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={() => setSelectedTicket(null)}
            className="font-medium text-blue-600 text-sm hover:text-blue-800"
          >
            ← Back to Tickets
          </button>
          <div className="flex items-center space-x-2">
            {getStatusIcon(selectedTicketData.status)}
            <span
              className={`rounded-full border px-2 py-1 font-medium text-xs ${getStatusColor(selectedTicketData.status)}`}
            >
              {selectedTicketData.status.toUpperCase()}
            </span>
          </div>
        </div>

        <Card className="p-6">
          <div className="mb-4 border-b pb-4">
            <div className="flex items-start justify-between">
              <div>
                <h1 className="font-semibold text-gray-900 text-xl">
                  {selectedTicketData.subject}
                </h1>
                <p className="mt-1 text-gray-600 text-sm">Ticket #{selectedTicketData.id}</p>
              </div>
              <span
                className={`rounded px-2 py-1 font-medium text-xs ${getPriorityColor(selectedTicketData.priority)}`}
              >
                {selectedTicketData.priority.toUpperCase()} PRIORITY
              </span>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
              <div>
                <span className="text-gray-600">Created:</span>
                <p className="font-medium">{formatDate(selectedTicketData.createdDate)}</p>
              </div>
              <div>
                <span className="text-gray-600">Last Updated:</span>
                <p className="font-medium">{formatDate(selectedTicketData.lastUpdated)}</p>
              </div>
              <div>
                <span className="text-gray-600">Assigned To:</span>
                <p className="font-medium">{selectedTicketData.assignedTo}</p>
              </div>
              <div>
                <span className="text-gray-600">Category:</span>
                <p className="font-medium capitalize">{selectedTicketData.category}</p>
              </div>
            </div>
          </div>

          {/* Messages */}
          <div className="mb-6 space-y-4">
            {selectedTicketData.messages.map((message, index) => (
              <div
                key={`${selectedTicketData.id}-message-${index}`}
                className={`flex ${message.sender === 'customer' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-lg ${
                    message.sender === 'customer'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-900'
                  } rounded-lg p-4`}
                >
                  <div className="mb-2 flex items-center justify-between">
                    <span className="font-medium text-sm">{message.senderName}</span>
                    <span
                      className={`text-xs ${
                        message.sender === 'customer' ? 'text-blue-100' : 'text-gray-500'
                      }`}
                    >
                      {formatTimestamp(message.timestamp)}
                    </span>
                  </div>
                  <p className="whitespace-pre-wrap text-sm">{message.message}</p>
                  {message.attachments.length > 0 && (
                    <div className="mt-2">
                      {message.attachments.map((attachment, index) => (
                        <div
                          key={`${message.id}-attachment-${index}`}
                          className="flex items-center text-xs"
                        >
                          <Paperclip className="mr-1 h-3 w-3" />
                          <span>{attachment}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Resolution (if resolved) */}
          {selectedTicketData.status === 'resolved' && selectedTicketData.resolution ? (
            <div className="mb-6 rounded-lg border border-green-200 bg-green-50 p-4">
              <h4 className="mb-2 font-medium text-green-900">Resolution</h4>
              <p className="text-green-800 text-sm">{selectedTicketData.resolution}</p>
              {selectedTicketData.rating ? (
                <div className="mt-2 flex items-center">
                  <span className="mr-2 text-green-800 text-sm">Your Rating:</span>
                  <div className="flex">
                    {[...Array(5)].map((_, i) => (
                      <Star
                        key={`${selectedTicketData.id}-rating-star-${i}`}
                        className={`h-4 w-4 ${
                          i < selectedTicketData.rating
                            ? 'fill-current text-yellow-400'
                            : 'text-gray-300'
                        }`}
                      />
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          ) : null}

          {/* Reply Form (if not resolved) */}
          {selectedTicketData.status !== 'resolved' && selectedTicketData.status !== 'closed' && (
            <div className="border-t pt-4">
              <h4 className="mb-3 font-medium text-gray-900">Reply to Ticket</h4>
              <div className="space-y-3">
                <textarea
                  value={newTicketMessage}
                  onChange={e => setNewTicketMessage(e.target.value)}
                  placeholder="Type your message..."
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
                    type="button"
                    className="flex items-center rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700"
                  >
                    <Send className="mr-2 h-4 w-4" />
                    Send Reply
                  </button>
                </div>
              </div>
            </div>
          )}
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="font-bold text-2xl text-gray-900">Support Tickets</h1>
        <button
          type="button"
          onClick={() => setShowCreateTicket(true)}
          className="flex items-center rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700"
        >
          <Plus className="mr-2 h-4 w-4" />
          New Ticket
        </button>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
        {/* Sidebar */}
        <div className="space-y-4">
          {/* Search */}
          <Card className="p-4">
            <div className="relative">
              <Search className="-translate-y-1/2 absolute top-1/2 left-3 h-4 w-4 transform text-gray-400" />
              <input
                type="text"
                placeholder="Search tickets..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full rounded-lg border border-gray-300 py-2 pr-4 pl-10 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </Card>

          {/* Categories */}
          <Card className="p-4">
            <h3 className="mb-3 font-medium text-gray-900 text-sm">Categories</h3>
            <div className="space-y-1">
              {ticketData.categories.map(category => (
                <button
                  type="button"
                  key={category.id}
                  onClick={() => setSelectedCategory(category.id)}
                  className={`w-full rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                    selectedCategory === category.id
                      ? 'bg-blue-100 text-blue-900'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span>{category.name}</span>
                    <span className="text-gray-500 text-xs">{category.count}</span>
                  </div>
                </button>
              ))}
            </div>
          </Card>
        </div>

        {/* Ticket List */}
        <div className="lg:col-span-3">
          <Card className="divide-y divide-gray-200">
            {filteredTickets.length === 0 ? (
              <div className="p-8 text-center">
                <MessageCircle className="mx-auto mb-4 h-12 w-12 text-gray-400" />
                <h3 className="mb-2 font-medium text-gray-900 text-lg">No tickets found</h3>
                <p className="text-gray-600">
                  {searchQuery
                    ? 'No tickets match your search criteria.'
                    : "You haven't created any support tickets yet."}
                </p>
              </div>
            ) : (
              filteredTickets.map(ticket => (
                <button
                  key={ticket.id}
                  onClick={() => setSelectedTicket(ticket.id)}
                  type="button"
                  className="w-full cursor-pointer p-6 text-left transition-colors hover:bg-gray-50"
                >
                  <div className="flex items-start justify-between">
                    <div className="min-w-0 flex-1">
                      <div className="mb-1 flex items-center space-x-2">
                        {getStatusIcon(ticket.status)}
                        <span
                          className={`rounded-full border px-2 py-1 font-medium text-xs ${getStatusColor(ticket.status)}`}
                        >
                          {ticket.status.toUpperCase()}
                        </span>
                        <span
                          className={`rounded px-2 py-1 font-medium text-xs ${getPriorityColor(ticket.priority)}`}
                        >
                          {ticket.priority.toUpperCase()}
                        </span>
                      </div>

                      <h3 className="mb-1 font-medium text-gray-900 text-lg">{ticket.subject}</h3>

                      <p className="mb-2 line-clamp-2 text-gray-600 text-sm">
                        {ticket.description}
                      </p>

                      <div className="flex items-center space-x-4 text-gray-500 text-xs">
                        <span>#{ticket.id}</span>
                        <span>Created {formatDate(ticket.createdDate)}</span>
                        <span>Updated {formatDate(ticket.lastUpdated)}</span>
                      </div>
                    </div>

                    <ChevronRight className="ml-4 h-5 w-5 text-gray-400" />
                  </div>
                </button>
              ))
            )}
          </Card>
        </div>
      </div>

      {/* Create Ticket Modal */}
      {showCreateTicket ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white">
            <div className="border-b p-6">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold text-gray-900 text-xl">Create Support Ticket</h2>
                <button
                  type="button"
                  onClick={() => setShowCreateTicket(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <XCircle className="h-6 w-6" />
                </button>
              </div>
            </div>

            <div className="space-y-4 p-6">
              <div>
                <label
                  htmlFor="input-1755609778622-yfypjzaia"
                  className="mb-1 block font-medium text-gray-700 text-sm"
                >
                  Category
                </label>
                <select className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
                  <option value="technical">Technical Support</option>
                  <option value="billing">Billing</option>
                  <option value="sales">Sales</option>
                  <option value="general">General</option>
                </select>
              </div>

              <div>
                <label
                  htmlFor="input-1755609778622-3mrqzgmdl"
                  className="mb-1 block font-medium text-gray-700 text-sm"
                >
                  Priority
                </label>
                <select className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>

              <div>
                <label
                  htmlFor="input-1755609778622-ba4nzyjns"
                  className="mb-1 block font-medium text-gray-700 text-sm"
                >
                  Subject
                </label>
                <input
                  type="text"
                  placeholder="Brief description of your issue"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label
                  htmlFor="input-1755609778622-fcpuyat6a"
                  className="mb-1 block font-medium text-gray-700 text-sm"
                >
                  Description
                </label>
                <textarea
                  placeholder="Please provide detailed information about your issue..."
                  rows={6}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div className="flex justify-end space-x-3 border-t bg-gray-50 p-6">
              <button
                type="button"
                onClick={() => setShowCreateTicket(false)}
                className="rounded-lg border border-gray-300 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-100"
              >
                Cancel
              </button>
              <button
                type="button"
                className="rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700"
              >
                Create Ticket
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
