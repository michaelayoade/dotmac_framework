/**
 * Usage Charts Section - Decomposed from CustomerDashboard
 */
import { LinearProgress } from '../../ui/ProgressIndicator';
import { TrendingUp, Download, Upload, Calendar } from 'lucide-react';
import React, { useState } from 'react';

interface UsageData {
  date: string;
  download: number;
  upload: number;
  total: number;
}

interface UsageChartsSectionProps {
  currentUsage: {
    download: number;
    upload: number;
    total: number;
    limit: number;
  };
  historicalData: UsageData[];
  billingPeriod: {
    start: string;
    end: string;
    daysRemaining: number;
  };
  onViewDetailedUsage?: () => void;
  className?: string;
}

export function UsageChartsSection({
  currentUsage,
  historicalData,
  billingPeriod,
  onViewDetailedUsage,
  className = ''
}: UsageChartsSectionProps) {
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('30d');
  
  const usagePercentage = (currentUsage.total / currentUsage.limit) * 100;
  const downloadPercentage = (currentUsage.download / currentUsage.limit) * 100;
  const uploadPercentage = (currentUsage.upload / currentUsage.limit) * 100;

  const getUsageColor = (percentage: number) => {
    if (percentage >= 90) return 'red';
    if (percentage >= 75) return 'yellow';
    return 'blue';
  };

  const getFilteredData = () => {
    const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90;
    return historicalData.slice(-days);
  };

  return (
    <div className={`bg-white border border-gray-200 rounded-lg ${className}`}>
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <TrendingUp className="h-5 w-5 text-blue-600 mr-2" />
            <h3 className="font-semibold text-gray-900">Usage Overview</h3>
          </div>
          <div className="flex items-center space-x-3">
            {/* Time Range Selector */}
            <div className="flex space-x-1 bg-gray-100 rounded-lg p-1">
              {(['7d', '30d', '90d'] as const).map((range) => (
                <button
                  key={range}
                  onClick={() => setTimeRange(range)}
                  className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                    timeRange === range
                      ? 'bg-white text-blue-600 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  {range.toUpperCase()}
                </button>
              ))}
            </div>
            {onViewDetailedUsage && (
              <button
                onClick={onViewDetailedUsage}
                className="text-sm font-medium text-blue-600 hover:text-blue-500"
              >
                View Details
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="p-6">
        {/* Current Period Summary */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {/* Total Usage */}
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-600">Total Usage</span>
              <Calendar className="h-4 w-4 text-gray-400" />
            </div>
            <div className="text-2xl font-bold text-gray-900 mb-2">
              {currentUsage.total.toFixed(1)} GB
            </div>
            <LinearProgress
              value={currentUsage.total}
              max={currentUsage.limit}
              color={getUsageColor(usagePercentage)}
              size="md"
              showPercentage={false}
            />
            <div className="flex justify-between items-center mt-2">
              <span className="text-xs text-gray-500">
                {currentUsage.limit} GB limit
              </span>
              <span className="text-xs text-gray-500">
                {billingPeriod.daysRemaining} days remaining
              </span>
            </div>
          </div>

          {/* Download */}
          <div className="bg-blue-50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-blue-700">Download</span>
              <Download className="h-4 w-4 text-blue-600" />
            </div>
            <div className="text-2xl font-bold text-blue-900 mb-2">
              {currentUsage.download.toFixed(1)} GB
            </div>
            <LinearProgress
              value={currentUsage.download}
              max={currentUsage.limit}
              color="blue"
              size="sm"
              showPercentage={false}
            />
            <p className="text-xs text-blue-600 mt-2">
              {downloadPercentage.toFixed(1)}% of limit
            </p>
          </div>

          {/* Upload */}
          <div className="bg-green-50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-green-700">Upload</span>
              <Upload className="h-4 w-4 text-green-600" />
            </div>
            <div className="text-2xl font-bold text-green-900 mb-2">
              {currentUsage.upload.toFixed(1)} GB
            </div>
            <LinearProgress
              value={currentUsage.upload}
              max={currentUsage.limit}
              color="green"
              size="sm"
              showPercentage={false}
            />
            <p className="text-xs text-green-600 mt-2">
              {uploadPercentage.toFixed(1)}% of limit
            </p>
          </div>
        </div>

        {/* Usage Chart Placeholder */}
        <div className="bg-gray-50 rounded-lg p-6">
          <h4 className="font-medium text-gray-900 mb-4">
            Daily Usage - Last {timeRange.toUpperCase()}
          </h4>
          <div className="h-48 flex items-center justify-center text-gray-500">
            {/* This would be replaced with an actual chart component */}
            <div className="text-center">
              <TrendingUp className="h-8 w-8 mx-auto mb-2 text-gray-400" />
              <p className="text-sm">Usage chart would appear here</p>
              <p className="text-xs text-gray-400 mt-1">
                Showing {getFilteredData().length} data points
              </p>
            </div>
          </div>
        </div>

        {/* Billing Period Info */}
        <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-blue-900">Current Billing Period</p>
              <p className="text-sm text-blue-700">
                {new Date(billingPeriod.start).toLocaleDateString()} - {new Date(billingPeriod.end).toLocaleDateString()}
              </p>
            </div>
            <div className="text-right">
              <p className="font-bold text-blue-900">{billingPeriod.daysRemaining}</p>
              <p className="text-sm text-blue-700">days remaining</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}