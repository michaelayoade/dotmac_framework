/**
 * Collaboration Management Dashboard - Admin Portal Integration
 * Demonstrates integration of @dotmac/collaboration package in admin portal
 */

'use client';

import React, { useState } from 'react';
import { Card } from '@dotmac/primitives';
import {
  CollaborativeEditor,
  PresenceIndicators,
  CommentsPanel,
  SuggestionsList,
  ConflictResolution,
  useCollaboration,
  usePresence,
  useComments,
  useSuggestions,
  type DocumentConfig,
  type CollaborationOptions
} from '@dotmac/collaboration';
import {
  Users,
  MessageSquare,
  Edit3,
  AlertTriangle,
  FileText,
  Settings,
  Eye,
  Share2
} from 'lucide-react';

interface CollaborationManagementProps {
  tenantId: string;
  currentUser: {
    id: string;
    name: string;
    role: string;
    avatar?: string;
  };
}

export const CollaborationManagement: React.FC<CollaborationManagementProps> = ({
  tenantId,
  currentUser
}) => {
  // State for active document and view modes
  const [activeDocument, setActiveDocument] = useState<string>('policy-document-1');
  const [activeView, setActiveView] = useState<'editor' | 'comments' | 'suggestions' | 'conflicts'>('editor');
  const [showPresence, setShowPresence] = useState(true);

  // Document configuration
  const documentConfig: DocumentConfig = {
    document_id: activeDocument,
    tenant_id: tenantId,
    document_type: 'policy',
    permissions: {
      read: true,
      write: currentUser.role === 'admin' || currentUser.role === 'editor',
      comment: true,
      suggest: true
    }
  };

  // Collaboration options
  const collaborationOptions: CollaborationOptions = {
    enable_operational_transform: true,
    enable_presence: true,
    enable_comments: true,
    enable_suggestions: true,
    auto_save_interval: 5000,
    conflict_resolution_strategy: 'last_writer_wins'
  };

  // Collaboration hooks
  const {
    document,
    isConnected,
    participants,
    conflicts,
    saveDocument,
    loading: docLoading,
    error: docError
  } = useCollaboration(documentConfig, collaborationOptions);

  const {
    activeUsers,
    userCursors,
    userSelections,
    loading: presenceLoading
  } = usePresence({
    document_id: activeDocument,
    user: currentUser,
    tenant_id: tenantId
  });

  const {
    comments,
    addComment,
    resolveComment,
    loading: commentsLoading
  } = useComments({
    document_id: activeDocument,
    tenant_id: tenantId
  });

  const {
    suggestions,
    acceptSuggestion,
    rejectSuggestion,
    loading: suggestionsLoading
  } = useSuggestions({
    document_id: activeDocument,
    tenant_id: tenantId
  });

  // Handle document change
  const handleDocumentChange = (newDocumentId: string) => {
    setActiveDocument(newDocumentId);
  };

  // Handle save
  const handleSave = async () => {
    try {
      await saveDocument();
    } catch (error) {
      console.error('Failed to save document:', error);
    }
  };

  return (
    <div className="collaboration-management space-y-6">
      {/* Header with document selector and controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h1 className="text-2xl font-bold text-gray-900">Collaboration Management</h1>

          <select
            value={activeDocument}
            onChange={(e) => handleDocumentChange(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md text-sm"
          >
            <option value="policy-document-1">Network Policy Document</option>
            <option value="procedures-doc-1">Service Procedures</option>
            <option value="maintenance-plan-1">Maintenance Plan</option>
          </select>
        </div>

        {/* Connection status and controls */}
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <div className={`h-2 w-2 rounded-full ${
              isConnected ? 'bg-green-500' : 'bg-red-500'
            }`} />
            <span className="text-sm text-gray-600">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>

          <button
            onClick={() => setShowPresence(!showPresence)}
            className={`px-3 py-2 text-sm rounded-md flex items-center space-x-2 ${
              showPresence
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            <Eye className="h-4 w-4" />
            <span>Presence</span>
          </button>

          <button
            onClick={handleSave}
            className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 flex items-center space-x-2"
            disabled={docLoading}
          >
            <Share2 className="h-4 w-4" />
            <span>{docLoading ? 'Saving...' : 'Save'}</span>
          </button>
        </div>
      </div>

      {/* Statistics cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Active Users</p>
              <p className="text-2xl font-bold text-gray-900">{activeUsers.length}</p>
            </div>
            <Users className="h-8 w-8 text-blue-600" />
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Comments</p>
              <p className="text-2xl font-bold text-gray-900">
                {comments.filter(c => !c.resolved).length}
              </p>
            </div>
            <MessageSquare className="h-8 w-8 text-green-600" />
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Suggestions</p>
              <p className="text-2xl font-bold text-gray-900">{suggestions.length}</p>
            </div>
            <Edit3 className="h-8 w-8 text-purple-600" />
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Conflicts</p>
              <p className="text-2xl font-bold text-gray-900">{conflicts.length}</p>
            </div>
            <AlertTriangle className="h-8 w-8 text-yellow-600" />
          </div>
        </Card>
      </div>

      {/* View selector */}
      <div className="flex items-center space-x-1 bg-gray-100 rounded-lg p-1 w-fit">
        <button
          onClick={() => setActiveView('editor')}
          className={`px-3 py-2 text-sm font-medium rounded-md flex items-center space-x-2 ${
            activeView === 'editor'
              ? 'bg-white text-blue-600 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          <FileText className="h-4 w-4" />
          <span>Editor</span>
        </button>
        <button
          onClick={() => setActiveView('comments')}
          className={`px-3 py-2 text-sm font-medium rounded-md flex items-center space-x-2 ${
            activeView === 'comments'
              ? 'bg-white text-blue-600 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          <MessageSquare className="h-4 w-4" />
          <span>Comments</span>
        </button>
        <button
          onClick={() => setActiveView('suggestions')}
          className={`px-3 py-2 text-sm font-medium rounded-md flex items-center space-x-2 ${
            activeView === 'suggestions'
              ? 'bg-white text-blue-600 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          <Edit3 className="h-4 w-4" />
          <span>Suggestions</span>
        </button>
        <button
          onClick={() => setActiveView('conflicts')}
          className={`px-3 py-2 text-sm font-medium rounded-md flex items-center space-x-2 ${
            activeView === 'conflicts'
              ? 'bg-white text-blue-600 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          <AlertTriangle className="h-4 w-4" />
          <span>Conflicts</span>
        </button>
      </div>

      {/* Main content area based on active view */}
      <div className="min-h-96">
        {activeView === 'editor' && (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Main editor */}
            <Card className="lg:col-span-3 p-0">
              {showPresence && (
                <div className="p-4 border-b border-gray-200">
                  <PresenceIndicators
                    users={activeUsers}
                    cursors={userCursors}
                    selections={userSelections}
                    compact={true}
                  />
                </div>
              )}

              <div className="p-6">
                {docLoading ? (
                  <div className="h-96 flex items-center justify-center">
                    <div className="text-gray-500">Loading document...</div>
                  </div>
                ) : docError ? (
                  <div className="h-96 flex items-center justify-center">
                    <div className="text-red-500">Error loading document: {docError}</div>
                  </div>
                ) : (
                  <div className="h-96">
                    <CollaborativeEditor
                      document={document}
                      user={currentUser}
                      options={collaborationOptions}
                      show_toolbar={true}
                      show_word_count={true}
                      show_revision_history={true}
                      className="w-full h-full"
                    />
                  </div>
                )}
              </div>
            </Card>

            {/* Sidebar with quick info */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Document Info</h3>
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-gray-600">Last Modified</p>
                  <p className="text-sm font-medium">{document?.last_modified ? new Date(document.last_modified).toLocaleString() : 'Never'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Word Count</p>
                  <p className="text-sm font-medium">{document?.word_count || 0}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Participants</p>
                  <p className="text-sm font-medium">{participants.length}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Auto-save</p>
                  <p className="text-sm font-medium text-green-600">Enabled</p>
                </div>
              </div>
            </Card>
          </div>
        )}

        {activeView === 'comments' && (
          <Card className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold">Comments & Discussions</h2>
              <div className="text-sm text-gray-600">
                {comments.filter(c => !c.resolved).length} active comments
              </div>
            </div>

            {commentsLoading ? (
              <div className="h-96 flex items-center justify-center">
                <div className="text-gray-500">Loading comments...</div>
              </div>
            ) : (
              <div className="h-96 overflow-y-auto">
                <CommentsPanel
                  comments={comments}
                  currentUser={currentUser}
                  onAddComment={addComment}
                  onResolveComment={resolveComment}
                  show_resolved={false}
                  group_by_thread={true}
                  className="w-full h-full"
                />
              </div>
            )}
          </Card>
        )}

        {activeView === 'suggestions' && (
          <Card className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold">Suggestions & Edits</h2>
              <div className="text-sm text-gray-600">
                {suggestions.filter(s => s.status === 'pending').length} pending suggestions
              </div>
            </div>

            {suggestionsLoading ? (
              <div className="h-96 flex items-center justify-center">
                <div className="text-gray-500">Loading suggestions...</div>
              </div>
            ) : (
              <div className="h-96 overflow-y-auto">
                <SuggestionsList
                  suggestions={suggestions}
                  currentUser={currentUser}
                  onAccept={acceptSuggestion}
                  onReject={rejectSuggestion}
                  show_preview={true}
                  filter_by_status="pending"
                  className="w-full h-full"
                />
              </div>
            )}
          </Card>
        )}

        {activeView === 'conflicts' && (
          <Card className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold">Conflict Resolution</h2>
              <div className="text-sm text-gray-600">
                {conflicts.filter(c => c.status === 'unresolved').length} unresolved conflicts
              </div>
            </div>

            {conflicts.length === 0 ? (
              <div className="h-96 flex items-center justify-center">
                <div className="text-gray-500 text-center">
                  <AlertTriangle className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                  <p>No conflicts detected</p>
                  <p className="text-sm">All changes are synchronized</p>
                </div>
              </div>
            ) : (
              <div className="h-96 overflow-y-auto">
                <ConflictResolution
                  conflicts={conflicts}
                  currentUser={currentUser}
                  strategy={collaborationOptions.conflict_resolution_strategy}
                  show_diff_view={true}
                  allow_manual_resolution={true}
                  className="w-full h-full"
                />
              </div>
            )}
          </Card>
        )}
      </div>
    </div>
  );
};
