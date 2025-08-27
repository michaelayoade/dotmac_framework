'use client';

import React, { useState, useCallback, useMemo } from 'react';
import { useCommunication } from '@dotmac/headless';
import { 
  useNotifications, 
  NotificationList, 
  NotificationBadge 
} from '@dotmac/primitives';

interface CommunicationCenterProps {
  className?: string;
}

export function CommunicationCenter({ className = '' }: CommunicationCenterProps) {
  const [activeTab, setActiveTab] = useState<'messages' | 'templates' | 'channels' | 'settings'>('messages');
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [messageFilters, setMessageFilters] = useState({
    status: '',
    channel: '',
    priority: '',
    dateFrom: '',
    dateTo: '',
  });

  const communication = useCommunication({
    websocketEndpoint: process.env.NEXT_PUBLIC_WS_URL,
    apiKey: process.env.NEXT_PUBLIC_API_KEY,
    enableRealtime: true,
    pollInterval: 30000,
  });

  const { state, addNotification } = useNotifications();

  // Quick Actions
  const sendTestMessage = useCallback(async () => {
    try {
      await communication.sendMessage({
        channel: 'email',
        recipient: 'test@example.com',
        subject: 'Test Message',
        body: 'This is a test message from the communication center.',
        priority: 'low',
        metadata: { source: 'communication_center_test' },
      });
    } catch (error) {
      console.error('Failed to send test message:', error);
    }
  }, [communication]);

  const sendBulkCustomerNotification = useCallback(async (templateId: string, recipients: string[]) => {
    try {
      const template = communication.templates.find(t => t.id === templateId);
      if (!template) {
        throw new Error('Template not found');
      }

      const messages = recipients.map(recipient => ({
        templateId,
        channel: template.channel,
        recipient,
        priority: template.priority,
        metadata: { source: 'bulk_customer_notification' },
      }));

      await communication.sendBulkMessages(messages);
      
      addNotification({
        type: 'success',
        priority: 'medium',
        title: 'Bulk Notification Sent',
        message: `Sent notifications to ${recipients.length} customers`,
        channel: ['browser'],
        persistent: false,
      });
    } catch (error) {
      console.error('Failed to send bulk notification:', error);
    }
  }, [communication, addNotification]);

  // Filtered and sorted data
  const filteredMessages = useMemo(() => {
    return communication.messages.filter(message => {
      if (messageFilters.status && message.status !== messageFilters.status) return false;
      if (messageFilters.channel && message.channel !== messageFilters.channel) return false;
      if (messageFilters.priority && message.priority !== messageFilters.priority) return false;
      if (messageFilters.dateFrom && message.sentAt && message.sentAt < new Date(messageFilters.dateFrom)) return false;
      if (messageFilters.dateTo && message.sentAt && message.sentAt > new Date(messageFilters.dateTo)) return false;
      return true;
    });
  }, [communication.messages, messageFilters]);

  const stats = communication.stats || {
    totalSent: 0,
    totalDelivered: 0,
    totalFailed: 0,
    deliveryRate: 0,
    failureRate: 0,
    channelBreakdown: {},
    recentActivity: [],
  };

  return (
    <div className={`communication-center ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-4">
          <h1 className="text-2xl font-bold text-gray-900">Communication Center</h1>
          <div className="flex items-center space-x-2">
            {communication.isConnected ? (
              <div className="flex items-center space-x-1 text-green-600">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-sm">Connected</span>
              </div>
            ) : (
              <div className="flex items-center space-x-1 text-red-600">
                <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                <span className="text-sm">Disconnected</span>
              </div>
            )}
          </div>
        </div>
        
        <div className="flex items-center space-x-3">
          <NotificationBadge className="mr-2" />
          <button
            onClick={sendTestMessage}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            disabled={communication.isLoading}
          >
            Send Test Message
          </button>
        </div>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-600">Total Sent</p>
              <p className="text-2xl font-bold text-gray-900">{stats.totalSent.toLocaleString()}</p>
            </div>
            <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
              <span className="text-blue-600">📤</span>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-600">Delivered</p>
              <p className="text-2xl font-bold text-green-600">{stats.totalDelivered.toLocaleString()}</p>
            </div>
            <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
              <span className="text-green-600">✅</span>
            </div>
          </div>
          <div className="mt-2">
            <p className="text-xs text-gray-500">
              {stats.deliveryRate.toFixed(1)}% delivery rate
            </p>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-600">Failed</p>
              <p className="text-2xl font-bold text-red-600">{stats.totalFailed.toLocaleString()}</p>
            </div>
            <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
              <span className="text-red-600">❌</span>
            </div>
          </div>
          <div className="mt-2">
            <p className="text-xs text-gray-500">
              {stats.failureRate.toFixed(1)}% failure rate
            </p>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-600">Active Channels</p>
              <p className="text-2xl font-bold text-blue-600">{communication.activeChannels.length}</p>
            </div>
            <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
              <span className="text-blue-600">📡</span>
            </div>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: 'messages', label: 'Messages', count: communication.messages.length },
            { id: 'templates', label: 'Templates', count: communication.templates.length },
            { id: 'channels', label: 'Channels', count: communication.channels.length },
            { id: 'settings', label: 'Settings' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`
                py-2 px-1 border-b-2 font-medium text-sm whitespace-nowrap
                ${activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }
              `}
            >
              {tab.label}
              {tab.count !== undefined && (
                <span className="ml-2 bg-gray-100 text-gray-900 py-0.5 px-2.5 rounded-full text-xs">
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {activeTab === 'messages' && (
          <MessagesTab
            messages={filteredMessages}
            filters={messageFilters}
            onFiltersChange={setMessageFilters}
            onRetry={communication.retryMessage}
            onCancel={communication.cancelMessage}
            isLoading={communication.isLoading}
          />
        )}

        {activeTab === 'templates' && (
          <TemplatesTab
            templates={communication.templates}
            channels={communication.channels}
            onCreateTemplate={communication.createTemplate}
            onUpdateTemplate={communication.updateTemplate}
            onDeleteTemplate={communication.deleteTemplate}
            onBulkSend={sendBulkCustomerNotification}
          />
        )}

        {activeTab === 'channels' && (
          <ChannelsTab
            channels={communication.channels}
            onTestChannel={communication.testChannel}
          />
        )}

        {activeTab === 'settings' && (
          <SettingsTab
            settings={state.settings}
            onUpdateSettings={(settings) => {
              // Update notification settings if needed
            }}
          />
        )}
      </div>

      {/* Notification List */}
      <NotificationList
        position="top-right"
        maxVisible={3}
        showActions={true}
        onNotificationClick={(notification) => {
          console.log('Notification clicked:', notification);
        }}
      />
    </div>
  );
}

// Messages Tab Component
interface MessagesTabProps {
  messages: any[];
  filters: any;
  onFiltersChange: (filters: any) => void;
  onRetry: (id: string) => Promise<any>;
  onCancel: (id: string) => Promise<void>;
  isLoading: boolean;
}

function MessagesTab({ 
  messages, 
  filters, 
  onFiltersChange, 
  onRetry, 
  onCancel, 
  isLoading 
}: MessagesTabProps) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'sent': return '📤';
      case 'delivered': return '✅';
      case 'failed': return '❌';
      case 'pending': return '⏳';
      case 'bounced': return '↩️';
      default: return '📋';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'sent': return 'text-blue-600 bg-blue-50';
      case 'delivered': return 'text-green-600 bg-green-50';
      case 'failed': return 'text-red-600 bg-red-50';
      case 'pending': return 'text-yellow-600 bg-yellow-50';
      case 'bounced': return 'text-orange-600 bg-orange-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  return (
    <div className="messages-tab">
      {/* Filters */}
      <div className="bg-white p-4 rounded-lg shadow mb-6">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select
              value={filters.status}
              onChange={(e) => onFiltersChange({ ...filters, status: e.target.value })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              <option value="">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="sent">Sent</option>
              <option value="delivered">Delivered</option>
              <option value="failed">Failed</option>
              <option value="bounced">Bounced</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Channel</label>
            <select
              value={filters.channel}
              onChange={(e) => onFiltersChange({ ...filters, channel: e.target.value })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              <option value="">All Channels</option>
              <option value="email">Email</option>
              <option value="sms">SMS</option>
              <option value="push">Push</option>
              <option value="websocket">WebSocket</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
            <select
              value={filters.priority}
              onChange={(e) => onFiltersChange({ ...filters, priority: e.target.value })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              <option value="">All Priorities</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">From Date</label>
            <input
              type="date"
              value={filters.dateFrom}
              onChange={(e) => onFiltersChange({ ...filters, dateFrom: e.target.value })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">To Date</label>
            <input
              type="date"
              value={filters.dateTo}
              onChange={(e) => onFiltersChange({ ...filters, dateTo: e.target.value })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            />
          </div>
        </div>
      </div>

      {/* Messages List */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="mt-2 text-gray-500">Loading messages...</p>
          </div>
        ) : messages.length === 0 ? (
          <div className="p-8 text-center">
            <div className="text-gray-400 text-4xl mb-4">📭</div>
            <p className="text-gray-500">No messages found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Recipient
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Channel
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Subject
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Priority
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Sent At
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {messages.map((message) => (
                  <tr key={message.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(message.status)}`}>
                        <span className="mr-1">{getStatusIcon(message.status)}</span>
                        {message.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {message.recipient}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {message.channel}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 max-w-xs truncate">
                      {message.subject || 'No subject'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {message.priority}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {message.sentAt ? new Date(message.sentAt).toLocaleString() : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      {message.status === 'failed' && (
                        <button
                          onClick={() => onRetry(message.id)}
                          className="text-blue-600 hover:text-blue-900 mr-3"
                        >
                          Retry
                        </button>
                      )}
                      {message.status === 'pending' && (
                        <button
                          onClick={() => onCancel(message.id)}
                          className="text-red-600 hover:text-red-900"
                        >
                          Cancel
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// Templates Tab Component
interface TemplatesTabProps {
  templates: any[];
  channels: any[];
  onCreateTemplate: (template: any) => Promise<any>;
  onUpdateTemplate: (id: string, template: any) => Promise<any>;
  onDeleteTemplate: (id: string) => Promise<void>;
  onBulkSend: (templateId: string, recipients: string[]) => Promise<void>;
}

function TemplatesTab({ 
  templates, 
  channels, 
  onCreateTemplate, 
  onUpdateTemplate, 
  onDeleteTemplate,
  onBulkSend 
}: TemplatesTabProps) {
  const [isCreating, setIsCreating] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<any>(null);

  return (
    <div className="templates-tab">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-lg font-medium text-gray-900">Communication Templates</h2>
        <button
          onClick={() => setIsCreating(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Create Template
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {templates.map((template) => (
          <div key={template.id} className="bg-white p-6 rounded-lg shadow">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900">{template.name}</h3>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                template.priority === 'critical' ? 'bg-red-100 text-red-800' :
                template.priority === 'high' ? 'bg-orange-100 text-orange-800' :
                template.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                'bg-green-100 text-green-800'
              }`}>
                {template.priority}
              </span>
            </div>

            <div className="space-y-2 mb-4">
              <p className="text-sm text-gray-600">Channel: <span className="font-medium">{template.channel}</span></p>
              <p className="text-sm text-gray-600">Category: <span className="font-medium">{template.category}</span></p>
              {template.subject && (
                <p className="text-sm text-gray-600">Subject: <span className="font-medium">{template.subject}</span></p>
              )}
            </div>

            <div className="mb-4">
              <p className="text-sm text-gray-700 line-clamp-3">{template.body}</p>
            </div>

            <div className="flex space-x-2">
              <button
                onClick={() => setEditingTemplate(template)}
                className="flex-1 px-3 py-2 border border-gray-300 text-gray-700 rounded-md text-sm hover:bg-gray-50"
              >
                Edit
              </button>
              <button
                onClick={() => {
                  const recipients = prompt('Enter comma-separated email addresses:');
                  if (recipients) {
                    onBulkSend(template.id, recipients.split(',').map(r => r.trim()));
                  }
                }}
                className="flex-1 px-3 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700"
              >
                Bulk Send
              </button>
            </div>
          </div>
        ))}
      </div>

      {templates.length === 0 && (
        <div className="text-center py-12">
          <div className="text-gray-400 text-4xl mb-4">📝</div>
          <p className="text-gray-500">No templates found. Create your first template to get started.</p>
        </div>
      )}
    </div>
  );
}

// Channels Tab Component
interface ChannelsTabProps {
  channels: any[];
  onTestChannel: (channelId: string, testData: any) => Promise<any>;
}

function ChannelsTab({ channels, onTestChannel }: ChannelsTabProps) {
  const getChannelIcon = (type: string) => {
    switch (type) {
      case 'email': return '📧';
      case 'sms': return '📱';
      case 'push': return '🔔';
      case 'websocket': return '🔗';
      case 'webhook': return '🎣';
      default: return '📡';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'text-green-600 bg-green-50';
      case 'inactive': return 'text-gray-600 bg-gray-50';
      case 'error': return 'text-red-600 bg-red-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  return (
    <div className="channels-tab">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {channels.map((channel) => (
          <div key={channel.id} className="bg-white p-6 rounded-lg shadow">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-3">
                <span className="text-2xl">{getChannelIcon(channel.type)}</span>
                <div>
                  <h3 className="text-lg font-medium text-gray-900">{channel.name}</h3>
                  <p className="text-sm text-gray-500 capitalize">{channel.type}</p>
                </div>
              </div>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(channel.status)}`}>
                {channel.status}
              </span>
            </div>

            {channel.config && (
              <div className="mb-4">
                <h4 className="text-sm font-medium text-gray-700 mb-2">Configuration</h4>
                <div className="space-y-1">
                  {Object.entries(channel.config).slice(0, 3).map(([key, value]) => (
                    <div key={key} className="flex justify-between text-sm">
                      <span className="text-gray-500">{key}:</span>
                      <span className="text-gray-900 truncate ml-2">
                        {typeof value === 'string' && value.length > 20 
                          ? `${value.substring(0, 20)}...` 
                          : String(value)
                        }
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <button
              onClick={() => onTestChannel(channel.id, { message: 'Test message' })}
              className="w-full px-4 py-2 border border-gray-300 text-gray-700 rounded-md text-sm hover:bg-gray-50"
              disabled={channel.status !== 'active'}
            >
              Test Channel
            </button>
          </div>
        ))}
      </div>

      {channels.length === 0 && (
        <div className="text-center py-12">
          <div className="text-gray-400 text-4xl mb-4">📡</div>
          <p className="text-gray-500">No communication channels configured.</p>
        </div>
      )}
    </div>
  );
}

// Settings Tab Component
interface SettingsTabProps {
  settings: any;
  onUpdateSettings: (settings: any) => void;
}

function SettingsTab({ settings, onUpdateSettings }: SettingsTabProps) {
  return (
    <div className="settings-tab">
      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-lg font-medium text-gray-900 mb-6">Notification Settings</h2>
        
        <div className="space-y-6">
          <div>
            <h3 className="text-base font-medium text-gray-900 mb-4">Channel Preferences</h3>
            <div className="space-y-3">
              {Object.entries(settings.channels || {}).map(([channel, enabled]) => (
                <div key={channel} className="flex items-center justify-between">
                  <span className="text-sm text-gray-700 capitalize">{channel}</span>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      className="sr-only peer"
                      checked={enabled as boolean}
                      onChange={(e) => onUpdateSettings({
                        ...settings,
                        channels: { ...settings.channels, [channel]: e.target.checked }
                      })}
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                  </label>
                </div>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-base font-medium text-gray-900 mb-4">Priority Filters</h3>
            <div className="space-y-3">
              {Object.entries(settings.priorities || {}).map(([priority, enabled]) => (
                <div key={priority} className="flex items-center justify-between">
                  <span className="text-sm text-gray-700 capitalize">{priority}</span>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      className="sr-only peer"
                      checked={enabled as boolean}
                      onChange={(e) => onUpdateSettings({
                        ...settings,
                        priorities: { ...settings.priorities, [priority]: e.target.checked }
                      })}
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                  </label>
                </div>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-base font-medium text-gray-900 mb-4">General Settings</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-sm text-gray-700">Sound Notifications</span>
                  <p className="text-xs text-gray-500">Play sound for high priority notifications</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    className="sr-only peer"
                    checked={settings.soundEnabled || false}
                    onChange={(e) => onUpdateSettings({
                      ...settings,
                      soundEnabled: e.target.checked
                    })}
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Auto Hide Delay (seconds)
                </label>
                <input
                  type="number"
                  min="1"
                  max="60"
                  value={(settings.autoHideDelay || 5000) / 1000}
                  onChange={(e) => onUpdateSettings({
                    ...settings,
                    autoHideDelay: parseInt(e.target.value) * 1000
                  })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Maximum Notifications
                </label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={settings.maxNotifications || 100}
                  onChange={(e) => onUpdateSettings({
                    ...settings,
                    maxNotifications: parseInt(e.target.value)
                  })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default CommunicationCenter;