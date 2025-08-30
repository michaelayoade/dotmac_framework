import type { Operation, OperationType, OperationData, ConflictResolutionStrategy } from '../types';

/**
 * Operational Transform utilities for real-time collaborative editing
 *
 * Provides functions for transforming operations to maintain consistency
 * across multiple concurrent editors using operational transformation (OT).
 */

export interface TransformResult {
  transformedOp: Operation;
  conflictsDetected: boolean;
  conflictingOperations?: Operation[];
}

export class OperationalTransform {
  /**
   * Transform operation A against operation B
   * Returns the transformed version of operation A that can be applied after B
   */
  static transform(opA: Operation, opB: Operation): TransformResult {
    const transformedOp = { ...opA };
    let conflictsDetected = false;
    const conflictingOperations: Operation[] = [];

    // Same position operations are potential conflicts
    if (opA.data.position === opB.data.position) {
      conflictsDetected = true;
      conflictingOperations.push(opB);
    }

    switch (opA.type) {
      case OperationType.INSERT:
        transformedOp.data = this.transformInsert(opA.data, opB);
        break;

      case OperationType.DELETE:
        const deleteResult = this.transformDelete(opA.data, opB);
        transformedOp.data = deleteResult.data;
        if (deleteResult.conflict) {
          conflictsDetected = true;
          conflictingOperations.push(opB);
        }
        break;

      case OperationType.REPLACE:
        const replaceResult = this.transformReplace(opA.data, opB);
        transformedOp.data = replaceResult.data;
        if (replaceResult.conflict) {
          conflictsDetected = true;
          conflictingOperations.push(opB);
        }
        break;

      case OperationType.RETAIN:
        // Retain operations typically don't conflict
        break;

      case OperationType.FORMAT:
        const formatResult = this.transformFormat(opA.data, opB);
        transformedOp.data = formatResult.data;
        if (formatResult.conflict) {
          conflictsDetected = true;
          conflictingOperations.push(opB);
        }
        break;
    }

    return {
      transformedOp,
      conflictsDetected,
      conflictingOperations: conflictsDetected ? conflictingOperations : undefined
    };
  }

  /**
   * Transform multiple operations against each other
   */
  static transformBatch(operations: Operation[]): {
    transformedOperations: Operation[];
    conflicts: Array<{
      operations: Operation[];
      conflictingOperations: Operation[];
    }>;
  } {
    const transformedOperations: Operation[] = [];
    const conflicts: Array<{
      operations: Operation[];
      conflictingOperations: Operation[];
    }> = [];

    // Sort operations by timestamp
    const sortedOps = [...operations].sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );

    for (let i = 0; i < sortedOps.length; i++) {
      let currentOp = sortedOps[i];
      let hasConflicts = false;
      const conflictingOps: Operation[] = [];

      // Transform against all previous operations
      for (let j = 0; j < i; j++) {
        const result = this.transform(currentOp, transformedOperations[j]);
        currentOp = result.transformedOp;

        if (result.conflictsDetected && result.conflictingOperations) {
          hasConflicts = true;
          conflictingOps.push(...result.conflictingOperations);
        }
      }

      transformedOperations.push(currentOp);

      if (hasConflicts) {
        conflicts.push({
          operations: [currentOp],
          conflictingOperations: conflictingOps
        });
      }
    }

    return {
      transformedOperations,
      conflicts
    };
  }

  /**
   * Transform insert operation against another operation
   */
  private static transformInsert(insertData: OperationData, otherOp: Operation): OperationData {
    const transformed = { ...insertData };

    switch (otherOp.type) {
      case OperationType.INSERT:
        // If other insert is at or before our position, shift our position
        if (otherOp.data.position <= insertData.position) {
          transformed.position = insertData.position + (otherOp.data.content?.length || 0);
        }
        break;

      case OperationType.DELETE:
        // If delete is before our position, shift position back
        if (otherOp.data.position < insertData.position) {
          transformed.position = Math.max(
            otherOp.data.position,
            insertData.position - (otherOp.data.length || 0)
          );
        }
        break;

      case OperationType.REPLACE:
        // Similar to delete + insert
        if (otherOp.data.position < insertData.position) {
          const oldLength = otherOp.data.oldContent?.length || 0;
          const newLength = otherOp.data.newContent?.length || 0;
          transformed.position = insertData.position - oldLength + newLength;
        }
        break;
    }

    return transformed;
  }

  /**
   * Transform delete operation against another operation
   */
  private static transformDelete(deleteData: OperationData, otherOp: Operation): {
    data: OperationData;
    conflict: boolean;
  } {
    const transformed = { ...deleteData };
    let conflict = false;

    switch (otherOp.type) {
      case OperationType.INSERT:
        // If insert is at or before our delete position, shift our position
        if (otherOp.data.position <= deleteData.position) {
          transformed.position = deleteData.position + (otherOp.data.content?.length || 0);
        }
        break;

      case OperationType.DELETE:
        // Overlapping deletes are conflicts
        const ourEnd = deleteData.position + (deleteData.length || 0);
        const otherEnd = otherOp.data.position + (otherOp.data.length || 0);

        if (this.rangesOverlap(
          deleteData.position, ourEnd,
          otherOp.data.position, otherEnd
        )) {
          conflict = true;
          // Adjust range to avoid double-deletion
          if (otherOp.data.position < deleteData.position) {
            transformed.position = otherOp.data.position;
            transformed.length = Math.max(0, ourEnd - otherEnd);
          }
        } else if (otherOp.data.position < deleteData.position) {
          // Other delete is before ours, shift our position
          transformed.position = Math.max(
            otherOp.data.position,
            deleteData.position - (otherOp.data.length || 0)
          );
        }
        break;

      case OperationType.REPLACE:
        // Check for overlap with the replaced range
        const replaceEnd = otherOp.data.position + (otherOp.data.oldContent?.length || 0);
        if (this.rangesOverlap(
          deleteData.position, deleteData.position + (deleteData.length || 0),
          otherOp.data.position, replaceEnd
        )) {
          conflict = true;
        }
        break;
    }

    return { data: transformed, conflict };
  }

  /**
   * Transform replace operation against another operation
   */
  private static transformReplace(replaceData: OperationData, otherOp: Operation): {
    data: OperationData;
    conflict: boolean;
  } {
    const transformed = { ...replaceData };
    let conflict = false;

    switch (otherOp.type) {
      case OperationType.INSERT:
        // If insert is before our replace, shift position
        if (otherOp.data.position <= replaceData.position) {
          transformed.position = replaceData.position + (otherOp.data.content?.length || 0);
        }
        break;

      case OperationType.DELETE:
        // Check for overlap
        const replaceEnd = replaceData.position + (replaceData.oldContent?.length || 0);
        const deleteEnd = otherOp.data.position + (otherOp.data.length || 0);

        if (this.rangesOverlap(
          replaceData.position, replaceEnd,
          otherOp.data.position, deleteEnd
        )) {
          conflict = true;
        } else if (otherOp.data.position < replaceData.position) {
          // Delete is before our replace, shift position
          transformed.position = Math.max(
            otherOp.data.position,
            replaceData.position - (otherOp.data.length || 0)
          );
        }
        break;

      case OperationType.REPLACE:
        // Overlapping replaces are always conflicts
        const ourEnd = replaceData.position + (replaceData.oldContent?.length || 0);
        const theirEnd = otherOp.data.position + (otherOp.data.oldContent?.length || 0);

        if (this.rangesOverlap(
          replaceData.position, ourEnd,
          otherOp.data.position, theirEnd
        )) {
          conflict = true;
        }
        break;
    }

    return { data: transformed, conflict };
  }

  /**
   * Transform format operation against another operation
   */
  private static transformFormat(formatData: OperationData, otherOp: Operation): {
    data: OperationData;
    conflict: boolean;
  } {
    const transformed = { ...formatData };
    let conflict = false;

    // Format operations rarely conflict unless they're exact overlaps
    // with conflicting formatting attributes
    if (otherOp.type === OperationType.FORMAT &&
        formatData.position === otherOp.data.position &&
        formatData.length === otherOp.data.length) {

      // Check for conflicting attributes
      const ourAttrs = formatData.attributes || {};
      const theirAttrs = otherOp.data.attributes || {};

      for (const key of Object.keys(ourAttrs)) {
        if (key in theirAttrs && ourAttrs[key] !== theirAttrs[key]) {
          conflict = true;
          break;
        }
      }
    }

    return { data: transformed, conflict };
  }

  /**
   * Check if two ranges overlap
   */
  private static rangesOverlap(
    start1: number, end1: number,
    start2: number, end2: number
  ): boolean {
    return start1 < end2 && start2 < end1;
  }

  /**
   * Apply conflict resolution strategy
   */
  static resolveConflict(
    conflictingOps: Operation[],
    strategy: ConflictResolutionStrategy
  ): Operation[] {
    switch (strategy) {
      case ConflictResolutionStrategy.LAST_WRITER_WINS:
        // Keep the operation with the latest timestamp
        return [conflictingOps.reduce((latest, op) =>
          new Date(op.timestamp) > new Date(latest.timestamp) ? op : latest
        )];

      case ConflictResolutionStrategy.FIRST_WRITER_WINS:
        // Keep the operation with the earliest timestamp
        return [conflictingOps.reduce((earliest, op) =>
          new Date(op.timestamp) < new Date(earliest.timestamp) ? op : earliest
        )];

      case ConflictResolutionStrategy.MERGE_CHANGES:
        // Attempt to merge compatible changes
        return this.mergeOperations(conflictingOps);

      case ConflictResolutionStrategy.MANUAL_RESOLUTION:
        // Return all operations for manual review
        return conflictingOps;

      default:
        return conflictingOps;
    }
  }

  /**
   * Merge compatible operations
   */
  private static mergeOperations(operations: Operation[]): Operation[] {
    // Sort by position to merge sequentially
    const sorted = [...operations].sort((a, b) => a.data.position - b.data.position);
    const merged: Operation[] = [];

    for (const op of sorted) {
      if (merged.length === 0) {
        merged.push(op);
        continue;
      }

      const lastMerged = merged[merged.length - 1];

      // Try to merge with the last operation
      const mergedOp = this.tryMergeTwo(lastMerged, op);
      if (mergedOp) {
        merged[merged.length - 1] = mergedOp;
      } else {
        merged.push(op);
      }
    }

    return merged;
  }

  /**
   * Try to merge two operations
   */
  private static tryMergeTwo(op1: Operation, op2: Operation): Operation | null {
    // Can only merge operations of the same type
    if (op1.type !== op2.type) return null;

    switch (op1.type) {
      case OperationType.INSERT:
        // Merge adjacent inserts
        const end1 = op1.data.position + (op1.data.content?.length || 0);
        if (end1 === op2.data.position) {
          return {
            ...op1,
            data: {
              ...op1.data,
              content: (op1.data.content || '') + (op2.data.content || '')
            },
            timestamp: op2.timestamp // Use later timestamp
          };
        }
        break;

      case OperationType.DELETE:
        // Merge adjacent deletes
        const deleteEnd1 = op1.data.position + (op1.data.length || 0);
        if (deleteEnd1 === op2.data.position) {
          return {
            ...op1,
            data: {
              ...op1.data,
              length: (op1.data.length || 0) + (op2.data.length || 0)
            },
            timestamp: op2.timestamp
          };
        }
        break;
    }

    return null;
  }

  /**
   * Validate operation integrity
   */
  static validateOperation(operation: Operation): {
    valid: boolean;
    errors: string[];
  } {
    const errors: string[] = [];

    // Check required fields
    if (!operation.id) errors.push('Operation ID is required');
    if (!operation.author) errors.push('Operation author is required');
    if (!operation.timestamp) errors.push('Operation timestamp is required');

    // Validate position
    if (typeof operation.data.position !== 'number' || operation.data.position < 0) {
      errors.push('Operation position must be a non-negative number');
    }

    // Type-specific validation
    switch (operation.type) {
      case OperationType.INSERT:
        if (!operation.data.content) {
          errors.push('Insert operation requires content');
        }
        break;

      case OperationType.DELETE:
        if (!operation.data.length || operation.data.length <= 0) {
          errors.push('Delete operation requires positive length');
        }
        break;

      case OperationType.REPLACE:
        if (!operation.data.oldContent || !operation.data.newContent) {
          errors.push('Replace operation requires both old and new content');
        }
        break;
    }

    return {
      valid: errors.length === 0,
      errors
    };
  }
}
