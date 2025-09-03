/**
 * Kanban Board Component
 * Reusable Kanban board for pipeline management
 */

import React, { useState, useCallback, useMemo } from 'react';
import { Card, Button, Badge, Input, Drawer, Avatar, Select } from '@dotmac/primitives';
import { DragDropContext, Droppable, Draggable, DropResult } from '@hello-pangea/dnd';
import {
  Plus,
  MoreHorizontal,
  User,
  Calendar,
  DollarSign,
  Clock,
  Phone,
  Mail,
  Edit,
  Trash2,
} from 'lucide-react';

export interface KanbanCard {
  id: string;
  title: string;
  description?: string;
  value?: number;
  priority: 'low' | 'medium' | 'high';
  assignee?: {
    id: string;
    name: string;
    avatar?: string;
  };
  dueDate?: string;
  tags?: string[];
  metadata?: Record<string, any>;
}

export interface KanbanColumn {
  id: string;
  title: string;
  cards: KanbanCard[];
  color?: string;
  limit?: number;
  allowAdd?: boolean;
  allowDrop?: boolean;
}

export interface KanbanBoardProps {
  columns: KanbanColumn[];
  onCardMove: (cardId: string, sourceColumn: string, destColumn: string, destIndex: number) => void;
  onCardAdd?: (columnId: string, card: Omit<KanbanCard, 'id'>) => void;
  onCardEdit?: (card: KanbanCard) => void;
  onCardDelete?: (cardId: string) => void;
  onCardClick?: (card: KanbanCard) => void;
  cardComponent?: React.ComponentType<{
    card: KanbanCard;
    onEdit?: () => void;
    onDelete?: () => void;
  }>;
  showAddCard?: boolean;
  showColumnLimits?: boolean;
  className?: string;
}

// Default card component
function DefaultKanbanCard({
  card,
  onEdit,
  onDelete,
}: {
  card: KanbanCard;
  onEdit?: () => void;
  onDelete?: () => void;
}) {
  const priorityColors = {
    low: 'bg-gray-100 text-gray-700',
    medium: 'bg-yellow-100 text-yellow-700',
    high: 'bg-red-100 text-red-700',
  };

  const handleActionClick = (e: React.MouseEvent, action: () => void) => {
    e.stopPropagation();
    action();
  };

  return (
    <Card className='p-4 mb-3 cursor-pointer hover:shadow-md transition-shadow'>
      <div className='flex items-start justify-between mb-2'>
        <h4 className='font-medium text-sm leading-tight flex-1 pr-2'>{card.title}</h4>
        <div className='flex items-center gap-1'>
          {onEdit && (
            <Button
              size='sm'
              variant='ghost'
              onClick={(e) => handleActionClick(e, onEdit)}
              className='h-6 w-6 p-0'
            >
              <Edit className='w-3 h-3' />
            </Button>
          )}
          {onDelete && (
            <Button
              size='sm'
              variant='ghost'
              onClick={(e) => handleActionClick(e, onDelete)}
              className='h-6 w-6 p-0 text-red-500'
            >
              <Trash2 className='w-3 h-3' />
            </Button>
          )}
        </div>
      </div>

      {card.description && (
        <p className='text-xs text-gray-600 mb-3 line-clamp-2'>{card.description}</p>
      )}

      <div className='space-y-2'>
        {card.value && (
          <div className='flex items-center text-xs text-gray-500'>
            <DollarSign className='w-3 h-3 mr-1' />${card.value.toLocaleString()}
          </div>
        )}

        {card.dueDate && (
          <div className='flex items-center text-xs text-gray-500'>
            <Calendar className='w-3 h-3 mr-1' />
            {new Date(card.dueDate).toLocaleDateString()}
          </div>
        )}

        <div className='flex items-center justify-between'>
          <div className='flex items-center gap-1'>
            <Badge variant='secondary' className={`text-xs ${priorityColors[card.priority]}`}>
              {card.priority}
            </Badge>

            {card.tags?.slice(0, 2).map((tag) => (
              <Badge key={tag} variant='outline' className='text-xs'>
                {tag}
              </Badge>
            ))}
          </div>

          {card.assignee && (
            <div className='flex items-center'>
              <Avatar
                src={card.assignee.avatar}
                alt={card.assignee.name}
                size='sm'
                className='w-6 h-6'
              />
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}

export function KanbanBoard({
  columns,
  onCardMove,
  onCardAdd,
  onCardEdit,
  onCardDelete,
  onCardClick,
  cardComponent: CardComponent = DefaultKanbanCard,
  showAddCard = true,
  showColumnLimits = true,
  className = '',
}: KanbanBoardProps) {
  const [draggedCard, setDraggedCard] = useState<KanbanCard | null>(null);
  const [newCardColumn, setNewCardColumn] = useState<string | null>(null);
  const [newCardData, setNewCardData] = useState<Partial<KanbanCard>>({});

  // Calculate column statistics
  const columnStats = useMemo(() => {
    return columns.reduce(
      (acc, column) => {
        const totalValue = column.cards.reduce((sum, card) => sum + (card.value || 0), 0);
        acc[column.id] = {
          count: column.cards.length,
          totalValue,
          limitReached: column.limit ? column.cards.length >= column.limit : false,
        };
        return acc;
      },
      {} as Record<string, { count: number; totalValue: number; limitReached: boolean }>
    );
  }, [columns]);

  const handleDragEnd = useCallback(
    (result: DropResult) => {
      const { draggableId, source, destination } = result;

      // Dropped outside valid droppable area
      if (!destination) {
        setDraggedCard(null);
        return;
      }

      // Dropped in same position
      if (destination.droppableId === source.droppableId && destination.index === source.index) {
        setDraggedCard(null);
        return;
      }

      // Check if destination column accepts drops
      const destColumn = columns.find((col) => col.id === destination.droppableId);
      if (destColumn && destColumn.allowDrop === false) {
        setDraggedCard(null);
        return;
      }

      // Emit action event for observability
      const event = new CustomEvent('ui.action.card-move', {
        detail: {
          cardId: draggableId,
          from: source.droppableId,
          to: destination.droppableId,
          timestamp: new Date().toISOString(),
        },
      });
      window.dispatchEvent(event);

      onCardMove(draggableId, source.droppableId, destination.droppableId, destination.index);
      setDraggedCard(null);
    },
    [columns, onCardMove]
  );

  const handleDragStart = useCallback(
    (start: any) => {
      const card = columns
        .flatMap((col) => col.cards)
        .find((card) => card.id === start.draggableId);
      setDraggedCard(card || null);
    },
    [columns]
  );

  const handleAddCard = useCallback(() => {
    if (!newCardColumn || !onCardAdd) return;

    if (!newCardData.title?.trim()) {
      alert('Please enter a title for the card');
      return;
    }

    const cardData: Omit<KanbanCard, 'id'> = {
      title: newCardData.title,
      description: newCardData.description || '',
      priority: (newCardData.priority as KanbanCard['priority']) || 'medium',
      value: newCardData.value,
      tags: newCardData.tags || [],
    };

    onCardAdd(newCardColumn, cardData);
    setNewCardColumn(null);
    setNewCardData({});

    // Emit action event
    const event = new CustomEvent('ui.action.card-add', {
      detail: {
        column: newCardColumn,
        timestamp: new Date().toISOString(),
      },
    });
    window.dispatchEvent(event);
  }, [newCardColumn, newCardData, onCardAdd]);

  const handleCardClick = useCallback(
    (card: KanbanCard) => {
      // Emit action event
      const event = new CustomEvent('ui.action.card-click', {
        detail: {
          cardId: card.id,
          timestamp: new Date().toISOString(),
        },
      });
      window.dispatchEvent(event);

      onCardClick?.(card);
    },
    [onCardClick]
  );

  return (
    <div className={`flex gap-6 overflow-x-auto pb-4 ${className}`}>
      <DragDropContext onDragEnd={handleDragEnd} onDragStart={handleDragStart}>
        {columns.map((column) => {
          const stats = columnStats[column.id];

          return (
            <div key={column.id} className='flex-shrink-0 w-80'>
              {/* Column Header */}
              <div className='flex items-center justify-between mb-4 p-3 bg-gray-50 rounded-lg'>
                <div className='flex items-center gap-2'>
                  {column.color && (
                    <div
                      className='w-3 h-3 rounded-full'
                      style={{ backgroundColor: column.color }}
                    />
                  )}
                  <h3 className='font-medium text-gray-900'>{column.title}</h3>
                  <Badge variant='secondary' className='text-xs'>
                    {stats.count}
                  </Badge>
                </div>

                {showAddCard && column.allowAdd !== false && onCardAdd && (
                  <Button
                    size='sm'
                    variant='ghost'
                    onClick={() => setNewCardColumn(column.id)}
                    disabled={stats.limitReached}
                    data-testid={`add-card-${column.id}`}
                  >
                    <Plus className='w-4 h-4' />
                  </Button>
                )}
              </div>

              {/* Column Stats */}
              {showColumnLimits && (
                <div className='mb-3 text-xs text-gray-500 px-3'>
                  {stats.totalValue > 0 && <div>Value: ${stats.totalValue.toLocaleString()}</div>}
                  {column.limit && (
                    <div className={stats.limitReached ? 'text-red-500' : ''}>
                      {stats.count}/{column.limit} items
                    </div>
                  )}
                </div>
              )}

              {/* Droppable Column */}
              <Droppable droppableId={column.id}>
                {(provided, snapshot) => (
                  <div
                    ref={provided.innerRef}
                    {...provided.droppableProps}
                    className={`min-h-32 p-3 rounded-lg transition-colors ${
                      snapshot.isDraggingOver ? 'bg-blue-50 border-2 border-blue-200' : 'bg-gray-25'
                    }`}
                    data-testid={`column-${column.id}`}
                  >
                    {column.cards.map((card, index) => (
                      <Draggable key={card.id} draggableId={card.id} index={index}>
                        {(provided, snapshot) => (
                          <div
                            ref={provided.innerRef}
                            {...provided.draggableProps}
                            {...provided.dragHandleProps}
                            className={`${snapshot.isDragging ? 'opacity-50 rotate-2' : ''}`}
                            onClick={() => handleCardClick(card)}
                            data-testid={`card-${card.id}`}
                          >
                            <CardComponent
                              card={card}
                              onEdit={onCardEdit ? () => onCardEdit(card) : undefined}
                              onDelete={onCardDelete ? () => onCardDelete(card.id) : undefined}
                            />
                          </div>
                        )}
                      </Draggable>
                    ))}
                    {provided.placeholder}
                  </div>
                )}
              </Droppable>
            </div>
          );
        })}
      </DragDropContext>

      {/* Add Card Modal */}
      {newCardColumn && (
        <Drawer
          isOpen={!!newCardColumn}
          onClose={() => setNewCardColumn(null)}
          title='Add New Card'
          size='md'
        >
          <div className='space-y-4'>
            <Input
              placeholder='Card title'
              value={newCardData.title || ''}
              onChange={(e) => setNewCardData((prev) => ({ ...prev, title: e.target.value }))}
              autoFocus
            />

            <Input
              placeholder='Description (optional)'
              value={newCardData.description || ''}
              onChange={(e) => setNewCardData((prev) => ({ ...prev, description: e.target.value }))}
            />

            <Input
              type='number'
              placeholder='Value (optional)'
              value={newCardData.value || ''}
              onChange={(e) =>
                setNewCardData((prev) => ({
                  ...prev,
                  value: e.target.value ? Number(e.target.value) : undefined,
                }))
              }
            />

            <Select
              value={newCardData.priority || 'medium'}
              onChange={(value) =>
                setNewCardData((prev) => ({ ...prev, priority: value as KanbanCard['priority'] }))
              }
            >
              <option value='low'>Low Priority</option>
              <option value='medium'>Medium Priority</option>
              <option value='high'>High Priority</option>
            </Select>

            <div className='flex gap-3 pt-4'>
              <Button onClick={handleAddCard}>Add Card</Button>
              <Button variant='outline' onClick={() => setNewCardColumn(null)}>
                Cancel
              </Button>
            </div>
          </div>
        </Drawer>
      )}
    </div>
  );
}

export default KanbanBoard;
