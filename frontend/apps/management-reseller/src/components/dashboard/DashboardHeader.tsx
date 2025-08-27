/**
 * Dashboard Header Component
 * Extracted header section with export and refresh functionality
 */

import React, { useState } from 'react';
import { Download, RefreshCw } from 'lucide-react';
import { ManagementUser } from '@/components/auth/ManagementAuthProvider';

interface DashboardHeaderProps {
  user: ManagementUser;
  onExport: (format: 'CSV' | 'XLSX' | 'PDF') => void;
  onRefresh: () => void;
  isRefreshing?: boolean;
}

export function DashboardHeader({ user, onExport, onRefresh, isRefreshing }: DashboardHeaderProps) {
  const [showExportMenu, setShowExportMenu] = useState(false);

  const handleExport = (format: 'CSV' | 'XLSX' | 'PDF') => {
    onExport(format);
    setShowExportMenu(false);
  };

  return (
    <div className="flex items-center justify-between">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">
          Channel Management Dashboard
        </h2>
        <p className="text-gray-600">
          Welcome back, {user?.name}. Here's your reseller network overview.
        </p>
      </div>

      <div className="flex items-center space-x-3">
        <ExportDropdown 
          isOpen={showExportMenu}
          onToggle={() => setShowExportMenu(!showExportMenu)}
          onExport={handleExport}
        />

        <RefreshButton 
          onClick={onRefresh}
          isRefreshing={isRefreshing}
        />
      </div>
    </div>
  );
}

function ExportDropdown({ 
  isOpen, 
  onToggle, 
  onExport 
}: { 
  isOpen: boolean; 
  onToggle: () => void; 
  onExport: (format: 'CSV' | 'XLSX' | 'PDF') => void;
}) {
  return (
    <div className="relative">
      <button
        onClick={onToggle}
        className="flex items-center px-3 py-2 rounded-lg text-sm font-medium bg-white border border-gray-200 hover:bg-gray-50 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        <Download className="h-4 w-4 mr-1" />
        Export
      </button>
      
      {isOpen && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 z-10" 
            onClick={onToggle}
            aria-hidden="true"
          />
          
          {/* Dropdown Menu */}
          <div className="absolute right-0 mt-2 w-32 bg-white rounded-lg shadow-lg border border-gray-200 z-20">
            <div className="py-1" role="menu">
              <ExportButton 
                format="CSV" 
                onClick={() => onExport('CSV')}
              />
              <ExportButton 
                format="XLSX" 
                onClick={() => onExport('XLSX')}
                label="Excel"
              />
              <ExportButton 
                format="PDF" 
                onClick={() => onExport('PDF')}
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function ExportButton({ 
  format, 
  label, 
  onClick 
}: { 
  format: string; 
  label?: string; 
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left px-4 py-2 text-sm hover:bg-gray-50 focus:outline-none focus:bg-gray-50 transition-colors"
      role="menuitem"
    >
      {label || format}
    </button>
  );
}

function RefreshButton({ 
  onClick, 
  isRefreshing 
}: { 
  onClick: () => void; 
  isRefreshing?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={isRefreshing}
      className="flex items-center px-3 py-2 rounded-lg text-sm font-medium bg-white border border-gray-200 hover:bg-gray-50 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
      title="Refresh Dashboard"
    >
      <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
      <span className="sr-only">Refresh</span>
    </button>
  );
}