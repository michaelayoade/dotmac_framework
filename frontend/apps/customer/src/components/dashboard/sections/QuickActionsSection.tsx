/**
 * Quick Actions Section - Decomposed from CustomerDashboard
 */
import { 
  CreditCard, 
  MessageSquare, 
  Settings, 
  Download, 
  Phone, 
  BookOpen,
  RefreshCw,
  Wifi
} from 'lucide-react';
import React from 'react';

interface QuickAction {
  id: string;
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  onClick: () => void;
  variant?: 'primary' | 'secondary' | 'outline';
  disabled?: boolean;
}

interface QuickActionsSectionProps {
  onPayBill?: () => void;
  onContactSupport?: () => void;
  onManageServices?: () => void;
  onRunSpeedTest?: () => void;
  onRestartEquipment?: () => void;
  onViewBilling?: () => void;
  onAccessSupport?: () => void;
  onScheduleService?: () => void;
  isSpeedTestRunning?: boolean;
  isEquipmentRestarting?: boolean;
  className?: string;
}

export function QuickActionsSection({
  onPayBill,
  onContactSupport,
  onManageServices,
  onRunSpeedTest,
  onRestartEquipment,
  onViewBilling,
  onAccessSupport,
  onScheduleService,
  isSpeedTestRunning = false,
  isEquipmentRestarting = false,
  className = ''
}: QuickActionsSectionProps) {
  const quickActions: QuickAction[] = [
    {
      id: 'pay-bill',
      title: 'Pay Bill',
      description: 'Make a payment or set up autopay',
      icon: CreditCard,
      onClick: onPayBill || (() => {}),
      variant: 'primary',
      disabled: !onPayBill
    },
    {
      id: 'speed-test',
      title: 'Speed Test',
      description: 'Test your internet connection speed',
      icon: Download,
      onClick: onRunSpeedTest || (() => {}),
      variant: 'secondary',
      disabled: !onRunSpeedTest || isSpeedTestRunning
    },
    {
      id: 'restart-equipment',
      title: 'Restart Equipment',
      description: 'Remotely restart your modem/router',
      icon: RefreshCw,
      onClick: onRestartEquipment || (() => {}),
      variant: 'outline',
      disabled: !onRestartEquipment || isEquipmentRestarting
    },
    {
      id: 'contact-support',
      title: 'Contact Support',
      description: 'Get help from our support team',
      icon: MessageSquare,
      onClick: onContactSupport || (() => {}),
      variant: 'outline',
      disabled: !onContactSupport
    }
  ];

  const secondaryActions = [
    {
      title: 'Manage Services',
      icon: Settings,
      onClick: onManageServices,
      disabled: !onManageServices
    },
    {
      title: 'View Billing',
      icon: CreditCard,
      onClick: onViewBilling,
      disabled: !onViewBilling
    },
    {
      title: 'Support Center',
      icon: BookOpen,
      onClick: onAccessSupport,
      disabled: !onAccessSupport
    },
    {
      title: 'Schedule Service',
      icon: Phone,
      onClick: onScheduleService,
      disabled: !onScheduleService
    }
  ];

  const getVariantStyles = (variant: QuickAction['variant']) => {
    switch (variant) {
      case 'primary':
        return 'bg-blue-600 text-white hover:bg-blue-700 border-blue-600';
      case 'secondary':
        return 'bg-blue-50 text-blue-700 hover:bg-blue-100 border-blue-200';
      case 'outline':
        return 'bg-white text-gray-700 hover:bg-gray-50 border-gray-300';
      default:
        return 'bg-gray-50 text-gray-700 hover:bg-gray-100 border-gray-200';
    }
  };

  return (
    <div className={`bg-white border border-gray-200 rounded-lg ${className}`}>
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="font-semibold text-gray-900">Quick Actions</h3>
        <p className="text-sm text-gray-600 mt-1">Common tasks and shortcuts</p>
      </div>

      <div className="p-6">
        {/* Primary Actions */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          {quickActions.map((action) => {
            const Icon = action.icon;
            const isLoading = (action.id === 'speed-test' && isSpeedTestRunning) ||
                             (action.id === 'restart-equipment' && isEquipmentRestarting);
            
            return (
              <button
                key={action.id}
                onClick={action.onClick}
                disabled={action.disabled || isLoading}
                className={`p-4 rounded-lg border-2 text-left transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${getVariantStyles(action.variant)}`}
              >
                <div className="flex items-start">
                  <div className="flex-shrink-0">
                    {isLoading ? (
                      <div className="animate-spin h-6 w-6 border-2 border-current border-t-transparent rounded-full" />
                    ) : (
                      <Icon className="h-6 w-6" />
                    )}
                  </div>
                  <div className="ml-3">
                    <h4 className="font-medium">
                      {isLoading ? (
                        action.id === 'speed-test' ? 'Running Speed Test...' :
                        action.id === 'restart-equipment' ? 'Restarting Equipment...' :
                        action.title
                      ) : action.title}
                    </h4>
                    <p className="text-sm opacity-90 mt-1">
                      {action.description}
                    </p>
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        {/* Secondary Actions */}
        <div className="border-t border-gray-200 pt-6">
          <h4 className="font-medium text-gray-900 mb-4">More Actions</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {secondaryActions.map((action, index) => {
              if (!action.onClick) return null;
              
              const Icon = action.icon;
              
              return (
                <button
                  key={index}
                  onClick={action.onClick}
                  disabled={action.disabled}
                  className="flex flex-col items-center p-3 rounded-lg text-gray-600 hover:text-blue-600 hover:bg-blue-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Icon className="h-6 w-6 mb-2" />
                  <span className="text-sm font-medium text-center">
                    {action.title}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}