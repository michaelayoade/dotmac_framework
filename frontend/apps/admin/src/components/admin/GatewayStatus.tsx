/**
 * API Gateway Status Component
 * Displays real-time status of backend services and routing health
 */

import React, { useState, useEffect } from 'react';
import { useApiGateway } from '../../hooks/useApiGateway';
import { monitoring } from '../../lib/monitoring';

interface ServiceStatusProps {
  name: string;
  isHealthy: boolean;
  responseTime: number;
  failureCount: number;
  circuitBreakerOpen: boolean;
  lastCheck: number;
}

const ServiceStatus: React.FC<ServiceStatusProps> = ({
  name,
  isHealthy,
  responseTime,
  failureCount,
  circuitBreakerOpen,
  lastCheck,
}) => {
  const getStatusColor = () => {
    if (circuitBreakerOpen) return 'bg-red-500';
    if (!isHealthy) return 'bg-orange-500';
    if (responseTime > 1000) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const getStatusText = () => {
    if (circuitBreakerOpen) return 'Circuit Breaker Open';
    if (!isHealthy) return 'Unhealthy';
    if (responseTime > 1000) return 'Slow Response';
    return 'Healthy';
  };

  const formatResponseTime = (time: number) => {
    if (time < 1000) return `${time}ms`;
    return `${(time / 1000).toFixed(2)}s`;
  };

  const formatLastCheck = (timestamp: number) => {
    const diff = Date.now() - timestamp;
    if (diff < 60000) return `${Math.floor(diff / 1000)}s ago`;
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    return `${Math.floor(diff / 3600000)}h ago`;
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-900">{name}</h3>
        <div className="flex items-center">
          <div className={`w-3 h-3 rounded-full ${getStatusColor()} mr-2`} />
          <span className="text-sm text-gray-600">{getStatusText()}</span>
        </div>
      </div>
      
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-gray-500">Response Time:</span>
          <span className="ml-2 font-medium">
            {responseTime > 0 ? formatResponseTime(responseTime) : 'N/A'}
          </span>
        </div>
        <div>
          <span className="text-gray-500">Failures:</span>
          <span className="ml-2 font-medium">{failureCount}</span>
        </div>
        <div className="col-span-2">
          <span className="text-gray-500">Last Check:</span>
          <span className="ml-2 font-medium">
            {lastCheck > 0 ? formatLastCheck(lastCheck) : 'Never'}
          </span>
        </div>
      </div>
    </div>
  );
};

const GatewayStatus: React.FC = () => {
  const { services, isHealthy, getStatus } = useApiGateway();
  const [detailedStatus, setDetailedStatus] = useState<any>(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    const updateStatus = () => {
      const status = getStatus();
      setDetailedStatus(status);
    };

    updateStatus();
    const interval = setInterval(updateStatus, 5000); // Update every 5 seconds

    return () => clearInterval(interval);
  }, [getStatus]);

  const handleRefresh = async () => {
    setRefreshing(true);
    
    monitoring.recordInteraction({
      event: 'gateway_status_refresh',
      target: 'gateway_dashboard',
    });

    try {
      // Force a refresh of the status
      const status = getStatus();
      setDetailedStatus(status);
      
      // Small delay to show the refresh state
      await new Promise(resolve => setTimeout(resolve, 500));
    } finally {
      setRefreshing(false);
    }
  };

  if (!detailedStatus) {
    return (
      <div className="p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded mb-4"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="bg-gray-200 h-32 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  const overallHealthPercentage = detailedStatus.totalServices > 0 
    ? Math.round((detailedStatus.healthyServices / detailedStatus.totalServices) * 100)
    : 0;

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">API Gateway Status</h2>
          <p className="text-gray-600 mt-1">
            Monitor backend services and routing health
          </p>
        </div>
        
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
        >
          <svg 
            className={`-ml-1 mr-2 h-4 w-4 ${refreshing ? 'animate-spin' : ''}`}
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={2} 
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" 
            />
          </svg>
          {refreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {/* Overall Status */}
      <div className="bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg p-6 text-white mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold mb-2">Overall System Health</h3>
            <div className="flex items-center">
              <div className={`w-4 h-4 rounded-full mr-3 ${isHealthy ? 'bg-green-400' : 'bg-red-400'}`} />
              <span className="text-2xl font-bold">{overallHealthPercentage}%</span>
            </div>
            <p className="text-blue-100 mt-1">
              {detailedStatus.healthyServices} of {detailedStatus.totalServices} services healthy
            </p>
          </div>
          
          <div className="text-right">
            <div className="text-3xl font-bold">{detailedStatus.totalRequests}</div>
            <div className="text-blue-100">Total Requests</div>
          </div>
        </div>
      </div>

      {/* Service Status Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
        {services.map((service: any) => (
          <ServiceStatus
            key={service.name}
            name={service.name}
            isHealthy={service.isHealthy}
            responseTime={service.responseTime}
            failureCount={service.failureCount}
            circuitBreakerOpen={service.circuitBreakerOpen}
            lastCheck={service.lastCheck}
          />
        ))}
      </div>

      {/* System Alerts */}
      {!isHealthy && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center">
            <svg className="w-5 h-5 text-red-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <h4 className="font-semibold text-red-800">System Health Alert</h4>
          </div>
          <p className="text-red-700 mt-2">
            One or more backend services are experiencing issues. 
            API requests may be slower or fail. Check individual service status above.
          </p>
        </div>
      )}

      {/* Performance Metrics */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="font-semibold text-gray-900 mb-4">Performance Metrics</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">
              {services.reduce((avg, s) => avg + s.responseTime, 0) / services.length || 0}ms
            </div>
            <div className="text-gray-600">Average Response Time</div>
          </div>
          
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">
              {services.filter(s => s.isHealthy).length}
            </div>
            <div className="text-gray-600">Healthy Services</div>
          </div>
          
          <div className="text-center">
            <div className="text-2xl font-bold text-red-600">
              {services.filter(s => s.circuitBreakerOpen).length}
            </div>
            <div className="text-gray-600">Circuit Breakers Open</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GatewayStatus;