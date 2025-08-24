'use client';

import React, { Fragment } from 'react';
import { Listbox, Transition } from '@headlessui/react';
import { CheckIcon, ChevronUpDownIcon } from '@heroicons/react/24/outline';
import { useTenant } from '@/lib/tenant-context';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { useSecurityMonitor, SecurityEventType, SecuritySeverity } from '@/lib/security-monitor';
import { useRateLimit } from '@/lib/rate-limiting';

export function TenantSwitcher() {
  const {
    currentTenant,
    accessibleTenants,
    isMultiTenant,
    switchTenant,
    isLoadingTenantSwitch,
  } = useTenant();
  
  const { logSecurityEvent } = useSecurityMonitor();
  const { checkRateLimit, recordAttempt, getRemainingAttempts } = useRateLimit();

  if (!isMultiTenant) {
    return null;
  }

  const handleTenantChange = async (tenantId: string) => {
    if (tenantId !== currentTenant?.id) {
      try {
        // Check rate limiting for tenant switches
        if (checkRateLimit('tenantSwitch')) {
          const remaining = getRemainingAttempts('tenantSwitch');
          
          logSecurityEvent(
            SecurityEventType.RATE_LIMIT_EXCEEDED,
            SecuritySeverity.MEDIUM,
            {
              action: 'tenant_switch',
              fromTenantId: currentTenant?.id,
              toTenantId: tenantId,
              remaining,
              timestamp: new Date().toISOString(),
            }
          );
          
          console.warn('Too many tenant switches. Please wait before trying again.');
          return;
        }
        
        // Record tenant switch attempt for rate limiting
        recordAttempt('tenantSwitch');
        
        // Log tenant switch attempt
        logSecurityEvent(
          SecurityEventType.TENANT_SWITCH,
          SecuritySeverity.MEDIUM,
          {
            fromTenantId: currentTenant?.id,
            toTenantId: tenantId,
            fromTenantName: currentTenant?.name,
            toTenantName: accessibleTenants.find(t => t.id === tenantId)?.name,
            timestamp: new Date().toISOString(),
          }
        );
        
        await switchTenant(tenantId);
        
        // Log successful tenant switch
        logSecurityEvent(
          SecurityEventType.TENANT_SWITCH,
          SecuritySeverity.LOW,
          {
            fromTenantId: currentTenant?.id,
            toTenantId: tenantId,
            success: true,
            timestamp: new Date().toISOString(),
          }
        );
      } catch (error) {
        console.error('Failed to switch tenant:', error);
        
        // Log failed tenant switch
        logSecurityEvent(
          SecurityEventType.TENANT_SWITCH,
          SecuritySeverity.HIGH,
          {
            fromTenantId: currentTenant?.id,
            toTenantId: tenantId,
            success: false,
            error: error instanceof Error ? error.message : 'Unknown error',
            timestamp: new Date().toISOString(),
          }
        );
        
        // You might want to show a toast notification here
      }
    }
  };

  return (
    <div className="w-72">
      <Listbox 
        value={currentTenant?.id || ''} 
        onChange={handleTenantChange}
        disabled={isLoadingTenantSwitch}
      >
        <div className="relative">
          <Listbox.Button className="relative w-full cursor-default rounded-lg bg-white py-2 pl-3 pr-10 text-left shadow-md focus:outline-none focus-visible:border-indigo-500 focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-opacity-75 focus-visible:ring-offset-2 focus-visible:ring-offset-orange-300 sm:text-sm">
            {isLoadingTenantSwitch ? (
              <div className="flex items-center">
                <LoadingSpinner size="small" className="mr-2" />
                <span className="text-gray-500">Switching...</span>
              </div>
            ) : currentTenant ? (
              <div>
                <span className="block truncate font-medium">{currentTenant.name}</span>
                <span className="block truncate text-xs text-gray-500">
                  {currentTenant.slug} • {currentTenant.status}
                </span>
              </div>
            ) : (
              <span className="block truncate text-gray-500">Select tenant...</span>
            )}
            <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
              <ChevronUpDownIcon
                className="h-5 w-5 text-gray-400"
                aria-hidden="true"
              />
            </span>
          </Listbox.Button>
          
          <Transition
            as={Fragment}
            leave="transition ease-in duration-100"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <Listbox.Options className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm">
              {accessibleTenants.map((tenant) => (
                <Listbox.Option
                  key={tenant.id}
                  className={({ active }) =>
                    `relative cursor-default select-none py-2 pl-10 pr-4 ${
                      active ? 'bg-amber-100 text-amber-900' : 'text-gray-900'
                    }`
                  }
                  value={tenant.id}
                >
                  {({ selected }) => (
                    <>
                      <div className={selected ? 'font-medium' : 'font-normal'}>
                        <div className="truncate">{tenant.name}</div>
                        <div className="truncate text-xs text-gray-500">
                          {tenant.slug} • {tenant.status}
                          {tenant.plan && ` • ${tenant.plan}`}
                        </div>
                      </div>
                      {selected ? (
                        <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-amber-600">
                          <CheckIcon className="h-5 w-5" aria-hidden="true" />
                        </span>
                      ) : null}
                    </>
                  )}
                </Listbox.Option>
              ))}
            </Listbox.Options>
          </Transition>
        </div>
      </Listbox>
    </div>
  );
}