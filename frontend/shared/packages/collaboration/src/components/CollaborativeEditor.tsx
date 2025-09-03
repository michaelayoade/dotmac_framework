import React, { useEffect, useRef, useCallback, useState } from 'react';
import { Card } from '@dotmac/ui';
import {
  Save,
  Users,
  MessageSquare,
  Edit3,
  Lock,
  Unlock,
  AlertTriangle,
  Wifi,
  WifiOff,
  Loader2,
} from 'lucide-react';

import { useCollaboration } from '../hooks';
import { PresenceIndicator } from './PresenceIndicator';
import { CommentsPanel } from './CommentsPanel';
import { SuggestionsPanel } from './SuggestionsPanel';
import { ConflictResolver } from './ConflictResolver';

import type {
  CollaborativeEditorProps,
  UserPermissions,
  CursorPosition,
  TextSelection,
} from '../types';

export const CollaborativeEditor: React.FC<CollaborativeEditorProps> = ({
  document_id,
  initial_content = '',
  user,
  permissions = {
    read: true,
    write: true,
    comment: true,
    suggest: true,
    admin: false,
  },
  websocket_url,
  auto_save = true,
  auto_save_interval = 5000,
  language = 'text',
  theme = 'light',
  show_presence = true,
  show_comments = true,
  show_suggestions = true,
  show_line_numbers = true,
  enable_minimap = false,
  read_only = false,
  on_save,
  on_error,
  on_user_join,
  on_user_leave,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [showComments, setShowComments] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [showConflicts, setShowConflicts] = useState(false);

  const collaboration = useCollaboration({
    document_id,
    user,
    websocket_url,
    auto_save,
    auto_save_interval,
    enable_presence: show_presence,
    enable_comments: show_comments,
    enable_suggestions: show_suggestions,
  });

  const {
    document,
    content,
    saving,
    saved,
    conflicts,
    users,
    comments,
    suggestions,
    connected,
    connecting,
    error,
    updateContent,
    saveDocument,
    addComment,
    resolveComment,
    addSuggestion,
    acceptSuggestion,
    rejectSuggestion,
    updateCursor,
    updateSelection,
    lockDocument,
    unlockDocument,
    resolveConflict,
  } = collaboration;

  // Handle textarea content changes
  const handleContentChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      if (read_only || !permissions.write) return;

      const newContent = e.target.value;
      updateContent(newContent);
    },
    [read_only, permissions.write, updateContent]
  );

  // Handle cursor position updates
  const handleSelectionChange = useCallback(() => {
    if (!textareaRef.current || !show_presence) return;

    const textarea = textareaRef.current;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;

    // Calculate line and column for cursor position
    const lines = textarea.value.substring(0, start).split('\n');
    const line = lines.length - 1;
    const column = lines[lines.length - 1].length;

    const cursorPosition: CursorPosition = {
      x: column * 8, // Approximate character width
      y: line * 20, // Approximate line height
      line,
      column,
      visible: true,
      timestamp: new Date().toISOString(),
    };

    updateCursor(cursorPosition);

    if (start !== end) {
      const selection: TextSelection = {
        start,
        end,
        direction: start < end ? 'forward' : 'backward',
        text: textarea.value.substring(Math.min(start, end), Math.max(start, end)),
      };
      updateSelection(selection);
    } else {
      updateSelection(null);
    }
  }, [show_presence, updateCursor, updateSelection]);

  // Handle save shortcut
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        if (permissions.write && !saving) {
          saveDocument();
        }
      }
    },
    [permissions.write, saving, saveDocument]
  );

  // Handle save action
  const handleSave = useCallback(async () => {
    if (!permissions.write || saving) return;

    try {
      await saveDocument();
      on_save?.(document!);
    } catch (err) {
      on_error?.(err as Error);
    }
  }, [permissions.write, saving, saveDocument, document, on_save, on_error]);

  // Handle lock/unlock
  const handleToggleLock = useCallback(async () => {
    if (!permissions.admin) return;

    try {
      if (document?.metadata.locked) {
        await unlockDocument();
      } else {
        await lockDocument();
      }
    } catch (err) {
      on_error?.(err as Error);
    }
  }, [permissions.admin, document, lockDocument, unlockDocument, on_error]);

  // Handle adding quick comment
  const handleAddQuickComment = useCallback(async () => {
    if (!permissions.comment || !textareaRef.current) return;

    const textarea = textareaRef.current;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;

    if (start === end) return; // No selection

    const selectedText = textarea.value.substring(start, end);
    const lines = textarea.value.substring(0, start).split('\n');
    const line = lines.length - 1;
    const column = lines[lines.length - 1].length;

    try {
      await addComment({
        content: '', // Will be filled by user in comments panel
        position: {
          line,
          column,
          selection: { start, end, text: selectedText },
        },
        resolved: false,
        replies: [],
      });
      setShowComments(true);
    } catch (err) {
      on_error?.(err as Error);
    }
  }, [permissions.comment, addComment, on_error]);

  // Handle user events
  useEffect(() => {
    const currentUsers = users.filter((u) => u.id !== user.id);
    const previousUserIds = useRef<Set<string>>(new Set());

    // Check for new users
    currentUsers.forEach((collaborationUser) => {
      if (!previousUserIds.current.has(collaborationUser.id)) {
        on_user_join?.(collaborationUser);
      }
    });

    // Check for users who left
    previousUserIds.current.forEach((userId) => {
      if (!currentUsers.find((u) => u.id === userId)) {
        const leftUser = users.find((u) => u.id === userId);
        if (leftUser) {
          on_user_leave?.(leftUser);
        }
      }
    });

    previousUserIds.current = new Set(currentUsers.map((u) => u.id));
  }, [users, user.id, on_user_join, on_user_leave]);

  // Handle conflicts
  useEffect(() => {
    if (conflicts.length > 0 && !showConflicts) {
      setShowConflicts(true);
    }
  }, [conflicts.length, showConflicts]);

  // Handle errors
  useEffect(() => {
    if (error) {
      on_error?.(new Error(error));
    }
  }, [error, on_error]);

  // Initialize content
  useEffect(() => {
    if (!content && initial_content) {
      updateContent(initial_content);
    }
  }, [content, initial_content, updateContent]);

  const isLocked = document?.metadata.locked && document?.metadata.locked_by !== user.id;
  const effectiveReadOnly = read_only || !permissions.write || isLocked;

  return (
    <div className='collaborative-editor flex flex-col h-full'>
      {/* Header */}
      <div className='editor-header flex items-center justify-between p-4 border-b bg-white'>
        <div className='flex items-center gap-4'>
          <h2 className='text-lg font-semibold truncate'>
            {document?.title || 'Untitled Document'}
          </h2>

          {/* Connection status */}
          <div className='flex items-center gap-2 text-sm'>
            {connecting ? (
              <div className='flex items-center gap-1 text-blue-600'>
                <Loader2 className='h-4 w-4 animate-spin' />
                <span>Connecting...</span>
              </div>
            ) : connected ? (
              <div className='flex items-center gap-1 text-green-600'>
                <Wifi className='h-4 w-4' />
                <span>Connected</span>
              </div>
            ) : (
              <div className='flex items-center gap-1 text-red-600'>
                <WifiOff className='h-4 w-4' />
                <span>Disconnected</span>
              </div>
            )}
          </div>

          {/* Save status */}
          <div className='flex items-center gap-2 text-sm text-gray-600'>
            {saving ? (
              <div className='flex items-center gap-1'>
                <Loader2 className='h-4 w-4 animate-spin' />
                <span>Saving...</span>
              </div>
            ) : saved ? (
              <span>All changes saved</span>
            ) : (
              <span>Unsaved changes</span>
            )}
          </div>

          {/* Lock status */}
          {isLocked && (
            <div className='flex items-center gap-1 text-orange-600'>
              <Lock className='h-4 w-4' />
              <span className='text-sm'>Locked by {document?.metadata.locked_by}</span>
            </div>
          )}
        </div>

        <div className='flex items-center gap-2'>
          {/* Presence indicator */}
          {show_presence && (
            <PresenceIndicator
              users={users}
              current_user={user}
              max_avatars={5}
              show_names={false}
              show_status={true}
            />
          )}

          {/* Action buttons */}
          <div className='flex items-center gap-1'>
            {show_comments && (
              <button
                onClick={() => setShowComments(!showComments)}
                className={`p-2 rounded-lg hover:bg-gray-100 relative ${
                  showComments ? 'bg-blue-100 text-blue-600' : 'text-gray-600'
                }`}
                title='Comments'
              >
                <MessageSquare className='h-4 w-4' />
                {comments.filter((c) => !c.resolved).length > 0 && (
                  <span className='absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center'>
                    {comments.filter((c) => !c.resolved).length}
                  </span>
                )}
              </button>
            )}

            {show_suggestions && (
              <button
                onClick={() => setShowSuggestions(!showSuggestions)}
                className={`p-2 rounded-lg hover:bg-gray-100 relative ${
                  showSuggestions ? 'bg-green-100 text-green-600' : 'text-gray-600'
                }`}
                title='Suggestions'
              >
                <Edit3 className='h-4 w-4' />
                {suggestions.filter((s) => s.status === 'pending').length > 0 && (
                  <span className='absolute -top-1 -right-1 bg-green-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center'>
                    {suggestions.filter((s) => s.status === 'pending').length}
                  </span>
                )}
              </button>
            )}

            {conflicts.length > 0 && (
              <button
                onClick={() => setShowConflicts(!showConflicts)}
                className={`p-2 rounded-lg hover:bg-gray-100 relative ${
                  showConflicts ? 'bg-red-100 text-red-600' : 'text-red-600'
                }`}
                title='Conflicts'
              >
                <AlertTriangle className='h-4 w-4' />
                <span className='absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center'>
                  {conflicts.length}
                </span>
              </button>
            )}

            {permissions.admin && (
              <button
                onClick={handleToggleLock}
                className='p-2 rounded-lg hover:bg-gray-100 text-gray-600'
                title={document?.metadata.locked ? 'Unlock Document' : 'Lock Document'}
              >
                {document?.metadata.locked ? (
                  <Unlock className='h-4 w-4' />
                ) : (
                  <Lock className='h-4 w-4' />
                )}
              </button>
            )}

            {permissions.write && (
              <button
                onClick={handleSave}
                disabled={saving || saved}
                className='flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed'
              >
                {saving ? (
                  <Loader2 className='h-4 w-4 animate-spin' />
                ) : (
                  <Save className='h-4 w-4' />
                )}
                <span>Save</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Editor content */}
      <div className='editor-content flex-1 flex'>
        {/* Main editor */}
        <div className='editor-main flex-1 relative'>
          <textarea
            ref={textareaRef}
            value={content}
            onChange={handleContentChange}
            onSelect={handleSelectionChange}
            onKeyDown={handleKeyDown}
            readOnly={effectiveReadOnly}
            placeholder={effectiveReadOnly ? 'This document is read-only' : 'Start typing...'}
            className={`w-full h-full p-4 border-none outline-none resize-none font-mono text-sm leading-relaxed ${
              theme === 'dark' ? 'bg-gray-900 text-white' : 'bg-white text-gray-900'
            } ${effectiveReadOnly ? 'cursor-not-allowed bg-gray-50' : ''}`}
            style={{
              tabSize: 2,
              whiteSpace: 'pre-wrap',
              wordWrap: 'break-word',
            }}
          />

          {/* User cursors overlay */}
          {show_presence && (
            <div className='cursors-overlay absolute inset-0 pointer-events-none'>
              {users
                .filter((u) => u.id !== user.id && u.cursor?.visible)
                .map((collaborationUser) => (
                  <div
                    key={collaborationUser.id}
                    className='absolute w-0.5 h-5 bg-blue-500 animate-pulse'
                    style={{
                      left: collaborationUser.cursor?.x || 0,
                      top: collaborationUser.cursor?.y || 0,
                      borderColor: collaborationUser.color || '#3B82F6',
                    }}
                  >
                    <div className='absolute -top-6 left-0 bg-blue-500 text-white text-xs px-1 py-0.5 rounded whitespace-nowrap'>
                      {collaborationUser.name}
                    </div>
                  </div>
                ))}
            </div>
          )}
        </div>

        {/* Side panels */}
        <div className='editor-panels flex'>
          {/* Comments panel */}
          {show_comments && showComments && (
            <div className='comments-panel w-80 border-l bg-gray-50'>
              <CommentsPanel
                comments={comments}
                current_user={user}
                document_id={document_id}
                on_add_comment={addComment}
                on_resolve_comment={resolveComment}
              />
            </div>
          )}

          {/* Suggestions panel */}
          {show_suggestions && showSuggestions && (
            <div className='suggestions-panel w-80 border-l bg-gray-50'>
              <SuggestionsPanel
                suggestions={suggestions}
                current_user={user}
                document_id={document_id}
                on_accept_suggestion={acceptSuggestion}
                on_reject_suggestion={rejectSuggestion}
              />
            </div>
          )}

          {/* Conflicts panel */}
          {showConflicts && conflicts.length > 0 && (
            <div className='conflicts-panel w-80 border-l bg-red-50'>
              <ConflictResolver
                conflicts={conflicts}
                document_id={document_id}
                current_user={user}
                on_resolve_conflict={resolveConflict}
              />
            </div>
          )}
        </div>
      </div>

      {/* Quick actions bar */}
      {!effectiveReadOnly && (
        <div className='editor-footer p-2 border-t bg-gray-50'>
          <div className='flex items-center gap-2 text-sm text-gray-600'>
            {permissions.comment && (
              <button
                onClick={handleAddQuickComment}
                className='flex items-center gap-1 px-2 py-1 hover:bg-gray-200 rounded'
              >
                <MessageSquare className='h-3 w-3' />
                Add Comment
              </button>
            )}

            <div className='flex-1' />

            <div className='text-xs'>
              {users.length} {users.length === 1 ? 'user' : 'users'} online
            </div>

            <div className='text-xs'>Version {document?.version || 0}</div>
          </div>
        </div>
      )}
    </div>
  );
};
