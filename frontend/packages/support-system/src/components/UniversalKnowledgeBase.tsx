/**
 * Universal Knowledge Base Component
 * Production-ready knowledge base that works across all portal types
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Search,
  Book,
  FileText,
  Video,
  Download,
  ExternalLink,
  ChevronRight,
  ChevronDown,
  Star,
  Eye,
  Clock,
  Tag,
  Filter,
  SortAsc,
  SortDesc,
  Grid,
  List,
  Bookmark,
  Share2,
  ThumbsUp,
  ThumbsDown,
  MessageSquare,
  AlertCircle,
  CheckCircle,
  Loader2
} from 'lucide-react';
import { useSupportKnowledgeBase, useSupport } from '../providers/SupportProvider';
import type {
  KnowledgeBaseArticle,
  KnowledgeBaseCategory,
  PortalType,
  ArticleType,
  ArticleStatus
} from '../types';

// ===== INTERFACES =====

export interface UniversalKnowledgeBaseProps {
  // Display options
  variant?: 'full' | 'compact' | 'embedded' | 'modal';
  viewMode?: 'grid' | 'list';
  showCategories?: boolean;
  showSearch?: boolean;
  showFilters?: boolean;
  showSorting?: boolean;
  showStats?: boolean;

  // Content filtering
  categories?: string[];
  excludeCategories?: string[];
  articleTypes?: ArticleType[];
  maxResults?: number;
  featuredOnly?: boolean;

  // Portal-specific
  allowComments?: boolean;
  allowRating?: boolean;
  allowBookmark?: boolean;
  allowShare?: boolean;
  showInternalContent?: boolean;

  // Customization
  searchPlaceholder?: string;
  emptyStateMessage?: string;

  // Callbacks
  onArticleView?: (article: KnowledgeBaseArticle) => void;
  onCategorySelect?: (category: KnowledgeBaseCategory) => void;
  onSearch?: (query: string) => void;
  onRate?: (articleId: string, rating: number) => void;
  onBookmark?: (articleId: string, bookmarked: boolean) => void;
}

interface CategoryTreeProps {
  categories: KnowledgeBaseCategory[];
  selectedCategory?: string;
  onCategorySelect: (categoryId: string) => void;
  showArticleCount?: boolean;
}

interface ArticleCardProps {
  article: KnowledgeBaseArticle;
  viewMode: 'grid' | 'list';
  showActions?: boolean;
  showStats?: boolean;
  onView: (article: KnowledgeBaseArticle) => void;
  onRate?: (rating: number) => void;
  onBookmark?: (bookmarked: boolean) => void;
  onShare?: () => void;
}

interface ArticleFiltersProps {
  categories: KnowledgeBaseCategory[];
  articleTypes: ArticleType[];
  selectedCategory?: string;
  selectedTypes: ArticleType[];
  sortBy: string;
  sortOrder: 'asc' | 'desc';
  onCategoryChange: (category: string) => void;
  onTypeChange: (types: ArticleType[]) => void;
  onSortChange: (field: string, order: 'asc' | 'desc') => void;
}

// ===== SUB-COMPONENTS =====

function CategoryTree({
  categories,
  selectedCategory,
  onCategorySelect,
  showArticleCount = true
}: CategoryTreeProps) {
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());

  const toggleCategory = useCallback((categoryId: string) => {
    setExpandedCategories(prev => {
      const next = new Set(prev);
      if (next.has(categoryId)) {
        next.delete(categoryId);
      } else {
        next.add(categoryId);
      }
      return next;
    });
  }, []);

  const renderCategory = useCallback((category: KnowledgeBaseCategory, level = 0) => {
    const hasChildren = category.subcategories && category.subcategories.length > 0;
    const isExpanded = expandedCategories.has(category.id);
    const isSelected = selectedCategory === category.id;

    return (
      <div key={category.id} className="mb-1">
        <div
          className={`
            flex items-center space-x-2 px-2 py-1.5 rounded cursor-pointer transition-colors
            ${isSelected ? 'bg-blue-100 text-blue-700' : 'hover:bg-gray-100'}
          `}
          style={{ marginLeft: `${level * 16}px` }}
          onClick={() => onCategorySelect(category.id)}
        >
          {hasChildren && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                toggleCategory(category.id);
              }}
              className="text-gray-400 hover:text-gray-600"
            >
              {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            </button>
          )}

          {!hasChildren && <div className="w-4" />}

          <span className="text-sm font-medium flex-1">{category.name}</span>

          {showArticleCount && (
            <span className="text-xs text-gray-500 bg-gray-200 px-2 py-0.5 rounded-full">
              {category.articleCount || 0}
            </span>
          )}
        </div>

        {hasChildren && isExpanded && category.subcategories && (
          <div>
            {category.subcategories.map(subcategory => renderCategory(subcategory, level + 1))}
          </div>
        )}
      </div>
    );
  }, [expandedCategories, selectedCategory, onCategorySelect, toggleCategory, showArticleCount]);

  return (
    <div className="space-y-1">
      {categories.map(category => renderCategory(category))}
    </div>
  );
}

function ArticleCard({
  article,
  viewMode,
  showActions = true,
  showStats = true,
  onView,
  onRate,
  onBookmark,
  onShare
}: ArticleCardProps) {
  const [isBookmarked, setIsBookmarked] = useState(article.isBookmarked || false);
  const [userRating, setUserRating] = useState(article.userRating || 0);

  const handleBookmark = useCallback(() => {
    const newBookmarked = !isBookmarked;
    setIsBookmarked(newBookmarked);
    onBookmark?.(newBookmarked);
  }, [isBookmarked, onBookmark]);

  const handleRate = useCallback((rating: number) => {
    setUserRating(rating);
    onRate?.(rating);
  }, [onRate]);

  const getTypeIcon = (type: ArticleType) => {
    switch (type) {
      case 'video': return <Video className="w-4 h-4" />;
      case 'document': return <Download className="w-4 h-4" />;
      case 'external': return <ExternalLink className="w-4 h-4" />;
      default: return <FileText className="w-4 h-4" />;
    }
  };

  const getStatusColor = (status: ArticleStatus) => {
    switch (status) {
      case 'published': return 'text-green-600';
      case 'draft': return 'text-yellow-600';
      case 'archived': return 'text-gray-500';
      default: return 'text-gray-600';
    }
  };

  if (viewMode === 'list') {
    return (
      <div className="flex items-start space-x-4 p-4 border-b hover:bg-gray-50 transition-colors">
        <div className="flex-shrink-0 mt-1">
          {getTypeIcon(article.type)}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between mb-2">
            <div className="flex-1">
              <button
                onClick={() => onView(article)}
                className="text-left w-full"
              >
                <h3 className="text-lg font-semibold text-gray-900 hover:text-blue-600 transition-colors">
                  {article.title}
                </h3>
              </button>

              {article.summary && (
                <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                  {article.summary}
                </p>
              )}
            </div>

            {showActions && (
              <div className="flex items-center space-x-2 ml-4">
                {onBookmark && (
                  <button
                    onClick={handleBookmark}
                    className={`p-1 rounded transition-colors ${
                      isBookmarked ? 'text-yellow-500' : 'text-gray-400 hover:text-yellow-500'
                    }`}
                  >
                    <Bookmark className="w-4 h-4" fill={isBookmarked ? 'currentColor' : 'none'} />
                  </button>
                )}

                {onShare && (
                  <button
                    onClick={onShare}
                    className="p-1 text-gray-400 hover:text-gray-600 rounded transition-colors"
                  >
                    <Share2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            )}
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4 text-xs text-gray-500">
              {article.tags && article.tags.length > 0 && (
                <div className="flex items-center space-x-1">
                  <Tag className="w-3 h-3" />
                  <span>{article.tags.slice(0, 2).join(', ')}</span>
                  {article.tags.length > 2 && <span>+{article.tags.length - 2}</span>}
                </div>
              )}

              <div className="flex items-center space-x-1">
                <Clock className="w-3 h-3" />
                <span>{new Date(article.updatedAt).toLocaleDateString()}</span>
              </div>

              {showStats && (
                <>
                  <div className="flex items-center space-x-1">
                    <Eye className="w-3 h-3" />
                    <span>{article.viewCount}</span>
                  </div>

                  {article.rating && (
                    <div className="flex items-center space-x-1">
                      <Star className="w-3 h-3 text-yellow-500" fill="currentColor" />
                      <span>{article.rating.toFixed(1)}</span>
                    </div>
                  )}
                </>
              )}
            </div>

            {onRate && (
              <div className="flex items-center space-x-1">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    onClick={() => handleRate(star)}
                    className={`text-xs ${
                      star <= userRating ? 'text-yellow-500' : 'text-gray-300'
                    } hover:text-yellow-400`}
                  >
                    <Star className="w-3 h-3" fill="currentColor" />
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Grid view
  return (
    <div className="bg-white border rounded-lg p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center space-x-2">
          {getTypeIcon(article.type)}
          <span className={`text-xs font-medium ${getStatusColor(article.status)}`}>
            {article.status.toUpperCase()}
          </span>
        </div>

        {showActions && (
          <div className="flex items-center space-x-1">
            {onBookmark && (
              <button
                onClick={handleBookmark}
                className={`p-1 rounded transition-colors ${
                  isBookmarked ? 'text-yellow-500' : 'text-gray-400 hover:text-yellow-500'
                }`}
              >
                <Bookmark className="w-4 h-4" fill={isBookmarked ? 'currentColor' : 'none'} />
              </button>
            )}

            {onShare && (
              <button
                onClick={onShare}
                className="p-1 text-gray-400 hover:text-gray-600 rounded transition-colors"
              >
                <Share2 className="w-4 h-4" />
              </button>
            )}
          </div>
        )}
      </div>

      <button
        onClick={() => onView(article)}
        className="text-left w-full mb-3"
      >
        <h3 className="font-semibold text-gray-900 hover:text-blue-600 transition-colors mb-2 line-clamp-2">
          {article.title}
        </h3>

        {article.summary && (
          <p className="text-sm text-gray-600 line-clamp-3">
            {article.summary}
          </p>
        )}
      </button>

      {article.tags && article.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {article.tags.slice(0, 3).map((tag) => (
            <span key={tag} className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
              {tag}
            </span>
          ))}
          {article.tags.length > 3 && (
            <span className="text-xs text-gray-500">
              +{article.tags.length - 3}
            </span>
          )}
        </div>
      )}

      <div className="flex items-center justify-between text-xs text-gray-500">
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1">
            <Clock className="w-3 h-3" />
            <span>{new Date(article.updatedAt).toLocaleDateString()}</span>
          </div>

          {showStats && (
            <>
              <div className="flex items-center space-x-1">
                <Eye className="w-3 h-3" />
                <span>{article.viewCount}</span>
              </div>

              {article.rating && (
                <div className="flex items-center space-x-1">
                  <Star className="w-3 h-3 text-yellow-500" fill="currentColor" />
                  <span>{article.rating.toFixed(1)}</span>
                </div>
              )}
            </>
          )}
        </div>

        {onRate && (
          <div className="flex items-center space-x-1">
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                onClick={() => handleRate(star)}
                className={`${
                  star <= userRating ? 'text-yellow-500' : 'text-gray-300'
                } hover:text-yellow-400`}
              >
                <Star className="w-3 h-3" fill="currentColor" />
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ArticleFilters({
  categories,
  articleTypes,
  selectedCategory,
  selectedTypes,
  sortBy,
  sortOrder,
  onCategoryChange,
  onTypeChange,
  onSortChange
}: ArticleFiltersProps) {
  const [showFilters, setShowFilters] = useState(false);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="flex items-center space-x-2 text-sm text-gray-600 hover:text-gray-900"
        >
          <Filter className="w-4 h-4" />
          <span>Filters</span>
          <ChevronRight className={`w-4 h-4 transform transition-transform ${showFilters ? 'rotate-90' : ''}`} />
        </button>

        <div className="flex items-center space-x-2">
          <select
            value={`${sortBy}-${sortOrder}`}
            onChange={(e) => {
              const [field, order] = e.target.value.split('-');
              onSortChange(field, order as 'asc' | 'desc');
            }}
            className="text-sm border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="updatedAt-desc">Latest</option>
            <option value="updatedAt-asc">Oldest</option>
            <option value="title-asc">Title A-Z</option>
            <option value="title-desc">Title Z-A</option>
            <option value="viewCount-desc">Most Viewed</option>
            <option value="rating-desc">Highest Rated</option>
          </select>
        </div>
      </div>

      {showFilters && (
        <div className="bg-gray-50 p-4 rounded-lg space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Category</label>
            <select
              value={selectedCategory || ''}
              onChange={(e) => onCategoryChange(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Categories</option>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Content Type</label>
            <div className="space-y-2">
              {articleTypes.map((type) => (
                <label key={type} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={selectedTypes.includes(type)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        onTypeChange([...selectedTypes, type]);
                      } else {
                        onTypeChange(selectedTypes.filter(t => t !== type));
                      }
                    }}
                    className="mr-2"
                  />
                  <span className="text-sm capitalize">{type}</span>
                </label>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ===== MAIN COMPONENT =====

export function UniversalKnowledgeBase({
  variant = 'full',
  viewMode: initialViewMode = 'grid',
  showCategories = true,
  showSearch = true,
  showFilters = true,
  showSorting = true,
  showStats = true,
  categories: filterCategories,
  excludeCategories,
  articleTypes: filterArticleTypes,
  maxResults,
  featuredOnly = false,
  allowComments = true,
  allowRating = true,
  allowBookmark = true,
  allowShare = true,
  showInternalContent = false,
  searchPlaceholder = "Search knowledge base...",
  emptyStateMessage = "No articles found matching your criteria.",
  onArticleView,
  onCategorySelect,
  onSearch,
  onRate,
  onBookmark
}: UniversalKnowledgeBaseProps) {

  const { features, portalConfig } = useSupport();
  const {
    articles,
    categories,
    searchArticles,
    getArticle,
    rateArticle,
    bookmarkArticle,
    getPopularArticles,
    getFeaturedArticles,
    isLoading,
    hasError,
    getError
  } = useSupportKnowledgeBase();

  const [viewMode, setViewMode] = useState(initialViewMode);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>();
  const [selectedTypes, setSelectedTypes] = useState<ArticleType[]>([]);
  const [sortBy, setSortBy] = useState('updatedAt');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  // Portal-specific configurations
  const canRate = useMemo(() =>
    allowRating && (portalConfig.type === 'customer' || portalConfig.permissions.includes('create')),
    [allowRating, portalConfig.type, portalConfig.permissions]
  );

  const canBookmark = useMemo(() =>
    allowBookmark && portalConfig.permissions.includes('read'),
    [allowBookmark, portalConfig.permissions]
  );

  const canComment = useMemo(() =>
    allowComments && portalConfig.permissions.includes('create'),
    [allowComments, portalConfig.permissions]
  );

  const canShare = useMemo(() =>
    allowShare && portalConfig.permissions.includes('read'),
    [allowShare, portalConfig.permissions]
  );

  const showInternal = useMemo(() =>
    showInternalContent &&
    (portalConfig.type === 'admin' || portalConfig.type === 'agent' || portalConfig.type === 'management'),
    [showInternalContent, portalConfig.type]
  );

  // Filter and sort articles
  const filteredArticles = useMemo(() => {
    let filtered = [...articles];

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(article =>
        article.title.toLowerCase().includes(query) ||
        article.summary?.toLowerCase().includes(query) ||
        article.content.toLowerCase().includes(query) ||
        article.tags?.some(tag => tag.toLowerCase().includes(query))
      );
    }

    // Filter by category
    if (selectedCategory) {
      filtered = filtered.filter(article => article.categoryId === selectedCategory);
    }

    // Filter by categories prop
    if (filterCategories && filterCategories.length > 0) {
      filtered = filtered.filter(article => filterCategories.includes(article.categoryId));
    }

    // Exclude categories
    if (excludeCategories && excludeCategories.length > 0) {
      filtered = filtered.filter(article => !excludeCategories.includes(article.categoryId));
    }

    // Filter by article types
    if (selectedTypes.length > 0) {
      filtered = filtered.filter(article => selectedTypes.includes(article.type));
    }

    if (filterArticleTypes && filterArticleTypes.length > 0) {
      filtered = filtered.filter(article => filterArticleTypes.includes(article.type));
    }

    // Filter by featured
    if (featuredOnly) {
      filtered = filtered.filter(article => article.featured);
    }

    // Filter by visibility
    if (!showInternal) {
      filtered = filtered.filter(article => article.visibility === 'public');
    }

    // Filter by status
    filtered = filtered.filter(article => article.status === 'published');

    // Sort articles
    filtered.sort((a, b) => {
      let aVal: any, bVal: any;

      switch (sortBy) {
        case 'title':
          aVal = a.title.toLowerCase();
          bVal = b.title.toLowerCase();
          break;
        case 'viewCount':
          aVal = a.viewCount || 0;
          bVal = b.viewCount || 0;
          break;
        case 'rating':
          aVal = a.rating || 0;
          bVal = b.rating || 0;
          break;
        case 'updatedAt':
        default:
          aVal = new Date(a.updatedAt);
          bVal = new Date(b.updatedAt);
          break;
      }

      if (sortOrder === 'asc') {
        return aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
      } else {
        return aVal > bVal ? -1 : aVal < bVal ? 1 : 0;
      }
    });

    // Limit results
    if (maxResults && maxResults > 0) {
      filtered = filtered.slice(0, maxResults);
    }

    return filtered;
  }, [
    articles,
    searchQuery,
    selectedCategory,
    filterCategories,
    excludeCategories,
    selectedTypes,
    filterArticleTypes,
    featuredOnly,
    showInternal,
    sortBy,
    sortOrder,
    maxResults
  ]);

  // Available article types from current articles
  const availableTypes = useMemo(() => {
    const types = new Set(articles.map(article => article.type));
    return Array.from(types);
  }, [articles]);

  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query);
    onSearch?.(query);
  }, [onSearch]);

  const handleCategorySelect = useCallback((categoryId: string) => {
    setSelectedCategory(categoryId === selectedCategory ? undefined : categoryId);
    const category = categories.find(c => c.id === categoryId);
    if (category) {
      onCategorySelect?.(category);
    }
  }, [selectedCategory, categories, onCategorySelect]);

  const handleArticleView = useCallback(async (article: KnowledgeBaseArticle) => {
    try {
      // Get full article content
      const fullArticle = await getArticle(article.id);
      onArticleView?.(fullArticle);
    } catch (error) {
      console.error('Failed to load article:', error);
      onArticleView?.(article);
    }
  }, [getArticle, onArticleView]);

  const handleRate = useCallback(async (articleId: string, rating: number) => {
    try {
      await rateArticle(articleId, rating);
      onRate?.(articleId, rating);
    } catch (error) {
      console.error('Failed to rate article:', error);
    }
  }, [rateArticle, onRate]);

  const handleBookmark = useCallback(async (articleId: string, bookmarked: boolean) => {
    try {
      await bookmarkArticle(articleId, bookmarked);
      onBookmark?.(articleId, bookmarked);
    } catch (error) {
      console.error('Failed to bookmark article:', error);
    }
  }, [bookmarkArticle, onBookmark]);

  if (isLoading('articles')) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        <span className="ml-2 text-gray-600">Loading knowledge base...</span>
      </div>
    );
  }

  if (hasError('articles')) {
    const error = getError('articles');
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Failed to load knowledge base</h3>
          <p className="text-gray-600">{error?.message || 'An unexpected error occurred'}</p>
        </div>
      </div>
    );
  }

  const containerClass = useMemo(() => {
    switch (variant) {
      case 'compact':
        return 'max-w-2xl';
      case 'embedded':
        return 'w-full h-full';
      case 'modal':
        return 'max-w-4xl mx-auto';
      case 'full':
      default:
        return 'max-w-7xl mx-auto';
    }
  }, [variant]);

  return (
    <div className={`${containerClass} ${variant === 'embedded' ? 'flex flex-col h-full' : 'p-6'}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <Book className="w-6 h-6 text-blue-600" />
          <h1 className="text-2xl font-bold text-gray-900">Knowledge Base</h1>
        </div>

        {variant === 'full' && (
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 rounded ${viewMode === 'grid' ? 'bg-blue-100 text-blue-600' : 'text-gray-400 hover:text-gray-600'}`}
            >
              <Grid className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 rounded ${viewMode === 'list' ? 'bg-blue-100 text-blue-600' : 'text-gray-400 hover:text-gray-600'}`}
            >
              <List className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Search */}
      {showSearch && (
        <div className="mb-6">
          <div className="relative">
            <Search className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder={searchPlaceholder}
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>
      )}

      <div className={`${variant === 'embedded' ? 'flex flex-1 min-h-0' : 'flex gap-6'}`}>
        {/* Sidebar */}
        {showCategories && categories.length > 0 && (
          <div className={`${variant === 'embedded' ? 'w-64 flex-shrink-0' : 'w-64'} space-y-6`}>
            <div>
              <h3 className="font-semibold text-gray-900 mb-3">Categories</h3>
              <CategoryTree
                categories={categories}
                selectedCategory={selectedCategory}
                onCategorySelect={handleCategorySelect}
                showArticleCount={showStats}
              />
            </div>
          </div>
        )}

        {/* Main Content */}
        <div className={`${variant === 'embedded' ? 'flex-1 flex flex-col min-w-0' : 'flex-1'}`}>
          {/* Filters */}
          {showFilters && (
            <div className="mb-6">
              <ArticleFilters
                categories={categories}
                articleTypes={availableTypes}
                selectedCategory={selectedCategory}
                selectedTypes={selectedTypes}
                sortBy={sortBy}
                sortOrder={sortOrder}
                onCategoryChange={setSelectedCategory}
                onTypeChange={setSelectedTypes}
                onSortChange={(field, order) => {
                  setSortBy(field);
                  setSortOrder(order);
                }}
              />
            </div>
          )}

          {/* Results */}
          <div className={`${variant === 'embedded' ? 'flex-1 overflow-y-auto' : ''}`}>
            {filteredArticles.length === 0 ? (
              <div className="text-center py-12">
                <Book className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-600">{emptyStateMessage}</p>
              </div>
            ) : (
              <>
                {showStats && (
                  <div className="mb-4 text-sm text-gray-600">
                    Showing {filteredArticles.length} of {articles.length} articles
                  </div>
                )}

                <div className={
                  viewMode === 'grid'
                    ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'
                    : 'divide-y'
                }>
                  {filteredArticles.map((article) => (
                    <ArticleCard
                      key={article.id}
                      article={article}
                      viewMode={viewMode}
                      showActions={canBookmark || canShare}
                      showStats={showStats}
                      onView={handleArticleView}
                      onRate={canRate ? (rating) => handleRate(article.id, rating) : undefined}
                      onBookmark={canBookmark ? (bookmarked) => handleBookmark(article.id, bookmarked) : undefined}
                      onShare={canShare ? () => {} : undefined}
                    />
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default UniversalKnowledgeBase;
