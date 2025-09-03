/**
 * Global Next.js mocks for testing
 */

const React = require('react');

// Mock next/navigation
const mockRouter = {
  push: jest.fn(),
  replace: jest.fn(),
  back: jest.fn(),
  forward: jest.fn(),
  refresh: jest.fn(),
  prefetch: jest.fn(),
};

const mockParams = {};
const mockSearchParams = new URLSearchParams();

const useRouter = jest.fn(() => mockRouter);
const useParams = jest.fn(() => mockParams);
const useSearchParams = jest.fn(() => mockSearchParams);
const usePathname = jest.fn(() => '/');

// Mock next/image
const NextImage = jest.fn(({ src, alt, ...props }) => {
  // eslint-disable-next-line @next/next/no-img-element
  return React.createElement('img', { src, alt, ...props });
});

// Mock next/link
const NextLink = jest.fn(({ href, children, ...props }) => {
  return React.createElement('a', { href, ...props }, children);
});

// Reset functions for tests
const resetNextMocks = () => {
  Object.values(mockRouter).forEach((fn) => fn.mockClear());
  useRouter.mockClear();
  useParams.mockClear();
  useSearchParams.mockClear();
  usePathname.mockClear();
};

module.exports = {
  useRouter,
  useParams,
  useSearchParams,
  usePathname,
  NextImage,
  NextLink,
  resetNextMocks,
  mockRouter,
  mockParams,
  mockSearchParams,
};
