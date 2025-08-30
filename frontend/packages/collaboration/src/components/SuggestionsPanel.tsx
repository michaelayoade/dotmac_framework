import React, { useState, useCallback } from 'react';
import { Button, Card } from '@dotmac/ui';
import {
  Edit3,
  Check,
  X,
  MessageSquare,
  Clock,
  User,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

import type { SuggestionsPanelProps, Suggestion, SuggestionStatus } from '../types';

interface SuggestionItemProps {
  suggestion: Suggestion;
  current_user_id: string;
  on_accept?: (suggestion_id: string) => void;
  on_reject?: (suggestion_id: string) => void;
  on_add_comment?: (suggestion_id: string, content: string) => void;
}

const SuggestionItem: React.FC<SuggestionItemProps> = ({
  suggestion,
  current_user_id,
  on_accept,
  on_reject,
  on_add_comment
}) => {
  const [expanded, setExpanded] = useState(false);
  const [showCommentForm, setShowCommentForm] = useState(false);
  const [commentContent, setCommentContent] = useState('');
  const [submittingComment, setSubmittingComment] = useState(false);
  const [processing, setProcessing] = useState(false);

  const handleAccept = useCallback(async () => {
    try {
      setProcessing(true);
      await on_accept?.(suggestion.id);
    } catch (err) {
      console.error('Failed to accept suggestion:', err);
    } finally {
      setProcessing(false);
    }
  }, [suggestion.id, on_accept]);

  const handleReject = useCallback(async () => {
    try {
      setProcessing(true);
      await on_reject?.(suggestion.id);
    } catch (err) {
      console.error('Failed to reject suggestion:', err);
    } finally {
      setProcessing(false);
    }
  }, [suggestion.id, on_reject]);

  const handleAddComment = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!commentContent.trim()) return;

    try {
      setSubmittingComment(true);
      await on_add_comment?.(suggestion.id, commentContent);
      setCommentContent('');
      setShowCommentForm(false);
    } catch (err) {
      console.error('Failed to add comment:', err);
    } finally {
      setSubmittingComment(false);
    }
  }, [suggestion.id, commentContent, on_add_comment]);

  const getStatusColor = (status: SuggestionStatus): string => {
    const statusColors = {
      pending: 'border-yellow-400 bg-yellow-50',
      accepted: 'border-green-400 bg-green-50',
      rejected: 'border-red-400 bg-red-50',
      withdrawn: 'border-gray-400 bg-gray-50'
    };
    return statusColors[status] || statusColors.pending;
  };

  const getStatusIcon = (status: SuggestionStatus): React.ReactNode => {
    const statusIcons = {
      pending: <Clock className="h-4 w-4 text-yellow-600" />,
      accepted: <Check className="h-4 w-4 text-green-600" />,
      rejected: <X className="h-4 w-4 text-red-600" />,
      withdrawn: <X className="h-4 w-4 text-gray-600" />
    };
    return statusIcons[status] || statusIcons.pending;
  };

  const getStatusText = (status: SuggestionStatus): string => {
    const statusTexts = {
      pending: 'Pending Review',
      accepted: 'Accepted',
      rejected: 'Rejected',
      withdrawn: 'Withdrawn'
    };
    return statusTexts[status] || 'Unknown';
  };

  const canTakeAction = suggestion.status === 'pending' && suggestion.author.id !== current_user_id;

  return (
    <div className={`suggestion-item border-l-4 ${getStatusColor(suggestion.status)}`}>
      {/* Suggestion header */}
      <div className="p-4">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-purple-500 rounded-full flex items-center justify-center text-xs font-medium text-white">
              {suggestion.author.avatar ? (
                <img
                  src={suggestion.author.avatar}
                  alt={suggestion.author.name}
                  className="w-full h-full rounded-full object-cover"
                />
              ) : (
                suggestion.author.name.charAt(0).toUpperCase()
              )}
            </div>

            <div>
              <div className="text-sm font-medium text-gray-900">
                {suggestion.author.name}
              </div>
              <div className="text-xs text-gray-500 flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {formatDistanceToNow(new Date(suggestion.created_at), { addSuffix: true })}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1 text-xs">
              {getStatusIcon(suggestion.status)}
              <span className="text-gray-600">{getStatusText(suggestion.status)}</span>
            </div>

            <button
              onClick={() => setExpanded(!expanded)}
              className="text-gray-400 hover:text-gray-600 p-1 rounded"
            >
              {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>
          </div>
        </div>

        {/* Suggestion description */}
        {suggestion.description && (
          <div className="mb-3">
            <p className="text-sm text-gray-700">{suggestion.description}</p>
          </div>
        )}

        {/* Text changes preview */}
        <div className="suggestion-changes mb-4">
          <div className="text-xs font-medium text-gray-600 mb-2">Suggested changes:</div>

          <div className="bg-white rounded-lg border overflow-hidden">
            {/* Original text */}
            <div className="bg-red-50 border-l-4 border-red-400 p-3">
              <div className="text-xs text-red-600 font-medium mb-1">- Remove</div>
              <pre className="text-sm font-mono whitespace-pre-wrap text-red-800">
                {suggestion.original_text}
              </pre>
            </div>

            {/* Suggested text */}
            <div className="bg-green-50 border-l-4 border-green-400 p-3">
              <div className="text-xs text-green-600 font-medium mb-1">+ Add</div>
              <pre className="text-sm font-mono whitespace-pre-wrap text-green-800">
                {suggestion.suggested_text}
              </pre>
            </div>
          </div>
        </div>

        {/* Action buttons */}
        {canTakeAction && (
          <div className="flex items-center gap-2 mb-3">
            <Button
              onClick={handleAccept}
              disabled={processing}
              className="bg-green-600 hover:bg-green-700 text-white"
              size="sm"
            >
              {processing ? (
                'Accepting...'
              ) : (
                <>
                  <Check className="h-4 w-4 mr-1" />
                  Accept
                </>
              )}
            </Button>

            <Button
              onClick={handleReject}
              disabled={processing}
              variant="outline"
              className="border-red-300 text-red-600 hover:bg-red-50"
              size="sm"
            >
              {processing ? (
                'Rejecting...'
              ) : (
                <>
                  <X className="h-4 w-4 mr-1" />
                  Reject
                </>
              )}
            </Button>
          </div>
        )}

        {/* Review info */}
        {suggestion.status !== 'pending' && suggestion.reviewed_by && (
          <div className="text-xs text-gray-500 mb-3 p-2 bg-gray-100 rounded">
            {suggestion.status === 'accepted' ? 'Accepted' : 'Rejected'} by {suggestion.reviewed_by} {' '}
            {suggestion.reviewed_at && formatDistanceToNow(new Date(suggestion.reviewed_at), { addSuffix: true })}
          </div>
        )}

        {/* Comments section */}
        {expanded && (
          <div className="comments-section border-t pt-3">
            {/* Existing comments */}
            {suggestion.comments.length > 0 && (
              <div className="existing-comments mb-3 space-y-2">
                {suggestion.comments.map((comment) => (
                  <div key={comment.id} className="comment-item p-2 bg-gray-50 rounded">
                    <div className="flex items-start gap-2">
                      <div className="w-4 h-4 bg-gray-400 rounded-full flex items-center justify-center text-xs text-white">
                        {comment.author.name.charAt(0).toUpperCase()}
                      </div>

                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-medium text-gray-700">
                            {comment.author.name}
                          </span>
                          <span className="text-xs text-gray-500">
                            {formatDistanceToNow(new Date(comment.created_at), { addSuffix: true })}
                          </span>
                        </div>

                        <p className="text-xs text-gray-600 whitespace-pre-wrap">
                          {comment.content}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Add comment form */}
            <div className="add-comment-form">
              {showCommentForm ? (
                <form onSubmit={handleAddComment} className="space-y-2">
                  <textarea
                    value={commentContent}
                    onChange={(e) => setCommentContent(e.target.value)}
                    placeholder="Add a comment about this suggestion..."
                    className="w-full p-2 text-xs border border-gray-300 rounded resize-none focus:outline-none focus:ring-1 focus:ring-blue-500"
                    rows={2}
                    autoFocus
                  />
                  <div className="flex items-center gap-2">
                    <Button
                      type="submit"
                      size="sm"
                      disabled={!commentContent.trim() || submittingComment}
                      className="text-xs"
                    >
                      {submittingComment ? (
                        'Adding...'
                      ) : (
                        <>
                          <MessageSquare className="h-3 w-3 mr-1" />
                          Comment
                        </>
                      )}
                    </Button>

                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setShowCommentForm(false);
                        setCommentContent('');
                      }}
                      className="text-xs"
                    >
                      Cancel
                    </Button>
                  </div>
                </form>
              ) : (
                <button
                  onClick={() => setShowCommentForm(true)}
                  className="flex items-center gap-1 text-xs text-gray-600 hover:text-gray-800"
                >
                  <MessageSquare className="h-3 w-3" />
                  Add comment
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export const SuggestionsPanel: React.FC<SuggestionsPanelProps> = ({
  suggestions,
  current_user,
  document_id,
  on_accept_suggestion,
  on_reject_suggestion,
  on_add_comment
}) => {
  const [filter, setFilter] = useState<'all' | 'pending' | 'accepted' | 'rejected'>('pending');

  // Filter suggestions
  const filteredSuggestions = suggestions.filter(suggestion => {
    switch (filter) {
      case 'pending':
        return suggestion.status === 'pending';
      case 'accepted':
        return suggestion.status === 'accepted';
      case 'rejected':
        return suggestion.status === 'rejected';
      default:
        return true;
    }
  });

  // Sort suggestions by creation date (newest first)
  const sortedSuggestions = [...filteredSuggestions].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  const pendingCount = suggestions.filter(s => s.status === 'pending').length;
  const acceptedCount = suggestions.filter(s => s.status === 'accepted').length;
  const rejectedCount = suggestions.filter(s => s.status === 'rejected').length;

  return (
    <div className="suggestions-panel h-full flex flex-col bg-white">
      {/* Panel header */}
      <div className="panel-header p-4 border-b">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Edit3 className="h-5 w-5" />
            Suggestions
          </h3>

          <div className="text-sm text-gray-600">
            {suggestions.length} total
          </div>
        </div>

        {/* Filter tabs */}
        <div className="flex border-b">
          <button
            onClick={() => setFilter('pending')}
            className={`px-3 py-2 text-sm border-b-2 transition-colors ${
              filter === 'pending'
                ? 'border-yellow-500 text-yellow-600 bg-yellow-50'
                : 'border-transparent text-gray-600 hover:text-gray-800'
            }`}
          >
            Pending ({pendingCount})
          </button>

          <button
            onClick={() => setFilter('accepted')}
            className={`px-3 py-2 text-sm border-b-2 transition-colors ${
              filter === 'accepted'
                ? 'border-green-500 text-green-600 bg-green-50'
                : 'border-transparent text-gray-600 hover:text-gray-800'
            }`}
          >
            Accepted ({acceptedCount})
          </button>

          <button
            onClick={() => setFilter('rejected')}
            className={`px-3 py-2 text-sm border-b-2 transition-colors ${
              filter === 'rejected'
                ? 'border-red-500 text-red-600 bg-red-50'
                : 'border-transparent text-gray-600 hover:text-gray-800'
            }`}
          >
            Rejected ({rejectedCount})
          </button>

          <button
            onClick={() => setFilter('all')}
            className={`px-3 py-2 text-sm border-b-2 transition-colors ${
              filter === 'all'
                ? 'border-gray-500 text-gray-600 bg-gray-50'
                : 'border-transparent text-gray-600 hover:text-gray-800'
            }`}
          >
            All ({suggestions.length})
          </button>
        </div>
      </div>

      {/* Suggestions list */}
      <div className="suggestions-list flex-1 overflow-y-auto">
        {sortedSuggestions.length > 0 ? (
          <div className="space-y-1">
            {sortedSuggestions.map((suggestion) => (
              <SuggestionItem
                key={suggestion.id}
                suggestion={suggestion}
                current_user_id={current_user.id}
                on_accept={on_accept_suggestion}
                on_reject={on_reject_suggestion}
                on_add_comment={on_add_comment}
              />
            ))}
          </div>
        ) : (
          <div className="empty-state flex flex-col items-center justify-center h-full text-gray-500 p-8">
            <Edit3 className="h-12 w-12 mb-4 opacity-50" />
            <h4 className="text-lg font-medium mb-2">
              {filter === 'pending' && 'No pending suggestions'}
              {filter === 'accepted' && 'No accepted suggestions'}
              {filter === 'rejected' && 'No rejected suggestions'}
              {filter === 'all' && 'No suggestions yet'}
            </h4>
            <p className="text-sm text-center">
              {filter === 'pending' && 'All suggestions have been reviewed!'}
              {filter === 'accepted' && 'No suggestions have been accepted yet.'}
              {filter === 'rejected' && 'No suggestions have been rejected yet.'}
              {filter === 'all' && 'Suggestions will appear here when collaborators propose changes.'}
            </p>
          </div>
        )}
      </div>

      {/* Help text */}
      <div className="panel-footer p-4 border-t bg-gray-50">
        <div className="text-xs text-gray-600">
          <p className="mb-1">
            <strong>Tip:</strong> Select text in the editor and right-click to suggest changes.
          </p>
          <p>
            Suggestions allow collaborators to propose edits without directly modifying the document.
          </p>
        </div>
      </div>
    </div>
  );
};
