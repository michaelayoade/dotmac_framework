/**
 * Sync Status Component
 * Displays real-time synchronization status and provides manual sync controls
 */

'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Wifi,
  WifiOff,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  Clock,
  Database,
  AlertCircle,
  Settings,
  X,
} from 'lucide-react';
import { useRealtimeSync } from '../../hooks/useRealtimeSync';

interface SyncStatusProps {
  websocketUrl: string;
  className?: string;
  showDetails?: boolean;
  onConflictResolve?: () => void;
}

export function SyncStatus({
  websocketUrl,
  className = '',
  showDetails = false,
  onConflictResolve,
}: SyncStatusProps) {
  const [showDetailPanel, setShowDetailPanel] = useState(showDetails);
  const sync = useRealtimeSync({ 
    websocketUrl,
    autoConnect: true,
  });

  const getStatusIcon = () => {
    if (sync.isInitializing) {
      return <RefreshCw className="w-4 h-4 animate-spin" />;
    }
    
    if (!sync.isConnected) {
      return <WifiOff className="w-4 h-4 text-red-500" />;
    }
    
    if (sync.conflicts > 0) {
      return <AlertTriangle className="w-4 h-4 text-yellow-500" />;
    }
    
    if (sync.pendingOperations > 0) {
      return <Clock className="w-4 h-4 text-blue-500" />;
    }
    
    return <CheckCircle className="w-4 h-4 text-green-500" />;
  };

  const getStatusText = () => {
    if (sync.isInitializing) {
      return 'Initializing...';
    }
    
    if (!sync.isConnected) {
      return 'Offline';
    }
    
    if (sync.conflicts > 0) {
      return `${sync.conflicts} conflict${sync.conflicts > 1 ? 's' : ''}`;
    }
    
    if (sync.pendingOperations > 0) {
      return `Syncing ${sync.pendingOperations}`;
    }
    
    return 'Synced';
  };

  const getStatusColor = () => {
    if (!sync.isConnected) return 'bg-red-100 text-red-700 border-red-200';
    if (sync.conflicts > 0) return 'bg-yellow-100 text-yellow-700 border-yellow-200';
    if (sync.pendingOperations > 0) return 'bg-blue-100 text-blue-700 border-blue-200';
    return 'bg-green-100 text-green-700 border-green-200';
  };

  const handleManualSync = async () => {
    if (!sync.isConnected) {
      await sync.connect();
    }
  };

  const handleViewConflicts = () => {
    setShowDetailPanel(true);
    onConflictResolve?.();
  };

  return (
    <>
      {/* Status Indicator */}
      <div className={`flex items-center space-x-2 ${className}`}>
        <button
          onClick={() => setShowDetailPanel(!showDetailPanel)}
          className={`
            flex items-center space-x-2 px-3 py-2 rounded-lg border text-sm font-medium
            transition-colors hover:bg-opacity-80
            ${getStatusColor()}
          `}
        >
          {getStatusIcon()}
          <span>{getStatusText()}</span>
          
          {!sync.isConnected && (
            <button
              onClick={handleManualSync}
              className="ml-2 p-1 hover:bg-white hover:bg-opacity-50 rounded"
              title="Retry connection"
            >
              <RefreshCw className="w-3 h-3" />
            </button>
          )}
        </button>

        {sync.conflicts > 0 && (
          <button
            onClick={handleViewConflicts}
            className="px-2 py-1 bg-yellow-500 hover:bg-yellow-600 text-white text-xs rounded-md font-medium"
          >
            Resolve
          </button>
        )}
      </div>

      {/* Detailed Status Panel */}
      <AnimatePresence>
        {showDetailPanel && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
          >
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              className="bg-white rounded-lg shadow-xl w-full max-w-md"
            >
              {/* Header */}
              <div className="flex items-center justify-between p-4 border-b border-gray-200">
                <div className="flex items-center space-x-2">
                  <Database className="w-5 h-5 text-gray-600" />
                  <h3 className="text-lg font-semibold text-gray-900">Sync Status</h3>
                </div>
                <button
                  onClick={() => setShowDetailPanel(false)}
                  className="w-8 h-8 bg-gray-100 hover:bg-gray-200 rounded-full flex items-center justify-center text-gray-600"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Status Details */}
              <div className="p-4 space-y-4">
                {/* Connection Status */}
                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center space-x-3">
                    {sync.isConnected ? (
                      <Wifi className="w-5 h-5 text-green-500" />
                    ) : (
                      <WifiOff className="w-5 h-5 text-red-500" />
                    )}
                    <div>
                      <p className="font-medium text-gray-900">Connection</p>
                      <p className="text-sm text-gray-600">{sync.connectionState}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-gray-600">
                      {sync.isConnected ? 'Connected' : 'Disconnected'}
                    </p>
                  </div>
                </div>

                {/* Pending Operations */}
                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center space-x-3">
                    <Clock className="w-5 h-5 text-blue-500" />
                    <div>
                      <p className="font-medium text-gray-900">Pending Sync</p>
                      <p className="text-sm text-gray-600">Operations waiting to sync</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-semibold text-blue-600">
                      {sync.pendingOperations}
                    </p>
                  </div>
                </div>

                {/* Conflicts */}
                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center space-x-3">
                    <AlertTriangle className="w-5 h-5 text-yellow-500" />
                    <div>
                      <p className="font-medium text-gray-900">Conflicts</p>
                      <p className="text-sm text-gray-600">Items needing resolution</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-semibold text-yellow-600">
                      {sync.conflicts}
                    </p>
                    {sync.conflicts > 0 && (
                      <button
                        onClick={handleViewConflicts}
                        className="text-xs text-yellow-600 hover:text-yellow-700 underline"
                      >
                        View Details
                      </button>
                    )}
                  </div>
                </div>

                {/* Last Sync */}
                {sync.lastSyncTime && (
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center space-x-3">
                      <CheckCircle className="w-5 h-5 text-green-500" />
                      <div>
                        <p className="font-medium text-gray-900">Last Sync</p>
                        <p className="text-sm text-gray-600">Most recent successful sync</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-gray-600">
                        {sync.lastSyncTime.toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                )}

                {/* Error Display */}
                {sync.error && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="p-3 bg-red-50 border border-red-200 rounded-lg"
                  >
                    <div className="flex items-start space-x-3">
                      <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                      <div className="flex-1">
                        <p className="font-medium text-red-800">Sync Error</p>
                        <p className="text-sm text-red-700 mt-1">{sync.error}</p>
                      </div>
                      <button
                        onClick={sync.clearError}
                        className="text-red-500 hover:text-red-700"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  </motion.div>
                )}
              </div>

              {/* Actions */}
              <div className="p-4 border-t border-gray-200">
                <div className="flex space-x-3">
                  <button
                    onClick={handleManualSync}
                    disabled={sync.isConnected && sync.isInitializing}
                    className="flex-1 flex items-center justify-center space-x-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
                  >
                    <RefreshCw className={`w-4 h-4 ${sync.isInitializing ? 'animate-spin' : ''}`} />
                    <span>
                      {sync.isConnected ? 'Force Sync' : 'Reconnect'}
                    </span>
                  </button>
                  
                  <button
                    onClick={() => setShowDetailPanel(false)}
                    className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
                  >
                    Close
                  </button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}