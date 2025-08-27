'use client';

import React, { useState, useEffect } from 'react';
import {
  WifiIcon,
  SignalIcon,
  SignalSlashIcon,
  BellIcon,
  UsersIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon
} from '@heroicons/react/24/outline';
import { useWebSocket, useRealtimeData, WebSocketEventType, ConnectionState } from '@/lib/websocket-client';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

interface RealtimeMetric {
  name: string;
  value: number | string;
  change: number;
  trend: 'up' | 'down' | 'stable';
  lastUpdated: string;
}

interface SystemAlert {
  id: string;
  type: 'info' | 'warning' | 'error' | 'success';
  title: string;
  message: string;
  timestamp: string;
  acknowledged: boolean;
}

interface UserActivity {
  userId: string;
  userName: string;
  action: string;
  timestamp: string;
  metadata?: any;
}

export function RealtimeDashboard() {
  const { connectionState, stats, connect, disconnect, isConnected } = useWebSocket(true);
  const [notifications, setNotifications] = useState<SystemAlert[]>([]);
  const [activities, setActivities] = useState<UserActivity[]>([]);

  // Real-time data subscriptions
  const { data: metrics } = useRealtimeData<RealtimeMetric[]>(WebSocketEventType.METRICS_UPDATED, []);
  const { data: systemAlert } = useRealtimeData<SystemAlert>(WebSocketEventType.SYSTEM_ALERT);
  const { data: userActivity } = useRealtimeData<UserActivity>(WebSocketEventType.ACTIVITY_LOG);

  // Handle new alerts
  useEffect(() => {
    if (systemAlert) {
      setNotifications(prev => [systemAlert, ...prev.slice(0, 9)]); // Keep last 10
    }
  }, [systemAlert]);

  // Handle new activities
  useEffect(() => {
    if (userActivity) {
      setActivities(prev => [userActivity, ...prev.slice(0, 19)]); // Keep last 20
    }
  }, [userActivity]);

  const acknowledgeAlert = (alertId: string) => {
    setNotifications(prev => 
      prev.map(alert => 
        alert.id === alertId ? { ...alert, acknowledged: true } : alert
      )
    );
  };

  const getConnectionIcon = () => {
    switch (connectionState) {
      case ConnectionState.CONNECTED:
        return <WifiIcon className="h-5 w-5 text-green-500" />;
      case ConnectionState.CONNECTING:
      case ConnectionState.RECONNECTING:
        return <SignalIcon className="h-5 w-5 text-yellow-500 animate-pulse" />;
      default:
        return <SignalSlashIcon className="h-5 w-5 text-red-500" />;
    }
  };

  const getConnectionStatusText = () => {
    switch (connectionState) {
      case ConnectionState.CONNECTED:
        return 'Connected';
      case ConnectionState.CONNECTING:
        return 'Connecting...';
      case ConnectionState.RECONNECTING:
        return `Reconnecting... (${stats?.reconnectAttempts || 0})`;
      case ConnectionState.DISCONNECTED:
        return 'Disconnected';
      default:
        return 'Error';
    }
  };

  const formatTrend = (change: number) => {
    const prefix = change > 0 ? '+' : '';
    return `${prefix}${change.toFixed(1)}%`;
  };

  const getTrendIcon = (trend: 'up' | 'down' | 'stable') => {
    switch (trend) {
      case 'up':
        return '↗️';
      case 'down':
        return '↘️';
      default:
        return '→';
    }
  };

  return (
    <div className="space-y-6">
      {/* Connection Status Header */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {getConnectionIcon()}
            <div>
              <h3 className="text-sm font-medium text-gray-900">Real-time Connection</h3>
              <p className="text-sm text-gray-500">{getConnectionStatusText()}</p>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            {stats && (
              <div className="text-xs text-gray-500">
                <span>Subscriptions: {stats.activeSubscriptions}</span>
                {stats.queuedMessages > 0 && (
                  <span className="ml-2 text-yellow-600">
                    Queued: {stats.queuedMessages}
                  </span>
                )}
              </div>
            )}
            
            <div className="flex space-x-2">
              <button
                onClick={connect}
                disabled={isConnected}
                className="px-3 py-1 text-xs bg-green-100 text-green-700 rounded-md hover:bg-green-200 disabled:opacity-50"
              >
                Connect
              </button>
              <button
                onClick={disconnect}
                disabled={!isConnected}
                className="px-3 py-1 text-xs bg-red-100 text-red-700 rounded-md hover:bg-red-200 disabled:opacity-50"
              >
                Disconnect
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Real-time Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {metrics && metrics.length > 0 ? (
          metrics.map((metric, index) => (
            <div key={index} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">{metric.name}</p>
                  <p className="text-2xl font-bold text-gray-900">{metric.value}</p>
                </div>
                <div className="text-right">
                  <span className="text-2xl">{getTrendIcon(metric.trend)}</span>
                </div>
              </div>
              
              <div className="mt-2 flex items-center justify-between text-xs">
                <span className={`font-medium ${
                  metric.change > 0 ? 'text-green-600' : 
                  metric.change < 0 ? 'text-red-600' : 'text-gray-500'
                }`}>
                  {formatTrend(metric.change)}
                </span>
                <span className="text-gray-500">
                  {new Date(metric.lastUpdated).toLocaleTimeString()}
                </span>
              </div>
            </div>
          ))
        ) : (
          <div className="col-span-full bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
            {isConnected ? (
              <>
                <LoadingSpinner size="large" />
                <p className="mt-4 text-gray-500">Waiting for real-time metrics...</p>
              </>
            ) : (
              <>
                <SignalSlashIcon className="mx-auto h-12 w-12 text-gray-400" />
                <p className="mt-4 text-gray-500">Connect to view real-time metrics</p>
              </>
            )}
          </div>
        )}
      </div>

      {/* Alerts and Activities Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* System Alerts */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-medium text-gray-900 flex items-center">
                <BellIcon className="h-5 w-5 mr-2" />
                System Alerts
              </h3>
              <span className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded-full">
                {notifications.filter(n => !n.acknowledged).length} unread
              </span>
            </div>
          </div>

          <div className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
            {notifications.length > 0 ? (
              notifications.map((alert) => (
                <div
                  key={alert.id}
                  className={`p-4 ${!alert.acknowledged ? 'bg-blue-50' : 'bg-white'} hover:bg-gray-50`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start space-x-3">
                      <div className={`mt-1 ${
                        alert.type === 'error' ? 'text-red-500' :
                        alert.type === 'warning' ? 'text-yellow-500' :
                        alert.type === 'success' ? 'text-green-500' : 'text-blue-500'
                      }`}>
                        {alert.type === 'error' ? <ExclamationTriangleIcon className="h-5 w-5" /> :
                         alert.type === 'success' ? <CheckCircleIcon className="h-5 w-5" /> :
                         <BellIcon className="h-5 w-5" />}
                      </div>
                      
                      <div className="flex-1">
                        <h4 className="text-sm font-medium text-gray-900">{alert.title}</h4>
                        <p className="text-sm text-gray-600 mt-1">{alert.message}</p>
                        <p className="text-xs text-gray-500 mt-2">
                          {new Date(alert.timestamp).toLocaleString()}
                        </p>
                      </div>
                    </div>

                    {!alert.acknowledged && (
                      <button
                        onClick={() => acknowledgeAlert(alert.id)}
                        className="text-xs text-blue-600 hover:text-blue-800"
                      >
                        Acknowledge
                      </button>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="p-8 text-center">
                <BellIcon className="mx-auto h-8 w-8 text-gray-400" />
                <p className="mt-2 text-sm text-gray-500">No alerts</p>
              </div>
            )}
          </div>
        </div>

        {/* User Activity Feed */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900 flex items-center">
              <UsersIcon className="h-5 w-5 mr-2" />
              Live Activity Feed
            </h3>
          </div>

          <div className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
            {activities.length > 0 ? (
              activities.map((activity, index) => (
                <div key={index} className="p-4 hover:bg-gray-50">
                  <div className="flex items-center space-x-3">
                    <div className="flex-shrink-0">
                      <div className="h-8 w-8 bg-blue-100 rounded-full flex items-center justify-center">
                        <span className="text-xs font-medium text-blue-600">
                          {activity.userName.charAt(0).toUpperCase()}
                        </span>
                      </div>
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900">
                        {activity.userName}
                      </p>
                      <p className="text-sm text-gray-600">
                        {activity.action}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {new Date(activity.timestamp).toLocaleString()}
                      </p>
                    </div>

                    <div className="flex-shrink-0">
                      <span className="inline-block h-2 w-2 bg-green-400 rounded-full animate-pulse"></span>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="p-8 text-center">
                <ChartBarIcon className="mx-auto h-8 w-8 text-gray-400" />
                <p className="mt-2 text-sm text-gray-500">No recent activity</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Connection Statistics */}
      {stats && isConnected && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Connection Statistics</h3>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-blue-600">{stats.activeSubscriptions}</p>
              <p className="text-sm text-gray-500">Active Subscriptions</p>
            </div>
            
            <div className="text-center">
              <p className="text-2xl font-bold text-green-600">{stats.reconnectAttempts}</p>
              <p className="text-sm text-gray-500">Reconnect Attempts</p>
            </div>
            
            <div className="text-center">
              <p className="text-2xl font-bold text-yellow-600">{stats.queuedMessages}</p>
              <p className="text-sm text-gray-500">Queued Messages</p>
            </div>
            
            <div className="text-center">
              <p className="text-2xl font-bold text-purple-600">
                {connectionState === ConnectionState.CONNECTED ? 'Online' : 'Offline'}
              </p>
              <p className="text-sm text-gray-500">Status</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}