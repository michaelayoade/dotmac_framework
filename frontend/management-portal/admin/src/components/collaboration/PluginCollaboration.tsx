/**
 * Plugin Development Collaboration - Management Admin Integration
 * Demonstrates collaborative plugin development using @dotmac/collaboration
 */

'use client';

import React, { useState } from 'react';
import { Card } from '@dotmac/primitives';
import {
  CollaborativeEditor,
  PresenceIndicators,
  useCollaboration,
  usePresence,
  type DocumentConfig,
  type CollaborationOptions
} from '@dotmac/collaboration';
import {
  Code,
  Users,
  GitBranch,
  Play,
  Save,
  Eye,
  Settings
} from 'lucide-react';

interface PluginCollaborationProps {
  pluginId: string;
  currentUser: {
    id: string;
    name: string;
    role: string;
    avatar?: string;
  };
}

export const PluginCollaboration: React.FC<PluginCollaborationProps> = ({
  pluginId,
  currentUser
}) => {
  const [activeFile, setActiveFile] = useState<string>('main.py');
  const [showPresence, setShowPresence] = useState(true);

  // Document configuration for plugin file
  const documentConfig: DocumentConfig = {
    document_id: `plugin-${pluginId}-${activeFile}`,
    tenant_id: 'system', // System-level for plugin development
    document_type: 'code',
    permissions: {
      read: true,
      write: currentUser.role === 'admin' || currentUser.role === 'developer',
      comment: true,
      suggest: true
    }
  };

  // Collaboration options optimized for code
  const collaborationOptions: CollaborationOptions = {
    enable_operational_transform: true,
    enable_presence: true,
    enable_comments: true,
    enable_suggestions: true,
    auto_save_interval: 3000, // Faster for code
    conflict_resolution_strategy: 'operational_transform',
    syntax_highlighting: 'python'
  };

  // Collaboration hooks
  const {
    document,
    isConnected,
    participants,
    saveDocument,
    loading: docLoading,
    error: docError
  } = useCollaboration(documentConfig, collaborationOptions);

  const {
    activeUsers,
    userCursors,
    userSelections,
    loading: presenceLoading
  } = usePresence({
    document_id: documentConfig.document_id,
    user: currentUser,
    tenant_id: 'system'
  });

  // Plugin files
  const pluginFiles = [
    { name: 'main.py', type: 'python', icon: '🐍' },
    { name: 'config.yaml', type: 'yaml', icon: '⚙️' },
    { name: 'requirements.txt', type: 'text', icon: '📄' },
    { name: 'README.md', type: 'markdown', icon: '📝' }
  ];

  const handleFileChange = (fileName: string) => {
    setActiveFile(fileName);
  };

  const handleSave = async () => {
    try {
      await saveDocument();
    } catch (error) {
      console.error('Failed to save plugin file:', error);
    }
  };

  const handleTestRun = () => {
    // Simulate test run
    console.log('Running plugin tests...');
  };

  return (
    <div className="plugin-collaboration space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h2 className="text-xl font-bold text-gray-900">Plugin Development</h2>
          <div className="text-sm text-gray-600">
            Plugin ID: {pluginId}
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <div className={`h-2 w-2 rounded-full ${
            isConnected ? 'bg-green-500' : 'bg-red-500'
          }`} />
          <span className="text-sm text-gray-600">
            {activeUsers.length} developer{activeUsers.length !== 1 ? 's' : ''} online
          </span>
        </div>
      </div>

      {/* Developer stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-600">Active Developers</p>
              <p className="text-lg font-bold text-gray-900">{activeUsers.length}</p>
            </div>
            <Users className="h-6 w-6 text-blue-600" />
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-600">Lines of Code</p>
              <p className="text-lg font-bold text-gray-900">{document?.word_count || 0}</p>
            </div>
            <Code className="h-6 w-6 text-green-600" />
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-600">Files</p>
              <p className="text-lg font-bold text-gray-900">{pluginFiles.length}</p>
            </div>
            <GitBranch className="h-6 w-6 text-purple-600" />
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-600">Status</p>
              <p className="text-sm font-medium text-green-600">Development</p>
            </div>
            <Settings className="h-6 w-6 text-gray-600" />
          </div>
        </Card>
      </div>

      {/* Main development area */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* File explorer */}
        <Card className="p-4">
          <h3 className="text-sm font-semibold mb-3">Plugin Files</h3>
          <div className="space-y-1">
            {pluginFiles.map((file) => (
              <button
                key={file.name}
                onClick={() => handleFileChange(file.name)}
                className={`w-full text-left px-3 py-2 rounded-md text-sm flex items-center space-x-2 ${
                  activeFile === file.name
                    ? 'bg-blue-50 text-blue-600 border border-blue-200'
                    : 'hover:bg-gray-50 text-gray-700'
                }`}
              >
                <span>{file.icon}</span>
                <span>{file.name}</span>
              </button>
            ))}
          </div>

          <div className="mt-6 pt-4 border-t border-gray-200">
            <h4 className="text-sm font-semibold mb-2">Actions</h4>
            <div className="space-y-2">
              <button
                onClick={handleSave}
                disabled={docLoading}
                className="w-full px-3 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 text-sm flex items-center justify-center space-x-2"
              >
                <Save className="h-4 w-4" />
                <span>{docLoading ? 'Saving...' : 'Save'}</span>
              </button>

              <button
                onClick={handleTestRun}
                className="w-full px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm flex items-center justify-center space-x-2"
              >
                <Play className="h-4 w-4" />
                <span>Test Run</span>
              </button>
            </div>
          </div>
        </Card>

        {/* Code editor */}
        <Card className="lg:col-span-3 p-0">
          {showPresence && (
            <div className="p-3 border-b border-gray-200 bg-gray-50">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Code className="h-4 w-4 text-gray-600" />
                  <span className="text-sm font-medium text-gray-700">{activeFile}</span>
                </div>
                <div className="flex items-center space-x-2">
                  <PresenceIndicators
                    users={activeUsers}
                    cursors={userCursors}
                    selections={userSelections}
                    compact={true}
                  />
                  <button
                    onClick={() => setShowPresence(!showPresence)}
                    className="text-gray-500 hover:text-gray-700"
                  >
                    <Eye className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          )}

          <div className="p-4">
            {docLoading ? (
              <div className="h-96 flex items-center justify-center">
                <div className="text-gray-500">Loading {activeFile}...</div>
              </div>
            ) : docError ? (
              <div className="h-96 flex items-center justify-center">
                <div className="text-red-500">Error loading file: {docError}</div>
              </div>
            ) : (
              <div className="h-96">
                <CollaborativeEditor
                  document={document}
                  user={currentUser}
                  options={collaborationOptions}
                  show_toolbar={false}
                  show_line_numbers={true}
                  show_minimap={true}
                  theme="vs-code"
                  className="w-full h-full font-mono"
                />
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Development info */}
      {document && (
        <Card className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-gray-600">Last saved:</span>
              <span className="ml-2 font-medium">
                {document.last_modified ? new Date(document.last_modified).toLocaleTimeString() : 'Never'}
              </span>
            </div>
            <div>
              <span className="text-gray-600">Participants:</span>
              <span className="ml-2 font-medium">{participants.length}</span>
            </div>
            <div>
              <span className="text-gray-600">Auto-save:</span>
              <span className="ml-2 font-medium text-green-600">Every 3 seconds</span>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};
