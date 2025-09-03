/**
 * Simple test to verify Jest configuration
 */

import { render, screen } from '@testing-library/react';
import React from 'react';

// Simple test component
const TestComponent: React.FC<{ message: string }> = ({ message }) => {
  return <div data-testid='test-message'>{message}</div>;
};

describe('Simple Integration Test', () => {
  it('should render a test component', () => {
    render(<TestComponent message='Hello Integration Tests!' />);

    expect(screen.getByTestId('test-message')).toHaveTextContent('Hello Integration Tests!');
  });

  it('should verify testing utilities work', () => {
    expect(1 + 1).toBe(2);
    expect('integration').toMatch(/integration/);
  });
});
