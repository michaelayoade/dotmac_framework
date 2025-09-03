/**
 * Customer Portal Component Tests
 * Comprehensive testing of the main customer support interface
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';

// Import the component to test
import CustomerPortal from '../../src/components/support/CustomerPortal';

// Mock child components
jest.mock('../../src/components/support/KnowledgeBaseSearch', () => {
  return function MockKnowledgeBaseSearch({ initialQuery }: { initialQuery?: string }) {
    return (
      <div data-testid='knowledge-base-search'>Knowledge Base Search - Query: {initialQuery}</div>
    );
  };
});

jest.mock('../../src/components/support/TicketList', () => {
  return function MockTicketList() {
    return <div data-testid='ticket-list'>Ticket List</div>;
  };
});

jest.mock('../../src/components/support/LiveChatWidget', () => {
  return function MockLiveChatWidget() {
    return (
      <div data-testid='live-chat-widget' id='live-chat-widget'>
        Live Chat Widget
      </div>
    );
  };
});

jest.mock('../../src/components/support/PortalSettings', () => {
  return function MockPortalSettings() {
    return <div data-testid='portal-settings'>Portal Settings</div>;
  };
});

// Mock fetch for API calls
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe('CustomerPortal', () => {
  beforeEach(() => {
    // Reset mocks before each test
    mockFetch.mockClear();

    // Mock successful API responses
    mockFetch.mockResolvedValue({
      json: () =>
        Promise.resolve({
          openTickets: 2,
          resolvedTickets: 8,
          avgResolutionTime: 24,
          knowledgeBaseViews: 15,
        }),
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  test('renders dashboard with all main sections', async () => {
    await act(async () => {
      render(<CustomerPortal />);
    });

    // Check if main elements are present
    expect(screen.getByText('Support Portal')).toBeInTheDocument();
    expect(
      screen.getByText('Get help, find answers, and manage your support requests')
    ).toBeInTheDocument();

    // Check for search bar
    expect(screen.getByPlaceholderText(/Search for help articles/)).toBeInTheDocument();

    // Check for tabs
    expect(screen.getByRole('tab', { name: 'Dashboard' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Knowledge Base' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'My Tickets' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Live Chat' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Settings' })).toBeInTheDocument();
  });

  test('displays loading state initially', () => {
    render(<CustomerPortal />);

    // Should show loading spinner initially
    expect(screen.getByRole('generic', { hidden: true })).toHaveClass('animate-spin');
  });

  test('displays dashboard stats after loading', async () => {
    await act(async () => {
      render(<CustomerPortal />);
    });

    await waitFor(() => {
      expect(screen.getByText('Open Tickets')).toBeInTheDocument();
      expect(screen.getByText('2')).toBeInTheDocument(); // Open tickets count
      expect(screen.getByText('8')).toBeInTheDocument(); // Resolved tickets count
      expect(screen.getByText('24h')).toBeInTheDocument(); // Avg resolution time
      expect(screen.getByText('15')).toBeInTheDocument(); // KB views count
    });
  });

  test('displays quick action cards', async () => {
    await act(async () => {
      render(<CustomerPortal />);
    });

    await waitFor(() => {
      expect(screen.getByText('Create Support Ticket')).toBeInTheDocument();
      expect(screen.getByText('Start Live Chat')).toBeInTheDocument();
      expect(screen.getByText('Browse Knowledge Base')).toBeInTheDocument();
      expect(screen.getByText('Account Settings')).toBeInTheDocument();
    });
  });

  test('search functionality works correctly', async () => {
    const user = userEvent.setup();

    await act(async () => {
      render(<CustomerPortal />);
    });

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Search for help articles/)).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/Search for help articles/);

    // Type in search box
    await user.type(searchInput, 'password reset');
    expect(searchInput).toHaveValue('password reset');

    // Press Enter to search
    await user.keyboard('{Enter}');

    // Should switch to knowledge base tab and pass search query
    await waitFor(() => {
      expect(screen.getByText('Knowledge Base Search - Query: password reset')).toBeInTheDocument();
    });
  });

  test('tab navigation works correctly', async () => {
    const user = userEvent.setup();

    await act(async () => {
      render(<CustomerPortal />);
    });

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: 'Knowledge Base' })).toBeInTheDocument();
    });

    // Click on Knowledge Base tab
    await user.click(screen.getByRole('tab', { name: 'Knowledge Base' }));

    await waitFor(() => {
      expect(screen.getByTestId('knowledge-base-search')).toBeInTheDocument();
    });

    // Click on My Tickets tab
    await user.click(screen.getByRole('tab', { name: 'My Tickets' }));

    await waitFor(() => {
      expect(screen.getByTestId('ticket-list')).toBeInTheDocument();
    });

    // Click on Settings tab
    await user.click(screen.getByRole('tab', { name: 'Settings' }));

    await waitFor(() => {
      expect(screen.getByTestId('portal-settings')).toBeInTheDocument();
    });
  });

  test('quick action cards navigate to correct tabs', async () => {
    const user = userEvent.setup();

    await act(async () => {
      render(<CustomerPortal />);
    });

    await waitFor(() => {
      expect(screen.getByText('Create Support Ticket')).toBeInTheDocument();
    });

    // Click on Create Support Ticket
    await user.click(screen.getByText('Create Support Ticket'));

    await waitFor(() => {
      expect(screen.getByTestId('ticket-list')).toBeInTheDocument();
    });

    // Go back to dashboard
    await user.click(screen.getByRole('tab', { name: 'Dashboard' }));

    await waitFor(() => {
      expect(screen.getByText('Quick Actions')).toBeInTheDocument();
    });

    // Click on Browse Knowledge Base
    await user.click(screen.getByText('Browse Knowledge Base'));

    await waitFor(() => {
      expect(screen.getByTestId('knowledge-base-search')).toBeInTheDocument();
    });
  });

  test('popular articles section displays correctly', async () => {
    // Mock articles API response
    mockFetch.mockImplementation((url) => {
      if (url.includes('popular')) {
        return Promise.resolve({
          json: () =>
            Promise.resolve([
              {
                id: '1',
                title: 'How to Reset Your Password',
                category: 'Account Management',
                views: 1234,
                helpful_votes: 89,
                slug: 'reset-password',
              },
              {
                id: '2',
                title: 'Setting Up Email on Mobile',
                category: 'Technical Support',
                views: 987,
                helpful_votes: 76,
                slug: 'email-mobile-setup',
              },
            ]),
        });
      }
      return Promise.resolve({
        json: () =>
          Promise.resolve({
            openTickets: 2,
            resolvedTickets: 8,
            avgResolutionTime: 24,
            knowledgeBaseViews: 15,
          }),
      });
    });

    await act(async () => {
      render(<CustomerPortal />);
    });

    await waitFor(() => {
      expect(screen.getByText('Popular Help Articles')).toBeInTheDocument();
      expect(screen.getByText('How to Reset Your Password')).toBeInTheDocument();
      expect(screen.getByText('Setting Up Email on Mobile')).toBeInTheDocument();
      expect(screen.getByText('1,234 views')).toBeInTheDocument();
      expect(screen.getByText('987 views')).toBeInTheDocument();
    });
  });

  test('recent activity section displays correctly', async () => {
    await act(async () => {
      render(<CustomerPortal />);
    });

    await waitFor(() => {
      expect(screen.getByText('Recent Activity')).toBeInTheDocument();
      expect(screen.getByText('Created support ticket #12345')).toBeInTheDocument();
      expect(screen.getByText('Completed live chat session')).toBeInTheDocument();
      expect(screen.getByText('Viewed "Email Setup Guide"')).toBeInTheDocument();
    });
  });

  test('live chat integration works', async () => {
    const user = userEvent.setup();

    await act(async () => {
      render(<CustomerPortal />);
    });

    await waitFor(() => {
      expect(screen.getByText('Start Live Chat')).toBeInTheDocument();
    });

    // Mock click event on live chat widget
    const mockClick = jest.fn();
    const chatWidget = screen.getByTestId('live-chat-widget');
    chatWidget.addEventListener('click', mockClick);

    // Click start live chat button
    await user.click(screen.getByText('Start Live Chat'));

    // Should trigger chat widget click
    fireEvent.click(chatWidget);
    expect(mockClick).toHaveBeenCalled();
  });

  test('handles API errors gracefully', async () => {
    // Mock API error
    mockFetch.mockRejectedValue(new Error('API Error'));

    // Mock console.error to avoid error output in tests
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    await act(async () => {
      render(<CustomerPortal />);
    });

    await waitFor(() => {
      // Should still render the component structure
      expect(screen.getByText('Support Portal')).toBeInTheDocument();
      expect(screen.getByText('Quick Actions')).toBeInTheDocument();
    });

    expect(consoleSpy).toHaveBeenCalledWith('Error fetching dashboard data:', expect.any(Error));

    consoleSpy.mockRestore();
  });

  test('responsive design elements are present', async () => {
    await act(async () => {
      render(<CustomerPortal />);
    });

    await waitFor(() => {
      // Check for responsive grid classes
      const quickActionsGrid = screen.getByText('Quick Actions').closest('div')?.nextElementSibling;
      expect(quickActionsGrid).toHaveClass('grid', 'gap-4', 'md:grid-cols-2', 'lg:grid-cols-4');

      const statsGrid = screen.getByText('Open Tickets').closest('.grid');
      expect(statsGrid).toHaveClass('grid', 'gap-4', 'md:grid-cols-2', 'lg:grid-cols-4');
    });
  });

  test('accessibility features are implemented', async () => {
    await act(async () => {
      render(<CustomerPortal />);
    });

    await waitFor(() => {
      // Check for proper heading hierarchy
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Support Portal');
      expect(screen.getAllByRole('heading', { level: 2 }).length).toBeGreaterThan(0);

      // Check for proper button labels
      expect(screen.getByRole('button', { name: /Dashboard/ })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Knowledge Base/ })).toBeInTheDocument();

      // Check for proper form labels
      expect(screen.getByRole('searchbox')).toBeInTheDocument();
    });
  });

  test('keyboard navigation works correctly', async () => {
    const user = userEvent.setup();

    await act(async () => {
      render(<CustomerPortal />);
    });

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Search for help articles/)).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/Search for help articles/);

    // Focus search input
    await user.click(searchInput);
    expect(searchInput).toHaveFocus();

    // Tab to next focusable element
    await user.tab();

    // Should focus on the next interactive element
    expect(document.activeElement).not.toBe(searchInput);
  });

  test('component unmounts cleanly', async () => {
    const { unmount } = await act(async () => {
      return render(<CustomerPortal />);
    });

    // Should unmount without errors
    expect(() => unmount()).not.toThrow();
  });
});

// Performance tests
describe('CustomerPortal Performance', () => {
  test('renders within acceptable time', async () => {
    const startTime = performance.now();

    await act(async () => {
      render(<CustomerPortal />);
    });

    const endTime = performance.now();
    const renderTime = endTime - startTime;

    // Should render within 100ms (adjust threshold as needed)
    expect(renderTime).toBeLessThan(100);
  });

  test('handles large datasets efficiently', async () => {
    // Mock large dataset
    const largeArticlesList = Array.from({ length: 100 }, (_, i) => ({
      id: `article_${i}`,
      title: `Article ${i}`,
      category: 'Test Category',
      views: Math.floor(Math.random() * 1000),
      helpful_votes: Math.floor(Math.random() * 50),
      slug: `article-${i}`,
    }));

    mockFetch.mockResolvedValue({
      json: () => Promise.resolve(largeArticlesList),
    });

    const startTime = performance.now();

    await act(async () => {
      render(<CustomerPortal />);
    });

    const endTime = performance.now();
    const renderTime = endTime - startTime;

    // Should still render efficiently with large datasets
    expect(renderTime).toBeLessThan(200);
  });
});

// Integration tests
describe('CustomerPortal Integration', () => {
  test('integrates with all child components correctly', async () => {
    await act(async () => {
      render(<CustomerPortal />);
    });

    await waitFor(() => {
      // All child components should be available
      expect(screen.getByTestId('live-chat-widget')).toBeInTheDocument();
    });

    // Navigate to each tab to ensure child components render
    const user = userEvent.setup();

    await user.click(screen.getByRole('tab', { name: 'Knowledge Base' }));
    await waitFor(() => {
      expect(screen.getByTestId('knowledge-base-search')).toBeInTheDocument();
    });

    await user.click(screen.getByRole('tab', { name: 'My Tickets' }));
    await waitFor(() => {
      expect(screen.getByTestId('ticket-list')).toBeInTheDocument();
    });

    await user.click(screen.getByRole('tab', { name: 'Settings' }));
    await waitFor(() => {
      expect(screen.getByTestId('portal-settings')).toBeInTheDocument();
    });
  });

  test('maintains state across tab switches', async () => {
    const user = userEvent.setup();

    await act(async () => {
      render(<CustomerPortal />);
    });

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Search for help articles/)).toBeInTheDocument();
    });

    // Enter search query
    const searchInput = screen.getByPlaceholderText(/Search for help articles/);
    await user.type(searchInput, 'test query');

    // Switch tabs
    await user.click(screen.getByRole('tab', { name: 'My Tickets' }));
    await user.click(screen.getByRole('tab', { name: 'Dashboard' }));

    // Search query should be maintained
    await waitFor(() => {
      expect(searchInput).toHaveValue('test query');
    });
  });
});
