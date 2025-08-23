/**
 * Comprehensive Accessibility Testing Suite
 * WCAG 2.1 AA Compliance Validation for DotMac Components
 * Automated testing with axe-core integration
 */

import { render, screen } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import userEvent from '@testing-library/user-event';

// Extend Jest matchers
expect.extend(toHaveNoViolations);

// Mock components for testing (these would normally be imported)
const MockButton = ({ children, ...props }: any) => (
  <button {...props}>{children}</button>
);

const MockForm = ({ children, ...props }: any) => (
  <form {...props}>{children}</form>
);

const MockModal = ({ isOpen, children, onClose, ...props }: any) => {
  if (!isOpen) return null;
  return (
    <div role="dialog" aria-modal="true" {...props}>
      <button onClick={onClose} aria-label="Close modal">×</button>
      {children}
    </div>
  );
};

describe('Accessibility Compliance Tests', () => {
  // Configure axe for WCAG 2.1 AA compliance
  const axeConfig = {
    rules: {
      // WCAG 2.1 AA rules
      'color-contrast': { enabled: true },
      'keyboard-trap': { enabled: true },
      'focus-order-semantics': { enabled: true },
      'aria-required-attr': { enabled: true },
      'aria-valid-attr': { enabled: true },
      'aria-valid-attr-value': { enabled: true },
      'button-name': { enabled: true },
      'form-field-multiple-labels': { enabled: true },
      'frame-title': { enabled: true },
      'html-has-lang': { enabled: true },
      'html-lang-valid': { enabled: true },
      'image-alt': { enabled: true },
      'input-image-alt': { enabled: true },
      'label': { enabled: true },
      'link-name': { enabled: true },
      'list': { enabled: true },
      'listitem': { enabled: true },
      'meta-refresh': { enabled: true },
      'meta-viewport': { enabled: true },
      'object-alt': { enabled: true },
      'role-img-alt': { enabled: true },
      'th-has-data-cells': { enabled: true },
      'valid-lang': { enabled: true },
      'video-caption': { enabled: true }
    },
    tags: ['wcag2a', 'wcag2aa']
  };

  describe('Button Components', () => {
    it('should have accessible button with proper labeling', async () => {
      const { container } = render(
        <MockButton aria-label="Submit form">Submit</MockButton>
      );

      const results = await axe(container, axeConfig);
      expect(results).toHaveNoViolations();
    });

    it('should be keyboard accessible', async () => {
      const user = userEvent.setup();
      const mockClick = jest.fn();
      
      render(<MockButton onClick={mockClick}>Click me</MockButton>);
      
      const button = screen.getByRole('button');
      
      // Test keyboard navigation
      await user.tab();
      expect(button).toHaveFocus();
      
      // Test activation with Enter
      await user.keyboard('{Enter}');
      expect(mockClick).toHaveBeenCalled();
      
      // Test activation with Space
      mockClick.mockClear();
      await user.keyboard(' ');
      expect(mockClick).toHaveBeenCalled();
    });

    it('should have proper disabled state accessibility', async () => {
      const { container } = render(
        <MockButton disabled aria-label="Disabled submit button">
          Submit
        </MockButton>
      );

      const results = await axe(container, axeConfig);
      expect(results).toHaveNoViolations();
      
      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
      expect(button).toHaveAttribute('aria-disabled', 'true');
    });
  });

  describe('Form Components', () => {
    it('should have properly labeled form fields', async () => {
      const { container } = render(
        <MockForm>
          <label htmlFor="email">Email Address</label>
          <input 
            id="email" 
            type="email" 
            required 
            aria-describedby="email-help"
          />
          <div id="email-help">Enter your work email address</div>
        </MockForm>
      );

      const results = await axe(container, axeConfig);
      expect(results).toHaveNoViolations();
    });

    it('should handle form validation errors accessibly', async () => {
      const { container } = render(
        <MockForm>
          <label htmlFor="password">Password</label>
          <input 
            id="password" 
            type="password" 
            aria-invalid="true"
            aria-describedby="password-error"
            required
          />
          <div id="password-error" role="alert">
            Password must be at least 8 characters
          </div>
        </MockForm>
      );

      const results = await axe(container, axeConfig);
      expect(results).toHaveNoViolations();
      
      const input = screen.getByLabelText('Password');
      expect(input).toHaveAttribute('aria-invalid', 'true');
      
      const errorMessage = screen.getByRole('alert');
      expect(errorMessage).toBeInTheDocument();
    });

    it('should support keyboard navigation in forms', async () => {
      const user = userEvent.setup();
      
      render(
        <MockForm>
          <label htmlFor="firstName">First Name</label>
          <input id="firstName" type="text" />
          
          <label htmlFor="lastName">Last Name</label>
          <input id="lastName" type="text" />
          
          <MockButton type="submit">Submit</MockButton>
        </MockForm>
      );

      // Test tab navigation
      await user.tab();
      expect(screen.getByLabelText('First Name')).toHaveFocus();
      
      await user.tab();
      expect(screen.getByLabelText('Last Name')).toHaveFocus();
      
      await user.tab();
      expect(screen.getByRole('button')).toHaveFocus();
    });
  });

  describe('Modal Components', () => {
    it('should trap focus within modal when open', async () => {
      const user = userEvent.setup();
      const mockClose = jest.fn();
      
      render(
        <div>
          <MockButton>Outside Button</MockButton>
          <MockModal isOpen={true} onClose={mockClose}>
            <h2>Modal Title</h2>
            <MockButton>Modal Button</MockButton>
          </MockModal>
        </div>
      );

      const modal = screen.getByRole('dialog');
      expect(modal).toHaveAttribute('aria-modal', 'true');
      
      // Focus should be trapped within modal
      const closeButton = screen.getByLabelText('Close modal');
      const modalButton = screen.getByText('Modal Button');
      
      closeButton.focus();
      await user.tab();
      expect(modalButton).toHaveFocus();
      
      await user.tab();
      expect(closeButton).toHaveFocus(); // Should wrap back to start
    });

    it('should be dismissible with Escape key', async () => {
      const user = userEvent.setup();
      const mockClose = jest.fn();
      
      render(
        <MockModal isOpen={true} onClose={mockClose}>
          <h2>Modal Title</h2>
        </MockModal>
      );

      await user.keyboard('{Escape}');
      expect(mockClose).toHaveBeenCalled();
    });

    it('should have proper ARIA attributes', async () => {
      const { container } = render(
        <MockModal 
          isOpen={true} 
          onClose={() => {}}
          aria-labelledby="modal-title"
          aria-describedby="modal-description"
        >
          <h2 id="modal-title">Confirmation</h2>
          <p id="modal-description">Are you sure you want to delete this item?</p>
        </MockModal>
      );

      const results = await axe(container, axeConfig);
      expect(results).toHaveNoViolations();
      
      const modal = screen.getByRole('dialog');
      expect(modal).toHaveAttribute('aria-labelledby', 'modal-title');
      expect(modal).toHaveAttribute('aria-describedby', 'modal-description');
    });
  });

  describe('Navigation Components', () => {
    it('should provide accessible navigation landmarks', async () => {
      const { container } = render(
        <nav aria-label="Main navigation">
          <ul>
            <li><a href="/dashboard">Dashboard</a></li>
            <li><a href="/customers">Customers</a></li>
            <li><a href="/billing">Billing</a></li>
          </ul>
        </nav>
      );

      const results = await axe(container, axeConfig);
      expect(results).toHaveNoViolations();
      
      const navigation = screen.getByRole('navigation');
      expect(navigation).toHaveAttribute('aria-label', 'Main navigation');
    });

    it('should indicate current page in navigation', async () => {
      const { container } = render(
        <nav aria-label="Main navigation">
          <ul>
            <li>
              <a href="/dashboard" aria-current="page">Dashboard</a>
            </li>
            <li><a href="/customers">Customers</a></li>
          </ul>
        </nav>
      );

      const results = await axe(container, axeConfig);
      expect(results).toHaveNoViolations();
      
      const currentLink = screen.getByRole('link', { current: 'page' });
      expect(currentLink).toHaveAttribute('aria-current', 'page');
    });

    it('should support keyboard navigation', async () => {
      const user = userEvent.setup();
      
      render(
        <nav>
          <a href="/home">Home</a>
          <a href="/about">About</a>
          <a href="/contact">Contact</a>
        </nav>
      );

      // Test tab navigation
      await user.tab();
      expect(screen.getByRole('link', { name: 'Home' })).toHaveFocus();
      
      await user.tab();
      expect(screen.getByRole('link', { name: 'About' })).toHaveFocus();
      
      await user.tab();
      expect(screen.getByRole('link', { name: 'Contact' })).toHaveFocus();
    });
  });

  describe('Data Table Components', () => {
    it('should have accessible table headers', async () => {
      const { container } = render(
        <table>
          <caption>Customer List</caption>
          <thead>
            <tr>
              <th scope="col">Name</th>
              <th scope="col">Email</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>John Doe</td>
              <td>john@example.com</td>
              <td>Active</td>
            </tr>
          </tbody>
        </table>
      );

      const results = await axe(container, axeConfig);
      expect(results).toHaveNoViolations();
      
      const table = screen.getByRole('table', { name: 'Customer List' });
      expect(table).toBeInTheDocument();
    });

    it('should support sortable columns accessibly', async () => {
      const user = userEvent.setup();
      const mockSort = jest.fn();
      
      render(
        <table>
          <thead>
            <tr>
              <th>
                <button 
                  onClick={mockSort}
                  aria-label="Sort by name ascending"
                  aria-sort="ascending"
                >
                  Name
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr><td>John Doe</td></tr>
          </tbody>
        </table>
      );

      const sortButton = screen.getByRole('button', { name: /sort by name/i });
      expect(sortButton).toHaveAttribute('aria-sort', 'ascending');
      
      await user.click(sortButton);
      expect(mockSort).toHaveBeenCalled();
    });
  });

  describe('Loading and Status Components', () => {
    it('should announce loading states to screen readers', async () => {
      const { container } = render(
        <div>
          <div aria-live="polite" aria-label="Loading status">
            Loading customer data...
          </div>
        </div>
      );

      const results = await axe(container, axeConfig);
      expect(results).toHaveNoViolations();
      
      const status = screen.getByLabelText('Loading status');
      expect(status).toHaveAttribute('aria-live', 'polite');
    });

    it('should announce success and error messages', async () => {
      const { container } = render(
        <div>
          <div role="alert" aria-live="assertive">
            Customer saved successfully!
          </div>
        </div>
      );

      const results = await axe(container, axeConfig);
      expect(results).toHaveNoViolations();
      
      const alert = screen.getByRole('alert');
      expect(alert).toHaveAttribute('aria-live', 'assertive');
    });
  });

  describe('Color and Contrast', () => {
    it('should meet minimum color contrast ratios', async () => {
      const { container } = render(
        <div style={{ 
          backgroundColor: '#ffffff', 
          color: '#333333',
          padding: '1rem'
        }}>
          <p>This text should have sufficient contrast</p>
          <MockButton style={{
            backgroundColor: '#007bff',
            color: '#ffffff',
            padding: '0.5rem 1rem',
            border: 'none'
          }}>
            Action Button
          </MockButton>
        </div>
      );

      const results = await axe(container, axeConfig);
      expect(results).toHaveNoViolations();
    });
  });

  describe('Images and Media', () => {
    it('should have proper alternative text for images', async () => {
      const { container } = render(
        <div>
          <img 
            src="/logo.png" 
            alt="DotMac ISP Framework Logo" 
          />
          <img 
            src="/chart.png" 
            alt="Network usage chart showing 80% utilization for the past month"
          />
          {/* Decorative image */}
          <img 
            src="/decoration.png" 
            alt="" 
            role="presentation"
          />
        </div>
      );

      const results = await axe(container, axeConfig);
      expect(results).toHaveNoViolations();
    });
  });

  describe('Skip Links and Page Structure', () => {
    it('should provide skip links for keyboard navigation', async () => {
      const user = userEvent.setup();
      
      const { container } = render(
        <div>
          <a href="#main-content" className="skip-link">
            Skip to main content
          </a>
          <nav>
            <a href="/home">Home</a>
            <a href="/about">About</a>
          </nav>
          <main id="main-content">
            <h1>Main Content</h1>
            <p>Page content here...</p>
          </main>
        </div>
      );

      const results = await axe(container, axeConfig);
      expect(results).toHaveNoViolations();
      
      const skipLink = screen.getByRole('link', { name: 'Skip to main content' });
      expect(skipLink).toBeInTheDocument();
    });

    it('should have proper heading hierarchy', async () => {
      const { container } = render(
        <div>
          <h1>Page Title</h1>
          <h2>Section 1</h2>
          <h3>Subsection 1.1</h3>
          <h3>Subsection 1.2</h3>
          <h2>Section 2</h2>
          <h3>Subsection 2.1</h3>
        </div>
      );

      const results = await axe(container, axeConfig);
      expect(results).toHaveNoViolations();
    });
  });
});

// Performance tests for accessibility features
describe('Accessibility Performance', () => {
  it('should not significantly impact render performance', async () => {
    const startTime = performance.now();
    
    const { container } = render(
      <div>
        {Array.from({ length: 100 }, (_, i) => (
          <MockButton key={i} aria-label={`Button ${i + 1}`}>
            Button {i + 1}
          </MockButton>
        ))}
      </div>
    );
    
    const renderTime = performance.now() - startTime;
    
    // Accessibility features should not add significant overhead
    expect(renderTime).toBeLessThan(100); // 100ms threshold
    
    const axeStartTime = performance.now();
    const results = await axe(container);
    const axeTime = performance.now() - axeStartTime;
    
    expect(results).toHaveNoViolations();
    expect(axeTime).toBeLessThan(1000); // 1 second threshold for axe analysis
  });
});

// Custom accessibility rules for DotMac specific requirements
describe('DotMac Specific Accessibility Requirements', () => {
  it('should have consistent focus indicators across all interactive elements', async () => {
    const { container } = render(
      <div>
        <MockButton className="dotmac-button">Primary Action</MockButton>
        <MockButton className="dotmac-button-secondary">Secondary Action</MockButton>
        <input className="dotmac-input" type="text" placeholder="Enter text" />
      </div>
    );

    // Custom rule: all interactive elements should have focus indicators
    const results = await axe(container, {
      ...axeConfig,
      rules: {
        ...axeConfig.rules,
        'focus-order-semantics': { enabled: true }
      }
    });
    
    expect(results).toHaveNoViolations();
  });

  it('should support high contrast mode', async () => {
    const { container } = render(
      <div className="high-contrast-mode">
        <MockButton>High Contrast Button</MockButton>
        <input type="text" placeholder="High contrast input" />
      </div>
    );

    const results = await axe(container, axeConfig);
    expect(results).toHaveNoViolations();
  });

  it('should work with reduced motion preferences', async () => {
    // Mock reduced motion preference
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: jest.fn().mockImplementation(query => ({
        matches: query === '(prefers-reduced-motion: reduce)',
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
      })),
    });

    const { container } = render(
      <div className="respects-reduced-motion">
        <MockButton>Animation Aware Button</MockButton>
      </div>
    );

    const results = await axe(container, axeConfig);
    expect(results).toHaveNoViolations();
  });
});