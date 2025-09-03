import React, { useState, useCallback } from 'react';
import { Button, Input, Card } from '@dotmac/ui';
import { MessageSquare, Send, Check, Reply, MoreVertical, Clock, User, X } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

import type { CommentsPanelProps, Comment, CommentReply } from '../types';

interface CommentItemProps {
  comment: Comment;
  current_user_id: string;
  on_resolve?: (comment_id: string) => void;
  on_reply?: (comment_id: string, content: string) => void;
}

const CommentItem: React.FC<CommentItemProps> = ({
  comment,
  current_user_id,
  on_resolve,
  on_reply,
}) => {
  const [showReplyForm, setShowReplyForm] = useState(false);
  const [replyContent, setReplyContent] = useState('');
  const [submittingReply, setSubmittingReply] = useState(false);

  const handleReply = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!replyContent.trim()) return;

      try {
        setSubmittingReply(true);
        await on_reply?.(comment.id, replyContent);
        setReplyContent('');
        setShowReplyForm(false);
      } catch (err) {
        console.error('Failed to add reply:', err);
      } finally {
        setSubmittingReply(false);
      }
    },
    [comment.id, replyContent, on_reply]
  );

  const handleResolve = useCallback(() => {
    on_resolve?.(comment.id);
  }, [comment.id, on_resolve]);

  return (
    <div
      className={`comment-item p-4 border-l-4 ${
        comment.resolved ? 'border-green-400 bg-green-50' : 'border-blue-400 bg-blue-50'
      }`}
    >
      {/* Comment header */}
      <div className='comment-header flex items-start justify-between mb-2'>
        <div className='flex items-center gap-2'>
          <div className='w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center text-xs font-medium text-white'>
            {comment.author.avatar ? (
              <img
                src={comment.author.avatar}
                alt={comment.author.name}
                className='w-full h-full rounded-full object-cover'
              />
            ) : (
              comment.author.name.charAt(0).toUpperCase()
            )}
          </div>

          <div>
            <div className='text-sm font-medium text-gray-900'>{comment.author.name}</div>
            <div className='text-xs text-gray-500 flex items-center gap-1'>
              <Clock className='h-3 w-3' />
              {formatDistanceToNow(new Date(comment.created_at), { addSuffix: true })}
            </div>
          </div>
        </div>

        <div className='flex items-center gap-1'>
          {comment.resolved ? (
            <div className='flex items-center gap-1 text-green-600 text-xs'>
              <Check className='h-3 w-3' />
              Resolved
            </div>
          ) : (
            <button
              onClick={handleResolve}
              className='text-gray-400 hover:text-green-600 p-1 rounded'
              title='Mark as resolved'
            >
              <Check className='h-3 w-3' />
            </button>
          )}

          <button className='text-gray-400 hover:text-gray-600 p-1 rounded'>
            <MoreVertical className='h-3 w-3' />
          </button>
        </div>
      </div>

      {/* Comment content */}
      <div className='comment-content mb-3'>
        <p className='text-sm text-gray-800 whitespace-pre-wrap'>{comment.content}</p>

        {comment.position.selection && (
          <div className='mt-2 p-2 bg-gray-100 rounded text-xs'>
            <div className='text-gray-600 mb-1'>Referenced text:</div>
            <div className='font-mono bg-white p-1 rounded border'>
              "{comment.position.selection.text}"
            </div>
            <div className='text-gray-500 mt-1'>
              Line {comment.position.line + 1}, Column {comment.position.column + 1}
            </div>
          </div>
        )}
      </div>

      {/* Replies */}
      {comment.replies.length > 0 && (
        <div className='comment-replies ml-4 border-l-2 border-gray-200 pl-3'>
          {comment.replies.map((reply) => (
            <div
              key={reply.id}
              className='reply-item py-2 border-b border-gray-100 last:border-b-0'
            >
              <div className='flex items-start gap-2'>
                <div className='w-4 h-4 bg-gray-400 rounded-full flex items-center justify-center text-xs text-white'>
                  {reply.author.name.charAt(0).toUpperCase()}
                </div>

                <div className='flex-1'>
                  <div className='flex items-center gap-2 mb-1'>
                    <span className='text-xs font-medium text-gray-700'>{reply.author.name}</span>
                    <span className='text-xs text-gray-500'>
                      {formatDistanceToNow(new Date(reply.created_at), { addSuffix: true })}
                    </span>
                  </div>

                  <p className='text-xs text-gray-600 whitespace-pre-wrap'>{reply.content}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Reply form */}
      {!comment.resolved && (
        <div className='comment-actions mt-3'>
          {showReplyForm ? (
            <form onSubmit={handleReply} className='space-y-2'>
              <textarea
                value={replyContent}
                onChange={(e) => setReplyContent(e.target.value)}
                placeholder='Add a reply...'
                className='w-full p-2 text-xs border border-gray-300 rounded resize-none focus:outline-none focus:ring-1 focus:ring-blue-500'
                rows={2}
                autoFocus
              />
              <div className='flex items-center gap-2'>
                <Button
                  type='submit'
                  size='sm'
                  disabled={!replyContent.trim() || submittingReply}
                  className='text-xs'
                >
                  {submittingReply ? (
                    'Replying...'
                  ) : (
                    <>
                      <Send className='h-3 w-3 mr-1' />
                      Reply
                    </>
                  )}
                </Button>

                <Button
                  type='button'
                  variant='outline'
                  size='sm'
                  onClick={() => {
                    setShowReplyForm(false);
                    setReplyContent('');
                  }}
                  className='text-xs'
                >
                  <X className='h-3 w-3 mr-1' />
                  Cancel
                </Button>
              </div>
            </form>
          ) : (
            <button
              onClick={() => setShowReplyForm(true)}
              className='flex items-center gap-1 text-xs text-gray-600 hover:text-gray-800'
            >
              <Reply className='h-3 w-3' />
              Reply
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export const CommentsPanel: React.FC<CommentsPanelProps> = ({
  comments,
  current_user,
  document_id,
  on_add_comment,
  on_resolve_comment,
  on_reply_comment,
}) => {
  const [newComment, setNewComment] = useState('');
  const [submittingComment, setSubmittingComment] = useState(false);
  const [filter, setFilter] = useState<'all' | 'unresolved' | 'resolved'>('unresolved');

  const handleAddComment = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!newComment.trim()) return;

      try {
        setSubmittingComment(true);
        await on_add_comment?.({
          content: newComment,
          position: {
            line: 0,
            column: 0,
          },
          resolved: false,
          replies: [],
        });
        setNewComment('');
      } catch (err) {
        console.error('Failed to add comment:', err);
      } finally {
        setSubmittingComment(false);
      }
    },
    [newComment, on_add_comment]
  );

  const handleReplyToComment = useCallback(
    async (comment_id: string, content: string) => {
      await on_reply_comment?.(comment_id, content);
    },
    [on_reply_comment]
  );

  // Filter comments
  const filteredComments = comments.filter((comment) => {
    switch (filter) {
      case 'resolved':
        return comment.resolved;
      case 'unresolved':
        return !comment.resolved;
      default:
        return true;
    }
  });

  // Sort comments by creation date (newest first)
  const sortedComments = [...filteredComments].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  const unresolvedCount = comments.filter((c) => !c.resolved).length;
  const resolvedCount = comments.filter((c) => c.resolved).length;

  return (
    <div className='comments-panel h-full flex flex-col bg-white'>
      {/* Panel header */}
      <div className='panel-header p-4 border-b'>
        <div className='flex items-center justify-between mb-4'>
          <h3 className='text-lg font-semibold flex items-center gap-2'>
            <MessageSquare className='h-5 w-5' />
            Comments
          </h3>

          <div className='text-sm text-gray-600'>{comments.length} total</div>
        </div>

        {/* Filter tabs */}
        <div className='flex border-b'>
          <button
            onClick={() => setFilter('unresolved')}
            className={`px-3 py-2 text-sm border-b-2 transition-colors ${
              filter === 'unresolved'
                ? 'border-blue-500 text-blue-600 bg-blue-50'
                : 'border-transparent text-gray-600 hover:text-gray-800'
            }`}
          >
            Open ({unresolvedCount})
          </button>

          <button
            onClick={() => setFilter('resolved')}
            className={`px-3 py-2 text-sm border-b-2 transition-colors ${
              filter === 'resolved'
                ? 'border-green-500 text-green-600 bg-green-50'
                : 'border-transparent text-gray-600 hover:text-gray-800'
            }`}
          >
            Resolved ({resolvedCount})
          </button>

          <button
            onClick={() => setFilter('all')}
            className={`px-3 py-2 text-sm border-b-2 transition-colors ${
              filter === 'all'
                ? 'border-gray-500 text-gray-600 bg-gray-50'
                : 'border-transparent text-gray-600 hover:text-gray-800'
            }`}
          >
            All ({comments.length})
          </button>
        </div>
      </div>

      {/* New comment form */}
      <div className='new-comment-form p-4 border-b'>
        <form onSubmit={handleAddComment} className='space-y-3'>
          <textarea
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            placeholder='Add a comment about the document...'
            className='w-full p-3 text-sm border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            rows={3}
          />

          <div className='flex items-center justify-between'>
            <div className='text-xs text-gray-500'>
              Tip: Select text in the editor to comment on specific sections
            </div>

            <Button type='submit' size='sm' disabled={!newComment.trim() || submittingComment}>
              {submittingComment ? (
                'Adding...'
              ) : (
                <>
                  <Send className='h-4 w-4 mr-1' />
                  Add Comment
                </>
              )}
            </Button>
          </div>
        </form>
      </div>

      {/* Comments list */}
      <div className='comments-list flex-1 overflow-y-auto'>
        {sortedComments.length > 0 ? (
          <div className='space-y-1'>
            {sortedComments.map((comment) => (
              <CommentItem
                key={comment.id}
                comment={comment}
                current_user_id={current_user.id}
                on_resolve={on_resolve_comment}
                on_reply={handleReplyToComment}
              />
            ))}
          </div>
        ) : (
          <div className='empty-state flex flex-col items-center justify-center h-full text-gray-500 p-8'>
            <MessageSquare className='h-12 w-12 mb-4 opacity-50' />
            <h4 className='text-lg font-medium mb-2'>
              {filter === 'unresolved' && 'No open comments'}
              {filter === 'resolved' && 'No resolved comments'}
              {filter === 'all' && 'No comments yet'}
            </h4>
            <p className='text-sm text-center'>
              {filter === 'unresolved' && 'All comments have been resolved!'}
              {filter === 'resolved' && 'No comments have been resolved yet.'}
              {filter === 'all' && 'Start a conversation by adding the first comment.'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
