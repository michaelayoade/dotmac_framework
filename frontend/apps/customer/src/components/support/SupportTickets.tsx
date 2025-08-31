'use client';

import React, { useState } from 'react';
import { ManagementPageTemplate } from '@dotmac/primitives/templates/ManagementPageTemplate';
import { 
  PlusIcon,
  EyeIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ChatBubbleLeftRightIcon,
  PhoneIcon,
  DocumentIcon,
  PhotoIcon
} from '@heroicons/react/24/outline';

interface SupportTicket {
  id: string;
  subject: string;
  description: string;
  category: 'technical' | 'billing' | 'general' | 'service_request' | 'complaint';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  status: 'open' | 'in_progress' | 'pending_customer' | 'resolved' | 'closed';
  createdDate: string;
  updatedDate: string;
  resolvedDate?: string;
  assignedAgent?: string;
  customerName: string;
  customerEmail: string;
  customerPhone?: string;
  attachments: {
    id: string;
    name: string;
    type: 'image' | 'document' | 'video';
    url: string;
    size: number;
  }[];
  responses: {
    id: string;
    author: 'customer' | 'agent';
    authorName: string;
    message: string;
    timestamp: string;
    attachments?: {
      id: string;
      name: string;
      url: string;
    }[];
  }[];
  tags: string[];
  relatedTickets?: string[];
}

const mockTickets: SupportTicket[] = [
  {
    id: 'TICK-001',
    subject: 'Internet connection keeps dropping',
    description: 'My internet connection has been dropping every few hours for the past week. The modem lights show everything is fine, but I lose connectivity completely.',
    category: 'technical',
    priority: 'high',
    status: 'in_progress',
    createdDate: '2023-11-28T09:15:00Z',
    updatedDate: '2023-11-29T14:30:00Z',
    assignedAgent: 'Sarah Johnson',
    customerName: 'John Doe',
    customerEmail: 'john.doe@email.com',
    customerPhone: '+1-555-123-4567',
    attachments: [
      {
        id: 'att1',
        name: 'modem_lights.jpg',
        type: 'image',
        url: '/api/attachments/att1',
        size: 1250000
      }
    ],
    responses: [
      {
        id: 'resp1',
        author: 'customer',
        authorName: 'John Doe',
        message: 'My internet connection has been dropping every few hours for the past week. The modem lights show everything is fine, but I lose connectivity completely.',
        timestamp: '2023-11-28T09:15:00Z'
      },
      {
        id: 'resp2',
        author: 'agent',
        authorName: 'Sarah Johnson',
        message: 'Hi John, thank you for contacting us. I can see you are experiencing intermittent connectivity issues. Let me run some diagnostics on your line. Can you please restart your modem and router and let me know if the issue persists?',
        timestamp: '2023-11-28T11:30:00Z'
      }
    ],
    tags: ['connectivity', 'modem', 'intermittent']
  }
];

export const SupportTickets: React.FC = () => {
  const [tickets, setTickets] = useState<SupportTicket[]>(mockTickets);
  const [filteredTickets, setFilteredTickets] = useState<SupportTicket[]>(mockTickets);
  const [selectedTicket, setSelectedTicket] = useState<SupportTicket | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'resolved':
      case 'closed':
        return <CheckCircleIcon className="w-5 h-5 text-green-600" />;
      case 'in_progress':
        return <ClockIcon className="w-5 h-5 text-blue-600" />;
      case 'pending_customer':
        return <ExclamationCircleIcon className="w-5 h-5 text-yellow-600" />;
      default:
        return <ClockIcon className="w-5 h-5 text-gray-600" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'open': return 'bg-blue-100 text-blue-800';
      case 'in_progress': return 'bg-indigo-100 text-indigo-800';
      case 'pending_customer': return 'bg-yellow-100 text-yellow-800';
      case 'resolved': return 'bg-green-100 text-green-800';
      case 'closed': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent': return 'bg-red-100 text-red-800';
      case 'high': return 'bg-orange-100 text-orange-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'low': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'technical': return 'bg-blue-100 text-blue-800';
      case 'billing': return 'bg-green-100 text-green-800';
      case 'service_request': return 'bg-purple-100 text-purple-800';
      case 'complaint': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const columns = [
    {
      key: 'id' as keyof SupportTicket,
      label: 'Ticket ID',
      render: (value: string) => (
        <div className="font-mono text-sm text-gray-900">{value}</div>
      )
    },
    {
      key: 'subject' as keyof SupportTicket,
      label: 'Subject',
      render: (value: string, item: SupportTicket) => (
        <div>
          <div className="font-medium text-gray-900">{value}</div>
          <div className="text-sm text-gray-500 mt-1">
            {item.responses.length} responses
          </div>
        </div>
      )
    },
    {
      key: 'category' as keyof SupportTicket,
      label: 'Category',
      render: (value: string) => (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${getCategoryColor(value)}`}>
          {value.replace('_', ' ')}
        </span>
      )
    },
    {
      key: 'status' as keyof SupportTicket,
      label: 'Status',
      render: (value: string) => (
        <div className="flex items-center space-x-2">
          {getStatusIcon(value)}
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${getStatusColor(value)}`}>
            {value.replace('_', ' ')}
          </span>
        </div>
      )
    },
    {
      key: 'priority' as keyof SupportTicket,
      label: 'Priority',
      render: (value: string) => (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${getPriorityColor(value)}`}>
          {value}
        </span>
      )
    },
    {
      key: 'updatedDate' as keyof SupportTicket,
      label: 'Last Updated',
      render: (value: string) => (
        <div className="text-sm text-gray-900">
          {new Date(value).toLocaleDateString()}
        </div>
      )
    },
    {
      key: 'assignedAgent' as keyof SupportTicket,
      label: 'Agent',
      render: (value: string | undefined) => (
        <div className="text-sm text-gray-900">
          {value || 'Unassigned'}
        </div>
      )
    },
    {
      key: 'id' as keyof SupportTicket,
      label: 'Actions',
      render: (value: string, item: SupportTicket) => (
        <button
          onClick={() => setSelectedTicket(item)}
          className="text-blue-600 hover:text-blue-800 flex items-center space-x-1"
          aria-label={`View details for ticket ${value}`}
        >
          <EyeIcon className="w-4 h-4" />
          <span className="text-sm">View</span>
        </button>
      )
    }
  ];

  const handleSearch = (query: string) => {
    const filtered = tickets.filter(ticket => 
      ticket.id.toLowerCase().includes(query.toLowerCase()) ||
      ticket.subject.toLowerCase().includes(query.toLowerCase()) ||
      ticket.description.toLowerCase().includes(query.toLowerCase()) ||
      ticket.tags.some(tag => tag.toLowerCase().includes(query.toLowerCase()))
    );
    setFilteredTickets(filtered);
  };

  const handleFilter = (filters: Record<string, string>) => {
    let filtered = tickets;
    
    if (filters.status) {
      filtered = filtered.filter(ticket => ticket.status === filters.status);
    }
    if (filters.category) {
      filtered = filtered.filter(ticket => ticket.category === filters.category);
    }
    if (filters.priority) {
      filtered = filtered.filter(ticket => ticket.priority === filters.priority);
    }
    
    setFilteredTickets(filtered);
  };

  const actions = [
    {
      label: 'Create Ticket',
      onClick: () => setShowCreateModal(true),
      variant: 'primary' as const,
      icon: PlusIcon
    },
    {
      label: 'Call Support',
      onClick: () => window.open('tel:+1-800-555-0123', '_self'),
      variant: 'secondary' as const,
      icon: PhoneIcon
    },
    {
      label: 'Live Chat',
      onClick: () => {
        // Open live chat widget
      },
      variant: 'secondary' as const,
      icon: ChatBubbleLeftRightIcon
    }
  ];

  const filters = [
    {
      key: 'status',
      label: 'Status',
      options: [
        { value: 'open', label: 'Open' },
        { value: 'in_progress', label: 'In Progress' },
        { value: 'pending_customer', label: 'Pending Customer' },
        { value: 'resolved', label: 'Resolved' },
        { value: 'closed', label: 'Closed' }
      ]
    },
    {
      key: 'category',
      label: 'Category',
      options: [
        { value: 'technical', label: 'Technical' },
        { value: 'billing', label: 'Billing' },
        { value: 'service_request', label: 'Service Request' },
        { value: 'general', label: 'General' },
        { value: 'complaint', label: 'Complaint' }
      ]
    },
    {
      key: 'priority',
      label: 'Priority',
      options: [
        { value: 'urgent', label: 'Urgent' },
        { value: 'high', label: 'High' },
        { value: 'medium', label: 'Medium' },
        { value: 'low', label: 'Low' }
      ]
    }
  ];

  const openTickets = tickets.filter(t => !['resolved', 'closed'].includes(t.status)).length;

  return (
    <ManagementPageTemplate
      title="Support Tickets"
      subtitle={`${tickets.length} total tickets • ${openTickets} open`}
      data={filteredTickets}
      columns={columns}
      onSearch={handleSearch}
      onFilter={handleFilter}
      actions={actions}
      filters={filters}
      searchPlaceholder="Search tickets by ID, subject, or description..."
      emptyMessage="No support tickets found"
      className="h-full"
    />
  );
};