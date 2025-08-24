'use client';

import { useState, useEffect } from 'react';
import { 
  Users, 
  Search, 
  Filter, 
  MoreVertical, 
  Star, 
  MapPin, 
  DollarSign, 
  TrendingUp, 
  TrendingDown,
  Mail,
  Phone,
  Building,
  Calendar,
  Award,
  AlertCircle,
  CheckCircle,
  Eye,
  Edit,
  Pause,
  Play
} from 'lucide-react';

interface Partner {
  id: string;
  companyName: string;
  contactName: string;
  email: string;
  phone: string;
  partnerType: 'AGENT' | 'DEALER' | 'DISTRIBUTOR' | 'VAR' | 'REFERRAL';
  tier: 'BRONZE' | 'SILVER' | 'GOLD' | 'PLATINUM' | 'DIAMOND';
  status: 'ACTIVE' | 'INACTIVE' | 'SUSPENDED' | 'PENDING';
  territory: string;
  joinedAt: string;
  lastActivity: string;
  monthlyRevenue: number;
  totalRevenue: number;
  commissionRate: number;
  performance: {
    score: number;
    trend: 'up' | 'down' | 'stable';
    salesThisMonth: number;
    customersAcquired: number;
  };
  certifications: string[];
  tags: string[];
}

export default function PartnersPage() {
  const [partners, setPartners] = useState<Partner[]>([]);
  const [filteredPartners, setFilteredPartners] = useState<Partner[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [tierFilter, setTierFilter] = useState<string>('all');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Mock data - replace with actual API call
    const mockPartners: Partner[] = [
      {
        id: 'partner_001',
        companyName: 'TechSolutions LLC',
        contactName: 'John Smith',
        email: 'john@techsolutions.com',
        phone: '+1 (555) 123-4567',
        partnerType: 'DEALER',
        tier: 'GOLD',
        status: 'ACTIVE',
        territory: 'California, USA',
        joinedAt: '2023-06-15T00:00:00Z',
        lastActivity: '2024-01-20T14:30:00Z',
        monthlyRevenue: 45000,
        totalRevenue: 320000,
        commissionRate: 12,
        performance: {
          score: 8.2,
          trend: 'up',
          salesThisMonth: 15,
          customersAcquired: 28
        },
        certifications: ['ISP Advanced', 'Sales Professional'],
        tags: ['high-performer', 'reliable']
      },
      {
        id: 'partner_002',
        companyName: 'Network Pro Services',
        contactName: 'Maria Garcia',
        email: 'maria@networkpro.com',
        phone: '+1 (555) 987-6543',
        partnerType: 'AGENT',
        tier: 'SILVER',
        status: 'ACTIVE',
        territory: 'Texas, USA',
        joinedAt: '2023-09-22T00:00:00Z',
        lastActivity: '2024-01-19T09:15:00Z',
        monthlyRevenue: 28000,
        totalRevenue: 124000,
        commissionRate: 10,
        performance: {
          score: 7.1,
          trend: 'stable',
          salesThisMonth: 8,
          customersAcquired: 15
        },
        certifications: ['ISP Basic'],
        tags: ['consistent']
      },
      {
        id: 'partner_003',
        companyName: 'Metro ISP Partners',
        contactName: 'David Chen',
        email: 'david@metroisp.com',
        phone: '+1 (555) 456-7890',
        partnerType: 'DISTRIBUTOR',
        tier: 'PLATINUM',
        status: 'ACTIVE',
        territory: 'New York Metro',
        joinedAt: '2022-03-10T00:00:00Z',
        lastActivity: '2024-01-21T11:45:00Z',
        monthlyRevenue: 85000,
        totalRevenue: 1250000,
        commissionRate: 15,
        performance: {
          score: 9.1,
          trend: 'up',
          salesThisMonth: 32,
          customersAcquired: 67
        },
        certifications: ['ISP Advanced', 'Enterprise Sales', 'Leadership'],
        tags: ['top-performer', 'strategic']
      },
      {
        id: 'partner_004',
        companyName: 'ConnectFirst Solutions',
        contactName: 'Sarah Johnson',
        email: 'sarah@connectfirst.com',
        phone: '+1 (555) 321-0987',
        partnerType: 'VAR',
        tier: 'BRONZE',
        status: 'INACTIVE',
        territory: 'Florida, USA',
        joinedAt: '2023-11-05T00:00:00Z',
        lastActivity: '2023-12-18T16:20:00Z',
        monthlyRevenue: 12000,
        totalRevenue: 24000,
        commissionRate: 8,
        performance: {
          score: 5.8,
          trend: 'down',
          salesThisMonth: 2,
          customersAcquired: 4
        },
        certifications: [],
        tags: ['needs-attention']
      }
    ];

    setTimeout(() => {
      setPartners(mockPartners);
      setFilteredPartners(mockPartners);
      setIsLoading(false);
    }, 1000);
  }, []);

  useEffect(() => {
    let filtered = partners;

    if (searchTerm) {
      filtered = filtered.filter(partner => 
        partner.companyName.toLowerCase().includes(searchTerm.toLowerCase()) ||
        partner.contactName.toLowerCase().includes(searchTerm.toLowerCase()) ||
        partner.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
        partner.territory.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    if (statusFilter !== 'all') {
      filtered = filtered.filter(partner => partner.status === statusFilter);
    }

    if (typeFilter !== 'all') {
      filtered = filtered.filter(partner => partner.partnerType === typeFilter);
    }

    if (tierFilter !== 'all') {
      filtered = filtered.filter(partner => partner.tier === tierFilter);
    }

    setFilteredPartners(filtered);
  }, [partners, searchTerm, statusFilter, typeFilter, tierFilter]);

  const getStatusColor = (status: Partner['status']) => {
    switch (status) {
      case 'ACTIVE': return 'bg-green-100 text-green-800';
      case 'INACTIVE': return 'bg-gray-100 text-gray-800';
      case 'SUSPENDED': return 'bg-red-100 text-red-800';
      case 'PENDING': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getTierColor = (tier: Partner['tier']) => {
    switch (tier) {
      case 'BRONZE': return 'bg-orange-100 text-orange-800';
      case 'SILVER': return 'bg-gray-100 text-gray-800';
      case 'GOLD': return 'bg-yellow-100 text-yellow-800';
      case 'PLATINUM': return 'bg-purple-100 text-purple-800';
      case 'DIAMOND': return 'bg-blue-100 text-blue-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getTypeColor = (type: Partner['partnerType']) => {
    switch (type) {
      case 'AGENT': return 'bg-blue-100 text-blue-800';
      case 'DEALER': return 'bg-green-100 text-green-800';
      case 'DISTRIBUTOR': return 'bg-purple-100 text-purple-800';
      case 'VAR': return 'bg-indigo-100 text-indigo-800';
      case 'REFERRAL': return 'bg-pink-100 text-pink-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up': return <TrendingUp className="h-4 w-4 text-green-500" />;
      case 'down': return <TrendingDown className="h-4 w-4 text-red-500" />;
      default: return <div className="h-4 w-4 bg-gray-300 rounded-full" />;
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-management-600 mx-auto mb-4" />
          <p className="text-gray-600">Loading partners...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">All Partners</h1>
          <p className="text-gray-600 mt-1">Manage your partner network</p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Users className="h-8 w-8 text-blue-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">Total Partners</dt>
                <dd className="text-lg font-medium text-gray-900">{partners.length}</dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">Active Partners</dt>
                <dd className="text-lg font-medium text-gray-900">
                  {partners.filter(p => p.status === 'ACTIVE').length}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <DollarSign className="h-8 w-8 text-purple-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">Monthly Revenue</dt>
                <dd className="text-lg font-medium text-gray-900">
                  ${partners.reduce((sum, p) => sum + p.monthlyRevenue, 0).toLocaleString()}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Star className="h-8 w-8 text-yellow-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">Avg Performance</dt>
                <dd className="text-lg font-medium text-gray-900">
                  {(partners.reduce((sum, p) => sum + p.performance.score, 0) / partners.length).toFixed(1)}
                </dd>
              </dl>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search partners..."
                className="management-input pl-10"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>
          <div className="flex gap-2">
            <select
              className="management-input min-w-32"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="all">All Status</option>
              <option value="ACTIVE">Active</option>
              <option value="INACTIVE">Inactive</option>
              <option value="SUSPENDED">Suspended</option>
              <option value="PENDING">Pending</option>
            </select>
            <select
              className="management-input min-w-32"
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
            >
              <option value="all">All Types</option>
              <option value="AGENT">Agent</option>
              <option value="DEALER">Dealer</option>
              <option value="DISTRIBUTOR">Distributor</option>
              <option value="VAR">VAR</option>
              <option value="REFERRAL">Referral</option>
            </select>
            <select
              className="management-input min-w-32"
              value={tierFilter}
              onChange={(e) => setTierFilter(e.target.value)}
            >
              <option value="all">All Tiers</option>
              <option value="BRONZE">Bronze</option>
              <option value="SILVER">Silver</option>
              <option value="GOLD">Gold</option>
              <option value="PLATINUM">Platinum</option>
              <option value="DIAMOND">Diamond</option>
            </select>
          </div>
        </div>
      </div>

      {/* Partners Table */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900">Partners</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Partner
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Contact
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type & Tier
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Territory
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Performance
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Revenue
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Last Activity
                </th>
                <th className="relative px-6 py-3">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredPartners.map((partner) => (
                <tr key={partner.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="flex-shrink-0 h-10 w-10">
                        <div className="h-10 w-10 rounded-full bg-management-500 flex items-center justify-center text-white font-medium">
                          {partner.companyName.charAt(0)}
                        </div>
                      </div>
                      <div className="ml-4">
                        <div className="text-sm font-medium text-gray-900">
                          {partner.companyName}
                        </div>
                        <div className="text-sm text-gray-500">
                          Member since {new Date(partner.joinedAt).getFullYear()}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <div className="text-sm font-medium text-gray-900">
                        {partner.contactName}
                      </div>
                      <div className="text-sm text-gray-500 flex items-center">
                        <Mail className="h-3 w-3 mr-1" />
                        {partner.email}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="space-y-1">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getTypeColor(partner.partnerType)}`}>
                        {partner.partnerType}
                      </span>
                      <br />
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getTierColor(partner.tier)}`}>
                        {partner.tier}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center text-sm text-gray-900">
                      <MapPin className="h-4 w-4 mr-1 text-gray-400" />
                      {partner.territory}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <Star className="h-4 w-4 text-yellow-400 mr-1" />
                      <span className="text-sm font-medium text-gray-900 mr-2">
                        {partner.performance.score}
                      </span>
                      {getTrendIcon(partner.performance.trend)}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {partner.performance.salesThisMonth} sales this month
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <div className="text-sm font-medium text-gray-900">
                        ${partner.monthlyRevenue.toLocaleString()}/mo
                      </div>
                      <div className="text-sm text-gray-500">
                        ${partner.totalRevenue.toLocaleString()} total
                      </div>
                      <div className="text-xs text-gray-500">
                        {partner.commissionRate}% commission
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(partner.status)}`}>
                      {partner.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(partner.lastActivity).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex items-center space-x-2">
                      <button
                        className="text-management-600 hover:text-management-900 p-1"
                        title="View Details"
                      >
                        <Eye className="h-4 w-4" />
                      </button>
                      <button
                        className="text-gray-600 hover:text-gray-900 p-1"
                        title="Edit Partner"
                      >
                        <Edit className="h-4 w-4" />
                      </button>
                      <button
                        className="text-gray-600 hover:text-gray-900 p-1"
                        title="More Actions"
                      >
                        <MoreVertical className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {filteredPartners.length === 0 && (
          <div className="text-center py-12">
            <Users className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No partners found</h3>
            <p className="mt-1 text-sm text-gray-500">
              {searchTerm || statusFilter !== 'all' || typeFilter !== 'all' || tierFilter !== 'all'
                ? 'Try adjusting your search or filter criteria.'
                : 'No partners have been added yet.'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}