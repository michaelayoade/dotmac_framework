import React, { useState, useCallback } from 'react';
import { Button, Card } from '@dotmac/ui';
import {
  AlertTriangle,
  GitMerge,
  Users,
  Clock,
  Check,
  X,
  ChevronDown,
  ChevronUp,
  RotateCcw,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

import type {
  ConflictResolverProps,
  Conflict,
  ConflictResolutionStrategy,
  Operation,
} from '../types';

interface ConflictItemProps {
  conflict: Conflict;
  current_user_id: string;
  on_resolve?: (conflict_id: string, resolution: ConflictResolutionStrategy) => void;
}

const ConflictItem: React.FC<ConflictItemProps> = ({ conflict, current_user_id, on_resolve }) => {
  const [expanded, setExpanded] = useState(false);
  const [selectedResolution, setSelectedResolution] = useState<ConflictResolutionStrategy | null>(
    null
  );
  const [resolving, setResolving] = useState(false);

  const handleResolve = useCallback(
    async (strategy: ConflictResolutionStrategy) => {
      if (resolving) return;

      try {
        setResolving(true);
        await on_resolve?.(conflict.id, strategy);
      } catch (err) {
        console.error('Failed to resolve conflict:', err);
      } finally {
        setResolving(false);
        setSelectedResolution(null);
      }
    },
    [conflict.id, on_resolve, resolving]
  );

  const getOperationDescription = (operation: Operation): string => {
    switch (operation.type) {
      case 'insert':
        return `Insert "${operation.data.content?.substring(0, 50)}${operation.data.content && operation.data.content.length > 50 ? '...' : ''}" at position ${operation.data.position}`;
      case 'delete':
        return `Delete ${operation.data.length} characters at position ${operation.data.position}`;
      case 'replace':
        return `Replace "${operation.data.oldContent?.substring(0, 30)}..." with "${operation.data.newContent?.substring(0, 30)}..." at position ${operation.data.position}`;
      default:
        return `${operation.type} operation at position ${operation.data.position}`;
    }
  };

  const getAuthorName = (authorId: string): string => {
    // This would typically come from user data
    return authorId === current_user_id ? 'You' : authorId;
  };

  const resolutionStrategies = [
    {
      value: ConflictResolutionStrategy.LAST_WRITER_WINS,
      label: 'Keep Latest Changes',
      description: 'Accept the most recent changes and discard conflicting ones',
      icon: <Clock className='h-4 w-4' />,
    },
    {
      value: ConflictResolutionStrategy.FIRST_WRITER_WINS,
      label: 'Keep First Changes',
      description: 'Keep the first changes and discard later conflicting ones',
      icon: <Users className='h-4 w-4' />,
    },
    {
      value: ConflictResolutionStrategy.MERGE_CHANGES,
      label: 'Merge Changes',
      description: 'Attempt to automatically merge non-conflicting parts',
      icon: <GitMerge className='h-4 w-4' />,
    },
    {
      value: ConflictResolutionStrategy.MANUAL_RESOLUTION,
      label: 'Manual Resolution',
      description: 'Resolve the conflict manually by choosing specific changes',
      icon: <AlertTriangle className='h-4 w-4' />,
    },
  ];

  return (
    <div className='conflict-item border-l-4 border-red-400 bg-red-50 p-4'>
      {/* Conflict header */}
      <div className='flex items-start justify-between mb-4'>
        <div className='flex items-center gap-3'>
          <div className='w-8 h-8 bg-red-500 rounded-full flex items-center justify-center'>
            <AlertTriangle className='h-5 w-5 text-white' />
          </div>

          <div>
            <h4 className='font-medium text-red-800'>Editing Conflict Detected</h4>
            <p className='text-sm text-red-600'>
              {conflict.operations.length} conflicting operations from{' '}
              {new Set(conflict.operations.map((op) => op.author)).size} collaborators
            </p>
          </div>
        </div>

        <button
          onClick={() => setExpanded(!expanded)}
          className='text-red-600 hover:text-red-800 p-1 rounded'
        >
          {expanded ? <ChevronUp className='h-5 w-5' /> : <ChevronDown className='h-5 w-5' />}
        </button>
      </div>

      {/* Conflict summary */}
      <div className='mb-4'>
        <div className='grid grid-cols-2 gap-4 text-sm'>
          <div>
            <span className='font-medium text-red-700'>Original Operations:</span>
            <div className='mt-1 space-y-1'>
              {conflict.operations.slice(0, 2).map((operation, index) => (
                <div
                  key={index}
                  className='text-xs bg-white p-2 rounded border-l-2 border-blue-400'
                >
                  <div className='font-medium text-blue-700'>{getAuthorName(operation.author)}</div>
                  <div className='text-gray-600'>{getOperationDescription(operation)}</div>
                </div>
              ))}
              {conflict.operations.length > 2 && (
                <div className='text-xs text-red-600'>
                  +{conflict.operations.length - 2} more operations
                </div>
              )}
            </div>
          </div>

          <div>
            <span className='font-medium text-red-700'>Conflicting Operations:</span>
            <div className='mt-1 space-y-1'>
              {conflict.conflicting_operations.slice(0, 2).map((operation, index) => (
                <div
                  key={index}
                  className='text-xs bg-white p-2 rounded border-l-2 border-orange-400'
                >
                  <div className='font-medium text-orange-700'>
                    {getAuthorName(operation.author)}
                  </div>
                  <div className='text-gray-600'>{getOperationDescription(operation)}</div>
                </div>
              ))}
              {conflict.conflicting_operations.length > 2 && (
                <div className='text-xs text-red-600'>
                  +{conflict.conflicting_operations.length - 2} more operations
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Detailed view */}
      {expanded && (
        <div className='detailed-view border-t border-red-200 pt-4 mb-4'>
          <h5 className='font-medium text-red-800 mb-3'>All Conflicting Operations</h5>

          <div className='space-y-2'>
            <div className='text-sm font-medium text-blue-700'>Original Operations:</div>
            {conflict.operations.map((operation, index) => (
              <div key={index} className='bg-white p-3 rounded border-l-4 border-blue-400'>
                <div className='flex items-start justify-between'>
                  <div className='flex-1'>
                    <div className='flex items-center gap-2 mb-1'>
                      <span className='font-medium text-blue-700'>
                        {getAuthorName(operation.author)}
                      </span>
                      <span className='text-xs text-gray-500'>
                        {formatDistanceToNow(new Date(operation.timestamp), { addSuffix: true })}
                      </span>
                    </div>
                    <div className='text-sm text-gray-700'>
                      {getOperationDescription(operation)}
                    </div>
                  </div>
                  <div className='text-xs text-gray-500'>v{operation.version}</div>
                </div>
              </div>
            ))}

            <div className='text-sm font-medium text-orange-700 mt-4'>Conflicting Operations:</div>
            {conflict.conflicting_operations.map((operation, index) => (
              <div key={index} className='bg-white p-3 rounded border-l-4 border-orange-400'>
                <div className='flex items-start justify-between'>
                  <div className='flex-1'>
                    <div className='flex items-center gap-2 mb-1'>
                      <span className='font-medium text-orange-700'>
                        {getAuthorName(operation.author)}
                      </span>
                      <span className='text-xs text-gray-500'>
                        {formatDistanceToNow(new Date(operation.timestamp), { addSuffix: true })}
                      </span>
                    </div>
                    <div className='text-sm text-gray-700'>
                      {getOperationDescription(operation)}
                    </div>
                  </div>
                  <div className='text-xs text-gray-500'>v{operation.version}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Resolution strategies */}
      <div className='resolution-strategies'>
        <h5 className='font-medium text-red-800 mb-3'>Choose Resolution Strategy:</h5>

        <div className='grid grid-cols-1 gap-2 mb-4'>
          {resolutionStrategies.map((strategy) => (
            <button
              key={strategy.value}
              onClick={() => setSelectedResolution(strategy.value)}
              className={`text-left p-3 rounded-lg border-2 transition-all ${
                selectedResolution === strategy.value
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 bg-white hover:border-gray-300'
              }`}
            >
              <div className='flex items-start gap-3'>
                <div
                  className={`p-1 rounded ${
                    selectedResolution === strategy.value ? 'text-blue-600' : 'text-gray-500'
                  }`}
                >
                  {strategy.icon}
                </div>

                <div className='flex-1'>
                  <div
                    className={`font-medium ${
                      selectedResolution === strategy.value ? 'text-blue-700' : 'text-gray-700'
                    }`}
                  >
                    {strategy.label}
                  </div>
                  <div className='text-sm text-gray-600'>{strategy.description}</div>
                </div>
              </div>
            </button>
          ))}
        </div>

        {/* Resolution buttons */}
        <div className='flex items-center gap-3'>
          <Button
            onClick={() => selectedResolution && handleResolve(selectedResolution)}
            disabled={!selectedResolution || resolving}
            className='bg-blue-600 hover:bg-blue-700 text-white'
          >
            {resolving ? (
              <>
                <RotateCcw className='h-4 w-4 mr-2 animate-spin' />
                Resolving...
              </>
            ) : (
              <>
                <Check className='h-4 w-4 mr-2' />
                Resolve Conflict
              </>
            )}
          </Button>

          <div className='text-xs text-gray-600'>
            Select a resolution strategy to continue editing
          </div>
        </div>
      </div>
    </div>
  );
};

export const ConflictResolver: React.FC<ConflictResolverProps> = ({
  conflicts,
  document_id,
  current_user,
  on_resolve_conflict,
}) => {
  // Sort conflicts by creation/detection time
  const sortedConflicts = [...conflicts].sort((a, b) => {
    // Since conflicts don't have creation time in the type definition,
    // we'll sort by the earliest operation timestamp
    const aTime = Math.min(...a.operations.map((op) => new Date(op.timestamp).getTime()));
    const bTime = Math.min(...b.operations.map((op) => new Date(op.timestamp).getTime()));
    return bTime - aTime; // Newest first
  });

  const handleResolveAll = useCallback(async () => {
    if (
      !confirm(
        `Are you sure you want to resolve all ${conflicts.length} conflicts using the "Merge Changes" strategy?`
      )
    ) {
      return;
    }

    try {
      for (const conflict of conflicts) {
        await on_resolve_conflict?.(conflict.id, ConflictResolutionStrategy.MERGE_CHANGES);
      }
    } catch (err) {
      console.error('Failed to resolve all conflicts:', err);
    }
  }, [conflicts, on_resolve_conflict]);

  return (
    <div className='conflict-resolver h-full flex flex-col bg-white'>
      {/* Panel header */}
      <div className='panel-header p-4 border-b border-red-200 bg-red-50'>
        <div className='flex items-center justify-between mb-4'>
          <h3 className='text-lg font-semibold flex items-center gap-2 text-red-800'>
            <AlertTriangle className='h-5 w-5' />
            Editing Conflicts
          </h3>

          <div className='text-sm text-red-700'>{conflicts.length} conflicts</div>
        </div>

        <div className='flex items-center justify-between'>
          <div className='text-sm text-red-700'>
            <p className='mb-1'>
              <strong>Action Required:</strong> Multiple collaborators edited the same content.
            </p>
            <p>Choose a resolution strategy to continue collaborative editing.</p>
          </div>

          {conflicts.length > 1 && (
            <Button
              onClick={handleResolveAll}
              variant='outline'
              size='sm'
              className='border-red-300 text-red-600 hover:bg-red-50'
            >
              <GitMerge className='h-4 w-4 mr-1' />
              Resolve All
            </Button>
          )}
        </div>
      </div>

      {/* Conflicts list */}
      <div className='conflicts-list flex-1 overflow-y-auto'>
        {sortedConflicts.length > 0 ? (
          <div className='space-y-4 p-4'>
            {sortedConflicts.map((conflict, index) => (
              <div key={conflict.id}>
                <div className='text-xs text-gray-500 mb-2'>Conflict #{index + 1}</div>
                <ConflictItem
                  conflict={conflict}
                  current_user_id={current_user.id}
                  on_resolve={on_resolve_conflict}
                />
              </div>
            ))}
          </div>
        ) : (
          <div className='empty-state flex flex-col items-center justify-center h-full text-gray-500 p-8'>
            <Check className='h-12 w-12 mb-4 text-green-500' />
            <h4 className='text-lg font-medium mb-2 text-green-700'>No Conflicts</h4>
            <p className='text-sm text-center text-green-600'>
              All editing conflicts have been resolved. Collaborative editing can continue normally.
            </p>
          </div>
        )}
      </div>

      {/* Help text */}
      <div className='panel-footer p-4 border-t bg-gray-50'>
        <div className='text-xs text-gray-600'>
          <p className='mb-2'>
            <strong>Understanding Conflicts:</strong>
          </p>
          <ul className='space-y-1 list-disc list-inside'>
            <li>
              <strong>Last Writer Wins:</strong> Keeps the most recent changes
            </li>
            <li>
              <strong>First Writer Wins:</strong> Preserves the original changes
            </li>
            <li>
              <strong>Merge Changes:</strong> Combines compatible changes automatically
            </li>
            <li>
              <strong>Manual Resolution:</strong> Review and choose specific changes
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};
