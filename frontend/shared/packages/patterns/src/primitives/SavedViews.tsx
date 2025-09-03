/**
 * Saved Views
 * Component for managing saved filter/view configurations
 */

import React, { useState, useCallback, useMemo } from 'react';
import { clsx } from 'clsx';
import { trackAction } from '@dotmac/monitoring/observability';
import {
  Button,
  Input,
  Card,
  Badge,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  Textarea,
  Checkbox,
  Select,
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@dotmac/primitives';
import { withComponentRegistration } from '@dotmac/registry';
import { SavedViewConfig, validateTemplateConfig, SavedViewConfigSchema } from '../types/templates';
import {
  Bookmark,
  BookmarkPlus,
  Star,
  Share2,
  Edit3,
  Trash2,
  Eye,
  EyeOff,
  Users,
  Lock,
  Calendar,
  Filter,
  Search,
  MoreHorizontal,
  Copy,
  Download,
} from 'lucide-react';

export interface SavedViewsProps {
  views: SavedViewConfig[];
  activeViewId?: string;
  currentFilters?: Record<string, any>;
  currentSorting?: {
    field: string;
    direction: 'asc' | 'desc';
  };
  currentColumns?: string[];
  canCreateViews?: boolean;
  canEditViews?: boolean;
  canDeleteViews?: boolean;
  canShareViews?: boolean;
  showPublicViews?: boolean;
  className?: string;
  onViewLoad?: (view: SavedViewConfig) => void;
  onViewSave?: (view: Omit<SavedViewConfig, 'id' | 'createdAt'>) => void;
  onViewUpdate?: (viewId: string, updates: Partial<SavedViewConfig>) => void;
  onViewDelete?: (viewId: string) => void;
  onViewShare?: (viewId: string, isPublic: boolean) => void;
  onViewDuplicate?: (viewId: string) => void;
  onViewExport?: (viewId: string, format: 'json' | 'url') => void;
  'data-testid'?: string;
}

interface SavedViewFormData {
  name: string;
  description?: string;
  isDefault: boolean;
  isPublic: boolean;
}

function SavedViewsImpl({
  views = [],
  activeViewId,
  currentFilters = {},
  currentSorting,
  currentColumns,
  canCreateViews = true,
  canEditViews = true,
  canDeleteViews = true,
  canShareViews = false,
  showPublicViews = true,
  className = '',
  onViewLoad,
  onViewSave,
  onViewUpdate,
  onViewDelete,
  onViewShare,
  onViewDuplicate,
  onViewExport,
  'data-testid': testId = 'saved-views',
}: SavedViewsProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'name' | 'created' | 'modified'>('name');
  const [filterBy, setFilterBy] = useState<'all' | 'mine' | 'public' | 'default'>('all');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingView, setEditingView] = useState<SavedViewConfig | null>(null);
  const [formData, setFormData] = useState<SavedViewFormData>({
    name: '',
    description: '',
    isDefault: false,
    isPublic: false,
  });
  const [deleteViewId, setDeleteViewId] = useState<string | null>(null);

  // Filter and sort views
  const filteredViews = useMemo(() => {
    let filtered = views.filter((view) => {
      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        if (
          !view.name.toLowerCase().includes(query) &&
          !view.createdBy?.toLowerCase().includes(query)
        ) {
          return false;
        }
      }

      // Category filter
      switch (filterBy) {
        case 'mine':
          return view.createdBy === 'current-user'; // TODO: Get actual current user
        case 'public':
          return view.isPublic;
        case 'default':
          return view.isDefault;
        default:
          return true;
      }
    });

    // Sort views
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'name':
          return a.name.localeCompare(b.name);
        case 'created':
          return (b.createdAt?.getTime() || 0) - (a.createdAt?.getTime() || 0);
        case 'modified':
          // TODO: Add modified date to schema
          return a.name.localeCompare(b.name);
        default:
          return 0;
      }
    });

    return filtered;
  }, [views, searchQuery, sortBy, filterBy]);

  // Group views by category
  const groupedViews = useMemo(() => {
    const groups: Record<string, SavedViewConfig[]> = {};

    filteredViews.forEach((view) => {
      const category = view.isDefault ? 'default' : view.isPublic ? 'public' : 'private';

      if (!groups[category]) {
        groups[category] = [];
      }
      groups[category].push(view);
    });

    return groups;
  }, [filteredViews]);

  // Reset form
  const resetForm = useCallback(() => {
    setFormData({
      name: '',
      description: '',
      isDefault: false,
      isPublic: false,
    });
    setEditingView(null);
  }, []);

  // Handle create/edit view
  const handleSaveView = useCallback(async () => {
    if (!formData.name.trim()) return;

    const viewData = {
      name: formData.name.trim(),
      filters: currentFilters,
      sorting: currentSorting,
      columns: currentColumns,
      isDefault: formData.isDefault,
      isPublic: formData.isPublic,
      createdBy: 'current-user', // TODO: Get actual current user
    };

    // Validate view data
    const validation = validateTemplateConfig(SavedViewConfigSchema, {
      ...viewData,
      id: editingView?.id || 'temp',
      createdAt: editingView?.createdAt || new Date(),
    });

    if (!validation.isValid) {
      console.error('Invalid view data:', validation.errors);
      return;
    }

    try {
      if (editingView) {
        onViewUpdate?.(editingView.id, viewData);
        trackAction('saved_view_update', 'interaction', { name: formData.name });
      } else {
        onViewSave?.(viewData);
        trackAction('saved_view_create', 'interaction', { name: formData.name });
      }

      setShowCreateDialog(false);
      resetForm();
    } catch (error) {
      console.error('Failed to save view:', error);
    }
  }, [
    formData,
    currentFilters,
    currentSorting,
    currentColumns,
    editingView,
    onViewSave,
    onViewUpdate,
  ]);

  // Handle load view
  const handleLoadView = useCallback(
    (view: SavedViewConfig) => {
      onViewLoad?.(view);

      try {
        trackAction('saved_view_load', 'interaction', { viewId: view.id, name: view.name });
      } catch {}
    },
    [onViewLoad]
  );

  // Handle delete view
  const handleDeleteView = useCallback(
    (viewId: string) => {
      onViewDelete?.(viewId);
      setDeleteViewId(null);

      try {
        trackAction('saved_view_delete', 'interaction', { viewId });
      } catch {}
    },
    [onViewDelete]
  );

  // Handle duplicate view
  const handleDuplicateView = useCallback(
    (view: SavedViewConfig) => {
      const duplicatedView = {
        name: `${view.name} (Copy)`,
        filters: view.filters,
        sorting: view.sorting,
        columns: view.columns,
        isDefault: false,
        isPublic: false,
        createdBy: 'current-user',
      };

      onViewSave?.(duplicatedView);

      try {
        trackAction('saved_view_duplicate', 'interaction', { originalId: view.id });
      } catch {}
    },
    [onViewSave]
  );

  // Handle share view
  const handleShareView = useCallback(
    (viewId: string, isPublic: boolean) => {
      onViewShare?.(viewId, isPublic);

      try {
        trackAction('saved_view_share', 'interaction', { viewId, isPublic });
      } catch {}
    },
    [onViewShare]
  );

  // Handle export view
  const handleExportView = useCallback(
    (view: SavedViewConfig, format: 'json' | 'url') => {
      onViewExport?.(view.id, format);

      try {
        trackAction('saved_view_export', 'interaction', { viewId: view.id, format });
      } catch {}
    },
    [onViewExport]
  );

  // Handle edit view
  const handleEditView = useCallback((view: SavedViewConfig) => {
    setEditingView(view);
    setFormData({
      name: view.name,
      description: '',
      isDefault: view.isDefault,
      isPublic: view.isPublic,
    });
    setShowCreateDialog(true);
  }, []);

  // Get active filters count
  const activeFiltersCount = Object.keys(currentFilters).length;

  return (
    <div className={clsx('space-y-4', className)} data-testid={testId}>
      {/* Header */}
      <div className='flex items-center justify-between'>
        <div className='flex items-center space-x-4'>
          <h3 className='text-lg font-medium'>Saved Views</h3>
          <Badge variant='secondary'>{views.length}</Badge>
        </div>

        {canCreateViews && (
          <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
            <DialogTrigger asChild>
              <Button
                size='sm'
                className='flex items-center space-x-2'
                onClick={resetForm}
                data-testid={`${testId}-create-button`}
              >
                <BookmarkPlus className='h-4 w-4' />
                <span>Save Current View</span>
              </Button>
            </DialogTrigger>
            <DialogContent className='max-w-md'>
              <DialogHeader>
                <DialogTitle>{editingView ? 'Edit View' : 'Save Current View'}</DialogTitle>
              </DialogHeader>

              <div className='space-y-4'>
                <div>
                  <label className='text-sm font-medium mb-2 block'>View Name *</label>
                  <Input
                    value={formData.name}
                    onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
                    placeholder='Enter view name...'
                    data-testid={`${testId}-name-input`}
                  />
                </div>

                <div>
                  <label className='text-sm font-medium mb-2 block'>Description</label>
                  <Textarea
                    value={formData.description}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, description: e.target.value }))
                    }
                    placeholder='Optional description...'
                    rows={2}
                  />
                </div>

                <div className='space-y-2'>
                  <label className='flex items-center space-x-2'>
                    <Checkbox
                      checked={formData.isDefault}
                      onChange={(checked) =>
                        setFormData((prev) => ({ ...prev, isDefault: checked }))
                      }
                      data-testid={`${testId}-default-checkbox`}
                    />
                    <span className='text-sm'>Set as default view</span>
                  </label>

                  {canShareViews && (
                    <label className='flex items-center space-x-2'>
                      <Checkbox
                        checked={formData.isPublic}
                        onChange={(checked) =>
                          setFormData((prev) => ({ ...prev, isPublic: checked }))
                        }
                        data-testid={`${testId}-public-checkbox`}
                      />
                      <span className='text-sm'>Make public (visible to all users)</span>
                    </label>
                  )}
                </div>

                {/* Current State Summary */}
                <div className='border-t pt-4'>
                  <h4 className='text-sm font-medium mb-2'>Current State</h4>
                  <div className='text-xs text-muted-foreground space-y-1'>
                    <div>Filters: {activeFiltersCount} active</div>
                    {currentSorting && (
                      <div>
                        Sort: {currentSorting.field} ({currentSorting.direction})
                      </div>
                    )}
                    {currentColumns && <div>Columns: {currentColumns.length} selected</div>}
                  </div>
                </div>

                <div className='flex justify-end space-x-2 pt-4'>
                  <Button variant='outline' onClick={() => setShowCreateDialog(false)}>
                    Cancel
                  </Button>
                  <Button
                    onClick={handleSaveView}
                    disabled={!formData.name.trim()}
                    data-testid={`${testId}-save-button`}
                  >
                    {editingView ? 'Update View' : 'Save View'}
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {/* Filters and Search */}
      <div className='flex items-center justify-between space-x-4'>
        <div className='flex items-center space-x-2 flex-1'>
          <div className='relative flex-1 max-w-sm'>
            <Search className='absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground' />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder='Search views...'
              className='pl-10'
              data-testid={`${testId}-search`}
            />
          </div>
        </div>

        <div className='flex items-center space-x-2'>
          <Select
            value={filterBy}
            onChange={(value) => setFilterBy(value as typeof filterBy)}
            data-testid={`${testId}-filter-select`}
          >
            <option value='all'>All Views</option>
            <option value='mine'>My Views</option>
            {showPublicViews && <option value='public'>Public Views</option>}
            <option value='default'>Default Views</option>
          </Select>

          <Select
            value={sortBy}
            onChange={(value) => setSortBy(value as typeof sortBy)}
            data-testid={`${testId}-sort-select`}
          >
            <option value='name'>Sort by Name</option>
            <option value='created'>Sort by Created</option>
            <option value='modified'>Sort by Modified</option>
          </Select>
        </div>
      </div>

      {/* Views List */}
      <div className='space-y-4'>
        {Object.entries(groupedViews).map(([category, categoryViews]) => (
          <div key={category}>
            <h4 className='text-sm font-medium text-muted-foreground mb-2 capitalize'>
              {category} Views ({categoryViews.length})
            </h4>

            <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3'>
              {categoryViews.map((view) => (
                <Card
                  key={view.id}
                  className={clsx(
                    'p-4 cursor-pointer transition-all hover:shadow-md',
                    activeViewId === view.id && 'ring-2 ring-primary'
                  )}
                  onClick={() => handleLoadView(view)}
                  data-testid={`${testId}-view-${view.id}`}
                >
                  <div className='flex items-start justify-between'>
                    <div className='flex-1 min-w-0'>
                      <div className='flex items-center space-x-2 mb-1'>
                        <h5 className='font-medium truncate'>{view.name}</h5>
                        <div className='flex items-center space-x-1'>
                          {view.isDefault && (
                            <Star className='h-3 w-3 text-yellow-500' title='Default view' />
                          )}
                          {view.isPublic ? (
                            <Users className='h-3 w-3 text-blue-500' title='Public view' />
                          ) : (
                            <Lock className='h-3 w-3 text-gray-400' title='Private view' />
                          )}
                        </div>
                      </div>

                      <div className='text-xs text-muted-foreground space-y-1'>
                        {Object.keys(view.filters).length > 0 && (
                          <div className='flex items-center space-x-1'>
                            <Filter className='h-3 w-3' />
                            <span>{Object.keys(view.filters).length} filters</span>
                          </div>
                        )}
                        {view.createdAt && (
                          <div className='flex items-center space-x-1'>
                            <Calendar className='h-3 w-3' />
                            <span>{view.createdAt.toLocaleDateString()}</span>
                          </div>
                        )}
                        {view.createdBy && <div>Created by {view.createdBy}</div>}
                      </div>
                    </div>

                    {/* Action Menu */}
                    <Dialog>
                      <DialogTrigger asChild>
                        <Button
                          variant='ghost'
                          size='icon'
                          className='h-6 w-6'
                          onClick={(e) => e.stopPropagation()}
                        >
                          <MoreHorizontal className='h-3 w-3' />
                        </Button>
                      </DialogTrigger>
                      <DialogContent className='max-w-xs p-2'>
                        <div className='space-y-1'>
                          {canEditViews && (
                            <Button
                              variant='ghost'
                              size='sm'
                              onClick={(e) => {
                                e.stopPropagation();
                                handleEditView(view);
                              }}
                              className='w-full justify-start'
                            >
                              <Edit3 className='h-4 w-4 mr-2' />
                              Edit
                            </Button>
                          )}

                          <Button
                            variant='ghost'
                            size='sm'
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDuplicateView(view);
                            }}
                            className='w-full justify-start'
                          >
                            <Copy className='h-4 w-4 mr-2' />
                            Duplicate
                          </Button>

                          {canShareViews && (
                            <Button
                              variant='ghost'
                              size='sm'
                              onClick={(e) => {
                                e.stopPropagation();
                                handleShareView(view.id, !view.isPublic);
                              }}
                              className='w-full justify-start'
                            >
                              <Share2 className='h-4 w-4 mr-2' />
                              {view.isPublic ? 'Make Private' : 'Make Public'}
                            </Button>
                          )}

                          <Button
                            variant='ghost'
                            size='sm'
                            onClick={(e) => {
                              e.stopPropagation();
                              handleExportView(view, 'json');
                            }}
                            className='w-full justify-start'
                          >
                            <Download className='h-4 w-4 mr-2' />
                            Export
                          </Button>

                          {canDeleteViews && (
                            <AlertDialog>
                              <AlertDialogTrigger asChild>
                                <Button
                                  variant='ghost'
                                  size='sm'
                                  onClick={(e) => e.stopPropagation()}
                                  className='w-full justify-start text-destructive hover:text-destructive'
                                >
                                  <Trash2 className='h-4 w-4 mr-2' />
                                  Delete
                                </Button>
                              </AlertDialogTrigger>
                              <AlertDialogContent>
                                <AlertDialogHeader>
                                  <AlertDialogTitle>Delete View</AlertDialogTitle>
                                  <AlertDialogDescription>
                                    Are you sure you want to delete "{view.name}"? This action
                                    cannot be undone.
                                  </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                                  <AlertDialogAction
                                    onClick={() => handleDeleteView(view.id)}
                                    className='bg-destructive text-destructive-foreground hover:bg-destructive/90'
                                  >
                                    Delete
                                  </AlertDialogAction>
                                </AlertDialogFooter>
                              </AlertDialogContent>
                            </AlertDialog>
                          )}
                        </div>
                      </DialogContent>
                    </Dialog>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        ))}

        {filteredViews.length === 0 && (
          <div className='text-center py-12'>
            <Bookmark className='h-12 w-12 text-muted-foreground mx-auto mb-4' />
            <h3 className='text-lg font-medium mb-2'>No saved views found</h3>
            <p className='text-muted-foreground mb-4'>
              {searchQuery
                ? 'Try adjusting your search criteria.'
                : 'Save your first view to get started.'}
            </p>
            {canCreateViews && !searchQuery && (
              <Button onClick={() => setShowCreateDialog(true)}>
                <BookmarkPlus className='h-4 w-4 mr-2' />
                Save Current View
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export const SavedViews = withComponentRegistration(SavedViewsImpl, {
  name: 'SavedViews',
  category: 'data',
  portal: 'shared',
  version: '1.0.0',
  description: 'Component for managing saved filter/view configurations',
});

export default SavedViews;
