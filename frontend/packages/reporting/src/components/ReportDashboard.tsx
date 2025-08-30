/**
 * Report Dashboard Component
 * Leverages existing dashboard patterns and components
 */

import React, { useState, useCallback, useMemo } from 'react';
import { Plus, Search, Filter, Grid, List, MoreVertical, Calendar, Download } from 'lucide-react';
import { Button, Card, Input } from '@dotmac/primitives';
import { UniversalReportGenerator } from '../generators/UniversalReportGenerator';
import { ReportScheduler } from './ReportScheduler';
import type {
  Report,
  ReportDashboard as ReportDashboardType,
  DashboardReport,
  ReportCategory,
  PortalVariant
} from '../types';
import { cn } from '../utils/cn';

interface ReportDashboardProps {
  dashboard?: ReportDashboardType;
  reports: Report[];
  portal: PortalVariant;
  className?: string;
  onReportCreate?: () => void;
  onReportEdit?: (reportId: string) => void;
  onReportDelete?: (reportId: string) => void;
  onReportSchedule?: (reportId: string, schedule: any) => void;
  onDashboardUpdate?: (dashboard: ReportDashboardType) => void;
}

export const ReportDashboard: React.FC<ReportDashboardProps> = ({
  dashboard,
  reports,
  portal,
  className,
  onReportCreate,
  onReportEdit,
  onReportDelete,
  onReportSchedule,
  onDashboardUpdate
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<ReportCategory | 'all'>('all');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [schedulerOpen, setSchedulerOpen] = useState<string | null>(null);

  // Filter reports based on search and category
  const filteredReports = useMemo(() => {
    return reports.filter(report => {
      const matchesSearch = !searchTerm ||
        report.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        report.description?.toLowerCase().includes(searchTerm.toLowerCase());

      const matchesCategory = selectedCategory === 'all' || report.category === selectedCategory;
      const matchesPortal = report.portal === portal || report.permissions.portalAccess.includes(portal);

      return matchesSearch && matchesCategory && matchesPortal;
    });
  }, [reports, searchTerm, selectedCategory, portal]);

  // Get unique categories for filtering
  const categories = useMemo(() => {
    const cats = Array.from(new Set(reports.map(r => r.category)));
    return ['all', ...cats] as const;
  }, [reports]);

  const handleScheduleReport = useCallback((reportId: string, schedule: any) => {
    onReportSchedule?.(reportId, schedule);
    setSchedulerOpen(null);
  }, [onReportSchedule]);

  const handleReportAction = useCallback((action: string, reportId: string) => {
    switch (action) {
      case 'edit':
        onReportEdit?.(reportId);
        break;
      case 'delete':
        onReportDelete?.(reportId);
        break;
      case 'schedule':
        setSchedulerOpen(reportId);
        break;
      case 'duplicate':
        // TODO: Implement duplicate functionality
        break;
    }
  }, [onReportEdit, onReportDelete]);

  const formatCategoryLabel = (category: ReportCategory | 'all') => {
    if (category === 'all') return 'All Reports';
    return category.charAt(0).toUpperCase() + category.slice(1);
  };

  const getPortalColor = (portal: PortalVariant) => {
    const colors = {
      admin: 'bg-blue-50 text-blue-700 border-blue-200',
      customer: 'bg-green-50 text-green-700 border-green-200',
      reseller: 'bg-purple-50 text-purple-700 border-purple-200',
      technician: 'bg-orange-50 text-orange-700 border-orange-200',
      management: 'bg-red-50 text-red-700 border-red-200'
    };
    return colors[portal] || colors.admin;
  };

  return (
    <div className={cn("space-y-6", className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {dashboard?.title || `${portal.charAt(0).toUpperCase() + portal.slice(1)} Reports`}
          </h1>
          <p className="text-gray-600 mt-1">
            Generate and manage reports for your {portal} portal
          </p>
        </div>

        {onReportCreate && (
          <Button onClick={onReportCreate} className="flex items-center space-x-2">
            <Plus className="h-4 w-4" />
            <span>Create Report</span>
          </Button>
        )}
      </div>

      {/* Filters and Search */}
      <Card className="p-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
          <div className="flex items-center space-x-4">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <Input
                placeholder="Search reports..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 w-64"
              />
            </div>

            {/* Category Filter */}
            <div className="relative">
              <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value as ReportCategory | 'all')}
                className="pl-10 pr-8 py-2 border border-gray-300 rounded-md bg-white text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {categories.map(category => (
                  <option key={category} value={category}>
                    {formatCategoryLabel(category)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* View Mode Toggle */}
          <div className="flex items-center space-x-2">
            <Button
              variant={viewMode === 'grid' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setViewMode('grid')}
            >
              <Grid className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === 'list' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setViewMode('list')}
            >
              <List className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </Card>

      {/* Results Summary */}
      <div className="flex items-center justify-between text-sm text-gray-600">
        <span>
          {filteredReports.length} report{filteredReports.length !== 1 ? 's' : ''} found
        </span>
        {searchTerm && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSearchTerm('')}
            className="text-gray-500"
          >
            Clear search
          </Button>
        )}
      </div>

      {/* Reports Grid/List */}
      {filteredReports.length > 0 ? (
        <div
          className={cn(
            viewMode === 'grid'
              ? "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
              : "space-y-4"
          )}
        >
          {filteredReports.map((report) => (
            <Card
              key={report.id}
              className={cn(
                "overflow-hidden hover:shadow-md transition-shadow",
                viewMode === 'list' && "p-0"
              )}
            >
              {viewMode === 'grid' ? (
                // Grid View
                <div className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-900 mb-2">{report.title}</h3>
                      {report.description && (
                        <p className="text-sm text-gray-600 mb-3">{report.description}</p>
                      )}
                      <div className="flex items-center space-x-2 mb-3">
                        <span className={cn(
                          "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border",
                          getPortalColor(report.portal)
                        )}>
                          {report.category}
                        </span>
                        {report.schedule?.enabled && (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-50 text-green-700 border border-green-200">
                            Scheduled
                          </span>
                        )}
                      </div>
                    </div>

                    <ReportActionMenu
                      reportId={report.id}
                      onAction={handleReportAction}
                    />
                  </div>

                  <div className="space-y-3">
                    <UniversalReportGenerator
                      report={report}
                      variant={portal}
                      showHeader={false}
                      showExport={false}
                      className="min-h-[200px]"
                    />
                  </div>
                </div>
              ) : (
                // List View
                <div className="flex items-center p-4">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3">
                      <h3 className="font-semibold text-gray-900">{report.title}</h3>
                      <span className={cn(
                        "inline-flex items-center px-2 py-1 rounded text-xs font-medium border",
                        getPortalColor(report.portal)
                      )}>
                        {report.category}
                      </span>
                      {report.schedule?.enabled && (
                        <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-green-50 text-green-700 border border-green-200">
                          <Calendar className="h-3 w-3 mr-1" />
                          Scheduled
                        </span>
                      )}
                    </div>
                    {report.description && (
                      <p className="text-sm text-gray-600 mt-1">{report.description}</p>
                    )}
                    <div className="text-xs text-gray-500 mt-2">
                      Last updated: {report.updatedAt.toLocaleDateString()}
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    <Button variant="outline" size="sm">
                      <Download className="h-4 w-4" />
                    </Button>
                    <ReportActionMenu
                      reportId={report.id}
                      onAction={handleReportAction}
                    />
                  </div>
                </div>
              )}
            </Card>
          ))}
        </div>
      ) : (
        // Empty State
        <Card className="p-12 text-center">
          <div className="text-gray-400 mb-4">
            <Grid className="h-12 w-12 mx-auto" />
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No reports found</h3>
          <p className="text-gray-600 mb-6">
            {searchTerm
              ? `No reports match "${searchTerm}"`
              : `No reports available for the ${portal} portal`
            }
          </p>
          {onReportCreate && (
            <Button onClick={onReportCreate}>
              <Plus className="h-4 w-4 mr-2" />
              Create Your First Report
            </Button>
          )}
        </Card>
      )}

      {/* Report Scheduler Modal */}
      {schedulerOpen && (
        <ReportScheduler
          reportId={schedulerOpen}
          portal={portal}
          onScheduleUpdate={(schedule) => handleScheduleReport(schedulerOpen, schedule)}
          onClose={() => setSchedulerOpen(null)}
          isOpen={!!schedulerOpen}
        />
      )}
    </div>
  );
};

// Report Action Menu Component
interface ReportActionMenuProps {
  reportId: string;
  onAction: (action: string, reportId: string) => void;
}

const ReportActionMenu: React.FC<ReportActionMenuProps> = ({ reportId, onAction }) => {
  const [isOpen, setIsOpen] = useState(false);

  const actions = [
    { label: 'Edit Report', action: 'edit' },
    { label: 'Schedule Report', action: 'schedule' },
    { label: 'Duplicate Report', action: 'duplicate' },
    { label: 'Delete Report', action: 'delete', destructive: true }
  ];

  return (
    <div className="relative">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setIsOpen(!isOpen)}
        className="text-gray-400 hover:text-gray-600"
      >
        <MoreVertical className="h-4 w-4" />
      </Button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 top-8 z-20 w-48 bg-white rounded-md shadow-lg border border-gray-200 py-1">
            {actions.map(({ label, action, destructive }) => (
              <button
                key={action}
                onClick={() => {
                  onAction(action, reportId);
                  setIsOpen(false);
                }}
                className={cn(
                  "block w-full text-left px-4 py-2 text-sm hover:bg-gray-50",
                  destructive ? "text-red-600 hover:bg-red-50" : "text-gray-700"
                )}
              >
                {label}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
};
