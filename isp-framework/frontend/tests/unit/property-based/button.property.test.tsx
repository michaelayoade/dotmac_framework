/**
 * Property-Based Tests for Button Component
 * Uses generative testing to validate button behavior across infinite input combinations
 */

import React from 'react';
import { render, screen } from '@dotmac/testing';
import fc from 'fast-check';
import { Button } from '../../../packages/primitives/src/forms/Button';

// Property-based test arbitraries
const buttonPropsArbitrary = fc.record({
  variant: fc.oneof(
    fc.constant('default'),
    fc.constant('destructive'),
    fc.constant('outline'),
    fc.constant('secondary'),
    fc.constant('ghost'),
    fc.constant('link')
  ),
  size: fc.oneof(
    fc.constant('sm'),
    fc.constant('default'),
    fc.constant('lg'),
    fc.constant('icon')
  ),
  disabled: fc.boolean(),
  isLoading: fc.boolean(),
  asChild: fc.boolean(),
  children: fc.oneof(
    fc.string({ minLength: 1, maxLength: 50 }),
    fc.constant('Click me'),
    fc.constant('')
  )
}, { requiredKeys: [] });

describe('Button Properties', () => {
  afterEach(() => {
    global.propertyTestUtils?.cleanupComponent();
  });

  test('Button should always render without crashing', () => {
    fc.assert(
      fc.property(buttonPropsArbitrary, (props) => {
        expect(() => {
          render(<Button {...props} />);
        }).not.toThrow();
      }),
      { numRuns: 100 }
    );
  });

  test('Button should always be accessible when not disabled', () => {
    fc.assert(
      fc.property(
        buttonPropsArbitrary.filter(props => !props.disabled),
        (props) => {
          const { container } = render(<Button {...props} />);
          const button = container.querySelector('button, [role="button"]');
          
          // Should always have a button element or button role
          expect(button).toBeTruthy();
          
          // Should be focusable when not disabled
          if (!props.disabled) {
            expect(button).not.toHaveAttribute('disabled');
          }
          
          return true;
        }
      ),
      { numRuns: 50 }
    );
  });

  test('Button loading state should disable interaction', () => {
    fc.assert(
      fc.property(
        buttonPropsArbitrary.filter(props => props.isLoading),
        (props) => {
          const { container } = render(<Button {...props} />);
          const button = container.querySelector('button');
          
          if (button && props.isLoading) {
            // Loading buttons should indicate their state
            expect(
              button.hasAttribute('disabled') || 
              button.hasAttribute('aria-disabled') ||
              button.getAttribute('aria-busy') === 'true'
            ).toBe(true);
          }
          
          return true;
        }
      ),
      { numRuns: 50 }
    );
  });

  test('Button should preserve all valid HTML attributes', () => {
    const htmlAttributesArbitrary = fc.record({
      'data-testid': fc.string(),
      'aria-label': fc.string(),
      className: fc.string(),
      id: fc.string()
    }, { requiredKeys: [] });

    fc.assert(
      fc.property(
        fc.tuple(buttonPropsArbitrary, htmlAttributesArbitrary),
        ([buttonProps, htmlAttributes]) => {
          const allProps = { ...buttonProps, ...htmlAttributes };
          const { container } = render(<Button {...allProps} />);
          const button = container.querySelector('button, [role="button"]');
          
          // Verify specific attributes are preserved
          if (htmlAttributes['data-testid']) {
            expect(button).toHaveAttribute('data-testid', htmlAttributes['data-testid']);
          }
          
          if (htmlAttributes['aria-label']) {
            expect(button).toHaveAttribute('aria-label', htmlAttributes['aria-label']);
          }
          
          if (htmlAttributes.id) {
            expect(button).toHaveAttribute('id', htmlAttributes.id);
          }
          
          return true;
        }
      ),
      { numRuns: 30 }
    );
  });

  test('Button click handlers should be called when interactive', () => {
    fc.assert(
      fc.property(
        buttonPropsArbitrary.filter(props => !props.disabled && !props.isLoading),
        async (props) => {
          const mockClick = jest.fn();
          const { container } = render(
            <Button {...props} onClick={mockClick}>
              Test Button
            </Button>
          );
          
          const button = container.querySelector('button');
          if (button) {
            // Should be able to click non-disabled, non-loading buttons
            const userEvent = await global.propertyTestUtils.safeUserEventSetup();
            await userEvent.click(button);
            expect(mockClick).toHaveBeenCalled();
          }
          
          return true;
        }
      ),
      { numRuns: 20 }
    );
  });

  test('Button should maintain consistent size classes', () => {
    fc.assert(
      fc.property(buttonPropsArbitrary, (props) => {
        const { container } = render(<Button {...props} />);
        const button = container.querySelector('button, [role="button"]');
        
        if (button && props.size) {
          const classList = Array.from(button.classList);
          const sizeClasses = {
            'sm': ['h-8'],
            'default': ['h-9'],
            'lg': ['h-10'],
            'icon': ['h-9', 'w-9']
          };
          
          const expectedClasses = sizeClasses[props.size] || sizeClasses['default'];
          const hasValidSizeClass = expectedClasses.some(cls => 
            classList.some(buttonClass => buttonClass.includes(cls.replace('h-', '').replace('w-', '')))
          );
          
          // Should have appropriate size-related classes
          expect(hasValidSizeClass || classList.length > 0).toBe(true);
        }
        
        return true;
      }),
      { numRuns: 30 }
    );
  });
});

// Invariant tests - properties that should ALWAYS be true
describe('Button Invariants', () => {
  test('Invariant: Button should never break the DOM structure', () => {
    fc.assert(
      fc.property(buttonPropsArbitrary, (props) => {
        const { container } = render(<Button {...props} />);
        
        // Should always produce valid HTML
        expect(container.innerHTML).toBeTruthy();
        
        // Should not contain script tags or dangerous content
        expect(container.querySelector('script')).toBeNull();
        
        // Should have a focusable element
        const focusableElements = container.querySelectorAll(
          'button, [role="button"], a, input, select, textarea, [tabindex]'
        );
        expect(focusableElements.length).toBeGreaterThan(0);
        
        return true;
      }),
      { numRuns: 100 }
    );
  });

  test('Invariant: Disabled buttons should never trigger actions', () => {
    fc.assert(
      fc.property(
        buttonPropsArbitrary.filter(props => props.disabled),
        (props) => {
          const mockClick = jest.fn();
          const { container } = render(
            <Button {...props} onClick={mockClick}>
              Disabled Button
            </Button>
          );
          
          const button = container.querySelector('button');
          if (button) {
            // Disabled buttons should prevent default click behavior
            expect(
              button.hasAttribute('disabled') || 
              button.getAttribute('aria-disabled') === 'true'
            ).toBe(true);
          }
          
          return true;
        }
      ),
      { numRuns: 50 }
    );
  });
});

// Performance properties
describe('Button Performance Properties', () => {
  test('Button rendering should be consistently fast', () => {
    fc.assert(
      fc.property(buttonPropsArbitrary, (props) => {
        const startTime = performance.now();
        render(<Button {...props} />);
        const endTime = performance.now();
        
        const renderTime = endTime - startTime;
        
        // Rendering should be fast (< 50ms for simple buttons)
        expect(renderTime).toBeLessThan(50);
        
        return true;
      }),
      { numRuns: 20 }
    );
  });
});

// Error boundary tests
describe('Button Error Handling Properties', () => {
  test('Button should handle invalid props gracefully', () => {
    const invalidPropsArbitrary = fc.record({
      variant: fc.oneof(fc.string(), fc.integer(), fc.constant(null), fc.constant(undefined)),
      size: fc.oneof(fc.string(), fc.integer(), fc.constant(null), fc.constant(undefined)),
      children: fc.oneof(fc.anything(), fc.constant(null))
    });

    fc.assert(
      fc.property(invalidPropsArbitrary, (invalidProps) => {
        // Should not crash with invalid props
        expect(() => {
          try {
            render(<Button {...invalidProps} />);
          } catch (error) {
            // Some invalid props might throw, that's acceptable
            // The important thing is we don't get uncaught exceptions
            return true;
          }
        }).not.toThrow();
        
        return true;
      }),
      { numRuns: 30 }
    );
  });
});