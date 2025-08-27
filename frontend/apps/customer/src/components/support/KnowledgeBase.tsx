'use client';

import { Card } from '@dotmac/styled-components/customer';
import {
  BookOpen,
  ChevronRight,
  Clock,
  CreditCard,
  ExternalLink,
  FileText,
  HelpCircle,
  Phone,
  Search,
  Settings,
  Shield,
  Star,
  ThumbsDown,
  ThumbsUp,
  TrendingUp,
  Video,
  Wifi,
  Zap,
} from 'lucide-react';
import { useState } from 'react';

interface Article {
  id: string;
  title: string;
  description: string;
  category: string;
  type: 'article' | 'video' | 'guide' | 'faq';
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  readTime: string;
  rating: number;
  views: number;
  lastUpdated: string;
  tags: string[];
  helpful: number;
  notHelpful: number;
}

interface Category {
  id: string;
  name: string;
  icon: React.ComponentType<{ className?: string }>;
  count: number;
  description: string;
}

const categories: Category[] = [
  {
    id: 'internet',
    name: 'Internet & WiFi',
    icon: Wifi,
    count: 24,
    description: 'Connection, speed, and networking help',
  },
  {
    id: 'billing',
    name: 'Billing & Payments',
    icon: CreditCard,
    count: 18,
    description: 'Account, billing, and payment questions',
  },
  {
    id: 'phone',
    name: 'Phone Service',
    icon: Phone,
    count: 12,
    description: 'Voice service and calling features',
  },
  {
    id: 'account',
    name: 'Account Settings',
    icon: Settings,
    count: 15,
    description: 'Profile, security, and preferences',
  },
  {
    id: 'security',
    name: 'Security & Privacy',
    icon: Shield,
    count: 8,
    description: 'Keep your account safe and secure',
  },
  {
    id: 'troubleshooting',
    name: 'Troubleshooting',
    icon: Zap,
    count: 20,
    description: 'Fix common issues quickly',
  },
];

const popularArticles: Article[] = [
  {
    id: '1',
    title: 'How to Fix Slow Internet Speeds',
    description: 'Step-by-step guide to diagnose and improve your internet connection speed',
    category: 'internet',
    type: 'guide',
    difficulty: 'beginner',
    readTime: '5 min read',
    rating: 4.8,
    views: 15420,
    lastUpdated: '2024-01-15',
    tags: ['speed', 'troubleshooting', 'wifi'],
    helpful: 142,
    notHelpful: 8,
  },
  {
    id: '2',
    title: 'Understanding Your Monthly Bill',
    description: 'Detailed breakdown of charges, taxes, and fees on your statement',
    category: 'billing',
    type: 'article',
    difficulty: 'beginner',
    readTime: '3 min read',
    rating: 4.6,
    views: 12350,
    lastUpdated: '2024-01-10',
    tags: ['billing', 'charges', 'fees'],
    helpful: 98,
    notHelpful: 5,
  },
  {
    id: '3',
    title: 'WiFi Network Setup and Optimization',
    description: 'Complete guide to setting up and optimizing your home WiFi network',
    category: 'internet',
    type: 'video',
    difficulty: 'intermediate',
    readTime: '12 min video',
    rating: 4.9,
    views: 8750,
    lastUpdated: '2024-01-20',
    tags: ['wifi', 'setup', 'optimization', 'router'],
    helpful: 87,
    notHelpful: 2,
  },
  {
    id: '4',
    title: 'Setting Up Auto-Pay',
    description: 'Never miss a payment - learn how to set up automatic billing',
    category: 'billing',
    type: 'guide',
    difficulty: 'beginner',
    readTime: '2 min read',
    rating: 4.7,
    views: 9240,
    lastUpdated: '2024-01-12',
    tags: ['autopay', 'billing', 'payments'],
    helpful: 76,
    notHelpful: 3,
  },
  {
    id: '5',
    title: 'Troubleshooting Phone Service Issues',
    description: 'Common phone problems and how to fix them',
    category: 'phone',
    type: 'article',
    difficulty: 'beginner',
    readTime: '4 min read',
    rating: 4.5,
    views: 6890,
    lastUpdated: '2024-01-08',
    tags: ['phone', 'troubleshooting', 'voip'],
    helpful: 65,
    notHelpful: 7,
  },
];

const recentArticles: Article[] = [
  {
    id: '6',
    title: 'New WiFi 6E Router Features',
    description: 'Learn about the latest WiFi 6E technology and its benefits',
    category: 'internet',
    type: 'article',
    difficulty: 'intermediate',
    readTime: '6 min read',
    rating: 4.8,
    views: 3420,
    lastUpdated: '2024-01-25',
    tags: ['wifi6e', 'router', 'technology'],
    helpful: 34,
    notHelpful: 1,
  },
  {
    id: '7',
    title: 'Enhanced Security Features Guide',
    description: 'Protect your account with two-factor authentication and more',
    category: 'security',
    type: 'guide',
    difficulty: 'intermediate',
    readTime: '8 min read',
    rating: 4.9,
    views: 2780,
    lastUpdated: '2024-01-22',
    tags: ['security', '2fa', 'account protection'],
    helpful: 28,
    notHelpful: 0,
  },
];

export function KnowledgeBase() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);

  const filteredArticles = [...popularArticles, ...recentArticles].filter(article => {
    const matchesSearch =
      !searchQuery ||
      article.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      article.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      article.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesCategory = !selectedCategory || article.category === selectedCategory;

    return matchesSearch && matchesCategory;
  });

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'video':
        return <Video className="h-4 w-4 text-red-600" />;
      case 'guide':
        return <BookOpen className="h-4 w-4 text-blue-600" />;
      case 'faq':
        return <HelpCircle className="h-4 w-4 text-purple-600" />;
      default:
        return <FileText className="h-4 w-4 text-green-600" />;
    }
  };

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'beginner':
        return 'bg-green-100 text-green-800';
      case 'intermediate':
        return 'bg-yellow-100 text-yellow-800';
      case 'advanced':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const formatViews = (views: number) => {
    if (views >= 1000) {
      return `${(views / 1000).toFixed(1)}k`;
    }
    return views.toString();
  };

  const handleArticleClick = (article: Article) => {
    setSelectedArticle(article);
    // In a real app, this would navigate to the article page
    // Debug: 'Opening article:', article.title
  };

  const handleFeedback = (articleId: string, helpful: boolean) => {
    // In a real app, this would submit feedback to the server
    // Debug: `Article ${articleId} marked as ${helpful ? 'helpful' : 'not helpful'}`
  };

  if (selectedArticle) {
    return (
      <Card className="p-6">
        <button
          onClick={() => setSelectedArticle(null)}
          className="mb-4 text-blue-600 hover:text-blue-800 font-medium text-sm"
        >
          ← Back to Knowledge Base
        </button>

        <div className="mb-6">
          <div className="flex items-center space-x-2 mb-2">
            {getTypeIcon(selectedArticle.type)}
            <span
              className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${getDifficultyColor(selectedArticle.difficulty)}`}
            >
              {selectedArticle.difficulty}
            </span>
            <span className="text-sm text-gray-600">{selectedArticle.readTime}</span>
          </div>

          <h1 className="text-2xl font-bold text-gray-900 mb-2">{selectedArticle.title}</h1>
          <p className="text-gray-600 mb-4">{selectedArticle.description}</p>

          <div className="flex items-center space-x-4 text-sm text-gray-500">
            <div className="flex items-center">
              <Star className="h-4 w-4 text-yellow-400 fill-current mr-1" />
              <span>{selectedArticle.rating}</span>
            </div>
            <span>{formatViews(selectedArticle.views)} views</span>
            <span>Updated {new Date(selectedArticle.lastUpdated).toLocaleDateString()}</span>
          </div>
        </div>

        <div className="prose max-w-none mb-8">
          <p className="text-gray-700 leading-relaxed">
            This would be the full article content. In a real implementation, this would contain the
            complete help article with formatting, images, and interactive elements.
          </p>
        </div>

        <div className="border-t pt-6">
          <h3 className="font-medium text-gray-900 mb-4">Was this article helpful?</h3>
          <div className="flex items-center space-x-4">
            <button
              onClick={() => handleFeedback(selectedArticle.id, true)}
              className="flex items-center space-x-2 px-4 py-2 border border-green-300 text-green-700 rounded-lg hover:bg-green-50 transition-colors"
            >
              <ThumbsUp className="h-4 w-4" />
              <span>Yes ({selectedArticle.helpful})</span>
            </button>
            <button
              onClick={() => handleFeedback(selectedArticle.id, false)}
              className="flex items-center space-x-2 px-4 py-2 border border-red-300 text-red-700 rounded-lg hover:bg-red-50 transition-colors"
            >
              <ThumbsDown className="h-4 w-4" />
              <span>No ({selectedArticle.notHelpful})</span>
            </button>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <div className="mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Knowledge Base</h2>
          <p className="text-gray-600 text-sm">
            Find answers to common questions and learn how to get the most from your services
          </p>
        </div>

        {/* Search */}
        <div className="mb-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search help articles..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        {/* Categories */}
        <div className="mb-6">
          <h3 className="font-medium text-gray-900 mb-3">Browse by Category</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {categories.map(category => (
              <button
                key={category.id}
                onClick={() =>
                  setSelectedCategory(selectedCategory === category.id ? null : category.id)
                }
                className={`flex items-center justify-between p-3 border rounded-lg text-left transition-colors ${
                  selectedCategory === category.id
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-200 hover:bg-gray-50'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <category.icon className="h-5 w-5" />
                  <div>
                    <p className="font-medium text-sm">{category.name}</p>
                    <p className="text-xs text-gray-600">{category.description}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-full">
                    {category.count}
                  </span>
                  <ChevronRight className="h-4 w-4" />
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Popular Articles */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-medium text-gray-900">
              {selectedCategory
                ? `${categories.find(c => c.id === selectedCategory)?.name} Articles`
                : 'Popular Articles'}
            </h3>
            <div className="flex items-center text-sm text-gray-600">
              <TrendingUp className="h-4 w-4 mr-1" />
              Most viewed
            </div>
          </div>

          <div className="space-y-3">
            {filteredArticles.slice(0, 5).map(article => (
              <div
                key={article.id}
                onClick={() => handleArticleClick(article)}
                className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors group"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2 mb-1">
                      {getTypeIcon(article.type)}
                      <h4 className="font-medium text-gray-900 text-sm group-hover:text-blue-600 transition-colors">
                        {article.title}
                      </h4>
                    </div>
                    <p className="text-gray-600 text-sm mb-2 line-clamp-2">{article.description}</p>
                    <div className="flex items-center space-x-4 text-xs text-gray-500">
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 ${getDifficultyColor(article.difficulty)}`}
                      >
                        {article.difficulty}
                      </span>
                      <span>{article.readTime}</span>
                      <div className="flex items-center">
                        <Star className="h-3 w-3 text-yellow-400 fill-current mr-1" />
                        <span>{article.rating}</span>
                      </div>
                      <span>{formatViews(article.views)} views</span>
                    </div>
                  </div>
                  <ExternalLink className="h-4 w-4 text-gray-400 group-hover:text-blue-600 transition-colors flex-shrink-0 ml-2" />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Quick Links */}
        <div className="pt-4 border-t">
          <h3 className="font-medium text-gray-900 mb-3">Quick Links</h3>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <a href="#" className="text-blue-600 hover:text-blue-800 flex items-center">
              <Clock className="h-3 w-3 mr-1" />
              Service Status
            </a>
            <a href="#" className="text-blue-600 hover:text-blue-800 flex items-center">
              <Phone className="h-3 w-3 mr-1" />
              Contact Support
            </a>
            <a href="#" className="text-blue-600 hover:text-blue-800 flex items-center">
              <Video className="h-3 w-3 mr-1" />
              Video Tutorials
            </a>
            <a href="#" className="text-blue-600 hover:text-blue-800 flex items-center">
              <HelpCircle className="h-3 w-3 mr-1" />
              Community Forum
            </a>
          </div>
        </div>
      </Card>

      {/* Recent Updates */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-medium text-gray-900">Recently Updated</h3>
          <span className="text-sm text-gray-600">Last 7 days</span>
        </div>

        <div className="space-y-3">
          {recentArticles.map(article => (
            <div
              key={article.id}
              onClick={() => handleArticleClick(article)}
              className="flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-lg hover:bg-green-100 cursor-pointer transition-colors group"
            >
              <div className="flex items-center space-x-3">
                {getTypeIcon(article.type)}
                <div>
                  <h4 className="font-medium text-gray-900 text-sm group-hover:text-green-700 transition-colors">
                    {article.title}
                  </h4>
                  <p className="text-green-600 text-xs">
                    Updated {new Date(article.lastUpdated).toLocaleDateString()}
                  </p>
                </div>
              </div>
              <ExternalLink className="h-4 w-4 text-green-600 group-hover:text-green-700 transition-colors" />
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
