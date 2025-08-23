'use client';

import { useId } from 'react';

('use client');

/**
 * Import Test Component
 * Validates that all package imports work correctly
 */

import { useFormatting } from '@dotmac/headless';
import { ErrorBoundary } from '@dotmac/primitives';
import { Button, Card } from '@dotmac/styled-components';

interface ImportTestProps {
  testValue?: number;
}

export function ImportTest({ testValue = 299.99 }: ImportTestProps): JSX.Element {
  const id = useId();
  const { formatCurrency } = useFormatting();

  return (
    <ErrorBoundary level='component'>
      <Card data-testid={`${id}-import-test`}>
        <div className='p-4'>
          <h2 className='mb-4 font-semibold text-xl'>Import Test</h2>
          <p className='mb-4'>Testing imports from all packages:</p>
          <ul className='mb-4 space-y-2'>
            <li>✅ @dotmac/headless - useFormatting hook</li>
            <li>✅ @dotmac/primitives - ErrorBoundary component</li>
            <li>✅ @dotmac/styled-components - Card and Button components</li>
          </ul>
          <p className='mb-4'>
            Formatted currency: <strong>{formatCurrency?.(testValue)}</strong>
          </p>
          <Button variant='primary' size='sm'>
            Test Button
          </Button>
        </div>
      </Card>
    </ErrorBoundary>
  );
}
