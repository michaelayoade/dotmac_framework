'use client';

import React, { useState } from 'react';
import {
  DocumentIcon,
  CodeBracketIcon,
  ArrowDownTrayIcon,
  BookOpenIcon,
  CommandLineIcon,
  CubeIcon,
} from '@heroicons/react/24/outline';
import { useAPIDocumentation } from '@/lib/api-documentation';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

export default function APIDocsPage() {
  const { documentation, loading, downloadDocumentation } = useAPIDocumentation();
  const [selectedTag, setSelectedTag] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');

  if (loading) {
    return (
      <div className='flex justify-center items-center min-h-96'>
        <LoadingSpinner size='large' />
      </div>
    );
  }

  if (!documentation) {
    return (
      <div className='text-center py-12'>
        <DocumentIcon className='mx-auto h-12 w-12 text-gray-400' />
        <h3 className='mt-2 text-sm font-medium text-gray-900'>No documentation available</h3>
        <p className='mt-1 text-sm text-gray-500'>Documentation could not be loaded</p>
      </div>
    );
  }

  // Filter endpoints based on selected tag and search term
  const filteredPaths = Object.entries(documentation.paths).filter(([path, methods]) => {
    const pathMatches = searchTerm === '' || path.toLowerCase().includes(searchTerm.toLowerCase());

    if (selectedTag === 'all') {
      return pathMatches;
    }

    const hasTaggedMethod = Object.values(methods).some((endpoint) =>
      endpoint.tags?.includes(selectedTag)
    );

    return pathMatches && hasTaggedMethod;
  });

  return (
    <div className='space-y-6'>
      {/* Header */}
      <div className='bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg shadow-lg text-white p-8'>
        <div className='flex items-start justify-between'>
          <div>
            <h1 className='text-3xl font-bold mb-2'>{documentation.info.title}</h1>
            <p className='text-blue-100 text-lg max-w-2xl'>
              Complete API documentation for the DotMac Management Admin Portal
            </p>
            <div className='mt-4 flex items-center space-x-4 text-sm text-blue-100'>
              <span>Version {documentation.info.version}</span>
              <span>•</span>
              <span>{Object.keys(documentation.paths).length} endpoints</span>
              <span>•</span>
              <span>{documentation.tags.length} categories</span>
            </div>
          </div>
          <div className='flex space-x-2'>
            <button
              onClick={() => downloadDocumentation('json')}
              className='bg-white bg-opacity-20 hover:bg-opacity-30 px-4 py-2 rounded-md text-sm font-medium transition-colors'
            >
              <ArrowDownTrayIcon className='h-4 w-4 inline mr-2' />
              JSON
            </button>
            <button
              onClick={() => downloadDocumentation('markdown')}
              className='bg-white bg-opacity-20 hover:bg-opacity-30 px-4 py-2 rounded-md text-sm font-medium transition-colors'
            >
              <DocumentIcon className='h-4 w-4 inline mr-2' />
              Markdown
            </button>
            <button
              onClick={() => downloadDocumentation('types')}
              className='bg-white bg-opacity-20 hover:bg-opacity-30 px-4 py-2 rounded-md text-sm font-medium transition-colors'
            >
              <CodeBracketIcon className='h-4 w-4 inline mr-2' />
              Types
            </button>
          </div>
        </div>
      </div>

      <div className='grid grid-cols-1 lg:grid-cols-12 gap-6'>
        {/* Sidebar */}
        <div className='lg:col-span-3'>
          <div className='card sticky top-6'>
            <div className='card-header'>
              <h3 className='text-lg font-medium text-gray-900'>Navigation</h3>
            </div>
            <div className='card-content space-y-4'>
              {/* Search */}
              <div>
                <label htmlFor='search' className='sr-only'>
                  Search endpoints
                </label>
                <input
                  type='text'
                  id='search'
                  placeholder='Search endpoints...'
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className='input w-full'
                />
              </div>

              {/* Tags */}
              <div>
                <h4 className='text-sm font-medium text-gray-900 mb-2'>Categories</h4>
                <div className='space-y-1'>
                  <button
                    onClick={() => setSelectedTag('all')}
                    className={`w-full text-left px-3 py-2 text-sm rounded-md transition-colors ${
                      selectedTag === 'all'
                        ? 'bg-blue-100 text-blue-700 font-medium'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                    }`}
                  >
                    All Endpoints
                  </button>
                  {documentation.tags.map((tag) => (
                    <button
                      key={tag.name}
                      onClick={() => setSelectedTag(tag.name)}
                      className={`w-full text-left px-3 py-2 text-sm rounded-md transition-colors ${
                        selectedTag === tag.name
                          ? 'bg-blue-100 text-blue-700 font-medium'
                          : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                      }`}
                    >
                      {tag.name}
                    </button>
                  ))}
                </div>
              </div>

              {/* Quick Links */}
              <div>
                <h4 className='text-sm font-medium text-gray-900 mb-2'>Quick Links</h4>
                <div className='space-y-1'>
                  <a
                    href='#authentication'
                    className='flex items-center px-3 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded-md'
                  >
                    <CommandLineIcon className='h-4 w-4 mr-2' />
                    Authentication
                  </a>
                  <a
                    href='#schemas'
                    className='flex items-center px-3 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded-md'
                  >
                    <CubeIcon className='h-4 w-4 mr-2' />
                    Data Models
                  </a>
                  <a
                    href='#examples'
                    className='flex items-center px-3 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded-md'
                  >
                    <BookOpenIcon className='h-4 w-4 mr-2' />
                    Examples
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className='lg:col-span-9 space-y-6'>
          {/* Authentication Info */}
          <div id='authentication' className='card'>
            <div className='card-header'>
              <h2 className='text-xl font-semibold text-gray-900'>Authentication</h2>
            </div>
            <div className='card-content prose prose-sm max-w-none'>
              <p>
                Most API endpoints require authentication using Bearer tokens. Include your token in
                the Authorization header:
              </p>
              <pre className='bg-gray-50 p-4 rounded-md overflow-x-auto'>
                <code>Authorization: Bearer &lt;your-token&gt;</code>
              </pre>
              <p>
                Tokens can be obtained through the <code>/api/v1/auth/login</code> endpoint.
              </p>
            </div>
          </div>

          {/* Endpoints */}
          <div className='space-y-4'>
            {filteredPaths.length === 0 ? (
              <div className='card'>
                <div className='card-content text-center py-12'>
                  <DocumentIcon className='mx-auto h-12 w-12 text-gray-400 mb-4' />
                  <h3 className='text-lg font-medium text-gray-900 mb-2'>No endpoints found</h3>
                  <p className='text-gray-600'>
                    {searchTerm
                      ? `No endpoints match "${searchTerm}"`
                      : selectedTag !== 'all'
                        ? `No endpoints in "${selectedTag}" category`
                        : 'No endpoints available'}
                  </p>
                </div>
              </div>
            ) : (
              filteredPaths.map(([path, methods]) => (
                <div key={path} className='card'>
                  <div className='card-header'>
                    <h3 className='text-lg font-medium text-gray-900 font-mono'>{path}</h3>
                  </div>
                  <div className='card-content space-y-6'>
                    {Object.entries(methods).map(([method, endpoint]) => (
                      <div key={method} className='border-l-4 border-blue-500 pl-6'>
                        <div className='flex items-start justify-between mb-3'>
                          <div>
                            <div className='flex items-center space-x-3 mb-2'>
                              <span
                                className={`px-2 py-1 text-xs font-medium rounded uppercase ${
                                  method === 'get'
                                    ? 'bg-green-100 text-green-700'
                                    : method === 'post'
                                      ? 'bg-blue-100 text-blue-700'
                                      : method === 'put'
                                        ? 'bg-orange-100 text-orange-700'
                                        : method === 'delete'
                                          ? 'bg-red-100 text-red-700'
                                          : 'bg-gray-100 text-gray-700'
                                }`}
                              >
                                {method}
                              </span>
                              <h4 className='text-lg font-medium text-gray-900'>
                                {endpoint.summary}
                              </h4>
                            </div>
                            <p className='text-gray-600'>{endpoint.description}</p>
                          </div>
                          {endpoint.tags && (
                            <div className='flex flex-wrap gap-1'>
                              {endpoint.tags.map((tag) => (
                                <span
                                  key={tag}
                                  className='px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded'
                                >
                                  {tag}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>

                        {/* Parameters */}
                        {endpoint.parameters && endpoint.parameters.length > 0 && (
                          <div className='mb-4'>
                            <h5 className='text-sm font-medium text-gray-900 mb-2'>Parameters</h5>
                            <div className='overflow-x-auto'>
                              <table className='min-w-full divide-y divide-gray-200'>
                                <thead className='bg-gray-50'>
                                  <tr>
                                    <th className='px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase'>
                                      Name
                                    </th>
                                    <th className='px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase'>
                                      Type
                                    </th>
                                    <th className='px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase'>
                                      Required
                                    </th>
                                    <th className='px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase'>
                                      Description
                                    </th>
                                  </tr>
                                </thead>
                                <tbody className='divide-y divide-gray-200'>
                                  {endpoint.parameters.map((param) => (
                                    <tr key={param.name}>
                                      <td className='px-3 py-2 text-sm font-mono text-gray-900'>
                                        {param.name}
                                      </td>
                                      <td className='px-3 py-2 text-sm text-gray-600'>
                                        {param.schema.type} ({param.in})
                                      </td>
                                      <td className='px-3 py-2 text-sm'>
                                        {param.required ? (
                                          <span className='text-red-600 font-medium'>Yes</span>
                                        ) : (
                                          <span className='text-gray-500'>No</span>
                                        )}
                                      </td>
                                      <td className='px-3 py-2 text-sm text-gray-600'>
                                        {param.description}
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        )}

                        {/* Request Body */}
                        {endpoint.requestBody && (
                          <div className='mb-4'>
                            <h5 className='text-sm font-medium text-gray-900 mb-2'>Request Body</h5>
                            <p className='text-sm text-gray-600 mb-2'>
                              {endpoint.requestBody.description}
                            </p>
                            {endpoint.requestBody.required && (
                              <span className='inline-block px-2 py-1 text-xs bg-red-100 text-red-700 rounded'>
                                Required
                              </span>
                            )}
                          </div>
                        )}

                        {/* Responses */}
                        <div className='mb-4'>
                          <h5 className='text-sm font-medium text-gray-900 mb-2'>Responses</h5>
                          <div className='space-y-2'>
                            {endpoint.responses.map((response) => (
                              <div
                                key={response.status}
                                className='flex items-start space-x-3 p-3 bg-gray-50 rounded-md'
                              >
                                <span
                                  className={`px-2 py-1 text-xs font-medium rounded ${
                                    response.status >= 200 && response.status < 300
                                      ? 'bg-green-100 text-green-700'
                                      : response.status >= 400
                                        ? 'bg-red-100 text-red-700'
                                        : 'bg-gray-100 text-gray-700'
                                  }`}
                                >
                                  {response.status}
                                </span>
                                <div>
                                  <p className='text-sm font-medium text-gray-900'>
                                    {response.description}
                                  </p>
                                  {response.content && (
                                    <div className='mt-1'>
                                      {Object.keys(response.content).map((mediaType) => (
                                        <span
                                          key={mediaType}
                                          className='inline-block px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded mr-1'
                                        >
                                          {mediaType}
                                        </span>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Data Models */}
          <div id='schemas' className='card'>
            <div className='card-header'>
              <h2 className='text-xl font-semibold text-gray-900'>Data Models</h2>
            </div>
            <div className='card-content'>
              <div className='grid grid-cols-1 md:grid-cols-2 gap-4'>
                {Object.entries(documentation.components.schemas).map(([name, schema]) => (
                  <div key={name} className='border border-gray-200 rounded-md p-4'>
                    <h4 className='text-lg font-medium text-gray-900 mb-2 font-mono'>{name}</h4>
                    {schema.description && (
                      <p className='text-sm text-gray-600 mb-3'>{schema.description}</p>
                    )}
                    {schema.properties && (
                      <div className='space-y-2'>
                        {Object.entries(schema.properties).map(([propName, propSchema]) => (
                          <div key={propName} className='flex justify-between items-start'>
                            <div>
                              <span className='text-sm font-mono text-gray-900'>{propName}</span>
                              {schema.required?.includes(propName) && (
                                <span className='ml-2 text-xs text-red-600'>required</span>
                              )}
                            </div>
                            <span className='text-sm text-gray-500'>{propSchema.type}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
