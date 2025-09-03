/**
 * Knowledge Base Search Component
 * Advanced search interface with filters, categories, and article display
 */

'use client';

import React, { useState, useEffect, useMemo } from 'react';
import {
  Search,
  Filter,
  BookOpen,
  Star,
  Eye,
  ThumbsUp,
  ChevronRight,
  Tag,
  Calendar,
  User,
  X,
  SortAsc,
  SortDesc,
  Grid,
  List,
} from 'lucide-react';

// Leverage existing DotMac UI components
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';

// Types
interface Article {
  id: string;
  title: string;
  slug: string;
  summary: string;
  content: string;
  category: string;
  subcategory?: string;
  tags: string[];
  author_name: string;
  created_at: string;
  updated_at: string;
  view_count: number;
  helpful_votes: number;
  unhelpful_votes: number;
  comment_count: number;
}

interface SearchFilters {
  category: string;
  articleType: string;
  tags: string[];
  sortBy: string;
  sortOrder: string;
}

interface SearchMetadata {
  total_results: number;
  page: number;
  page_size: number;
  total_pages: number;
  search_time_ms: number;
}

interface KnowledgeBaseSearchProps {
  initialQuery?: string;
}

const KnowledgeBaseSearch: React.FC<KnowledgeBaseSearchProps> = ({ initialQuery = '' }) => {
  const [searchQuery, setSearchQuery] = useState(initialQuery);
  const [articles, setArticles] = useState<Article[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('list');

  const [filters, setFilters] = useState<SearchFilters>({
    category: '',
    articleType: '',
    tags: [],
    sortBy: 'relevance',
    sortOrder: 'desc',
  });

  const [metadata, setMetadata] = useState<SearchMetadata>({
    total_results: 0,
    page: 1,
    page_size: 20,
    total_pages: 0,
    search_time_ms: 0,
  });

  // Available categories and filters (would come from API)
  const categories = [
    'Account Management',
    'Technical Support',
    'Billing',
    'Getting Started',
    'Troubleshooting',
    'Features',
    'Security',
    'Mobile Apps',
  ];

  const articleTypes = ['Article', 'FAQ', 'Tutorial', 'Troubleshooting', 'Video', 'Download'];

  const availableTags = [
    'email',
    'password',
    'mobile',
    'billing',
    'setup',
    'troubleshooting',
    'account',
    'security',
    'payment',
    'installation',
    'configuration',
  ];

  // Search function
  const performSearch = async (page: number = 1) => {
    try {
      setIsLoading(true);

      const searchParams = new URLSearchParams({
        query: searchQuery,
        page: page.toString(),
        page_size: metadata.page_size.toString(),
        sort_by: filters.sortBy,
        sort_order: filters.sortOrder,
      });

      if (filters.category) searchParams.append('category', filters.category);
      if (filters.articleType) searchParams.append('article_type', filters.articleType);
      filters.tags.forEach((tag) => searchParams.append('tags', tag));

      // In production, this would be a real API call
      // const response = await fetch(`/api/knowledge/articles/search?${searchParams}`);
      // const data = await response.json();

      // Mock data for demonstration
      const mockArticles: Article[] = [
        {
          id: '1',
          title: 'How to Reset Your Password',
          slug: 'reset-password',
          summary: 'Step-by-step guide to reset your account password securely.',
          content: 'Full article content would be here...',
          category: 'Account Management',
          subcategory: 'Security',
          tags: ['password', 'security', 'account'],
          author_name: 'Support Team',
          created_at: '2024-01-15T10:00:00Z',
          updated_at: '2024-02-01T15:30:00Z',
          view_count: 1234,
          helpful_votes: 89,
          unhelpful_votes: 12,
          comment_count: 5,
        },
        {
          id: '2',
          title: 'Setting Up Email on Mobile Devices',
          slug: 'email-mobile-setup',
          summary: 'Configure your email account on iOS and Android devices.',
          content: 'Full article content would be here...',
          category: 'Technical Support',
          subcategory: 'Email',
          tags: ['email', 'mobile', 'setup', 'iOS', 'Android'],
          author_name: 'Technical Support',
          created_at: '2024-01-20T14:00:00Z',
          updated_at: '2024-01-25T09:15:00Z',
          view_count: 987,
          helpful_votes: 76,
          unhelpful_votes: 8,
          comment_count: 12,
        },
        {
          id: '3',
          title: 'Understanding Your Monthly Bill',
          slug: 'understanding-bill',
          summary: 'Breakdown of charges and billing cycle information.',
          content: 'Full article content would be here...',
          category: 'Billing',
          tags: ['billing', 'charges', 'payment'],
          author_name: 'Billing Team',
          created_at: '2024-01-10T11:00:00Z',
          updated_at: '2024-01-30T16:45:00Z',
          view_count: 756,
          helpful_votes: 63,
          unhelpful_votes: 5,
          comment_count: 3,
        },
      ];

      // Filter mock data based on search query and filters
      let filteredArticles = mockArticles;

      if (searchQuery.trim()) {
        filteredArticles = filteredArticles.filter(
          (article) =>
            article.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
            article.summary.toLowerCase().includes(searchQuery.toLowerCase()) ||
            article.tags.some((tag) => tag.toLowerCase().includes(searchQuery.toLowerCase()))
        );
      }

      if (filters.category) {
        filteredArticles = filteredArticles.filter(
          (article) => article.category === filters.category
        );
      }

      if (filters.tags.length > 0) {
        filteredArticles = filteredArticles.filter((article) =>
          filters.tags.some((tag) => article.tags.includes(tag))
        );
      }

      setArticles(filteredArticles);
      setMetadata({
        total_results: filteredArticles.length,
        page: page,
        page_size: 20,
        total_pages: Math.ceil(filteredArticles.length / 20),
        search_time_ms: Math.random() * 100 + 50,
      });
    } catch (error) {
      console.error('Search error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Trigger search on query or filter changes
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      if (searchQuery.trim() || Object.values(filters).some(Boolean)) {
        performSearch();
      }
    }, 300); // Debounce search

    return () => clearTimeout(timeoutId);
  }, [searchQuery, filters]);

  // Initial search if query provided
  useEffect(() => {
    if (initialQuery) {
      performSearch();
    }
  }, []);

  const handleFilterChange = (key: keyof SearchFilters, value: any) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const handleTagToggle = (tag: string) => {
    setFilters((prev) => ({
      ...prev,
      tags: prev.tags.includes(tag) ? prev.tags.filter((t) => t !== tag) : [...prev.tags, tag],
    }));
  };

  const clearFilters = () => {
    setFilters({
      category: '',
      articleType: '',
      tags: [],
      sortBy: 'relevance',
      sortOrder: 'desc',
    });
  };

  const openArticle = (article: Article) => {
    setSelectedArticle(article);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const ArticleCard: React.FC<{ article: Article; compact?: boolean }> = ({
    article,
    compact = false,
  }) => (
    <Card
      className='hover:shadow-lg transition-shadow cursor-pointer'
      onClick={() => openArticle(article)}
    >
      <CardContent className={`p-${compact ? '4' : '6'}`}>
        <div className='flex justify-between items-start mb-2'>
          <Badge variant='secondary'>{article.category}</Badge>
          {article.subcategory && (
            <Badge variant='outline' className='ml-2'>
              {article.subcategory}
            </Badge>
          )}
        </div>

        <h3 className={`font-semibold mb-2 ${compact ? 'text-sm' : 'text-lg'} line-clamp-2`}>
          {article.title}
        </h3>

        {!compact && <p className='text-gray-600 mb-3 line-clamp-2'>{article.summary}</p>}

        <div className='flex flex-wrap gap-1 mb-3'>
          {article.tags.slice(0, 3).map((tag) => (
            <Badge key={tag} variant='outline' className='text-xs'>
              <Tag className='h-2 w-2 mr-1' />
              {tag}
            </Badge>
          ))}
          {article.tags.length > 3 && (
            <Badge variant='outline' className='text-xs'>
              +{article.tags.length - 3} more
            </Badge>
          )}
        </div>

        <div className='flex items-center justify-between text-sm text-gray-500'>
          <div className='flex items-center space-x-4'>
            <div className='flex items-center space-x-1'>
              <Eye className='h-3 w-3' />
              <span>{article.view_count.toLocaleString()}</span>
            </div>
            <div className='flex items-center space-x-1'>
              <ThumbsUp className='h-3 w-3' />
              <span>{article.helpful_votes}</span>
            </div>
            {article.comment_count > 0 && (
              <div className='flex items-center space-x-1'>
                <BookOpen className='h-3 w-3' />
                <span>{article.comment_count}</span>
              </div>
            )}
          </div>
          <div className='flex items-center space-x-1'>
            <User className='h-3 w-3' />
            <span>{article.author_name}</span>
          </div>
        </div>

        <div className='flex items-center justify-between mt-2'>
          <span className='text-xs text-gray-400'>Updated {formatDate(article.updated_at)}</span>
          <ChevronRight className='h-4 w-4 text-gray-400' />
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className='space-y-6'>
      {/* Search Header */}
      <div>
        <h2 className='text-2xl font-bold mb-2'>Knowledge Base</h2>
        <p className='text-gray-600'>
          Find answers to common questions and learn how to use our services
        </p>
      </div>

      {/* Search Bar */}
      <div className='flex gap-4'>
        <div className='flex-1 relative'>
          <Search className='absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4' />
          <Input
            type='text'
            placeholder='Search articles, FAQs, guides...'
            className='pl-10 pr-4'
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <Button
          variant='outline'
          onClick={() => setShowFilters(!showFilters)}
          className='flex items-center space-x-2'
        >
          <Filter className='h-4 w-4' />
          <span>Filters</span>
          {(filters.category || filters.articleType || filters.tags.length > 0) && (
            <Badge variant='secondary' className='ml-1'>
              {[filters.category, filters.articleType, ...filters.tags].filter(Boolean).length}
            </Badge>
          )}
        </Button>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <Card>
          <CardHeader>
            <div className='flex justify-between items-center'>
              <CardTitle className='text-lg'>Search Filters</CardTitle>
              <Button variant='ghost' size='sm' onClick={clearFilters}>
                Clear All
              </Button>
            </div>
          </CardHeader>
          <CardContent className='space-y-4'>
            <div className='grid grid-cols-1 md:grid-cols-3 gap-4'>
              {/* Category Filter */}
              <div>
                <label className='text-sm font-medium mb-2 block'>Category</label>
                <Select
                  value={filters.category}
                  onValueChange={(value) => handleFilterChange('category', value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder='All Categories' />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value=''>All Categories</SelectItem>
                    {categories.map((category) => (
                      <SelectItem key={category} value={category}>
                        {category}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Article Type Filter */}
              <div>
                <label className='text-sm font-medium mb-2 block'>Article Type</label>
                <Select
                  value={filters.articleType}
                  onValueChange={(value) => handleFilterChange('articleType', value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder='All Types' />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value=''>All Types</SelectItem>
                    {articleTypes.map((type) => (
                      <SelectItem key={type} value={type.toLowerCase()}>
                        {type}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Sort Options */}
              <div>
                <label className='text-sm font-medium mb-2 block'>Sort By</label>
                <Select
                  value={`${filters.sortBy}-${filters.sortOrder}`}
                  onValueChange={(value) => {
                    const [sortBy, sortOrder] = value.split('-');
                    setFilters((prev) => ({ ...prev, sortBy, sortOrder }));
                  }}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value='relevance-desc'>Relevance</SelectItem>
                    <SelectItem value='view_count-desc'>Most Viewed</SelectItem>
                    <SelectItem value='helpful_votes-desc'>Most Helpful</SelectItem>
                    <SelectItem value='updated_at-desc'>Recently Updated</SelectItem>
                    <SelectItem value='created_at-desc'>Newest First</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Tags Filter */}
            <div>
              <label className='text-sm font-medium mb-2 block'>Tags</label>
              <div className='flex flex-wrap gap-2'>
                {availableTags.map((tag) => (
                  <div key={tag} className='flex items-center space-x-2'>
                    <Checkbox
                      id={`tag-${tag}`}
                      checked={filters.tags.includes(tag)}
                      onCheckedChange={() => handleTagToggle(tag)}
                    />
                    <label
                      htmlFor={`tag-${tag}`}
                      className='text-sm cursor-pointer hover:text-blue-600'
                    >
                      {tag}
                    </label>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Results Header */}
      {(searchQuery || Object.values(filters).some(Boolean)) && (
        <div className='flex justify-between items-center'>
          <div className='flex items-center space-x-4'>
            <p className='text-gray-600'>
              {isLoading ? 'Searching...' : `${metadata.total_results} results`}
              {metadata.search_time_ms > 0 && (
                <span className='text-gray-400 ml-1'>({metadata.search_time_ms.toFixed(0)}ms)</span>
              )}
            </p>
            {searchQuery && <Badge variant='outline'>Searching for: "{searchQuery}"</Badge>}
          </div>

          <div className='flex items-center space-x-2'>
            <Button
              variant='ghost'
              size='sm'
              onClick={() => setViewMode('list')}
              className={viewMode === 'list' ? 'bg-gray-100' : ''}
            >
              <List className='h-4 w-4' />
            </Button>
            <Button
              variant='ghost'
              size='sm'
              onClick={() => setViewMode('grid')}
              className={viewMode === 'grid' ? 'bg-gray-100' : ''}
            >
              <Grid className='h-4 w-4' />
            </Button>
          </div>
        </div>
      )}

      {/* Results */}
      {isLoading ? (
        <div className='flex justify-center py-12'>
          <div className='animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600'></div>
        </div>
      ) : (
        <div
          className={`grid gap-4 ${
            viewMode === 'grid' ? 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3' : 'grid-cols-1'
          }`}
        >
          {articles.map((article) => (
            <ArticleCard key={article.id} article={article} compact={viewMode === 'grid'} />
          ))}
        </div>
      )}

      {/* No Results */}
      {!isLoading &&
        articles.length === 0 &&
        (searchQuery || Object.values(filters).some(Boolean)) && (
          <div className='text-center py-12'>
            <BookOpen className='h-16 w-16 text-gray-300 mx-auto mb-4' />
            <h3 className='text-lg font-medium mb-2'>No articles found</h3>
            <p className='text-gray-600 mb-4'>Try adjusting your search terms or filters</p>
            <Button onClick={clearFilters} variant='outline'>
              Clear Filters
            </Button>
          </div>
        )}

      {/* Article Modal */}
      <Dialog open={!!selectedArticle} onOpenChange={() => setSelectedArticle(null)}>
        <DialogContent className='max-w-4xl max-h-[80vh] overflow-y-auto'>
          {selectedArticle && (
            <>
              <DialogHeader>
                <div className='flex items-start justify-between'>
                  <div>
                    <DialogTitle className='text-xl mb-2'>{selectedArticle.title}</DialogTitle>
                    <div className='flex items-center space-x-4 text-sm text-gray-500'>
                      <Badge variant='secondary'>{selectedArticle.category}</Badge>
                      <span>By {selectedArticle.author_name}</span>
                      <span>Updated {formatDate(selectedArticle.updated_at)}</span>
                    </div>
                  </div>
                </div>
              </DialogHeader>

              <div className='space-y-4'>
                <p className='text-gray-600 text-lg'>{selectedArticle.summary}</p>

                <Separator />

                <div className='prose max-w-none'>
                  {/* In production, this would render the article content */}
                  <p>{selectedArticle.content}</p>
                  <p>
                    This is where the full article content would be displayed, properly formatted
                    with headings, lists, images, and other rich content elements.
                  </p>
                </div>

                <Separator />

                <div className='flex items-center justify-between'>
                  <div className='flex items-center space-x-4'>
                    <div className='flex items-center space-x-1'>
                      <Eye className='h-4 w-4 text-gray-500' />
                      <span className='text-sm text-gray-600'>
                        {selectedArticle.view_count.toLocaleString()} views
                      </span>
                    </div>
                    <div className='flex items-center space-x-1'>
                      <ThumbsUp className='h-4 w-4 text-gray-500' />
                      <span className='text-sm text-gray-600'>
                        {selectedArticle.helpful_votes} helpful
                      </span>
                    </div>
                  </div>

                  <div className='flex space-x-2'>
                    <Button variant='outline' size='sm'>
                      <ThumbsUp className='h-4 w-4 mr-1' />
                      Helpful
                    </Button>
                    <Button variant='outline' size='sm'>
                      Not Helpful
                    </Button>
                  </div>
                </div>

                <div className='flex flex-wrap gap-2'>
                  {selectedArticle.tags.map((tag) => (
                    <Badge key={tag} variant='outline'>
                      <Tag className='h-3 w-3 mr-1' />
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default KnowledgeBaseSearch;
