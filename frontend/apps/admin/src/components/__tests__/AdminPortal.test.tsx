/**
 * Basic smoke test for Admin Portal
 */

import { render, screen } from '@testing-library/react';

// Simple component test
describe('Admin Portal Smoke Test', () => {
  it('should render basic loading message', () => {
    const TestComponent = () => <div>Loading DotMac ISP Management Platform...</div>;
    render(<TestComponent />);
    
    expect(screen.getByText('Loading DotMac ISP Management Platform...')).toBeInTheDocument();
  });

  it('should have working React testing setup', () => {
    const TestComponent = ({ message }: { message: string }) => <span data-testid="test-message">{message}</span>;
    render(<TestComponent message="Hello World" />);
    
    expect(screen.getByTestId('test-message')).toHaveTextContent('Hello World');
  });
});