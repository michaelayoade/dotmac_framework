'use client';

import { Card } from '@dotmac/styled-components/customer';
import {
  AlertCircle,
  ArrowRight,
  BookOpen,
  Calendar,
  CheckCircle,
  Clock,
  ExternalLink,
  HelpCircle,
  Mail,
  MapPin,
  MessageSquare,
  Phone,
  Users,
  Video,
  Zap,
} from 'lucide-react';
import { useState } from 'react';

interface SupportOption {
  id: string;
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  availability: string;
  responseTime: string;
  action: string;
  isAvailable: boolean;
  priority: 'high' | 'medium' | 'low';
}

const supportOptions: SupportOption[] = [
  {
    id: 'live-chat',
    title: 'Live Chat',
    description: 'Get instant help from our support team',
    icon: MessageSquare,
    availability: '24/7',
    responseTime: 'Usually < 2 minutes',
    action: 'Start Chat',
    isAvailable: true,
    priority: 'high',
  },
  {
    id: 'phone-support',
    title: 'Phone Support',
    description: 'Speak directly with a support specialist',
    icon: Phone,
    availability: '6 AM - 10 PM PST',
    responseTime: 'Average wait: 3 minutes',
    action: 'Call Now',
    isAvailable: true,
    priority: 'high',
  },
  {
    id: 'video-call',
    title: 'Video Support',
    description: 'Screen sharing for technical issues',
    icon: Video,
    availability: '8 AM - 8 PM PST',
    responseTime: 'Schedule in advance',
    action: 'Book Session',
    isAvailable: true,
    priority: 'medium',
  },
  {
    id: 'email-support',
    title: 'Email Support',
    description: 'Send detailed questions and attachments',
    icon: Mail,
    availability: '24/7',
    responseTime: 'Within 4 hours',
    action: 'Send Email',
    isAvailable: true,
    priority: 'medium',
  },
  {
    id: 'technician-visit',
    title: 'Technician Visit',
    description: 'On-site support for complex issues',
    icon: Users,
    availability: 'Mon-Fri 8 AM - 6 PM',
    responseTime: 'Next available slot',
    action: 'Schedule Visit',
    isAvailable: true,
    priority: 'low',
  },
  {
    id: 'community-forum',
    title: 'Community Forum',
    description: 'Get help from other customers',
    icon: HelpCircle,
    availability: '24/7',
    responseTime: 'Community driven',
    action: 'Visit Forum',
    isAvailable: true,
    priority: 'low',
  },
];

const quickActions = [
  {
    id: 'check-outage',
    title: 'Check Service Status',
    description: 'View current outages and maintenance',
    icon: AlertCircle,
    action: 'Check Status',
  },
  {
    id: 'restart-service',
    title: 'Restart My Service',
    description: 'Reset your internet connection remotely',
    icon: Zap,
    action: 'Restart Now',
  },
  {
    id: 'speed-test',
    title: 'Run Speed Test',
    description: 'Test your internet speed',
    icon: Zap,
    action: 'Start Test',
  },
  {
    id: 'billing-help',
    title: 'Billing Questions',
    description: 'Help with payments and charges',
    icon: HelpCircle,
    action: 'Get Help',
  },
];

export function SupportCenter() {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  const handleSupportAction = (optionId: string) => {
    switch (optionId) {
      case 'live-chat':
        // Trigger live chat widget
        // Debug: 'Opening live chat...'
        break;
      case 'phone-support':
        window.location.href = 'tel:+18001234567';
        break;
      case 'email-support':
        window.location.href = 'mailto:support@dotmac.com';
        break;
      default:
      // Debug: `Opening ${optionId}...`
    }
  };

  const handleQuickAction = (actionId: string) => {
    switch (actionId) {
      case 'check-outage':
        // Navigate to service status page
        // Debug: 'Checking service status...'
        break;
      case 'restart-service':
        // Trigger service restart
        // Debug: 'Restarting service...'
        break;
      case 'speed-test':
        // Open speed test tool
        // Debug: 'Running speed test...'
        break;
      case 'billing-help':
        // Open billing help
        // Debug: 'Opening billing help...'
        break;
      default:
      // Debug: `Executing ${actionId}...`
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'border-green-200 bg-green-50';
      case 'medium':
        return 'border-blue-200 bg-blue-50';
      case 'low':
        return 'border-gray-200 bg-gray-50';
      default:
        return 'border-gray-200 bg-white';
    }
  };

  return (
    <div className="space-y-8">
      {/* Quick Actions */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {quickActions.map(action => (
            <Card
              key={action.id}
              className="p-4 hover:shadow-lg transition-shadow cursor-pointer group"
              onClick={() => handleQuickAction(action.id)}
            >
              <div className="text-center">
                <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-blue-100 group-hover:bg-blue-200 transition-colors">
                  <action.icon className="h-6 w-6 text-blue-600" />
                </div>
                <h3 className="font-medium text-gray-900 mb-1">{action.title}</h3>
                <p className="text-sm text-gray-600 mb-3">{action.description}</p>
                <div className="flex items-center justify-center text-blue-600 text-sm font-medium group-hover:text-blue-700">
                  {action.action}
                  <ArrowRight className="ml-1 h-4 w-4" />
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>

      {/* Support Options */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Get Support</h2>
          <div className="flex items-center text-sm text-gray-600">
            <Clock className="mr-1 h-4 w-4" />
            Available 24/7
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {supportOptions.map(option => (
            <Card
              key={option.id}
              className={`p-6 hover:shadow-lg transition-all duration-200 cursor-pointer group ${getPriorityColor(option.priority)}`}
              onClick={() => handleSupportAction(option.id)}
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center">
                  <div className="mr-3 flex h-10 w-10 items-center justify-center rounded-lg bg-white shadow-sm">
                    <option.icon className="h-5 w-5 text-blue-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{option.title}</h3>
                    <p className="text-sm text-gray-600">{option.description}</p>
                  </div>
                </div>
                {option.isAvailable ? (
                  <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0" />
                ) : (
                  <Clock className="h-5 w-5 text-gray-400 flex-shrink-0" />
                )}
              </div>

              <div className="space-y-2 text-sm text-gray-600 mb-4">
                <div className="flex items-center justify-between">
                  <span>Availability:</span>
                  <span className="font-medium">{option.availability}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Response Time:</span>
                  <span className="font-medium">{option.responseTime}</span>
                </div>
              </div>

              <button
                className={`w-full rounded-lg px-4 py-2 text-sm font-medium transition-colors group-hover:shadow-md ${
                  option.isAvailable
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'bg-gray-200 text-gray-500 cursor-not-allowed'
                }`}
                disabled={!option.isAvailable}
              >
                {option.action}
              </button>
            </Card>
          ))}
        </div>
      </div>

      {/* Emergency Contact */}
      <Card className="p-6 border-red-200 bg-red-50">
        <div className="flex items-start">
          <AlertCircle className="h-6 w-6 text-red-600 mt-1 flex-shrink-0" />
          <div className="ml-4 flex-grow">
            <h3 className="text-lg font-semibold text-red-900 mb-2">Emergency Service Issues?</h3>
            <p className="text-red-700 mb-4">
              If you're experiencing a complete service outage or emergency, call our emergency
              hotline for immediate assistance.
            </p>
            <div className="flex flex-col sm:flex-row gap-3">
              <a
                href="tel:+18001234911"
                className="inline-flex items-center rounded-lg bg-red-600 px-4 py-2 text-white font-medium transition-colors hover:bg-red-700"
              >
                <Phone className="mr-2 h-4 w-4" />
                Emergency: 1-800-123-4911
              </a>
              <button
                onClick={() => handleSupportAction('live-chat')}
                className="inline-flex items-center rounded-lg border border-red-300 px-4 py-2 text-red-700 font-medium transition-colors hover:bg-red-100"
              >
                <MessageSquare className="mr-2 h-4 w-4" />
                Emergency Chat
              </button>
            </div>
          </div>
        </div>
      </Card>

      {/* Support Hours & Contact Info */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Support Hours</h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <MessageSquare className="mr-2 h-4 w-4 text-blue-600" />
                <span className="text-sm">Live Chat</span>
              </div>
              <span className="text-sm font-medium text-green-600">24/7</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <Phone className="mr-2 h-4 w-4 text-green-600" />
                <span className="text-sm">Phone Support</span>
              </div>
              <span className="text-sm font-medium">6 AM - 10 PM PST</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <Video className="mr-2 h-4 w-4 text-purple-600" />
                <span className="text-sm">Video Support</span>
              </div>
              <span className="text-sm font-medium">8 AM - 8 PM PST</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <Users className="mr-2 h-4 w-4 text-orange-600" />
                <span className="text-sm">Technician Visits</span>
              </div>
              <span className="text-sm font-medium">Mon-Fri 8 AM - 6 PM</span>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Contact Information</h3>
          <div className="space-y-3">
            <div className="flex items-center">
              <Phone className="mr-3 h-4 w-4 text-gray-600" />
              <div>
                <p className="text-sm font-medium">Customer Support</p>
                <p className="text-sm text-gray-600">1-800-123-4567</p>
              </div>
            </div>
            <div className="flex items-center">
              <Mail className="mr-3 h-4 w-4 text-gray-600" />
              <div>
                <p className="text-sm font-medium">Email Support</p>
                <p className="text-sm text-gray-600">support@dotmac.com</p>
              </div>
            </div>
            <div className="flex items-center">
              <MapPin className="mr-3 h-4 w-4 text-gray-600" />
              <div>
                <p className="text-sm font-medium">Service Area</p>
                <p className="text-sm text-gray-600">Available nationwide</p>
              </div>
            </div>
            <div className="flex items-center">
              <ExternalLink className="mr-3 h-4 w-4 text-gray-600" />
              <div>
                <p className="text-sm font-medium">System Status</p>
                <a href="#" className="text-sm text-blue-600 hover:text-blue-800">
                  status.dotmac.com
                </a>
              </div>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
