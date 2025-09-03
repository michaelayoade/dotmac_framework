'use client';

import React, { useState } from 'react';
import { clsx } from 'clsx';
import {
  Download,
  Eye,
  FileText,
  Image,
  Video,
  Presentation,
  Mail,
  Share2,
  Heart,
  Calendar,
  Target,
  TrendingUp,
  Users,
  Megaphone,
  Palette,
  Globe,
  Search,
  Filter,
  Star,
  Clock,
  Tag,
} from 'lucide-react';

interface MarketingResource {
  id: string;
  title: string;
  description: string;
  type:
    | 'brochure'
    | 'flyer'
    | 'presentation'
    | 'video'
    | 'email-template'
    | 'social-media'
    | 'case-study'
    | 'whitepaper';
  category: 'sales-materials' | 'brand-assets' | 'co-marketing' | 'training' | 'competitive';
  format: 'pdf' | 'pptx' | 'docx' | 'jpg' | 'png' | 'mp4' | 'html';
  size: string;
  downloads: number;
  rating: number;
  lastUpdated: string;
  tags: string[];
  thumbnail?: string;
  downloadUrl: string;
  previewUrl?: string;
}

const mockResources: MarketingResource[] = [
  {
    id: '1',
    title: 'ISP Services Brochure 2025',
    description: 'Comprehensive overview of our internet service packages and pricing',
    type: 'brochure',
    category: 'sales-materials',
    format: 'pdf',
    size: '2.5 MB',
    downloads: 245,
    rating: 4.8,
    lastUpdated: '2025-08-15',
    tags: ['fiber', 'pricing', 'packages'],
    downloadUrl: '/resources/isp-brochure-2025.pdf',
    previewUrl: '/resources/previews/isp-brochure-2025.jpg',
  },
  {
    id: '2',
    title: 'DotMac Brand Guidelines',
    description: 'Official brand guidelines including logos, colors, and typography standards',
    type: 'presentation',
    category: 'brand-assets',
    format: 'pdf',
    size: '15.2 MB',
    downloads: 89,
    rating: 4.9,
    lastUpdated: '2025-08-01',
    tags: ['branding', 'logo', 'guidelines'],
    downloadUrl: '/resources/brand-guidelines.pdf',
  },
  {
    id: '3',
    title: 'Fiber Installation Case Study',
    description: 'Success story of enterprise fiber deployment for major client',
    type: 'case-study',
    category: 'sales-materials',
    format: 'pdf',
    size: '1.8 MB',
    downloads: 156,
    rating: 4.6,
    lastUpdated: '2025-08-20',
    tags: ['enterprise', 'fiber', 'case-study'],
    downloadUrl: '/resources/fiber-case-study.pdf',
  },
  {
    id: '4',
    title: 'Social Media Templates Q3 2025',
    description: 'Ready-to-use social media posts and templates for Facebook, LinkedIn, Twitter',
    type: 'social-media',
    category: 'co-marketing',
    format: 'zip',
    size: '45.8 MB',
    downloads: 78,
    rating: 4.7,
    lastUpdated: '2025-08-10',
    tags: ['social', 'templates', 'Q3'],
    downloadUrl: '/resources/social-templates-q3.zip',
  },
  {
    id: '5',
    title: 'Email Campaign: Business Internet',
    description: 'Email template for business internet marketing campaign',
    type: 'email-template',
    category: 'co-marketing',
    format: 'html',
    size: '125 KB',
    downloads: 201,
    rating: 4.5,
    lastUpdated: '2025-08-25',
    tags: ['email', 'business', 'campaign'],
    downloadUrl: '/resources/business-email-template.html',
    previewUrl: '/resources/previews/business-email.jpg',
  },
  {
    id: '6',
    title: 'Competitive Analysis Report',
    description: 'Q3 2025 competitive landscape and positioning strategies',
    type: 'whitepaper',
    category: 'competitive',
    format: 'pdf',
    size: '3.2 MB',
    downloads: 134,
    rating: 4.8,
    lastUpdated: '2025-08-18',
    tags: ['competitive', 'analysis', 'Q3'],
    downloadUrl: '/resources/competitive-analysis-q3.pdf',
  },
];

export function MarketingResourceCenter() {
  const [resources] = useState<MarketingResource[]>(mockResources);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'newest' | 'popular' | 'rating'>('newest');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  const filteredResources = resources
    .filter((resource) => {
      const matchesCategory = selectedCategory === 'all' || resource.category === selectedCategory;
      const matchesType = selectedType === 'all' || resource.type === selectedType;
      const matchesSearch =
        !searchQuery ||
        resource.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        resource.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        resource.tags.some((tag) => tag.toLowerCase().includes(searchQuery.toLowerCase()));

      return matchesCategory && matchesType && matchesSearch;
    })
    .sort((a, b) => {
      switch (sortBy) {
        case 'popular':
          return b.downloads - a.downloads;
        case 'rating':
          return b.rating - a.rating;
        case 'newest':
        default:
          return new Date(b.lastUpdated).getTime() - new Date(a.lastUpdated).getTime();
      }
    });

  const getTypeIcon = (type: MarketingResource['type']) => {
    const icons = {
      brochure: <FileText className='w-5 h-5' />,
      flyer: <FileText className='w-5 h-5' />,
      presentation: <Presentation className='w-5 h-5' />,
      video: <Video className='w-5 h-5' />,
      'email-template': <Mail className='w-5 h-5' />,
      'social-media': <Share2 className='w-5 h-5' />,
      'case-study': <TrendingUp className='w-5 h-5' />,
      whitepaper: <FileText className='w-5 h-5' />,
    };
    return icons[type] || <FileText className='w-5 h-5' />;
  };

  const getCategoryColor = (category: MarketingResource['category']) => {
    const colors = {
      'sales-materials': 'bg-blue-100 text-blue-800',
      'brand-assets': 'bg-purple-100 text-purple-800',
      'co-marketing': 'bg-green-100 text-green-800',
      training: 'bg-orange-100 text-orange-800',
      competitive: 'bg-red-100 text-red-800',
    };
    return colors[category] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className='space-y-6'>
      {/* Header Actions */}
      <div className='bg-white rounded-lg p-6 shadow-sm border'>
        <div className='flex flex-col lg:flex-row gap-4'>
          {/* Search */}
          <div className='flex-1 relative'>
            <Search className='absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4' />
            <input
              type='text'
              placeholder='Search marketing resources...'
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className='w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            />
          </div>

          {/* Filters */}
          <div className='flex flex-wrap gap-2'>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className='px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            >
              <option value='all'>All Categories</option>
              <option value='sales-materials'>Sales Materials</option>
              <option value='brand-assets'>Brand Assets</option>
              <option value='co-marketing'>Co-Marketing</option>
              <option value='training'>Training</option>
              <option value='competitive'>Competitive</option>
            </select>

            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className='px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            >
              <option value='all'>All Types</option>
              <option value='brochure'>Brochures</option>
              <option value='presentation'>Presentations</option>
              <option value='video'>Videos</option>
              <option value='email-template'>Email Templates</option>
              <option value='social-media'>Social Media</option>
              <option value='case-study'>Case Studies</option>
            </select>

            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className='px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            >
              <option value='newest'>Newest First</option>
              <option value='popular'>Most Downloaded</option>
              <option value='rating'>Highest Rated</option>
            </select>

            {/* View Toggle */}
            <div className='flex border border-gray-300 rounded-lg overflow-hidden'>
              <button
                onClick={() => setViewMode('grid')}
                className={clsx(
                  'px-3 py-2 text-sm transition-colors',
                  viewMode === 'grid'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-50'
                )}
              >
                Grid
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={clsx(
                  'px-3 py-2 text-sm transition-colors',
                  viewMode === 'list'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-50'
                )}
              >
                List
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Access Categories */}
      <div className='grid grid-cols-1 md:grid-cols-5 gap-4'>
        {[
          { key: 'sales-materials', label: 'Sales Materials', icon: Target, count: 12 },
          { key: 'brand-assets', label: 'Brand Assets', icon: Palette, count: 8 },
          { key: 'co-marketing', label: 'Co-Marketing', icon: Users, count: 15 },
          { key: 'training', label: 'Training', icon: Calendar, count: 6 },
          { key: 'competitive', label: 'Competitive', icon: TrendingUp, count: 4 },
        ].map((category) => (
          <button
            key={category.key}
            onClick={() =>
              setSelectedCategory(category.key === selectedCategory ? 'all' : category.key)
            }
            className={clsx(
              'bg-white rounded-lg p-4 shadow-sm border transition-all hover:shadow-md',
              'flex flex-col items-center space-y-2 text-center',
              selectedCategory === category.key ? 'ring-2 ring-blue-500 border-blue-500' : ''
            )}
          >
            <category.icon className='w-8 h-8 text-blue-600' />
            <div>
              <div className='font-medium text-gray-900'>{category.label}</div>
              <div className='text-sm text-gray-500'>{category.count} resources</div>
            </div>
          </button>
        ))}
      </div>

      {/* Resources Display */}
      <div className='bg-white rounded-lg shadow-sm border'>
        {viewMode === 'grid' ? (
          <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-6'>
            {filteredResources.map((resource) => (
              <div
                key={resource.id}
                className='border rounded-lg p-4 hover:shadow-md transition-shadow'
              >
                {/* Thumbnail */}
                <div className='aspect-video bg-gray-100 rounded-lg mb-4 flex items-center justify-center'>
                  {resource.thumbnail ? (
                    <img
                      src={resource.thumbnail}
                      alt={resource.title}
                      className='w-full h-full object-cover rounded-lg'
                    />
                  ) : (
                    <div className='text-gray-400'>{getTypeIcon(resource.type)}</div>
                  )}
                </div>

                {/* Content */}
                <div className='space-y-3'>
                  <div>
                    <h3 className='font-medium text-gray-900 line-clamp-2'>{resource.title}</h3>
                    <p className='text-sm text-gray-600 mt-1 line-clamp-2'>
                      {resource.description}
                    </p>
                  </div>

                  {/* Metadata */}
                  <div className='flex items-center justify-between text-xs text-gray-500'>
                    <span>
                      {resource.format.toUpperCase()} • {resource.size}
                    </span>
                    <div className='flex items-center space-x-1'>
                      <Star className='w-3 h-3 fill-yellow-400 text-yellow-400' />
                      <span>{resource.rating}</span>
                    </div>
                  </div>

                  {/* Category and Downloads */}
                  <div className='flex items-center justify-between'>
                    <span
                      className={clsx(
                        'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium',
                        getCategoryColor(resource.category)
                      )}
                    >
                      {resource.category.replace('-', ' ')}
                    </span>
                    <span className='text-xs text-gray-500'>{resource.downloads} downloads</span>
                  </div>

                  {/* Tags */}
                  <div className='flex flex-wrap gap-1'>
                    {resource.tags.slice(0, 3).map((tag) => (
                      <span
                        key={tag}
                        className='inline-flex items-center px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-600'
                      >
                        {tag}
                      </span>
                    ))}
                    {resource.tags.length > 3 && (
                      <span className='text-xs text-gray-400'>+{resource.tags.length - 3}</span>
                    )}
                  </div>

                  {/* Actions */}
                  <div className='flex space-x-2 pt-2'>
                    <button className='flex-1 bg-blue-600 text-white px-3 py-2 rounded-lg hover:bg-blue-700 transition-colors text-sm flex items-center justify-center space-x-1'>
                      <Download className='w-4 h-4' />
                      <span>Download</span>
                    </button>
                    {resource.previewUrl && (
                      <button className='border border-gray-300 text-gray-700 px-3 py-2 rounded-lg hover:bg-gray-50 transition-colors text-sm flex items-center justify-center'>
                        <Eye className='w-4 h-4' />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className='divide-y'>
            {filteredResources.map((resource) => (
              <div key={resource.id} className='p-6 hover:bg-gray-50 transition-colors'>
                <div className='flex items-start justify-between'>
                  <div className='flex items-start space-x-4 flex-1'>
                    {/* Icon */}
                    <div className='p-2 bg-gray-100 rounded-lg'>{getTypeIcon(resource.type)}</div>

                    {/* Content */}
                    <div className='flex-1 min-w-0'>
                      <div className='flex items-start justify-between'>
                        <div>
                          <h3 className='font-medium text-gray-900'>{resource.title}</h3>
                          <p className='text-sm text-gray-600 mt-1'>{resource.description}</p>
                        </div>

                        <div className='flex items-center space-x-4 ml-4'>
                          <div className='text-right'>
                            <div className='text-sm font-medium text-gray-900'>
                              {resource.downloads} downloads
                            </div>
                            <div className='flex items-center space-x-1 text-xs text-gray-500'>
                              <Star className='w-3 h-3 fill-yellow-400 text-yellow-400' />
                              <span>{resource.rating}</span>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Metadata Row */}
                      <div className='flex items-center space-x-4 mt-3 text-sm text-gray-500'>
                        <span
                          className={clsx(
                            'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium',
                            getCategoryColor(resource.category)
                          )}
                        >
                          {resource.category.replace('-', ' ')}
                        </span>
                        <span>
                          {resource.format.toUpperCase()} • {resource.size}
                        </span>
                        <span className='flex items-center space-x-1'>
                          <Clock className='w-3 h-3' />
                          <span>Updated {new Date(resource.lastUpdated).toLocaleDateString()}</span>
                        </span>
                      </div>

                      {/* Tags */}
                      <div className='flex flex-wrap gap-1 mt-2'>
                        {resource.tags.map((tag) => (
                          <span
                            key={tag}
                            className='inline-flex items-center px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-600'
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className='flex items-center space-x-2 ml-4'>
                    {resource.previewUrl && (
                      <button className='p-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors'>
                        <Eye className='w-4 h-4 text-gray-600' />
                      </button>
                    )}
                    <button className='bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors text-sm flex items-center space-x-1'>
                      <Download className='w-4 h-4' />
                      <span>Download</span>
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {filteredResources.length === 0 && (
          <div className='p-12 text-center'>
            <div className='w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4'>
              <Search className='w-8 h-8 text-gray-400' />
            </div>
            <h3 className='text-lg font-medium text-gray-900 mb-2'>No resources found</h3>
            <p className='text-gray-600'>Try adjusting your search criteria or filters</p>
          </div>
        )}
      </div>

      {/* Marketing Campaigns Section */}
      <div className='bg-white rounded-lg p-6 shadow-sm border'>
        <div className='flex items-center justify-between mb-6'>
          <h2 className='text-lg font-semibold text-gray-900'>Active Marketing Campaigns</h2>
          <button className='bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors text-sm flex items-center space-x-1'>
            <Megaphone className='w-4 h-4' />
            <span>New Campaign</span>
          </button>
        </div>

        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'>
          <div className='border rounded-lg p-4'>
            <div className='flex items-center justify-between mb-3'>
              <h3 className='font-medium text-gray-900'>Q3 Fiber Push</h3>
              <span className='bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs font-medium'>
                Active
              </span>
            </div>
            <p className='text-sm text-gray-600 mb-4'>
              Promoting fiber services to enterprise clients
            </p>
            <div className='space-y-2 text-sm'>
              <div className='flex justify-between'>
                <span className='text-gray-500'>Leads Generated:</span>
                <span className='font-medium'>47</span>
              </div>
              <div className='flex justify-between'>
                <span className='text-gray-500'>Conversion Rate:</span>
                <span className='font-medium'>12.3%</span>
              </div>
              <div className='flex justify-between'>
                <span className='text-gray-500'>Revenue:</span>
                <span className='font-medium'>$125,000</span>
              </div>
            </div>
          </div>

          <div className='border rounded-lg p-4'>
            <div className='flex items-center justify-between mb-3'>
              <h3 className='font-medium text-gray-900'>Small Business Outreach</h3>
              <span className='bg-yellow-100 text-yellow-800 px-2 py-1 rounded-full text-xs font-medium'>
                Planning
              </span>
            </div>
            <p className='text-sm text-gray-600 mb-4'>
              Targeting local small businesses for basic packages
            </p>
            <div className='space-y-2 text-sm'>
              <div className='flex justify-between'>
                <span className='text-gray-500'>Target Leads:</span>
                <span className='font-medium'>200</span>
              </div>
              <div className='flex justify-between'>
                <span className='text-gray-500'>Launch Date:</span>
                <span className='font-medium'>Sep 15, 2025</span>
              </div>
              <div className='flex justify-between'>
                <span className='text-gray-500'>Budget:</span>
                <span className='font-medium'>$15,000</span>
              </div>
            </div>
          </div>

          <div className='border rounded-lg p-4'>
            <div className='flex items-center justify-between mb-3'>
              <h3 className='font-medium text-gray-900'>Referral Program</h3>
              <span className='bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs font-medium'>
                Ongoing
              </span>
            </div>
            <p className='text-sm text-gray-600 mb-4'>Customer referral incentive program</p>
            <div className='space-y-2 text-sm'>
              <div className='flex justify-between'>
                <span className='text-gray-500'>Referrals:</span>
                <span className='font-medium'>23</span>
              </div>
              <div className='flex justify-between'>
                <span className='text-gray-500'>Conversion Rate:</span>
                <span className='font-medium'>34.8%</span>
              </div>
              <div className='flex justify-between'>
                <span className='text-gray-500'>Rewards Paid:</span>
                <span className='font-medium'>$4,600</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Co-Marketing Opportunities */}
      <div className='bg-white rounded-lg p-6 shadow-sm border'>
        <div className='flex items-center justify-between mb-6'>
          <h2 className='text-lg font-semibold text-gray-900'>Co-Marketing Opportunities</h2>
          <button className='border border-blue-600 text-blue-600 px-4 py-2 rounded-lg hover:bg-blue-50 transition-colors text-sm'>
            View All
          </button>
        </div>

        <div className='space-y-4'>
          <div className='border rounded-lg p-4 flex items-start justify-between'>
            <div className='flex items-start space-x-4'>
              <div className='w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center'>
                <Globe className='w-6 h-6 text-blue-600' />
              </div>
              <div>
                <h3 className='font-medium text-gray-900'>DotMac Trade Show Booth</h3>
                <p className='text-sm text-gray-600 mt-1'>
                  Partner with us at the upcoming ISP Technology Summit
                </p>
                <div className='flex items-center space-x-4 mt-2 text-xs text-gray-500'>
                  <span>Event: Oct 15-17, 2025</span>
                  <span>Location: Las Vegas, NV</span>
                  <span>Cost Share: 50%</span>
                </div>
              </div>
            </div>
            <button className='bg-green-600 text-white px-3 py-1.5 rounded text-sm hover:bg-green-700 transition-colors'>
              Join Campaign
            </button>
          </div>

          <div className='border rounded-lg p-4 flex items-start justify-between'>
            <div className='flex items-start space-x-4'>
              <div className='w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center'>
                <Mail className='w-6 h-6 text-purple-600' />
              </div>
              <div>
                <h3 className='font-medium text-gray-900'>Joint Email Campaign</h3>
                <p className='text-sm text-gray-600 mt-1'>
                  Collaborative email marketing to shared customer segments
                </p>
                <div className='flex items-center space-x-4 mt-2 text-xs text-gray-500'>
                  <span>Target: 2,500 contacts</span>
                  <span>Launch: Sep 1, 2025</span>
                  <span>Expected ROI: 250%</span>
                </div>
              </div>
            </div>
            <button className='border border-purple-600 text-purple-600 px-3 py-1.5 rounded text-sm hover:bg-purple-50 transition-colors'>
              Learn More
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
