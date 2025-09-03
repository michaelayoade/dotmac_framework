'use client';

import { useState, useEffect } from 'react';
import {
  UserPlus,
  FileText,
  CheckCircle,
  Clock,
  AlertCircle,
  Star,
  MapPin,
  Building,
  Mail,
  Phone,
  DollarSign,
  Calendar,
  Filter,
  Search,
  MoreVertical,
  Eye,
  Check,
  X,
  Download,
  Upload,
} from 'lucide-react';

interface OnboardingApplication {
  id: string;
  companyName: string;
  contactName: string;
  email: string;
  phone: string;
  partnerType: 'AGENT' | 'DEALER' | 'DISTRIBUTOR' | 'VAR' | 'REFERRAL';
  territory: {
    type: 'GEOGRAPHIC' | 'VERTICAL' | 'ACCOUNT_BASED';
    value: string;
  };
  expectedRevenue: number;
  submittedAt: string;
  status: 'PENDING_REVIEW' | 'UNDER_REVIEW' | 'PENDING_DOCS' | 'APPROVED' | 'REJECTED';
  completionPercentage: number;
  documents: {
    businessLicense: boolean;
    taxDocument: boolean;
    bankInfo: boolean;
    references: boolean;
    insurance: boolean;
  };
  score: number;
  notes?: string;
  reviewer?: string;
  reviewedAt?: string;
}

export default function PartnerOnboardingPage() {
  const [applications, setApplications] = useState<OnboardingApplication[]>([]);
  const [filteredApplications, setFilteredApplications] = useState<OnboardingApplication[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [selectedApplication, setSelectedApplication] = useState<OnboardingApplication | null>(
    null
  );
  const [showDetails, setShowDetails] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Mock data - replace with actual API call
    const mockApplications: OnboardingApplication[] = [
      {
        id: 'app_001',
        companyName: 'TechSolutions LLC',
        contactName: 'John Smith',
        email: 'john@techsolutions.com',
        phone: '+1 (555) 123-4567',
        partnerType: 'DEALER',
        territory: { type: 'GEOGRAPHIC', value: 'California, USA' },
        expectedRevenue: 250000,
        submittedAt: '2024-01-15T10:30:00Z',
        status: 'UNDER_REVIEW',
        completionPercentage: 85,
        documents: {
          businessLicense: true,
          taxDocument: true,
          bankInfo: false,
          references: true,
          insurance: true,
        },
        score: 8.2,
        reviewer: 'Sarah Johnson',
        notes: 'Strong application with good references',
      },
      {
        id: 'app_002',
        companyName: 'Network Pro Services',
        contactName: 'Maria Garcia',
        email: 'maria@networkpro.com',
        phone: '+1 (555) 987-6543',
        partnerType: 'AGENT',
        territory: { type: 'VERTICAL', value: 'Small Business' },
        expectedRevenue: 150000,
        submittedAt: '2024-01-18T14:20:00Z',
        status: 'PENDING_DOCS',
        completionPercentage: 60,
        documents: {
          businessLicense: true,
          taxDocument: false,
          bankInfo: true,
          references: true,
          insurance: false,
        },
        score: 7.1,
      },
      {
        id: 'app_003',
        companyName: 'Metro ISP Partners',
        contactName: 'David Chen',
        email: 'david@metroisp.com',
        phone: '+1 (555) 456-7890',
        partnerType: 'DISTRIBUTOR',
        territory: { type: 'GEOGRAPHIC', value: 'New York Metro' },
        expectedRevenue: 500000,
        submittedAt: '2024-01-12T09:15:00Z',
        status: 'APPROVED',
        completionPercentage: 100,
        documents: {
          businessLicense: true,
          taxDocument: true,
          bankInfo: true,
          references: true,
          insurance: true,
        },
        score: 9.1,
        reviewer: 'Mike Wilson',
        reviewedAt: '2024-01-20T11:00:00Z',
      },
    ];

    setTimeout(() => {
      setApplications(mockApplications);
      setFilteredApplications(mockApplications);
      setIsLoading(false);
    }, 1000);
  }, []);

  useEffect(() => {
    let filtered = applications;

    if (searchTerm) {
      filtered = filtered.filter(
        (app) =>
          app.companyName.toLowerCase().includes(searchTerm.toLowerCase()) ||
          app.contactName.toLowerCase().includes(searchTerm.toLowerCase()) ||
          app.email.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    if (statusFilter !== 'all') {
      filtered = filtered.filter((app) => app.status === statusFilter);
    }

    if (typeFilter !== 'all') {
      filtered = filtered.filter((app) => app.partnerType === typeFilter);
    }

    setFilteredApplications(filtered);
  }, [applications, searchTerm, statusFilter, typeFilter]);

  const getStatusColor = (status: OnboardingApplication['status']) => {
    switch (status) {
      case 'PENDING_REVIEW':
        return 'bg-yellow-100 text-yellow-800';
      case 'UNDER_REVIEW':
        return 'bg-blue-100 text-blue-800';
      case 'PENDING_DOCS':
        return 'bg-orange-100 text-orange-800';
      case 'APPROVED':
        return 'bg-green-100 text-green-800';
      case 'REJECTED':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getTypeColor = (type: OnboardingApplication['partnerType']) => {
    switch (type) {
      case 'AGENT':
        return 'bg-blue-100 text-blue-800';
      case 'DEALER':
        return 'bg-green-100 text-green-800';
      case 'DISTRIBUTOR':
        return 'bg-purple-100 text-purple-800';
      case 'VAR':
        return 'bg-indigo-100 text-indigo-800';
      case 'REFERRAL':
        return 'bg-pink-100 text-pink-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const handleApprove = (applicationId: string) => {
    setApplications((prev) =>
      prev.map((app) =>
        app.id === applicationId
          ? { ...app, status: 'APPROVED' as const, reviewedAt: new Date().toISOString() }
          : app
      )
    );
  };

  const handleReject = (applicationId: string) => {
    setApplications((prev) =>
      prev.map((app) =>
        app.id === applicationId
          ? { ...app, status: 'REJECTED' as const, reviewedAt: new Date().toISOString() }
          : app
      )
    );
  };

  const completedDocs = (docs: OnboardingApplication['documents']) => {
    return Object.values(docs).filter(Boolean).length;
  };

  const totalDocs = 5;

  if (isLoading) {
    return (
      <div className='flex items-center justify-center min-h-96'>
        <div className='text-center'>
          <div className='animate-spin rounded-full h-12 w-12 border-b-2 border-management-600 mx-auto mb-4' />
          <p className='text-gray-600'>Loading applications...</p>
        </div>
      </div>
    );
  }

  return (
    <div className='space-y-6'>
      {/* Header */}
      <div className='flex items-center justify-between'>
        <div>
          <h1 className='text-2xl font-bold text-gray-900'>Partner Onboarding</h1>
          <p className='text-gray-600 mt-1'>Manage partner applications and onboarding workflow</p>
        </div>
        <button className='management-button-primary flex items-center gap-2'>
          <UserPlus className='h-4 w-4' />
          Invite Partner
        </button>
      </div>

      {/* Stats Cards */}
      <div className='grid grid-cols-1 md:grid-cols-4 gap-6'>
        <div className='bg-white rounded-lg border border-gray-200 p-6'>
          <div className='flex items-center'>
            <div className='flex-shrink-0'>
              <Clock className='h-8 w-8 text-yellow-600' />
            </div>
            <div className='ml-5 w-0 flex-1'>
              <dl>
                <dt className='text-sm font-medium text-gray-500 truncate'>Pending Review</dt>
                <dd className='text-lg font-medium text-gray-900'>
                  {applications.filter((app) => app.status === 'PENDING_REVIEW').length}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className='bg-white rounded-lg border border-gray-200 p-6'>
          <div className='flex items-center'>
            <div className='flex-shrink-0'>
              <FileText className='h-8 w-8 text-blue-600' />
            </div>
            <div className='ml-5 w-0 flex-1'>
              <dl>
                <dt className='text-sm font-medium text-gray-500 truncate'>Under Review</dt>
                <dd className='text-lg font-medium text-gray-900'>
                  {applications.filter((app) => app.status === 'UNDER_REVIEW').length}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className='bg-white rounded-lg border border-gray-200 p-6'>
          <div className='flex items-center'>
            <div className='flex-shrink-0'>
              <CheckCircle className='h-8 w-8 text-green-600' />
            </div>
            <div className='ml-5 w-0 flex-1'>
              <dl>
                <dt className='text-sm font-medium text-gray-500 truncate'>Approved</dt>
                <dd className='text-lg font-medium text-gray-900'>
                  {applications.filter((app) => app.status === 'APPROVED').length}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className='bg-white rounded-lg border border-gray-200 p-6'>
          <div className='flex items-center'>
            <div className='flex-shrink-0'>
              <DollarSign className='h-8 w-8 text-purple-600' />
            </div>
            <div className='ml-5 w-0 flex-1'>
              <dl>
                <dt className='text-sm font-medium text-gray-500 truncate'>Expected Revenue</dt>
                <dd className='text-lg font-medium text-gray-900'>
                  $
                  {applications.reduce((sum, app) => sum + app.expectedRevenue, 0).toLocaleString()}
                </dd>
              </dl>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className='bg-white rounded-lg border border-gray-200 p-6'>
        <div className='flex flex-col sm:flex-row gap-4'>
          <div className='flex-1'>
            <div className='relative'>
              <Search className='absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400' />
              <input
                type='text'
                placeholder='Search applications...'
                className='management-input pl-10'
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>
          <div className='flex gap-2'>
            <select
              className='management-input min-w-32'
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value='all'>All Status</option>
              <option value='PENDING_REVIEW'>Pending Review</option>
              <option value='UNDER_REVIEW'>Under Review</option>
              <option value='PENDING_DOCS'>Pending Docs</option>
              <option value='APPROVED'>Approved</option>
              <option value='REJECTED'>Rejected</option>
            </select>
            <select
              className='management-input min-w-32'
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
            >
              <option value='all'>All Types</option>
              <option value='AGENT'>Agent</option>
              <option value='DEALER'>Dealer</option>
              <option value='DISTRIBUTOR'>Distributor</option>
              <option value='VAR'>VAR</option>
              <option value='REFERRAL'>Referral</option>
            </select>
          </div>
        </div>
      </div>

      {/* Applications Table */}
      <div className='bg-white rounded-lg border border-gray-200 overflow-hidden'>
        <div className='px-6 py-4 border-b border-gray-200'>
          <h2 className='text-lg font-medium text-gray-900'>Applications</h2>
        </div>
        <div className='overflow-x-auto'>
          <table className='min-w-full divide-y divide-gray-200'>
            <thead className='bg-gray-50'>
              <tr>
                <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                  Company
                </th>
                <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                  Contact
                </th>
                <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                  Type
                </th>
                <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                  Territory
                </th>
                <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                  Status
                </th>
                <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                  Progress
                </th>
                <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                  Score
                </th>
                <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                  Submitted
                </th>
                <th className='relative px-6 py-3'>
                  <span className='sr-only'>Actions</span>
                </th>
              </tr>
            </thead>
            <tbody className='bg-white divide-y divide-gray-200'>
              {filteredApplications.map((application) => (
                <tr key={application.id} className='hover:bg-gray-50'>
                  <td className='px-6 py-4 whitespace-nowrap'>
                    <div>
                      <div className='text-sm font-medium text-gray-900'>
                        {application.companyName}
                      </div>
                      <div className='text-sm text-gray-500'>
                        Expected: ${application.expectedRevenue.toLocaleString()}
                      </div>
                    </div>
                  </td>
                  <td className='px-6 py-4 whitespace-nowrap'>
                    <div>
                      <div className='text-sm font-medium text-gray-900'>
                        {application.contactName}
                      </div>
                      <div className='text-sm text-gray-500 flex items-center'>
                        <Mail className='h-3 w-3 mr-1' />
                        {application.email}
                      </div>
                    </div>
                  </td>
                  <td className='px-6 py-4 whitespace-nowrap'>
                    <span
                      className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getTypeColor(application.partnerType)}`}
                    >
                      {application.partnerType}
                    </span>
                  </td>
                  <td className='px-6 py-4 whitespace-nowrap'>
                    <div className='flex items-center text-sm text-gray-900'>
                      <MapPin className='h-4 w-4 mr-1 text-gray-400' />
                      {application.territory.value}
                    </div>
                    <div className='text-xs text-gray-500'>{application.territory.type}</div>
                  </td>
                  <td className='px-6 py-4 whitespace-nowrap'>
                    <span
                      className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(application.status)}`}
                    >
                      {application.status.replace('_', ' ')}
                    </span>
                  </td>
                  <td className='px-6 py-4 whitespace-nowrap'>
                    <div className='flex items-center'>
                      <div className='w-16 bg-gray-200 rounded-full h-2 mr-2'>
                        <div
                          className='bg-management-600 h-2 rounded-full'
                          style={{ width: `${application.completionPercentage}%` }}
                        />
                      </div>
                      <span className='text-sm text-gray-600'>
                        {application.completionPercentage}%
                      </span>
                    </div>
                    <div className='text-xs text-gray-500 mt-1'>
                      {completedDocs(application.documents)}/{totalDocs} docs
                    </div>
                  </td>
                  <td className='px-6 py-4 whitespace-nowrap'>
                    <div className='flex items-center'>
                      <Star className='h-4 w-4 text-yellow-400 mr-1' />
                      <span className='text-sm font-medium text-gray-900'>{application.score}</span>
                    </div>
                  </td>
                  <td className='px-6 py-4 whitespace-nowrap text-sm text-gray-500'>
                    {new Date(application.submittedAt).toLocaleDateString()}
                  </td>
                  <td className='px-6 py-4 whitespace-nowrap text-right text-sm font-medium'>
                    <div className='flex items-center space-x-2'>
                      <button
                        onClick={() => {
                          setSelectedApplication(application);
                          setShowDetails(true);
                        }}
                        className='text-management-600 hover:text-management-900 p-1'
                        title='View Details'
                      >
                        <Eye className='h-4 w-4' />
                      </button>
                      {application.status === 'UNDER_REVIEW' && (
                        <>
                          <button
                            onClick={() => handleApprove(application.id)}
                            className='text-green-600 hover:text-green-900 p-1'
                            title='Approve'
                          >
                            <Check className='h-4 w-4' />
                          </button>
                          <button
                            onClick={() => handleReject(application.id)}
                            className='text-red-600 hover:text-red-900 p-1'
                            title='Reject'
                          >
                            <X className='h-4 w-4' />
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {filteredApplications.length === 0 && (
          <div className='text-center py-12'>
            <FileText className='mx-auto h-12 w-12 text-gray-400' />
            <h3 className='mt-2 text-sm font-medium text-gray-900'>No applications found</h3>
            <p className='mt-1 text-sm text-gray-500'>
              {searchTerm || statusFilter !== 'all' || typeFilter !== 'all'
                ? 'Try adjusting your search or filter criteria.'
                : 'No partner applications have been submitted yet.'}
            </p>
          </div>
        )}
      </div>

      {/* Application Details Modal */}
      {showDetails && selectedApplication && (
        <div className='fixed inset-0 z-50 overflow-y-auto'>
          <div className='flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0'>
            <div
              className='fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity'
              onClick={() => setShowDetails(false)}
            />
            <div className='relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-4xl'>
              <div className='bg-white px-4 pb-4 pt-5 sm:p-6 sm:pb-4'>
                <div className='flex items-start justify-between mb-4'>
                  <div>
                    <h3 className='text-lg font-medium text-gray-900'>
                      {selectedApplication.companyName} - Application Details
                    </h3>
                    <p className='text-sm text-gray-500'>
                      Application ID: {selectedApplication.id}
                    </p>
                  </div>
                  <button
                    onClick={() => setShowDetails(false)}
                    className='text-gray-400 hover:text-gray-600'
                  >
                    <X className='h-6 w-6' />
                  </button>
                </div>

                <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
                  {/* Company Information */}
                  <div className='space-y-4'>
                    <div className='bg-gray-50 rounded-lg p-4'>
                      <h4 className='text-sm font-medium text-gray-900 mb-3'>
                        Company Information
                      </h4>
                      <div className='space-y-2'>
                        <div className='flex items-center'>
                          <Building className='h-4 w-4 text-gray-400 mr-2' />
                          <span className='text-sm text-gray-900'>
                            {selectedApplication.companyName}
                          </span>
                        </div>
                        <div className='flex items-center'>
                          <Mail className='h-4 w-4 text-gray-400 mr-2' />
                          <span className='text-sm text-gray-900'>{selectedApplication.email}</span>
                        </div>
                        <div className='flex items-center'>
                          <Phone className='h-4 w-4 text-gray-400 mr-2' />
                          <span className='text-sm text-gray-900'>{selectedApplication.phone}</span>
                        </div>
                        <div className='flex items-center'>
                          <MapPin className='h-4 w-4 text-gray-400 mr-2' />
                          <span className='text-sm text-gray-900'>
                            {selectedApplication.territory.value}
                          </span>
                        </div>
                        <div className='flex items-center'>
                          <DollarSign className='h-4 w-4 text-gray-400 mr-2' />
                          <span className='text-sm text-gray-900'>
                            ${selectedApplication.expectedRevenue.toLocaleString()} expected revenue
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Documents Checklist */}
                    <div className='bg-gray-50 rounded-lg p-4'>
                      <h4 className='text-sm font-medium text-gray-900 mb-3'>Required Documents</h4>
                      <div className='space-y-2'>
                        {Object.entries(selectedApplication.documents).map(([key, completed]) => (
                          <div key={key} className='flex items-center justify-between'>
                            <span className='text-sm text-gray-700 capitalize'>
                              {key.replace(/([A-Z])/g, ' $1').toLowerCase()}
                            </span>
                            {completed ? (
                              <CheckCircle className='h-4 w-4 text-green-500' />
                            ) : (
                              <AlertCircle className='h-4 w-4 text-red-500' />
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Review Information */}
                  <div className='space-y-4'>
                    <div className='bg-gray-50 rounded-lg p-4'>
                      <h4 className='text-sm font-medium text-gray-900 mb-3'>Review Status</h4>
                      <div className='space-y-2'>
                        <div className='flex justify-between items-center'>
                          <span className='text-sm text-gray-700'>Status:</span>
                          <span
                            className={`px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(selectedApplication.status)}`}
                          >
                            {selectedApplication.status.replace('_', ' ')}
                          </span>
                        </div>
                        <div className='flex justify-between items-center'>
                          <span className='text-sm text-gray-700'>Score:</span>
                          <div className='flex items-center'>
                            <Star className='h-4 w-4 text-yellow-400 mr-1' />
                            <span className='text-sm font-medium'>{selectedApplication.score}</span>
                          </div>
                        </div>
                        <div className='flex justify-between items-center'>
                          <span className='text-sm text-gray-700'>Completion:</span>
                          <span className='text-sm font-medium'>
                            {selectedApplication.completionPercentage}%
                          </span>
                        </div>
                        {selectedApplication.reviewer && (
                          <div className='flex justify-between items-center'>
                            <span className='text-sm text-gray-700'>Reviewer:</span>
                            <span className='text-sm text-gray-900'>
                              {selectedApplication.reviewer}
                            </span>
                          </div>
                        )}
                        {selectedApplication.reviewedAt && (
                          <div className='flex justify-between items-center'>
                            <span className='text-sm text-gray-700'>Reviewed:</span>
                            <span className='text-sm text-gray-900'>
                              {new Date(selectedApplication.reviewedAt).toLocaleDateString()}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Notes */}
                    {selectedApplication.notes && (
                      <div className='bg-gray-50 rounded-lg p-4'>
                        <h4 className='text-sm font-medium text-gray-900 mb-3'>Review Notes</h4>
                        <p className='text-sm text-gray-700'>{selectedApplication.notes}</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <div className='bg-gray-50 px-4 py-3 sm:flex sm:flex-row-reverse sm:px-6'>
                {selectedApplication.status === 'UNDER_REVIEW' && (
                  <>
                    <button
                      onClick={() => {
                        handleApprove(selectedApplication.id);
                        setShowDetails(false);
                      }}
                      className='inline-flex w-full justify-center rounded-md bg-green-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-green-500 sm:ml-3 sm:w-auto'
                    >
                      <Check className='h-4 w-4 mr-2' />
                      Approve Application
                    </button>
                    <button
                      onClick={() => {
                        handleReject(selectedApplication.id);
                        setShowDetails(false);
                      }}
                      className='mt-3 inline-flex w-full justify-center rounded-md bg-red-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-red-500 sm:mt-0 sm:ml-3 sm:w-auto'
                    >
                      <X className='h-4 w-4 mr-2' />
                      Reject Application
                    </button>
                  </>
                )}
                <button
                  onClick={() => setShowDetails(false)}
                  className='mt-3 inline-flex w-full justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 sm:mt-0 sm:w-auto'
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
