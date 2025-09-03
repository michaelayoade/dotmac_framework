/**
 * Conflict Resolution Component
 * Provides UI for resolving synchronization conflicts between local and remote data
 */

'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  AlertTriangle,
  Check,
  X,
  ArrowRight,
  Clock,
  Server,
  Smartphone,
  GitMerge,
  Eye,
  EyeOff,
} from 'lucide-react';
import { useRealtimeSync } from '../../hooks/useRealtimeSync';
import { SyncOperation } from '../../lib/realtime/sync-manager';

interface ConflictResolverProps {
  websocketUrl: string;
  isOpen: boolean;
  onClose: () => void;
  onResolved?: (resolvedCount: number) => void;
}

interface ConflictItem extends SyncOperation {
  serverData?: any;
  clientData?: any;
  preview?: {
    title: string;
    description: string;
    changes: string[];
  };
}

export function ConflictResolver({
  websocketUrl,
  isOpen,
  onClose,
  onResolved,
}: ConflictResolverProps) {
  const sync = useRealtimeSync({ websocketUrl, autoConnect: false });
  const [conflicts, setConflicts] = useState<ConflictItem[]>([]);
  const [selectedConflict, setSelectedConflict] = useState<ConflictItem | null>(null);
  const [showDiff, setShowDiff] = useState(false);
  const [isResolving, setIsResolving] = useState(false);
  const [resolvedCount, setResolvedCount] = useState(0);

  useEffect(() => {
    if (isOpen) {
      loadConflicts();
    }
  }, [isOpen, sync.conflicts]);

  const loadConflicts = async () => {
    try {
      const conflictOperations = await sync.getConflicts();
      const enrichedConflicts = conflictOperations.map((conflict) => ({
        ...conflict,
        preview: generatePreview(conflict),
      }));
      setConflicts(enrichedConflicts);

      if (enrichedConflicts.length > 0 && !selectedConflict) {
        setSelectedConflict(enrichedConflicts[0]);
      }
    } catch (error) {
      console.error('Failed to load conflicts:', error);
    }
  };

  const generatePreview = (conflict: SyncOperation): ConflictItem['preview'] => {
    const entityName = conflict.entity.toLowerCase().replace('_', ' ');

    switch (conflict.entity) {
      case 'WORK_ORDER':
        return {
          title: `Work Order #${conflict.data.id || 'New'}`,
          description: conflict.data.description || conflict.data.title || 'Work order details',
          changes: ['Status', 'Priority', 'Assigned technician', 'Completion notes'],
        };
      case 'CUSTOMER':
        return {
          title: `Customer: ${conflict.data.name || conflict.data.company || 'Unknown'}`,
          description: conflict.data.email || conflict.data.phone || 'Customer information',
          changes: ['Contact details', 'Service address', 'Billing information'],
        };
      case 'INVENTORY':
        return {
          title: `${conflict.data.name || conflict.data.partNumber || 'Inventory Item'}`,
          description: conflict.data.description || 'Inventory details',
          changes: ['Stock quantity', 'Location', 'Status', 'Last updated'],
        };
      default:
        return {
          title: `${entityName} conflict`,
          description: 'Data synchronization conflict',
          changes: ['Multiple fields'],
        };
    }
  };

  const resolveConflict = async (
    conflictId: string,
    strategy: 'CLIENT_WINS' | 'SERVER_WINS' | 'MERGE'
  ) => {
    setIsResolving(true);

    try {
      const success = await sync.resolveConflict(conflictId, strategy);

      if (success) {
        // Remove resolved conflict from list
        setConflicts((prev) => prev.filter((c) => c.id !== conflictId));
        setResolvedCount((prev) => prev + 1);

        // Select next conflict if available
        const remainingConflicts = conflicts.filter((c) => c.id !== conflictId);
        if (remainingConflicts.length > 0) {
          setSelectedConflict(remainingConflicts[0]);
        } else {
          setSelectedConflict(null);
        }
      }
    } catch (error) {
      console.error('Failed to resolve conflict:', error);
    } finally {
      setIsResolving(false);
    }
  };

  const resolveAllConflicts = async (strategy: 'CLIENT_WINS' | 'SERVER_WINS' | 'MERGE') => {
    setIsResolving(true);
    let resolved = 0;

    try {
      for (const conflict of conflicts) {
        const success = await sync.resolveConflict(conflict.id, strategy);
        if (success) resolved++;
      }

      setResolvedCount((prev) => prev + resolved);
      setConflicts([]);
      setSelectedConflict(null);
    } catch (error) {
      console.error('Failed to resolve all conflicts:', error);
    } finally {
      setIsResolving(false);
    }
  };

  const getStrategyIcon = (strategy: string) => {
    switch (strategy) {
      case 'CLIENT_WINS':
        return <Smartphone className='w-4 h-4' />;
      case 'SERVER_WINS':
        return <Server className='w-4 h-4' />;
      case 'MERGE':
        return <GitMerge className='w-4 h-4' />;
      default:
        return <AlertTriangle className='w-4 h-4' />;
    }
  };

  const getStrategyDescription = (strategy: string) => {
    switch (strategy) {
      case 'CLIENT_WINS':
        return 'Keep your local changes and overwrite server data';
      case 'SERVER_WINS':
        return 'Accept server changes and overwrite local data';
      case 'MERGE':
        return 'Combine both versions intelligently';
      default:
        return 'Manual resolution required';
    }
  };

  const handleClose = () => {
    if (resolvedCount > 0) {
      onResolved?.(resolvedCount);
    }
    setResolvedCount(0);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className='fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4'
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className='bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden'
        >
          {/* Header */}
          <div className='flex items-center justify-between p-4 border-b border-gray-200'>
            <div className='flex items-center space-x-2'>
              <AlertTriangle className='w-5 h-5 text-yellow-500' />
              <h2 className='text-lg font-semibold text-gray-900'>
                Resolve Conflicts ({conflicts.length})
              </h2>
            </div>
            <button
              onClick={handleClose}
              className='w-8 h-8 bg-gray-100 hover:bg-gray-200 rounded-full flex items-center justify-center text-gray-600'
            >
              <X className='w-4 h-4' />
            </button>
          </div>

          {conflicts.length === 0 ? (
            // No Conflicts
            <div className='p-8 text-center'>
              <Check className='w-16 h-16 text-green-500 mx-auto mb-4' />
              <h3 className='text-lg font-semibold text-gray-900 mb-2'>All Conflicts Resolved!</h3>
              <p className='text-gray-600 mb-4'>
                {resolvedCount > 0
                  ? `Successfully resolved ${resolvedCount} conflict${resolvedCount > 1 ? 's' : ''}.`
                  : 'No synchronization conflicts found.'}
              </p>
              <button
                onClick={handleClose}
                className='px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg'
              >
                Close
              </button>
            </div>
          ) : (
            <div className='flex h-[60vh]'>
              {/* Conflict List */}
              <div className='w-1/3 border-r border-gray-200 overflow-y-auto'>
                <div className='p-4 border-b border-gray-200'>
                  <h3 className='font-medium text-gray-900 mb-2'>Conflicts</h3>
                  <div className='flex space-x-2'>
                    <button
                      onClick={() => resolveAllConflicts('CLIENT_WINS')}
                      disabled={isResolving}
                      className='text-xs px-2 py-1 bg-blue-100 hover:bg-blue-200 text-blue-700 rounded'
                    >
                      All Local
                    </button>
                    <button
                      onClick={() => resolveAllConflicts('SERVER_WINS')}
                      disabled={isResolving}
                      className='text-xs px-2 py-1 bg-green-100 hover:bg-green-200 text-green-700 rounded'
                    >
                      All Remote
                    </button>
                    <button
                      onClick={() => resolveAllConflicts('MERGE')}
                      disabled={isResolving}
                      className='text-xs px-2 py-1 bg-purple-100 hover:bg-purple-200 text-purple-700 rounded'
                    >
                      Auto Merge
                    </button>
                  </div>
                </div>

                <div className='space-y-1'>
                  {conflicts.map((conflict) => (
                    <button
                      key={conflict.id}
                      onClick={() => setSelectedConflict(conflict)}
                      className={`w-full p-3 text-left hover:bg-gray-50 border-l-4 transition-colors ${
                        selectedConflict?.id === conflict.id
                          ? 'bg-primary-50 border-primary-500'
                          : 'border-transparent'
                      }`}
                    >
                      <div className='flex items-start justify-between'>
                        <div className='flex-1 min-w-0'>
                          <p className='text-sm font-medium text-gray-900 truncate'>
                            {conflict.preview?.title}
                          </p>
                          <p className='text-xs text-gray-600 mt-1 truncate'>
                            {conflict.preview?.description}
                          </p>
                          <div className='flex items-center mt-2 space-x-2'>
                            <Clock className='w-3 h-3 text-gray-400' />
                            <span className='text-xs text-gray-500'>
                              {new Date(conflict.timestamp).toLocaleTimeString()}
                            </span>
                          </div>
                        </div>
                        <div className='flex-shrink-0 ml-2'>
                          <span className='text-xs font-medium text-yellow-600 bg-yellow-100 px-2 py-1 rounded'>
                            {conflict.type}
                          </span>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Conflict Details */}
              <div className='flex-1 flex flex-col'>
                {selectedConflict ? (
                  <>
                    {/* Conflict Info */}
                    <div className='p-4 border-b border-gray-200'>
                      <div className='flex items-center justify-between mb-3'>
                        <h3 className='font-semibold text-gray-900'>
                          {selectedConflict.preview?.title}
                        </h3>
                        <button
                          onClick={() => setShowDiff(!showDiff)}
                          className='flex items-center space-x-1 text-sm text-gray-600 hover:text-gray-800'
                        >
                          {showDiff ? <EyeOff className='w-4 h-4' /> : <Eye className='w-4 h-4' />}
                          <span>{showDiff ? 'Hide' : 'Show'} Details</span>
                        </button>
                      </div>

                      <div className='text-sm text-gray-600 mb-3'>
                        <p className='mb-1'>{selectedConflict.preview?.description}</p>
                        <p>Conflicting fields: {selectedConflict.preview?.changes.join(', ')}</p>
                      </div>

                      {showDiff && (
                        <div className='mt-4 p-3 bg-gray-50 rounded-lg'>
                          <h4 className='text-sm font-medium text-gray-900 mb-2'>Data Preview</h4>
                          <div className='grid grid-cols-2 gap-4 text-xs'>
                            <div>
                              <p className='font-medium text-blue-600 mb-1 flex items-center'>
                                <Smartphone className='w-3 h-3 mr-1' />
                                Local Version
                              </p>
                              <pre className='bg-blue-50 p-2 rounded text-blue-800 overflow-auto max-h-24'>
                                {JSON.stringify(selectedConflict.data, null, 2)}
                              </pre>
                            </div>
                            <div>
                              <p className='font-medium text-green-600 mb-1 flex items-center'>
                                <Server className='w-3 h-3 mr-1' />
                                Server Version
                              </p>
                              <pre className='bg-green-50 p-2 rounded text-green-800 overflow-auto max-h-24'>
                                {JSON.stringify(selectedConflict.serverData || {}, null, 2)}
                              </pre>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Resolution Options */}
                    <div className='p-4 space-y-3'>
                      <h4 className='font-medium text-gray-900'>Choose Resolution Strategy</h4>

                      <div className='space-y-2'>
                        {/* Keep Local */}
                        <button
                          onClick={() => resolveConflict(selectedConflict.id, 'CLIENT_WINS')}
                          disabled={isResolving}
                          className='w-full p-3 border-2 border-blue-200 hover:border-blue-300 hover:bg-blue-50 rounded-lg text-left transition-colors disabled:opacity-50'
                        >
                          <div className='flex items-start space-x-3'>
                            {getStrategyIcon('CLIENT_WINS')}
                            <div className='flex-1'>
                              <p className='font-medium text-gray-900'>Keep Local Changes</p>
                              <p className='text-sm text-gray-600'>
                                {getStrategyDescription('CLIENT_WINS')}
                              </p>
                            </div>
                            <ArrowRight className='w-4 h-4 text-blue-500' />
                          </div>
                        </button>

                        {/* Accept Server */}
                        <button
                          onClick={() => resolveConflict(selectedConflict.id, 'SERVER_WINS')}
                          disabled={isResolving}
                          className='w-full p-3 border-2 border-green-200 hover:border-green-300 hover:bg-green-50 rounded-lg text-left transition-colors disabled:opacity-50'
                        >
                          <div className='flex items-start space-x-3'>
                            {getStrategyIcon('SERVER_WINS')}
                            <div className='flex-1'>
                              <p className='font-medium text-gray-900'>Accept Server Changes</p>
                              <p className='text-sm text-gray-600'>
                                {getStrategyDescription('SERVER_WINS')}
                              </p>
                            </div>
                            <ArrowRight className='w-4 h-4 text-green-500' />
                          </div>
                        </button>

                        {/* Smart Merge */}
                        <button
                          onClick={() => resolveConflict(selectedConflict.id, 'MERGE')}
                          disabled={isResolving}
                          className='w-full p-3 border-2 border-purple-200 hover:border-purple-300 hover:bg-purple-50 rounded-lg text-left transition-colors disabled:opacity-50'
                        >
                          <div className='flex items-start space-x-3'>
                            {getStrategyIcon('MERGE')}
                            <div className='flex-1'>
                              <p className='font-medium text-gray-900'>Smart Merge</p>
                              <p className='text-sm text-gray-600'>
                                {getStrategyDescription('MERGE')}
                              </p>
                            </div>
                            <ArrowRight className='w-4 h-4 text-purple-500' />
                          </div>
                        </button>
                      </div>
                    </div>
                  </>
                ) : (
                  <div className='flex-1 flex items-center justify-center text-gray-500'>
                    <div className='text-center'>
                      <AlertTriangle className='w-12 h-12 mx-auto mb-3 text-gray-400' />
                      <p>Select a conflict to view details</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Loading Overlay */}
          {isResolving && (
            <div className='absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center'>
              <div className='text-center'>
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                  className='w-8 h-8 border-4 border-primary-200 border-t-primary-600 rounded-full mx-auto mb-2'
                />
                <p className='text-gray-600'>Resolving conflicts...</p>
              </div>
            </div>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
