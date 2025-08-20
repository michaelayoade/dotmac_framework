/**
 * Jest setup for unit tests
 */

// Polyfill for TextEncoder/TextDecoder (needed for MSW)
if (typeof global.TextEncoder === 'undefined') {
  global.TextEncoder = require('node:util').TextEncoder;
  global.TextDecoder = require('node:util').TextDecoder;
}

require('@testing-library/jest-dom');
const { configure } = require('@testing-library/react');

// Setup jest-axe for accessibility testing
const { toHaveNoViolations } = require('jest-axe');
expect.extend(toHaveNoViolations);

// Try to import MSW server, skip if not available
let server;
try {
  const mswModule = require('./__mocks__/server.js');
  server = mswModule.server;
} catch (_error) {
  /* empty */
}

// Configure React Testing Library
configure({
  testIdAttribute: 'data-testid',
});

// Mock Next.js router
jest.mock('next/router', () => ({
  useRouter() {
    return {
      route: '/',
      pathname: '/',
      query: {
        /* empty */
      },
      asPath: '/',
      push: jest.fn(),
      pop: jest.fn(),
      reload: jest.fn(),
      back: jest.fn(),
      prefetch: jest.fn().mockResolvedValue(undefined),
      beforePopState: jest.fn(),
      events: {
        on: jest.fn(),
        off: jest.fn(),
        emit: jest.fn(),
      },
      isFallback: false,
    };
  },
}));

// Mock Next.js navigation
jest.mock('next/navigation', () => ({
  useRouter() {
    return {
      push: jest.fn(),
      pop: jest.fn(),
      reload: jest.fn(),
      back: jest.fn(),
      forward: jest.fn(),
      refresh: jest.fn(),
      prefetch: jest.fn(),
    };
  },
  usePathname() {
    return '/';
  },
  useSearchParams() {
    return new URLSearchParams();
  },
}));

// Mock Next.js Image component
jest.mock('next/image', () => {
  const MockedImage = ({ src, alt, ...props }) => {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={src} alt={alt} {...props} />;
  };
  MockedImage.displayName = 'NextImage';
  return MockedImage;
});

// Mock Next.js Link component
jest.mock('next/link', () => {
  const MockedLink = ({ children, href, ...props }) => {
    return (
      <a href={href} {...props}>
        {children}
      </a>
    );
  };
  MockedLink.displayName = 'NextLink';
  return MockedLink;
});

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  disconnect() {
    /* empty */
  }
  observe() {
    /* empty */
  }
  unobserve() {
    /* empty */
  }
};

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  disconnect() {
    /* empty */
  }
  observe() {
    /* empty */
  }
  unobserve() {
    /* empty */
  }
};

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock window.scrollTo
Object.defineProperty(window, 'scrollTo', {
  writable: true,
  value: jest.fn(),
});

// Mock localStorage
Object.defineProperty(window, 'localStorage', {
  value: {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
    clear: jest.fn(),
  },
  writable: true,
});

// Mock sessionStorage
Object.defineProperty(window, 'sessionStorage', {
  value: {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
    clear: jest.fn(),
  },
  writable: true,
});

// Mock clipboard API
Object.defineProperty(navigator, 'clipboard', {
  value: {
    writeText: jest.fn().mockResolvedValue(undefined),
    readText: jest.fn().mockResolvedValue(''),
  },
  writable: true,
});

// Setup MSW if available
if (server) {
  beforeAll(() => server.listen());
  afterEach(() => server.resetHandlers());
  afterAll(() => server.close());
}

// Clean up after each test
afterEach(() => {
  // Clear all mocks
  jest.clearAllMocks();

  // Clear localStorage
  localStorage.clear();
  sessionStorage.clear();
});

// Console error handler for development
const originalError = console.error;
beforeAll(() => {
  console.error = (...args) => {
    if (
      typeof args[0] === 'string' &&
      args[0].includes('Warning: ReactDOM.render is no longer supported')
    ) {
      return;
    }
    originalError.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
});

// Global test utilities
global.testUtils = {
  createMockUser: () => ({
    id: 'user-123',
    name: 'Test User',
    email: 'test@example.com',
    role: 'customer',
    tenant: 'tenant-123',
  }),

  createMockConfig: () => ({
    locale: {
      primary: 'en-US',
      supported: ['en-US'],
      fallback: 'en-US',
    },
    currency: {
      primary: 'USD',
      symbol: '$',
      position: 'before',
    },
    branding: {
      company: {
        name: 'Test ISP',
        colors: {
          primary: '#3b82f6',
          secondary: '#64748b',
        },
      },
    },
  }),

  delay: (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
};
