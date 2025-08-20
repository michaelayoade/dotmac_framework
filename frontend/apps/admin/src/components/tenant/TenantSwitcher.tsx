'use client';

import { useTenantStore } from '@dotmac/headless';
import { Button } from '@dotmac/styled-components/admin';
import { clsx } from 'clsx';
import { Building2, Check, ChevronDown } from 'lucide-react';
import { useState } from 'react';

export function TenantSwitcher() {
  const { currentTenant, availableTenants, switchTenant, switchingTenant } = useTenantStore();
  const [isOpen, setIsOpen] = useState(false);

  const handleTenantSwitch = async (tenantId: string) => {
    try {
      await switchTenant(tenantId);
      setIsOpen(false);
    } catch (_error) {
      // Error handling intentionally empty
    }
  };

  if (availableTenants.length <= 1) {
    return null;
  }

  return (
    <div className='relative'>
      <Button
        variant='outline'
        onClick={() => setIsOpen(!isOpen)}
        disabled={switchingTenant}
        className='w-64 justify-between'
      >
        <div className='flex items-center'>
          <Building2 className='mr-2 h-4 w-4' />
          <span className='truncate'>{currentTenant?.tenant?.name || 'Select Tenant'}</span>
        </div>
        <ChevronDown className='ml-2 h-4 w-4' />
      </Button>

      {isOpen ? (
        <div className='absolute right-0 z-50 mt-2 w-64 rounded-md border border-gray-200 bg-white py-1 shadow-lg'>
          <div className='px-4 py-2 font-semibold text-gray-400 text-xs uppercase tracking-wider'>
            Available Tenants
          </div>
          {availableTenants.map((tenant) => (
            <button
              type='button'
              key={tenant.id}
              onClick={() => handleTenantSwitch(tenant.id)}
              disabled={switchingTenant}
              className={clsx(
                'flex w-full items-center justify-between px-4 py-2 text-sm hover:bg-gray-100 disabled:opacity-50',
                currentTenant?.tenant?.id === tenant.id
                  ? 'bg-primary/5 text-primary'
                  : 'text-gray-700'
              )}
            >
              <div className='flex items-center'>
                <Building2 className='mr-2 h-4 w-4' />
                <div className='text-left'>
                  <div className='font-medium'>{tenant.name}</div>
                  <div className='text-gray-500 text-xs'>{tenant.domain}</div>
                </div>
              </div>
              {currentTenant?.tenant?.id === tenant.id && (
                <Check className='h-4 w-4 text-primary' />
              )}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
