'use client';

import React, { useState, useMemo } from 'react';
import { clsx } from 'clsx';
import {
  User,
  Phone,
  Mail,
  MapPin,
  Calendar,
  DollarSign,
  TrendingUp,
  Filter,
  Search,
  Plus,
  MoreVertical,
  Star,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Users,
  Target,
  Zap,
} from 'lucide-react';

interface Lead {
  id: string;
  name: string;
  email: string;
  phone: string;
  company?: string;
  location: string;
  source: 'website' | 'referral' | 'cold-call' | 'marketing' | 'partner';
  status:
    | 'new'
    | 'contacted'
    | 'qualified'
    | 'proposal'
    | 'negotiation'
    | 'closed-won'
    | 'closed-lost';
  value: number;
  probability: number;
  createdAt: string;
  lastContact?: string;
  nextAction?: string;
  nextActionDate?: string;
  notes?: string;
  tags?: string[];
  assignedTo?: string;
}

const mockLeads: Lead[] = [
  {
    id: '1',
    name: 'Acme Corporation',
    email: 'contact@acme.com',
    phone: '+1-555-0123',
    company: 'Acme Corp',
    location: 'San Francisco, CA',
    source: 'website',
    status: 'qualified',
    value: 50000,
    probability: 75,
    createdAt: '2025-08-25',
    lastContact: '2025-08-28',
    nextAction: 'Send proposal',
    nextActionDate: '2025-08-30',
    notes: 'Looking for fiber internet for 3 locations',
    tags: ['enterprise', 'fiber'],
    assignedTo: 'John Smith',
  },
  {
    id: '2',
    name: 'Tech Startup Inc',
    email: 'admin@techstartup.com',
    phone: '+1-555-0456',
    company: 'Tech Startup Inc',
    location: 'Austin, TX',
    source: 'referral',
    status: 'new',
    value: 25000,
    probability: 25,
    createdAt: '2025-08-29',
    notes: 'Small office, rapid growth expected',
    tags: ['startup', 'growth'],
    assignedTo: 'Sarah Johnson',
  },
  {
    id: '3',
    name: 'Local Restaurant Chain',
    email: 'it@restaurant.com',
    phone: '+1-555-0789',
    company: 'Local Restaurant Chain',
    location: 'Dallas, TX',
    source: 'cold-call',
    status: 'proposal',
    value: 75000,
    probability: 60,
    createdAt: '2025-08-20',
    lastContact: '2025-08-27',
    nextAction: 'Follow up on proposal',
    nextActionDate: '2025-08-31',
    notes: '5 locations need reliable internet for POS systems',
    tags: ['retail', 'multi-location'],
    assignedTo: 'Mike Davis',
  },
];

export function LeadManagementDashboard() {
  const [leads] = useState<Lead[]>(mockLeads);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterSource, setFilterSource] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'name' | 'value' | 'probability' | 'date'>('date');

  const filteredLeads = useMemo(() => {
    return leads
      .filter((lead) => {
        const matchesStatus = filterStatus === 'all' || lead.status === filterStatus;
        const matchesSource = filterSource === 'all' || lead.source === filterSource;
        const matchesSearch =
          !searchQuery ||
          lead.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          lead.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
          lead.company?.toLowerCase().includes(searchQuery.toLowerCase());

        return matchesStatus && matchesSource && matchesSearch;
      })
      .sort((a, b) => {
        switch (sortBy) {
          case 'name':
            return a.name.localeCompare(b.name);
          case 'value':
            return b.value - a.value;
          case 'probability':
            return b.probability - a.probability;
          case 'date':
            return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
          default:
            return 0;
        }
      });
  }, [leads, filterStatus, filterSource, searchQuery, sortBy]);

  const getStatusColor = (status: Lead['status']) => {
    const colors = {
      new: 'bg-blue-100 text-blue-800',
      contacted: 'bg-yellow-100 text-yellow-800',
      qualified: 'bg-purple-100 text-purple-800',
      proposal: 'bg-orange-100 text-orange-800',
      negotiation: 'bg-indigo-100 text-indigo-800',
      'closed-won': 'bg-green-100 text-green-800',
      'closed-lost': 'bg-red-100 text-red-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const getSourceIcon = (source: Lead['source']) => {
    const icons = {
      website: <TrendingUp className='w-4 h-4' />,
      referral: <Users className='w-4 h-4' />,
      'cold-call': <Phone className='w-4 h-4' />,
      marketing: <Target className='w-4 h-4' />,
      partner: <Zap className='w-4 h-4' />,
    };
    return icons[source];
  };

  const totalValue = filteredLeads.reduce((sum, lead) => sum + lead.value, 0);
  const avgProbability =
    filteredLeads.length > 0
      ? filteredLeads.reduce((sum, lead) => sum + lead.probability, 0) / filteredLeads.length
      : 0;
  const weightedValue = filteredLeads.reduce(
    (sum, lead) => sum + (lead.value * lead.probability) / 100,
    0
  );

  return (
    <div className='space-y-6'>
      {/* Stats Cards */}
      <div className='grid grid-cols-1 md:grid-cols-4 gap-4'>
        <div className='bg-white rounded-lg p-6 shadow-sm border'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='text-sm text-gray-600'>Total Leads</p>
              <p className='text-2xl font-bold text-gray-900'>{filteredLeads.length}</p>
            </div>
            <Users className='w-8 h-8 text-blue-500' />
          </div>
        </div>

        <div className='bg-white rounded-lg p-6 shadow-sm border'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='text-sm text-gray-600'>Pipeline Value</p>
              <p className='text-2xl font-bold text-gray-900'>${totalValue.toLocaleString()}</p>
            </div>
            <DollarSign className='w-8 h-8 text-green-500' />
          </div>
        </div>

        <div className='bg-white rounded-lg p-6 shadow-sm border'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='text-sm text-gray-600'>Weighted Value</p>
              <p className='text-2xl font-bold text-gray-900'>
                ${Math.round(weightedValue).toLocaleString()}
              </p>
            </div>
            <TrendingUp className='w-8 h-8 text-purple-500' />
          </div>
        </div>

        <div className='bg-white rounded-lg p-6 shadow-sm border'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='text-sm text-gray-600'>Avg Probability</p>
              <p className='text-2xl font-bold text-gray-900'>{Math.round(avgProbability)}%</p>
            </div>
            <Target className='w-8 h-8 text-orange-500' />
          </div>
        </div>
      </div>

      {/* Filters and Search */}
      <div className='bg-white rounded-lg p-6 shadow-sm border'>
        <div className='flex flex-col lg:flex-row gap-4'>
          {/* Search */}
          <div className='flex-1 relative'>
            <Search className='absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4' />
            <input
              type='text'
              placeholder='Search leads...'
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className='w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            />
          </div>

          {/* Status Filter */}
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className='px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
          >
            <option value='all'>All Statuses</option>
            <option value='new'>New</option>
            <option value='contacted'>Contacted</option>
            <option value='qualified'>Qualified</option>
            <option value='proposal'>Proposal</option>
            <option value='negotiation'>Negotiation</option>
            <option value='closed-won'>Closed Won</option>
            <option value='closed-lost'>Closed Lost</option>
          </select>

          {/* Source Filter */}
          <select
            value={filterSource}
            onChange={(e) => setFilterSource(e.target.value)}
            className='px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
          >
            <option value='all'>All Sources</option>
            <option value='website'>Website</option>
            <option value='referral'>Referral</option>
            <option value='cold-call'>Cold Call</option>
            <option value='marketing'>Marketing</option>
            <option value='partner'>Partner</option>
          </select>

          {/* Sort */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className='px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
          >
            <option value='date'>Latest First</option>
            <option value='name'>Name A-Z</option>
            <option value='value'>Highest Value</option>
            <option value='probability'>Highest Probability</option>
          </select>

          {/* Add Lead Button */}
          <button className='bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors flex items-center space-x-2'>
            <Plus className='w-4 h-4' />
            <span>Add Lead</span>
          </button>
        </div>
      </div>

      {/* Leads Table */}
      <div className='bg-white rounded-lg shadow-sm border overflow-hidden'>
        <div className='overflow-x-auto'>
          <table className='w-full'>
            <thead className='bg-gray-50 border-b'>
              <tr>
                <th className='text-left p-4 font-medium text-gray-900'>Lead</th>
                <th className='text-left p-4 font-medium text-gray-900'>Contact</th>
                <th className='text-left p-4 font-medium text-gray-900'>Source</th>
                <th className='text-left p-4 font-medium text-gray-900'>Status</th>
                <th className='text-left p-4 font-medium text-gray-900'>Value</th>
                <th className='text-left p-4 font-medium text-gray-900'>Probability</th>
                <th className='text-left p-4 font-medium text-gray-900'>Next Action</th>
                <th className='text-left p-4 font-medium text-gray-900'>Actions</th>
              </tr>
            </thead>
            <tbody className='divide-y divide-gray-200'>
              {filteredLeads.map((lead) => (
                <tr
                  key={lead.id}
                  className='hover:bg-gray-50 cursor-pointer transition-colors'
                  onClick={() => setSelectedLead(lead)}
                >
                  <td className='p-4'>
                    <div className='flex items-center space-x-3'>
                      <div className='w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center'>
                        <User className='w-5 h-5 text-gray-600' />
                      </div>
                      <div>
                        <div className='font-medium text-gray-900'>{lead.name}</div>
                        {lead.company && (
                          <div className='text-sm text-gray-500'>{lead.company}</div>
                        )}
                      </div>
                    </div>
                  </td>

                  <td className='p-4'>
                    <div className='space-y-1'>
                      <div className='flex items-center space-x-2 text-sm text-gray-600'>
                        <Mail className='w-3 h-3' />
                        <span>{lead.email}</span>
                      </div>
                      <div className='flex items-center space-x-2 text-sm text-gray-600'>
                        <Phone className='w-3 h-3' />
                        <span>{lead.phone}</span>
                      </div>
                      <div className='flex items-center space-x-2 text-sm text-gray-600'>
                        <MapPin className='w-3 h-3' />
                        <span>{lead.location}</span>
                      </div>
                    </div>
                  </td>

                  <td className='p-4'>
                    <div className='flex items-center space-x-2'>
                      {getSourceIcon(lead.source)}
                      <span className='text-sm text-gray-600 capitalize'>{lead.source}</span>
                    </div>
                  </td>

                  <td className='p-4'>
                    <span
                      className={clsx(
                        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                        getStatusColor(lead.status)
                      )}
                    >
                      {lead.status.replace('-', ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                    </span>
                  </td>

                  <td className='p-4'>
                    <div className='font-medium text-gray-900'>${lead.value.toLocaleString()}</div>
                  </td>

                  <td className='p-4'>
                    <div className='flex items-center space-x-2'>
                      <div className='flex-1 bg-gray-200 rounded-full h-2'>
                        <div
                          className='bg-blue-600 h-2 rounded-full transition-all duration-300'
                          style={{ width: `${lead.probability}%` }}
                        />
                      </div>
                      <span className='text-sm font-medium text-gray-700'>{lead.probability}%</span>
                    </div>
                  </td>

                  <td className='p-4'>
                    {lead.nextAction && lead.nextActionDate && (
                      <div className='space-y-1'>
                        <div className='text-sm font-medium text-gray-900'>{lead.nextAction}</div>
                        <div className='flex items-center space-x-1 text-xs text-gray-500'>
                          <Calendar className='w-3 h-3' />
                          <span>{new Date(lead.nextActionDate).toLocaleDateString()}</span>
                        </div>
                      </div>
                    )}
                  </td>

                  <td className='p-4'>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        // Handle actions menu
                      }}
                      className='p-1 hover:bg-gray-100 rounded transition-colors'
                    >
                      <MoreVertical className='w-4 h-4 text-gray-600' />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Lead Detail Modal */}
      {selectedLead && (
        <div className='fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4'>
          <div className='bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto'>
            <div className='sticky top-0 bg-white border-b p-6 flex items-center justify-between'>
              <h2 className='text-xl font-bold text-gray-900'>{selectedLead.name}</h2>
              <button
                onClick={() => setSelectedLead(null)}
                className='p-2 hover:bg-gray-100 rounded-full transition-colors'
              >
                <XCircle className='w-5 h-5 text-gray-500' />
              </button>
            </div>

            <div className='p-6 space-y-6'>
              {/* Lead Info */}
              <div className='grid grid-cols-1 md:grid-cols-2 gap-4'>
                <div className='space-y-3'>
                  <div className='flex items-center space-x-2'>
                    <Mail className='w-4 h-4 text-gray-400' />
                    <span className='text-sm text-gray-600'>{selectedLead.email}</span>
                  </div>
                  <div className='flex items-center space-x-2'>
                    <Phone className='w-4 h-4 text-gray-400' />
                    <span className='text-sm text-gray-600'>{selectedLead.phone}</span>
                  </div>
                  <div className='flex items-center space-x-2'>
                    <MapPin className='w-4 h-4 text-gray-400' />
                    <span className='text-sm text-gray-600'>{selectedLead.location}</span>
                  </div>
                </div>

                <div className='space-y-3'>
                  <div className='flex items-center justify-between'>
                    <span className='text-sm text-gray-600'>Status:</span>
                    <span
                      className={clsx(
                        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                        getStatusColor(selectedLead.status)
                      )}
                    >
                      {selectedLead.status
                        .replace('-', ' ')
                        .replace(/\b\w/g, (l) => l.toUpperCase())}
                    </span>
                  </div>
                  <div className='flex items-center justify-between'>
                    <span className='text-sm text-gray-600'>Value:</span>
                    <span className='font-medium text-gray-900'>
                      ${selectedLead.value.toLocaleString()}
                    </span>
                  </div>
                  <div className='flex items-center justify-between'>
                    <span className='text-sm text-gray-600'>Probability:</span>
                    <span className='font-medium text-gray-900'>{selectedLead.probability}%</span>
                  </div>
                </div>
              </div>

              {/* Tags */}
              {selectedLead.tags && selectedLead.tags.length > 0 && (
                <div>
                  <h3 className='text-sm font-medium text-gray-700 mb-2'>Tags</h3>
                  <div className='flex flex-wrap gap-2'>
                    {selectedLead.tags.map((tag) => (
                      <span
                        key={tag}
                        className='inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800'
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Notes */}
              {selectedLead.notes && (
                <div>
                  <h3 className='text-sm font-medium text-gray-700 mb-2'>Notes</h3>
                  <p className='text-sm text-gray-600 bg-gray-50 p-3 rounded-lg'>
                    {selectedLead.notes}
                  </p>
                </div>
              )}

              {/* Next Action */}
              {selectedLead.nextAction && (
                <div>
                  <h3 className='text-sm font-medium text-gray-700 mb-2'>Next Action</h3>
                  <div className='bg-blue-50 p-3 rounded-lg'>
                    <div className='flex items-center space-x-2'>
                      <Clock className='w-4 h-4 text-blue-600' />
                      <span className='text-sm font-medium text-blue-900'>
                        {selectedLead.nextAction}
                      </span>
                    </div>
                    {selectedLead.nextActionDate && (
                      <div className='text-xs text-blue-600 mt-1'>
                        Due: {new Date(selectedLead.nextActionDate).toLocaleDateString()}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className='flex flex-wrap gap-2 pt-4 border-t'>
                <button className='bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors text-sm'>
                  Update Status
                </button>
                <button className='bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors text-sm'>
                  Schedule Call
                </button>
                <button className='bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 transition-colors text-sm'>
                  Send Proposal
                </button>
                <button className='border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors text-sm'>
                  Add Note
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
