/**
 * Tab management system for ISP platform
 */

import React, { useState, useCallback, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';

export interface TabItem {
  id: string;
  label: string;
  href?: string;
  icon?: React.ComponentType<{ className?: string }>;
  badge?: string | number;
  closable?: boolean;
  disabled?: boolean;
  content?: React.ReactNode;
  requiredPermissions?: string[];
  requiredRoles?: string[];
}

interface TabManagerProps {
  tabs: TabItem[];
  activeTabId?: string;
  orientation?: 'horizontal' | 'vertical';
  variant?: 'default' | 'pills' | 'underline' | 'enclosed';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  onChange?: (tabId: string) => void;
  onClose?: (tabId: string) => void;
  allowReorder?: boolean;
  maxTabs?: number;
}

interface TabContextType {
  activeTab: string;
  tabs: TabItem[];
  addTab: (tab: TabItem) => void;
  removeTab: (tabId: string) => void;
  setActiveTab: (tabId: string) => void;
  moveTab: (fromIndex: number, toIndex: number) => void;
}

const TabContext = React.createContext<TabContextType | null>(null);

export function TabManager({
  tabs: initialTabs,
  activeTabId,
  orientation = 'horizontal',
  variant = 'default',
  size = 'md',
  className = '',
  onChange,
  onClose,
  allowReorder = false,
  maxTabs = 20,
}: TabManagerProps) {
  const [tabs, setTabs] = useState<TabItem[]>(initialTabs);
  const [activeTab, setActiveTabState] = useState(activeTabId || tabs[0]?.id || '');
  const [draggedTab, setDraggedTab] = useState<string | null>(null);

  const router = useRouter();
  const pathname = usePathname();

  // Update active tab when activeTabId prop changes
  useEffect(() => {
    if (activeTabId && activeTabId !== activeTab) {
      setActiveTabState(activeTabId);
    }
  }, [activeTabId, activeTab]);

  // Sync with URL if tabs have hrefs
  useEffect(() => {
    const matchingTab = tabs.find(tab => tab.href === pathname);
    if (matchingTab && matchingTab.id !== activeTab) {
      setActiveTabState(matchingTab.id);
    }
  }, [pathname, tabs, activeTab]);

  const setActiveTab = useCallback((tabId: string) => {
    const tab = tabs.find(t => t.id === tabId);
    if (!tab || tab.disabled) return;

    setActiveTabState(tabId);
    
    if (tab.href) {
      router.push(tab.href);
    }
    
    onChange?.(tabId);
  }, [tabs, router, onChange]);

  const addTab = useCallback((tab: TabItem) => {
    setTabs(prev => {
      if (prev.length >= maxTabs) {
        // Remove oldest tab if at max
        const newTabs = prev.slice(1);
        return [...newTabs, tab];
      }
      return [...prev, tab];
    });
  }, [maxTabs]);

  const removeTab = useCallback((tabId: string) => {
    const tabToRemove = tabs.find(t => t.id === tabId);
    if (!tabToRemove?.closable) return;

    setTabs(prev => {
      const newTabs = prev.filter(t => t.id !== tabId);
      
      // If removing active tab, switch to adjacent tab
      if (tabId === activeTab && newTabs.length > 0) {
        const removedIndex = prev.findIndex(t => t.id === tabId);
        const nextTab = newTabs[Math.min(removedIndex, newTabs.length - 1)];
        setActiveTabState(nextTab.id);
        
        if (nextTab.href) {
          router.push(nextTab.href);
        }
        
        onChange?.(nextTab.id);
      }
      
      return newTabs;
    });
    
    onClose?.(tabId);
  }, [tabs, activeTab, router, onChange, onClose]);

  const moveTab = useCallback((fromIndex: number, toIndex: number) => {
    setTabs(prev => {
      const newTabs = [...prev];
      const [movedTab] = newTabs.splice(fromIndex, 1);
      newTabs.splice(toIndex, 0, movedTab);
      return newTabs;
    });
  }, []);

  const handleDragStart = (e: React.DragEvent, tabId: string, index: number) => {
    if (!allowReorder) return;
    
    setDraggedTab(tabId);
    e.dataTransfer.setData('text/plain', index.toString());
  };

  const handleDragOver = (e: React.DragEvent) => {
    if (!allowReorder) return;
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent, dropIndex: number) => {
    if (!allowReorder) return;
    
    e.preventDefault();
    const dragIndex = parseInt(e.dataTransfer.getData('text/plain'));
    
    if (dragIndex !== dropIndex) {
      moveTab(dragIndex, dropIndex);
    }
    
    setDraggedTab(null);
  };

  const getTabStyles = (tab: TabItem, isActive: boolean) => {
    const baseStyles = 'relative inline-flex items-center justify-center transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2';
    
    const sizeStyles = {
      sm: 'px-3 py-1.5 text-sm',
      md: 'px-4 py-2 text-sm',
      lg: 'px-6 py-3 text-base',
    }[size];

    const variantStyles = {
      default: isActive 
        ? 'bg-white text-gray-900 border-gray-300 border-b-white' 
        : 'text-gray-500 hover:text-gray-700 border-transparent hover:border-gray-300',
      pills: isActive
        ? 'bg-blue-100 text-blue-700'
        : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100',
      underline: isActive
        ? 'text-blue-600 border-b-2 border-blue-600'
        : 'text-gray-500 hover:text-gray-700 border-b-2 border-transparent hover:border-gray-300',
      enclosed: isActive
        ? 'bg-white text-gray-900 border border-gray-300 border-b-white'
        : 'text-gray-500 hover:text-gray-700 border border-transparent',
    }[variant];

    const disabledStyles = tab.disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer';

    return `${baseStyles} ${sizeStyles} ${variantStyles} ${disabledStyles}`;
  };

  const contextValue: TabContextType = {
    activeTab,
    tabs,
    addTab,
    removeTab,
    setActiveTab,
    moveTab,
  };

  return (
    <TabContext.Provider value={contextValue}>
      <div className={`tab-manager ${className}`}>
        <div
          className={`tab-list ${
            orientation === 'vertical' ? 'flex-col' : 'flex-row'
          } ${
            variant === 'default' || variant === 'enclosed' 
              ? 'border-b border-gray-200' 
              : ''
          } flex`}
          role="tablist"
        >
          {tabs.map((tab, index) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={activeTab === tab.id}
              aria-controls={`tabpanel-${tab.id}`}
              className={getTabStyles(tab, activeTab === tab.id)}
              onClick={() => setActiveTab(tab.id)}
              disabled={tab.disabled}
              draggable={allowReorder}
              onDragStart={(e) => handleDragStart(e, tab.id, index)}
              onDragOver={handleDragOver}
              onDrop={(e) => handleDrop(e, index)}
            >
              <div className="flex items-center">
                {tab.icon && (
                  <tab.icon className={`${size === 'sm' ? 'h-4 w-4' : 'h-5 w-5'} mr-2 flex-shrink-0`} />
                )}
                <span className="truncate">{tab.label}</span>
                {tab.badge && (
                  <span className={`ml-2 inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800`}>
                    {tab.badge}
                  </span>
                )}
              </div>
              
              {tab.closable && (
                <button
                  type="button"
                  className="ml-2 inline-flex items-center justify-center h-4 w-4 rounded-full hover:bg-gray-200 focus:outline-none"
                  onClick={(e) => {
                    e.stopPropagation();
                    removeTab(tab.id);
                  }}
                  aria-label={`Close ${tab.label}`}
                >
                  <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
            </button>
          ))}
        </div>

        <div className="tab-panels mt-4">
          {tabs.map((tab) => (
            <div
              key={tab.id}
              id={`tabpanel-${tab.id}`}
              role="tabpanel"
              aria-labelledby={`tab-${tab.id}`}
              className={activeTab === tab.id ? 'block' : 'hidden'}
            >
              {tab.content}
            </div>
          ))}
        </div>
      </div>
    </TabContext.Provider>
  );
}

// Hook to use tab context
export function useTabManager() {
  const context = React.useContext(TabContext);
  if (!context) {
    throw new Error('useTabManager must be used within a TabManager');
  }
  return context;
}

// Dynamic tab management component
export function DynamicTabManager({
  initialTabs = [],
  className = '',
  ...props
}: Omit<TabManagerProps, 'tabs'> & { initialTabs?: TabItem[] }) {
  const [tabs, setTabs] = useState<TabItem[]>(initialTabs);

  const addTab = useCallback((tab: TabItem) => {
    setTabs(prev => {
      // Don't add duplicate tabs
      if (prev.some(t => t.id === tab.id)) {
        return prev;
      }
      return [...prev, tab];
    });
  }, []);

  const removeTab = useCallback((tabId: string) => {
    setTabs(prev => prev.filter(t => t.id !== tabId));
  }, []);

  return (
    <div className={className}>
      <TabManager
        {...props}
        tabs={tabs}
        onClose={(tabId) => {
          removeTab(tabId);
          props.onClose?.(tabId);
        }}
      />
    </div>
  );
}

// Predefined tab templates
export const TabTemplates = {
  createCustomerTab: (customerId: string): TabItem => ({
    id: `customer-${customerId}`,
    label: `Customer ${customerId}`,
    href: `/admin/customers/${customerId}`,
    closable: true,
    icon: ({ className }) => (
      <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
      </svg>
    ),
  }),

  createNetworkDeviceTab: (deviceId: string, deviceName: string): TabItem => ({
    id: `device-${deviceId}`,
    label: deviceName,
    href: `/admin/network/devices/${deviceId}`,
    closable: true,
    requiredPermissions: ['devices:read'],
    icon: ({ className }) => (
      <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
      </svg>
    ),
  }),

  createSupportTicketTab: (ticketId: string): TabItem => ({
    id: `ticket-${ticketId}`,
    label: `Ticket #${ticketId}`,
    href: `/admin/support/tickets/${ticketId}`,
    closable: true,
    requiredPermissions: ['support:read'],
    icon: ({ className }) => (
      <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192L5.636 18.364M12 2.636a9.364 9.364 0 000 18.728 9.364 9.364 0 000-18.728z" />
      </svg>
    ),
  }),
};