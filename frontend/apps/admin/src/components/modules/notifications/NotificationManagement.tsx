'use client';

import { useState } from 'react';
import { TemplateManager, BulkMessageSender } from '@dotmac/communication-system';
import { useAuth } from '@dotmac/auth';
import { Card, CardContent } from '../../ui/Card';
import { Bell, Mail, MessageSquare, Send, Settings } from 'lucide-react';

type TabType = 'templates' | 'bulk-send' | 'settings';

export function NotificationManagement() {
  const [activeTab, setActiveTab] = useState<TabType>('templates');
  const { user } = useAuth();

  if (!user) return null;

  const tabs = [
    { id: 'templates' as TabType, label: 'Templates', icon: Mail },
    { id: 'bulk-send' as TabType, label: 'Bulk Messaging', icon: Send },
    { id: 'settings' as TabType, label: 'Settings', icon: Settings },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Communication Management</h1>
        <p className="text-gray-600">
          Manage templates, send bulk messages, and configure communication channels
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {tabs.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center space-x-2 whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{label}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="mt-6">
        {activeTab === 'templates' && (
          <TemplateManager
            tenantId={user.tenantId}
            userId={user.id}
            showActions={true}
            onTemplateCreate={(template) => {
              console.log('Template created:', template);
            }}
            onTemplateUpdate={(template) => {
              console.log('Template updated:', template);
            }}
            onTemplateDelete={(templateId) => {
              console.log('Template deleted:', templateId);
            }}
          />
        )}

        {activeTab === 'bulk-send' && (
          <BulkMessageSender
            tenantId={user.tenantId}
            userId={user.id}
            maxRecipients={10000}
            onJobCreated={(job) => {
              console.log('Bulk message job created:', job);
            }}
            onJobComplete={(job) => {
              console.log('Bulk message job completed:', job);
            }}
          />
        )}

        {activeTab === 'settings' && (
          <Card>
            <CardContent className="p-6">
              <div className="text-center py-8">
                <Settings className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Communication Settings
                </h3>
                <p className="text-gray-500 mb-4">
                  Configure communication channels, rate limits, and provider settings
                </p>
                <div className="text-sm text-gray-400">
                  Channel configuration and provider settings will be available here
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
