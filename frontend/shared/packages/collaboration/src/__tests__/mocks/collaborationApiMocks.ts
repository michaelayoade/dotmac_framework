/**
 * Collaboration API mocks for testing
 * Provides mock data and API responses for documents, comments, suggestions, and real-time collaboration
 */

import type {
  CollaborativeDocument,
  DocumentComment,
  DocumentSuggestion,
  DocumentConflict,
  User,
  UserPresence,
  DocumentVersion,
  OperationTransform,
  ConflictStatus,
} from '../../types';

// Mock users
export const mockUsers: User[] = [
  {
    id: 'user-001',
    name: 'John Doe',
    email: 'john.doe@dotmac.local',
    avatar_url: 'https://api.dicebear.com/7.x/avataaars/svg?seed=john',
    role: 'admin',
    permissions: ['read', 'write', 'comment', 'suggest', 'resolve_conflicts'],
  },
  {
    id: 'user-002',
    name: 'Jane Smith',
    email: 'jane.smith@dotmac.local',
    avatar_url: 'https://api.dicebear.com/7.x/avataaars/svg?seed=jane',
    role: 'editor',
    permissions: ['read', 'write', 'comment', 'suggest'],
  },
  {
    id: 'user-003',
    name: 'Mike Johnson',
    email: 'mike.johnson@dotmac.local',
    avatar_url: 'https://api.dicebear.com/7.x/avataaars/svg?seed=mike',
    role: 'reviewer',
    permissions: ['read', 'comment'],
  },
  {
    id: 'user-004',
    name: 'Sarah Wilson',
    email: 'sarah.wilson@dotmac.local',
    avatar_url: 'https://api.dicebear.com/7.x/avataaars/svg?seed=sarah',
    role: 'contributor',
    permissions: ['read', 'write', 'comment'],
  },
];

// Mock documents
export const mockDocuments: CollaborativeDocument[] = [
  {
    id: 'doc-001',
    tenant_id: 'tenant-001',
    title: 'Network Infrastructure Plan Q4 2024',
    content:
      '# Network Infrastructure Plan Q4 2024\n\n## Overview\nThis document outlines our planned network infrastructure improvements for the fourth quarter of 2024.\n\n## Objectives\n- Expand fiber coverage to rural areas\n- Upgrade core routing equipment\n- Implement redundant connectivity\n\n## Timeline\n- **October**: Equipment procurement\n- **November**: Installation begins\n- **December**: Testing and deployment',
    document_type: 'markdown',
    version: 3,
    created_by: 'user-001',
    created_at: '2024-08-15T09:00:00Z',
    updated_at: '2024-08-30T14:22:00Z',
    updated_by: 'user-002',
    status: 'active',
    permissions: {
      read: ['user-001', 'user-002', 'user-003', 'user-004'],
      write: ['user-001', 'user-002', 'user-004'],
      comment: ['user-001', 'user-002', 'user-003', 'user-004'],
      admin: ['user-001'],
    },
    metadata: {
      category: 'planning',
      tags: ['network', 'infrastructure', 'q4', 'expansion'],
      priority: 'high',
      department: 'engineering',
    },
    lock_status: {
      is_locked: false,
      locked_by: null,
      locked_at: null,
      lock_expires_at: null,
    },
  },
  {
    id: 'doc-002',
    tenant_id: 'tenant-001',
    title: 'Customer Service Procedures Update',
    content:
      '# Customer Service Procedures\n\n## Support Ticket Handling\n1. Initial response within 2 hours\n2. Escalate critical issues immediately\n3. Follow up within 24 hours\n\n## Common Issues\n- Connection problems\n- Billing inquiries\n- Service outages',
    document_type: 'markdown',
    version: 1,
    created_by: 'user-003',
    created_at: '2024-08-28T11:30:00Z',
    updated_at: '2024-08-28T11:30:00Z',
    updated_by: 'user-003',
    status: 'draft',
    permissions: {
      read: ['user-001', 'user-002', 'user-003'],
      write: ['user-003'],
      comment: ['user-001', 'user-002', 'user-003'],
      admin: ['user-001'],
    },
    metadata: {
      category: 'procedures',
      tags: ['customer-service', 'support', 'procedures'],
      priority: 'medium',
      department: 'support',
    },
    lock_status: {
      is_locked: true,
      locked_by: 'user-003',
      locked_at: '2024-08-30T10:15:00Z',
      lock_expires_at: '2024-08-30T18:15:00Z',
    },
  },
];

// Mock document comments
export const mockComments: DocumentComment[] = [
  {
    id: 'comment-001',
    document_id: 'doc-001',
    user_id: 'user-002',
    content: 'Should we include budget estimates for each phase?',
    position: {
      line: 12,
      column: 0,
      selection_start: 245,
      selection_end: 245,
    },
    thread_id: 'thread-001',
    parent_comment_id: null,
    status: 'active',
    created_at: '2024-08-29T10:15:00Z',
    updated_at: '2024-08-29T10:15:00Z',
  },
  {
    id: 'comment-002',
    document_id: 'doc-001',
    user_id: 'user-001',
    content: "Good point. I'll add a budget section after the timeline.",
    position: {
      line: 12,
      column: 0,
      selection_start: 245,
      selection_end: 245,
    },
    thread_id: 'thread-001',
    parent_comment_id: 'comment-001',
    status: 'active',
    created_at: '2024-08-29T10:22:00Z',
    updated_at: '2024-08-29T10:22:00Z',
  },
  {
    id: 'comment-003',
    document_id: 'doc-001',
    user_id: 'user-003',
    content: 'The November timeline might be too aggressive. Equipment delivery could be delayed.',
    position: {
      line: 16,
      column: 0,
      selection_start: 356,
      selection_end: 386,
    },
    thread_id: 'thread-002',
    parent_comment_id: null,
    status: 'active',
    created_at: '2024-08-29T15:45:00Z',
    updated_at: '2024-08-29T15:45:00Z',
  },
];

// Mock suggestions
export const mockSuggestions: DocumentSuggestion[] = [
  {
    id: 'suggestion-001',
    document_id: 'doc-001',
    user_id: 'user-004',
    suggested_change: {
      operation: 'replace',
      position: { line: 8, column: 0, selection_start: 156, selection_end: 195 },
      original_content: '- Expand fiber coverage to rural areas',
      suggested_content:
        '- Expand fiber coverage to underserved rural areas with priority on high-density zones',
    },
    reason: 'More specific targeting will improve ROI',
    status: 'pending',
    created_at: '2024-08-29T14:30:00Z',
    updated_at: '2024-08-29T14:30:00Z',
  },
  {
    id: 'suggestion-002',
    document_id: 'doc-001',
    user_id: 'user-002',
    suggested_change: {
      operation: 'insert',
      position: { line: 18, column: 0, selection_start: 420, selection_end: 420 },
      original_content: '',
      suggested_content:
        '\n## Budget Allocation\n- Equipment: $2.5M\n- Installation: $800K\n- Testing: $200K',
    },
    reason: 'Adding budget details as discussed in comments',
    status: 'approved',
    approved_by: 'user-001',
    approved_at: '2024-08-29T16:10:00Z',
    created_at: '2024-08-29T15:55:00Z',
    updated_at: '2024-08-29T16:10:00Z',
  },
];

// Mock conflicts
export const mockConflicts: DocumentConflict[] = [
  {
    id: 'conflict-001',
    document_id: 'doc-001',
    position: { line: 10, column: 0, selection_start: 200, selection_end: 250 },
    conflicting_operations: [
      {
        id: 'op-001',
        user_id: 'user-001',
        operation: 'replace',
        content: '## Key Objectives for Network Expansion',
        timestamp: '2024-08-30T09:15:00Z',
      },
      {
        id: 'op-002',
        user_id: 'user-002',
        operation: 'replace',
        content: '## Primary Goals and Objectives',
        timestamp: '2024-08-30T09:16:00Z',
      },
    ],
    status: ConflictStatus.UNRESOLVED,
    detected_at: '2024-08-30T09:17:00Z',
    resolved_at: null,
    resolved_by: null,
    resolution_strategy: null,
  },
];

// Mock user presence
export const mockUserPresence: UserPresence[] = [
  {
    user_id: 'user-001',
    document_id: 'doc-001',
    status: 'active',
    cursor_position: { line: 15, column: 25 },
    selection: {
      start: { line: 15, column: 20 },
      end: { line: 15, column: 35 },
    },
    last_seen: new Date(Date.now() - 5000).toISOString(),
    viewport: {
      start_line: 10,
      end_line: 25,
    },
  },
  {
    user_id: 'user-002',
    document_id: 'doc-001',
    status: 'idle',
    cursor_position: { line: 8, column: 10 },
    selection: null,
    last_seen: new Date(Date.now() - 120000).toISOString(),
    viewport: {
      start_line: 5,
      end_line: 20,
    },
  },
  {
    user_id: 'user-004',
    document_id: 'doc-001',
    status: 'busy',
    cursor_position: { line: 12, column: 0 },
    selection: {
      start: { line: 12, column: 0 },
      end: { line: 14, column: 30 },
    },
    last_seen: new Date(Date.now() - 30000).toISOString(),
    viewport: {
      start_line: 8,
      end_line: 18,
    },
  },
];

// Mock document versions
export const mockDocumentVersions: DocumentVersion[] = [
  {
    id: 'version-001',
    document_id: 'doc-001',
    version_number: 1,
    content:
      '# Network Infrastructure Plan Q4 2024\n\n## Overview\nInitial draft of network infrastructure improvements.',
    created_by: 'user-001',
    created_at: '2024-08-15T09:00:00Z',
    change_summary: 'Initial document creation',
  },
  {
    id: 'version-002',
    document_id: 'doc-001',
    version_number: 2,
    content:
      '# Network Infrastructure Plan Q4 2024\n\n## Overview\nThis document outlines our planned network infrastructure improvements for the fourth quarter of 2024.\n\n## Objectives\n- Expand fiber coverage\n- Upgrade equipment',
    created_by: 'user-001',
    created_at: '2024-08-20T14:30:00Z',
    change_summary: 'Added objectives section',
  },
  {
    id: 'version-003',
    document_id: 'doc-001',
    version_number: 3,
    content: mockDocuments[0].content,
    created_by: 'user-002',
    created_at: '2024-08-30T14:22:00Z',
    change_summary: 'Added timeline section and detailed objectives',
  },
];

// Mock operation transforms
export const mockOperationTransforms: OperationTransform[] = [
  {
    id: 'op-transform-001',
    document_id: 'doc-001',
    user_id: 'user-001',
    operation: {
      type: 'insert',
      position: 150,
      content: 'additional ',
      metadata: {
        cursor_position: { line: 8, column: 15 },
        timestamp: '2024-08-30T10:30:00Z',
      },
    },
    transformed_operation: {
      type: 'insert',
      position: 150,
      content: 'additional ',
      metadata: {
        cursor_position: { line: 8, column: 15 },
        timestamp: '2024-08-30T10:30:00Z',
        transformed: true,
        original_position: 150,
      },
    },
    applied_at: '2024-08-30T10:30:05Z',
    sequence_number: 1245,
  },
];

// Mock API response functions
export const collaborationApiMocks = {
  // Document management
  getDocuments: () => Promise.resolve({ data: mockDocuments }),
  getDocument: (documentId: string) =>
    Promise.resolve({
      data: mockDocuments.find((doc) => doc.id === documentId) || mockDocuments[0],
    }),

  createDocument: (documentData: any) =>
    Promise.resolve({
      data: {
        id: `doc-${Date.now()}`,
        ...documentData,
        version: 1,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        status: 'active',
      },
    }),

  updateDocument: (documentId: string, updates: any) =>
    Promise.resolve({
      data: {
        ...mockDocuments.find((doc) => doc.id === documentId),
        ...updates,
        version: (mockDocuments.find((doc) => doc.id === documentId)?.version || 1) + 1,
        updated_at: new Date().toISOString(),
      },
    }),

  deleteDocument: (documentId: string) =>
    Promise.resolve({ data: { success: true, deleted_id: documentId } }),

  // Document operations
  applyOperation: (documentId: string, operation: any) =>
    Promise.resolve({
      data: {
        operation_id: `op-${Date.now()}`,
        applied: true,
        transformed_operation: {
          ...operation,
          sequence_number: Math.floor(Math.random() * 10000),
        },
      },
    }),

  // Document locking
  lockDocument: (documentId: string) =>
    Promise.resolve({
      data: {
        locked: true,
        locked_by: 'user-001',
        locked_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + 8 * 60 * 60 * 1000).toISOString(),
      },
    }),

  unlockDocument: (documentId: string) => Promise.resolve({ data: { unlocked: true } }),

  // Comments
  getDocumentComments: (documentId: string) =>
    Promise.resolve({
      data: mockComments.filter((comment) => comment.document_id === documentId),
    }),

  createComment: (documentId: string, commentData: any) =>
    Promise.resolve({
      data: {
        id: `comment-${Date.now()}`,
        document_id: documentId,
        ...commentData,
        status: 'active',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    }),

  updateComment: (commentId: string, updates: any) =>
    Promise.resolve({
      data: {
        ...mockComments.find((comment) => comment.id === commentId),
        ...updates,
        updated_at: new Date().toISOString(),
      },
    }),

  deleteComment: (commentId: string) =>
    Promise.resolve({ data: { success: true, deleted_id: commentId } }),

  // Suggestions
  getDocumentSuggestions: (documentId: string) =>
    Promise.resolve({
      data: mockSuggestions.filter((suggestion) => suggestion.document_id === documentId),
    }),

  createSuggestion: (documentId: string, suggestionData: any) =>
    Promise.resolve({
      data: {
        id: `suggestion-${Date.now()}`,
        document_id: documentId,
        ...suggestionData,
        status: 'pending',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    }),

  approveSuggestion: (suggestionId: string) =>
    Promise.resolve({
      data: {
        ...mockSuggestions.find((s) => s.id === suggestionId),
        status: 'approved',
        approved_by: 'user-001',
        approved_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    }),

  rejectSuggestion: (suggestionId: string, reason?: string) =>
    Promise.resolve({
      data: {
        ...mockSuggestions.find((s) => s.id === suggestionId),
        status: 'rejected',
        rejected_by: 'user-001',
        rejected_at: new Date().toISOString(),
        rejection_reason: reason,
        updated_at: new Date().toISOString(),
      },
    }),

  // Conflicts
  getDocumentConflicts: (documentId: string) =>
    Promise.resolve({
      data: mockConflicts.filter((conflict) => conflict.document_id === documentId),
    }),

  resolveConflict: (conflictId: string, resolution: any) =>
    Promise.resolve({
      data: {
        ...mockConflicts.find((c) => c.id === conflictId),
        status: ConflictStatus.RESOLVED,
        resolved_by: 'user-001',
        resolved_at: new Date().toISOString(),
        resolution_strategy: resolution.strategy,
      },
    }),

  // Document versions
  getDocumentVersions: (documentId: string) =>
    Promise.resolve({
      data: mockDocumentVersions.filter((version) => version.document_id === documentId),
    }),

  getDocumentVersion: (documentId: string, version: number) =>
    Promise.resolve({
      data: mockDocumentVersions.find(
        (v) => v.document_id === documentId && v.version_number === version
      ),
    }),

  // User presence
  getUserPresence: (documentId: string) =>
    Promise.resolve({
      data: mockUserPresence.filter((presence) => presence.document_id === documentId),
    }),

  updateUserPresence: (documentId: string, presenceData: any) =>
    Promise.resolve({
      data: {
        user_id: 'user-001',
        document_id: documentId,
        ...presenceData,
        last_seen: new Date().toISOString(),
      },
    }),
};

// Mock WebSocket events for real-time collaboration
export const mockCollaborationWebSocketEvents = {
  // Document collaboration events
  document_updated: (documentId: string) => ({
    document_id: documentId,
    version: Math.floor(Math.random() * 10) + 1,
    updated_by: mockUsers[Math.floor(Math.random() * mockUsers.length)].id,
    timestamp: new Date().toISOString(),
    change_summary: 'Content updated',
  }),

  operation_applied: (documentId: string) => ({
    document_id: documentId,
    operation: {
      type: 'insert',
      position: Math.floor(Math.random() * 1000),
      content: 'new content ',
      user_id: mockUsers[Math.floor(Math.random() * mockUsers.length)].id,
    },
    sequence_number: Math.floor(Math.random() * 10000),
    timestamp: new Date().toISOString(),
  }),

  conflict_detected: (documentId: string) => ({
    conflict: {
      id: `conflict-${Date.now()}`,
      document_id: documentId,
      position: { line: 10, column: 5, selection_start: 200, selection_end: 220 },
      conflicting_operations: [
        {
          id: `op-${Date.now() - 1}`,
          user_id: mockUsers[0].id,
          operation: 'replace',
          content: 'version A',
          timestamp: new Date(Date.now() - 1000).toISOString(),
        },
        {
          id: `op-${Date.now()}`,
          user_id: mockUsers[1].id,
          operation: 'replace',
          content: 'version B',
          timestamp: new Date().toISOString(),
        },
      ],
      status: ConflictStatus.UNRESOLVED,
      detected_at: new Date().toISOString(),
    },
  }),

  conflict_resolved: () => ({
    conflict_id: 'conflict-001',
    resolved_by: mockUsers[0].id,
    resolution_strategy: 'manual_merge',
    resolved_at: new Date().toISOString(),
  }),

  // Comment events
  comment_added: (documentId: string) => ({
    comment: {
      id: `comment-${Date.now()}`,
      document_id: documentId,
      user_id: mockUsers[Math.floor(Math.random() * mockUsers.length)].id,
      content: 'New comment added',
      position: { line: Math.floor(Math.random() * 20), column: 0 },
      created_at: new Date().toISOString(),
    },
  }),

  comment_updated: () => ({
    comment_id: 'comment-001',
    updated_content: 'Updated comment content',
    updated_at: new Date().toISOString(),
  }),

  comment_deleted: () => ({
    comment_id: 'comment-002',
    deleted_by: mockUsers[0].id,
    deleted_at: new Date().toISOString(),
  }),

  // Suggestion events
  suggestion_added: (documentId: string) => ({
    suggestion: {
      id: `suggestion-${Date.now()}`,
      document_id: documentId,
      user_id: mockUsers[Math.floor(Math.random() * mockUsers.length)].id,
      suggested_change: {
        operation: 'replace',
        position: { line: 8, column: 0 },
        original_content: 'original text',
        suggested_content: 'suggested text',
      },
      reason: 'Improvement suggestion',
      status: 'pending',
      created_at: new Date().toISOString(),
    },
  }),

  suggestion_approved: () => ({
    suggestion_id: 'suggestion-001',
    approved_by: mockUsers[0].id,
    approved_at: new Date().toISOString(),
  }),

  suggestion_rejected: () => ({
    suggestion_id: 'suggestion-002',
    rejected_by: mockUsers[0].id,
    rejection_reason: 'Does not align with requirements',
    rejected_at: new Date().toISOString(),
  }),

  // User presence events
  user_joined: (documentId: string) => ({
    user_id: mockUsers[Math.floor(Math.random() * mockUsers.length)].id,
    document_id: documentId,
    joined_at: new Date().toISOString(),
  }),

  user_left: (documentId: string) => ({
    user_id: mockUsers[Math.floor(Math.random() * mockUsers.length)].id,
    document_id: documentId,
    left_at: new Date().toISOString(),
  }),

  cursor_moved: (documentId: string) => ({
    user_id: mockUsers[Math.floor(Math.random() * mockUsers.length)].id,
    document_id: documentId,
    cursor_position: {
      line: Math.floor(Math.random() * 20),
      column: Math.floor(Math.random() * 50),
    },
    timestamp: new Date().toISOString(),
  }),

  selection_changed: (documentId: string) => ({
    user_id: mockUsers[Math.floor(Math.random() * mockUsers.length)].id,
    document_id: documentId,
    selection: {
      start: { line: 5, column: 10 },
      end: { line: 7, column: 25 },
    },
    timestamp: new Date().toISOString(),
  }),

  user_status_changed: (documentId: string) => ({
    user_id: mockUsers[Math.floor(Math.random() * mockUsers.length)].id,
    document_id: documentId,
    status: Math.random() > 0.5 ? 'active' : 'idle',
    timestamp: new Date().toISOString(),
  }),

  // Document locking events
  document_locked: (documentId: string) => ({
    document_id: documentId,
    locked_by: mockUsers[0].id,
    locked_at: new Date().toISOString(),
    expires_at: new Date(Date.now() + 8 * 60 * 60 * 1000).toISOString(),
  }),

  document_unlocked: (documentId: string) => ({
    document_id: documentId,
    unlocked_by: mockUsers[0].id,
    unlocked_at: new Date().toISOString(),
  }),

  lock_expired: (documentId: string) => ({
    document_id: documentId,
    previous_owner: mockUsers[0].id,
    expired_at: new Date().toISOString(),
  }),
};
