import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PluginMarketplace } from '../PluginMarketplace';

// Mock the hooks
jest.mock('@dotmac/headless', () => ({
  useApiClient: jest.fn(),
}));

const mockPlugins = [
  {
    id: 'plugin-1',
    name: 'Test Plugin 1',
    description: 'A test plugin for billing',
    category: 'billing',
    version: '1.0.0',
    author: 'Test Author',
    icon: 'https://example.com/icon1.png',
    screenshots: ['https://example.com/screenshot1.png'],
    stats: {
      rating: 4.5,
      reviews: 100,
      downloads: 1000,
    },
    pricing: {
      type: 'free',
      tiers: [],
    },
    security: {
      verified: true,
      signed: true,
    },
    permissions: {
      api: ['read:billing', 'write:billing'],
      database: [],
      network: [],
    },
  },
  {
    id: 'plugin-2',
    name: 'Test Plugin 2',
    description: 'A premium networking plugin',
    category: 'networking',
    version: '2.1.0',
    author: 'Network Corp',
    icon: null,
    screenshots: [],
    stats: {
      rating: 3.8,
      reviews: 50,
      downloads: 500,
    },
    pricing: {
      type: 'paid',
      tiers: [
        {
          name: 'Basic',
          price: 29.99,
          features: ['Feature 1', 'Feature 2'],
        },
        {
          name: 'Pro',
          price: 59.99,
          features: ['Feature 1', 'Feature 2', 'Feature 3'],
        },
      ],
    },
    security: {
      verified: false,
      signed: true,
    },
    permissions: {
      api: ['read:network'],
      database: ['read:devices'],
      network: ['manage:routes'],
    },
  },
];

describe('PluginMarketplace', () => {
  const mockApiClient = {
    getPluginCatalog: jest.fn(),
    installPlugin: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();

    const { useApiClient } = require('@dotmac/headless');
    useApiClient.mockReturnValue(mockApiClient);

    mockApiClient.getPluginCatalog.mockResolvedValue({
      data: mockPlugins,
    });

    mockApiClient.installPlugin.mockResolvedValue({
      data: {
        installation_id: 'install-123',
      },
    });
  });

  it('renders plugin marketplace component', async () => {
    render(<PluginMarketplace />);

    expect(screen.getByText('Plugin Marketplace')).toBeInTheDocument();
    expect(screen.getByText('Extend your ISP platform with powerful plugins')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Test Plugin 1')).toBeInTheDocument();
    });
  });

  it('loads and displays plugins', async () => {
    render(<PluginMarketplace />);

    await waitFor(() => {
      expect(screen.getByText('Test Plugin 1')).toBeInTheDocument();
      expect(screen.getByText('Test Plugin 2')).toBeInTheDocument();
      expect(screen.getByText('A test plugin for billing')).toBeInTheDocument();
      expect(screen.getByText('A premium networking plugin')).toBeInTheDocument();
    });

    expect(mockApiClient.getPluginCatalog).toHaveBeenCalledWith(
      expect.objectContaining({
        search: '',
        category: [],
        license_type: [],
        verified_only: false,
        min_rating: 0,
        sort_by: 'downloads',
        sort_order: 'desc',
      }),
      { limit: 24 }
    );
  });

  it('handles search input', async () => {
    const user = userEvent.setup();
    render(<PluginMarketplace />);

    await waitFor(() => {
      expect(screen.getByText('Test Plugin 1')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('Search plugins...');
    await user.type(searchInput, 'billing');

    expect(searchInput).toHaveValue('billing');

    // Should trigger a new API call with search filter
    await waitFor(() => {
      expect(mockApiClient.getPluginCatalog).toHaveBeenCalledWith(
        expect.objectContaining({
          search: 'billing',
        }),
        { limit: 24 }
      );
    });
  });

  it('handles sort options', async () => {
    const user = userEvent.setup();
    render(<PluginMarketplace />);

    await waitFor(() => {
      expect(screen.getByText('Test Plugin 1')).toBeInTheDocument();
    });

    const sortSelect = screen.getByDisplayValue('Most Downloaded');
    await user.selectOptions(sortSelect, 'rating');

    expect(sortSelect).toHaveValue('rating');

    await waitFor(() => {
      expect(mockApiClient.getPluginCatalog).toHaveBeenCalledWith(
        expect.objectContaining({
          sort_by: 'rating',
        }),
        { limit: 24 }
      );
    });
  });

  it('shows and hides filters panel', async () => {
    const user = userEvent.setup();
    render(<PluginMarketplace />);

    const filtersButton = screen.getByText('Filters');

    // Filters should not be visible initially
    expect(screen.queryByText('Category')).not.toBeInTheDocument();

    // Click to show filters
    await user.click(filtersButton);
    expect(screen.getByText('Category')).toBeInTheDocument();
    expect(screen.getByText('License Type')).toBeInTheDocument();

    // Click apply filters to hide
    const applyButton = screen.getByText('Apply Filters');
    await user.click(applyButton);
    expect(screen.queryByText('Category')).not.toBeInTheDocument();
  });

  it('handles category filtering', async () => {
    const user = userEvent.setup();
    render(<PluginMarketplace />);

    await waitFor(() => {
      expect(screen.getByText('Test Plugin 1')).toBeInTheDocument();
    });

    // Show filters
    const filtersButton = screen.getByText('Filters');
    await user.click(filtersButton);

    // Select billing category
    const billingCheckbox = screen.getByRole('checkbox', { name: /billing/i });
    await user.click(billingCheckbox);

    expect(billingCheckbox).toBeChecked();

    await waitFor(() => {
      expect(mockApiClient.getPluginCatalog).toHaveBeenCalledWith(
        expect.objectContaining({
          category: ['billing'],
        }),
        { limit: 24 }
      );
    });
  });

  it('handles license type filtering', async () => {
    const user = userEvent.setup();
    render(<PluginMarketplace />);

    await waitFor(() => {
      expect(screen.getByText('Test Plugin 1')).toBeInTheDocument();
    });

    // Show filters
    const filtersButton = screen.getByText('Filters');
    await user.click(filtersButton);

    // Select free license type
    const freeCheckbox = screen.getByRole('checkbox', { name: /free/i });
    await user.click(freeCheckbox);

    expect(freeCheckbox).toBeChecked();

    await waitFor(() => {
      expect(mockApiClient.getPluginCatalog).toHaveBeenCalledWith(
        expect.objectContaining({
          license_type: ['free'],
        }),
        { limit: 24 }
      );
    });
  });

  it('handles verified only filter', async () => {
    const user = userEvent.setup();
    render(<PluginMarketplace />);

    await waitFor(() => {
      expect(screen.getByText('Test Plugin 1')).toBeInTheDocument();
    });

    // Show filters
    const filtersButton = screen.getByText('Filters');
    await user.click(filtersButton);

    // Select verified only
    const verifiedCheckbox = screen.getByRole('checkbox', { name: /verified only/i });
    await user.click(verifiedCheckbox);

    expect(verifiedCheckbox).toBeChecked();

    await waitFor(() => {
      expect(mockApiClient.getPluginCatalog).toHaveBeenCalledWith(
        expect.objectContaining({
          verified_only: true,
        }),
        { limit: 24 }
      );
    });
  });

  it('displays plugin details correctly', async () => {
    render(<PluginMarketplace />);

    await waitFor(() => {
      expect(screen.getByText('Test Plugin 1')).toBeInTheDocument();
      expect(screen.getByText('Test Plugin 2')).toBeInTheDocument();
    });

    // Check category badges
    expect(screen.getByText('billing')).toBeInTheDocument();
    expect(screen.getByText('networking')).toBeInTheDocument();

    // Check pricing
    expect(screen.getByText('Free')).toBeInTheDocument();
    expect(screen.getByText('From $29.99/mo')).toBeInTheDocument();

    // Check download counts
    expect(screen.getByText('1,000 downloads')).toBeInTheDocument();
    expect(screen.getByText('500 downloads')).toBeInTheDocument();
  });

  it('shows security badges for verified and signed plugins', async () => {
    render(<PluginMarketplace />);

    await waitFor(() => {
      expect(screen.getByText('Test Plugin 1')).toBeInTheDocument();
    });

    // Plugin 1 should have both verified and signed badges
    const plugin1Card = screen.getByText('Test Plugin 1').closest('div');
    expect(plugin1Card).toContainHTML('title="Verified"');
    expect(plugin1Card).toContainHTML('title="Signed"');
  });

  it('handles plugin installation', async () => {
    const user = userEvent.setup();

    // Mock window.alert
    const alertSpy = jest.spyOn(window, 'alert').mockImplementation(() => {});

    render(<PluginMarketplace />);

    await waitFor(() => {
      expect(screen.getByText('Test Plugin 1')).toBeInTheDocument();
    });

    const installButtons = screen.getAllByText('Install');
    await user.click(installButtons[0]);

    expect(mockApiClient.installPlugin).toHaveBeenCalledWith({
      plugin_id: 'plugin-1',
      license_tier: 'trial',
      auto_enable: true,
    });

    await waitFor(() => {
      expect(alertSpy).toHaveBeenCalledWith(
        'Plugin installation started. Installation ID: install-123'
      );
    });

    alertSpy.mockRestore();
  });

  it('opens plugin details modal', async () => {
    const user = userEvent.setup();
    render(<PluginMarketplace />);

    await waitFor(() => {
      expect(screen.getByText('Test Plugin 1')).toBeInTheDocument();
    });

    const viewDetailsButtons = screen.getAllByText('View Details');
    await user.click(viewDetailsButtons[0]);

    // Modal should be open with plugin details
    expect(screen.getAllByText('Test Plugin 1')).toHaveLength(2); // One in card, one in modal
    expect(screen.getByText('by Test Author')).toBeInTheDocument();
    expect(screen.getByText('v1.0.0')).toBeInTheDocument();
  });

  it('displays loading state', () => {
    mockApiClient.getPluginCatalog.mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    render(<PluginMarketplace />);

    expect(screen.getByTestId('loading-spinner') || screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('displays error state', async () => {
    mockApiClient.getPluginCatalog.mockRejectedValue(new Error('Network error'));

    render(<PluginMarketplace />);

    await waitFor(() => {
      expect(screen.getByText('Error loading plugins')).toBeInTheDocument();
      expect(screen.getByText('Failed to load plugins')).toBeInTheDocument();
    });
  });

  it('displays empty state', async () => {
    mockApiClient.getPluginCatalog.mockResolvedValue({
      data: [],
    });

    render(<PluginMarketplace />);

    await waitFor(() => {
      expect(screen.getByText('No plugins found matching your criteria')).toBeInTheDocument();
    });
  });

  it('clears all filters', async () => {
    const user = userEvent.setup();
    render(<PluginMarketplace />);

    await waitFor(() => {
      expect(screen.getByText('Test Plugin 1')).toBeInTheDocument();
    });

    // Show filters
    const filtersButton = screen.getByText('Filters');
    await user.click(filtersButton);

    // Set some filters
    const billingCheckbox = screen.getByRole('checkbox', { name: /billing/i });
    await user.click(billingCheckbox);

    // Clear all filters
    const clearButton = screen.getByText('Clear All');
    await user.click(clearButton);

    expect(billingCheckbox).not.toBeChecked();

    await waitFor(() => {
      expect(mockApiClient.getPluginCatalog).toHaveBeenCalledWith(
        expect.objectContaining({
          search: '',
          category: [],
          license_type: [],
          verified_only: false,
          min_rating: 0,
          sort_by: 'downloads',
          sort_order: 'desc',
        }),
        { limit: 24 }
      );
    });
  });
});
