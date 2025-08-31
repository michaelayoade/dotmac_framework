"use client";

import React, { useState } from 'react';
import { clsx } from 'clsx';
import { 
  Users,
  MessageSquare,
  FileText,
  Calendar,
  CheckCircle,
  Clock,
  AlertCircle,
  Plus,
  Search,
  Filter,
  Share2,
  Download,
  User,
  Building,
  DollarSign,
  Target,
  Handshake,
  Lightbulb,
  Zap,
  Globe,
  Mail,
  Phone,
  Video,
  Send
} from 'lucide-react';

interface CollaborationProject {
  id: string;
  title: string;
  description: string;
  type: 'joint-deal' | 'co-marketing' | 'training' | 'technical' | 'strategic';
  status: 'planning' | 'active' | 'review' | 'completed' | 'on-hold';
  priority: 'low' | 'medium' | 'high' | 'critical';
  participants: {
    id: string;
    name: string;
    company: string;
    role: string;
    avatar?: string;
  }[];
  startDate: string;
  endDate?: string;
  progress: number;
  value?: number;
  lastActivity: string;
  unreadMessages: number;
}

interface CollaborationMessage {
  id: string;
  projectId: string;
  sender: {
    name: string;
    company: string;
    avatar?: string;
  };
  content: string;
  timestamp: string;
  attachments?: string[];
}

const mockProjects: CollaborationProject[] = [
  {
    id: '1',
    title: 'Enterprise Fiber Deployment - Acme Corp',
    description: 'Joint proposal for 5-location fiber installation with backup connectivity',
    type: 'joint-deal',
    status: 'active',
    priority: 'high',
    participants: [
      { id: '1', name: 'John Smith', company: 'Your Company', role: 'Lead Sales' },
      { id: '2', name: 'Sarah Wilson', company: 'DotMac ISP', role: 'Technical Lead' },
      { id: '3', name: 'Mike Johnson', company: 'Fiber Solutions Inc', role: 'Installation Partner' }
    ],
    startDate: '2025-08-20',
    endDate: '2025-09-15',
    progress: 65,
    value: 250000,
    lastActivity: '2025-08-29',
    unreadMessages: 3
  },
  {
    id: '2',
    title: 'Q4 Small Business Marketing Campaign',
    description: 'Co-branded marketing initiative targeting local small businesses',
    type: 'co-marketing',
    status: 'planning',
    priority: 'medium',
    participants: [
      { id: '4', name: 'Lisa Chen', company: 'Your Company', role: 'Marketing Lead' },
      { id: '5', name: 'David Brown', company: 'DotMac ISP', role: 'Marketing Manager' }
    ],
    startDate: '2025-09-01',
    endDate: '2025-12-31',
    progress: 25,
    lastActivity: '2025-08-28',
    unreadMessages: 1
  },
  {
    id: '3',
    title: 'Technical Training: Advanced Networking',
    description: 'Joint training program for advanced networking technologies',
    type: 'training',
    status: 'review',
    priority: 'medium',
    participants: [
      { id: '6', name: 'Alex Rodriguez', company: 'Your Company', role: 'Technical Manager' },
      { id: '7', name: 'Jennifer Kim', company: 'DotMac ISP', role: 'Training Coordinator' }
    ],
    startDate: '2025-08-15',
    endDate: '2025-08-30',
    progress: 90,
    lastActivity: '2025-08-27',
    unreadMessages: 0
  }
];

const mockMessages: CollaborationMessage[] = [
  {
    id: '1',
    projectId: '1',
    sender: { name: 'Sarah Wilson', company: 'DotMac ISP' },
    content: 'Updated the technical specifications for the Acme Corp deployment. Please review the fiber routing plan.',
    timestamp: '2025-08-29T14:30:00Z',
    attachments: ['fiber-routing-plan.pdf']
  },
  {
    id: '2',
    projectId: '1',
    sender: { name: 'Mike Johnson', company: 'Fiber Solutions Inc' },
    content: 'Installation timeline looks good. We can start Phase 1 on September 5th as planned.',
    timestamp: '2025-08-29T13:15:00Z'
  },
  {
    id: '3',
    projectId: '2',
    sender: { name: 'David Brown', company: 'DotMac ISP' },
    content: 'Marketing budget approved! Ready to finalize the campaign creative assets.',
    timestamp: '2025-08-28T16:45:00Z'
  }
];

export function PartnerCollaborationHub() {
  const [projects] = useState<CollaborationProject[]>(mockProjects);
  const [messages] = useState<CollaborationMessage[]>(mockMessages);
  const [selectedProject, setSelectedProject] = useState<CollaborationProject | null>(null);
  const [activeTab, setActiveTab] = useState<'projects' | 'messages' | 'opportunities'>('projects');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [newMessage, setNewMessage] = useState('');

  const getStatusColor = (status: CollaborationProject['status']) => {
    const colors = {
      'planning': 'bg-yellow-100 text-yellow-800',
      'active': 'bg-green-100 text-green-800',
      'review': 'bg-blue-100 text-blue-800',
      'completed': 'bg-gray-100 text-gray-800',
      'on-hold': 'bg-red-100 text-red-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const getPriorityColor = (priority: CollaborationProject['priority']) => {
    const colors = {
      'low': 'text-gray-500',
      'medium': 'text-yellow-500',
      'high': 'text-orange-500',
      'critical': 'text-red-500'
    };
    return colors[priority] || 'text-gray-500';
  };

  const getTypeIcon = (type: CollaborationProject['type']) => {
    const icons = {
      'joint-deal': <Handshake className="w-4 h-4" />,
      'co-marketing': <Target className="w-4 h-4" />,
      'training': <Users className="w-4 h-4" />,
      'technical': <Zap className="w-4 h-4" />,
      'strategic': <Lightbulb className="w-4 h-4" />
    };
    return icons[type] || <FileText className="w-4 h-4" />;
  };

  const filteredProjects = projects.filter(project => 
    filterStatus === 'all' || project.status === filterStatus
  );

  const projectMessages = selectedProject 
    ? messages.filter(msg => msg.projectId === selectedProject.id)
    : [];

  return (
    <div className="space-y-6">
      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg p-6 shadow-sm border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Active Projects</p>
              <p className="text-2xl font-bold text-gray-900">
                {projects.filter(p => p.status === 'active').length}
              </p>
            </div>
            <Users className="w-8 h-8 text-blue-500" />
          </div>
        </div>
        
        <div className="bg-white rounded-lg p-6 shadow-sm border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Pipeline Value</p>
              <p className="text-2xl font-bold text-gray-900">
                ${projects.reduce((sum, p) => sum + (p.value || 0), 0).toLocaleString()}
              </p>
            </div>
            <DollarSign className="w-8 h-8 text-green-500" />
          </div>
        </div>
        
        <div className="bg-white rounded-lg p-6 shadow-sm border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Avg Progress</p>
              <p className="text-2xl font-bold text-gray-900">
                {Math.round(projects.reduce((sum, p) => sum + p.progress, 0) / projects.length)}%
              </p>
            </div>
            <Target className="w-8 h-8 text-purple-500" />
          </div>
        </div>
        
        <div className="bg-white rounded-lg p-6 shadow-sm border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Unread Messages</p>
              <p className="text-2xl font-bold text-gray-900">
                {projects.reduce((sum, p) => sum + p.unreadMessages, 0)}
              </p>
            </div>
            <MessageSquare className="w-8 h-8 text-orange-500" />
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="bg-white rounded-lg shadow-sm border">
        <div className="border-b border-gray-200">
          <nav className="flex space-x-8 px-6">
            {[
              { key: 'projects', label: 'Projects', icon: FileText },
              { key: 'messages', label: 'Messages', icon: MessageSquare },
              { key: 'opportunities', label: 'Opportunities', icon: Lightbulb }
            ].map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key as any)}
                className={clsx(
                  'flex items-center space-x-2 py-4 border-b-2 font-medium text-sm transition-colors',
                  activeTab === tab.key 
                    ? 'border-blue-500 text-blue-600' 
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                )}
              >
                <tab.icon className="w-4 h-4" />
                <span>{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {activeTab === 'projects' && (
            <div className="space-y-4">
              {/* Filters */}
              <div className="flex items-center space-x-4">
                <select
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="all">All Status</option>
                  <option value="planning">Planning</option>
                  <option value="active">Active</option>
                  <option value="review">Review</option>
                  <option value="completed">Completed</option>
                  <option value="on-hold">On Hold</option>
                </select>

                <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors flex items-center space-x-2">
                  <Plus className="w-4 h-4" />
                  <span>New Project</span>
                </button>
              </div>

              {/* Projects List */}
              <div className="space-y-4">
                {filteredProjects.map((project) => (
                  <div
                    key={project.id}
                    className="border rounded-lg p-6 hover:shadow-md transition-shadow cursor-pointer"
                    onClick={() => setSelectedProject(project)}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start space-x-4 flex-1">
                        <div className="p-2 bg-gray-100 rounded-lg">
                          {getTypeIcon(project.type)}
                        </div>
                        
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-3 mb-2">
                            <h3 className="font-medium text-gray-900">{project.title}</h3>
                            <span className={clsx(
                              'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium',
                              getStatusColor(project.status)
                            )}>
                              {project.status.replace('-', ' ')}
                            </span>
                            <div className={clsx('flex items-center', getPriorityColor(project.priority))}>
                              <AlertCircle className="w-3 h-3" />
                            </div>
                          </div>
                          
                          <p className="text-sm text-gray-600 mb-3">{project.description}</p>
                          
                          <div className="flex items-center space-x-6 text-sm text-gray-500">
                            <div className="flex items-center space-x-1">
                              <Users className="w-3 h-3" />
                              <span>{project.participants.length} participants</span>
                            </div>
                            <div className="flex items-center space-x-1">
                              <Calendar className="w-3 h-3" />
                              <span>Due {new Date(project.endDate || project.startDate).toLocaleDateString()}</span>
                            </div>
                            {project.value && (
                              <div className="flex items-center space-x-1">
                                <DollarSign className="w-3 h-3" />
                                <span>${project.value.toLocaleString()}</span>
                              </div>
                            )}
                            {project.unreadMessages > 0 && (
                              <div className="flex items-center space-x-1 text-blue-600">
                                <MessageSquare className="w-3 h-3" />
                                <span>{project.unreadMessages} new</span>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Progress */}
                      <div className="text-right">
                        <div className="text-sm font-medium text-gray-900 mb-1">{project.progress}%</div>
                        <div className="w-24 bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${project.progress}%` }}
                          />
                        </div>
                      </div>
                    </div>

                    {/* Participants */}
                    <div className="flex items-center space-x-3 mt-4 pt-4 border-t">
                      <span className="text-sm text-gray-500">Team:</span>
                      <div className="flex -space-x-2">
                        {project.participants.slice(0, 4).map((participant) => (
                          <div
                            key={participant.id}
                            className="w-8 h-8 bg-gray-200 rounded-full border-2 border-white flex items-center justify-center"
                            title={`${participant.name} (${participant.company})`}
                          >
                            <span className="text-xs font-medium text-gray-600">
                              {participant.name.split(' ').map(n => n[0]).join('')}
                            </span>
                          </div>
                        ))}
                        {project.participants.length > 4 && (
                          <div className="w-8 h-8 bg-gray-300 rounded-full border-2 border-white flex items-center justify-center">
                            <span className="text-xs text-gray-600">+{project.participants.length - 4}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'messages' && (
            <div className="space-y-4">
              {/* Messages Header */}
              <div className="flex items-center justify-between">
                <h3 className="font-medium text-gray-900">Recent Messages</h3>
                <button className="text-blue-600 hover:text-blue-700 text-sm font-medium">
                  Mark all as read
                </button>
              </div>

              {/* Messages List */}
              <div className="space-y-3">
                {messages.map((message) => {
                  const project = projects.find(p => p.id === message.projectId);
                  return (
                    <div key={message.id} className="bg-gray-50 rounded-lg p-4">
                      <div className="flex items-start space-x-3">
                        <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                          <span className="text-sm font-medium text-blue-600">
                            {message.sender.name.split(' ').map(n => n[0]).join('')}
                          </span>
                        </div>
                        
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2 mb-1">
                            <span className="font-medium text-gray-900">{message.sender.name}</span>
                            <span className="text-sm text-gray-500">•</span>
                            <span className="text-sm text-gray-500">{message.sender.company}</span>
                            <span className="text-sm text-gray-500">•</span>
                            <span className="text-sm text-gray-500">
                              {new Date(message.timestamp).toLocaleDateString()}
                            </span>
                          </div>
                          
                          {project && (
                            <div className="text-sm text-blue-600 mb-2">
                              Re: {project.title}
                            </div>
                          )}
                          
                          <p className="text-sm text-gray-700">{message.content}</p>
                          
                          {message.attachments && message.attachments.length > 0 && (
                            <div className="flex items-center space-x-2 mt-2">
                              {message.attachments.map((attachment) => (
                                <button
                                  key={attachment}
                                  className="flex items-center space-x-1 text-xs text-blue-600 hover:text-blue-700"
                                >
                                  <FileText className="w-3 h-3" />
                                  <span>{attachment}</span>
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {activeTab === 'opportunities' && (
            <div className="space-y-6">
              {/* New Opportunities */}
              <div>
                <h3 className="font-medium text-gray-900 mb-4">New Collaboration Opportunities</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="border rounded-lg p-4">
                    <div className="flex items-start space-x-3">
                      <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                        <Globe className="w-5 h-5 text-green-600" />
                      </div>
                      <div className="flex-1">
                        <h4 className="font-medium text-gray-900">Regional Expansion Partnership</h4>
                        <p className="text-sm text-gray-600 mt-1">
                          Joint expansion into 3 new metropolitan areas
                        </p>
                        <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                          <span>Potential Value: $2M</span>
                          <span>Duration: 18 months</span>
                        </div>
                        <button className="mt-3 bg-green-600 text-white px-3 py-1.5 rounded text-sm hover:bg-green-700 transition-colors">
                          Express Interest
                        </button>
                      </div>
                    </div>
                  </div>

                  <div className="border rounded-lg p-4">
                    <div className="flex items-start space-x-3">
                      <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                        <Target className="w-5 h-5 text-purple-600" />
                      </div>
                      <div className="flex-1">
                        <h4 className="font-medium text-gray-900">5G Marketing Alliance</h4>
                        <p className="text-sm text-gray-600 mt-1">
                          Collaborative 5G service promotion campaign
                        </p>
                        <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                          <span>Marketing Budget: $50K</span>
                          <span>Launch: Q1 2026</span>
                        </div>
                        <button className="mt-3 border border-purple-600 text-purple-600 px-3 py-1.5 rounded text-sm hover:bg-purple-50 transition-colors">
                          Learn More
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Partner Network */}
              <div>
                <h3 className="font-medium text-gray-900 mb-4">Partner Network</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {[
                    { name: 'TechSolutions Inc', type: 'Technology Partner', projects: 5, status: 'Active' },
                    { name: 'Fiber Networks LLC', type: 'Infrastructure Partner', projects: 3, status: 'Active' },
                    { name: 'Marketing Pro Agency', type: 'Marketing Partner', projects: 8, status: 'Active' }
                  ].map((partner, index) => (
                    <div key={index} className="border rounded-lg p-4">
                      <div className="flex items-center space-x-3 mb-3">
                        <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                          <Building className="w-5 h-5 text-blue-600" />
                        </div>
                        <div>
                          <h4 className="font-medium text-gray-900">{partner.name}</h4>
                          <p className="text-sm text-gray-500">{partner.type}</p>
                        </div>
                      </div>
                      
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-gray-500">Active Projects:</span>
                          <span className="font-medium">{partner.projects}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">Status:</span>
                          <span className="font-medium text-green-600">{partner.status}</span>
                        </div>
                      </div>
                      
                      <div className="flex space-x-2 mt-4">
                        <button className="flex-1 bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700 transition-colors">
                          Contact
                        </button>
                        <button className="border border-gray-300 text-gray-700 px-3 py-1.5 rounded text-sm hover:bg-gray-50 transition-colors">
                          Profile
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Project Detail Modal */}
      {selectedProject && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden flex">
            {/* Project Info */}
            <div className="flex-1 p-6 overflow-y-auto">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900">{selectedProject.title}</h2>
                <button
                  onClick={() => setSelectedProject(null)}
                  className="p-2 hover:bg-gray-100 rounded-full transition-colors"
                >
                  ×
                </button>
              </div>

              <div className="space-y-6">
                {/* Status and Progress */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-sm text-gray-500">Status:</span>
                    <div className={clsx(
                      'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium mt-1',
                      getStatusColor(selectedProject.status)
                    )}>
                      {selectedProject.status.replace('-', ' ')}
                    </div>
                  </div>
                  <div>
                    <span className="text-sm text-gray-500">Progress:</span>
                    <div className="mt-1">
                      <div className="flex items-center space-x-2">
                        <div className="flex-1 bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full"
                            style={{ width: `${selectedProject.progress}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium">{selectedProject.progress}%</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Participants */}
                <div>
                  <h3 className="font-medium text-gray-900 mb-3">Team Members</h3>
                  <div className="space-y-2">
                    {selectedProject.participants.map((participant) => (
                      <div key={participant.id} className="flex items-center space-x-3">
                        <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
                          <span className="text-xs font-medium text-gray-600">
                            {participant.name.split(' ').map(n => n[0]).join('')}
                          </span>
                        </div>
                        <div>
                          <div className="font-medium text-gray-900">{participant.name}</div>
                          <div className="text-sm text-gray-500">{participant.role} • {participant.company}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Messages Sidebar */}
            <div className="w-80 border-l bg-gray-50 flex flex-col">
              <div className="p-4 border-b bg-white">
                <h3 className="font-medium text-gray-900">Project Messages</h3>
              </div>
              
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {projectMessages.map((message) => (
                  <div key={message.id} className="bg-white rounded-lg p-3">
                    <div className="flex items-center space-x-2 mb-2">
                      <span className="font-medium text-gray-900 text-sm">{message.sender.name}</span>
                      <span className="text-xs text-gray-500">
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <p className="text-sm text-gray-700">{message.content}</p>
                  </div>
                ))}
              </div>
              
              {/* Message Input */}
              <div className="p-4 border-t bg-white">
                <div className="flex space-x-2">
                  <input
                    type="text"
                    placeholder="Type a message..."
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
                  />
                  <button className="bg-blue-600 text-white p-2 rounded-lg hover:bg-blue-700 transition-colors">
                    <Send className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}