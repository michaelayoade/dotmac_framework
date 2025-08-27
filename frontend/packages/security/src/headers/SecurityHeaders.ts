/**
 * Production Security Headers Configuration
 * Implements OWASP security headers best practices for ISP customer portals
 */

export interface SecurityHeadersConfig {
  // Content Security Policy
  csp?: {
    enabled: boolean;
    directives: CSPDirectives;
    reportUri?: string;
    reportOnly?: boolean;
  };
  
  // HTTP Strict Transport Security
  hsts?: {
    enabled: boolean;
    maxAge: number;
    includeSubDomains: boolean;
    preload: boolean;
  };
  
  // X-Frame-Options
  frameOptions?: {
    enabled: boolean;
    policy: 'DENY' | 'SAMEORIGIN' | 'ALLOW-FROM';
    allowFrom?: string;
  };
  
  // X-Content-Type-Options
  contentTypeOptions?: {
    enabled: boolean;
    noSniff: boolean;
  };
  
  // Referrer Policy
  referrerPolicy?: {
    enabled: boolean;
    policy: ReferrerPolicyValue;
  };
  
  // Permissions Policy (formerly Feature Policy)
  permissionsPolicy?: {
    enabled: boolean;
    directives: PermissionsPolicyDirectives;
  };
  
  // Cross-Origin policies
  crossOrigin?: {
    embedderPolicy: 'unsafe-none' | 'require-corp';
    openerPolicy: 'same-origin' | 'same-origin-allow-popups' | 'unsafe-none';
    resourcePolicy: 'same-site' | 'same-origin' | 'cross-origin';
  };
  
  // Custom headers
  customHeaders?: Record<string, string>;
}

interface CSPDirectives {
  'default-src'?: string[];
  'script-src'?: string[];
  'style-src'?: string[];
  'img-src'?: string[];
  'font-src'?: string[];
  'connect-src'?: string[];
  'media-src'?: string[];
  'object-src'?: string[];
  'child-src'?: string[];
  'frame-src'?: string[];
  'worker-src'?: string[];
  'manifest-src'?: string[];
  'prefetch-src'?: string[];
  'form-action'?: string[];
  'frame-ancestors'?: string[];
  'base-uri'?: string[];
  'upgrade-insecure-requests'?: boolean;
  'block-all-mixed-content'?: boolean;
  'require-trusted-types-for'?: string[];
  'trusted-types'?: string[];
}

interface PermissionsPolicyDirectives {
  camera?: string[];
  microphone?: string[];
  geolocation?: string[];
  gyroscope?: string[];
  magnetometer?: string[];
  payment?: string[];
  usb?: string[];
  fullscreen?: string[];
  'picture-in-picture'?: string[];
  'accelerometer'?: string[];
  'ambient-light-sensor'?: string[];
  'autoplay'?: string[];
  'battery'?: string[];
  'clipboard-read'?: string[];
  'clipboard-write'?: string[];
  'display-capture'?: string[];
  'document-domain'?: string[];
  'encrypted-media'?: string[];
  'execution-while-not-rendered'?: string[];
  'execution-while-out-of-viewport'?: string[];
  'gamepad'?: string[];
  'hid'?: string[];
  'idle-detection'?: string[];
  'local-fonts'?: string[];
  'midi'?: string[];
  'navigation-override'?: string[];
  'otp-credentials'?: string[];
  'publickey-credentials-get'?: string[];
  'screen-wake-lock'?: string[];
  'serial'?: string[];
  'speaker-selection'?: string[];
  'sync-xhr'?: string[];
  'web-share'?: string[];
  'xr-spatial-tracking'?: string[];
}

type ReferrerPolicyValue = 
  | 'no-referrer'
  | 'no-referrer-when-downgrade'
  | 'origin'
  | 'origin-when-cross-origin'
  | 'same-origin'
  | 'strict-origin'
  | 'strict-origin-when-cross-origin'
  | 'unsafe-url';

/**
 * Generate security headers for production ISP portal
 */
export class SecurityHeadersGenerator {
  private config: SecurityHeadersConfig;
  private environment: 'development' | 'staging' | 'production';

  constructor(config: SecurityHeadersConfig, environment: 'development' | 'staging' | 'production' = 'production') {
    this.config = config;
    this.environment = environment;
  }

  /**
   * Generate all security headers as key-value pairs
   */
  generateHeaders(): Record<string, string> {
    const headers: Record<string, string> = {};

    // Content Security Policy
    if (this.config.csp?.enabled) {
      const cspValue = this.generateCSP();
      headers[this.config.csp.reportOnly ? 'Content-Security-Policy-Report-Only' : 'Content-Security-Policy'] = cspValue;
    }

    // HTTP Strict Transport Security
    if (this.config.hsts?.enabled) {
      headers['Strict-Transport-Security'] = this.generateHSTS();
    }

    // X-Frame-Options
    if (this.config.frameOptions?.enabled) {
      headers['X-Frame-Options'] = this.generateFrameOptions();
    }

    // X-Content-Type-Options
    if (this.config.contentTypeOptions?.enabled) {
      headers['X-Content-Type-Options'] = 'nosniff';
    }

    // Referrer Policy
    if (this.config.referrerPolicy?.enabled) {
      headers['Referrer-Policy'] = this.config.referrerPolicy.policy;
    }

    // Permissions Policy
    if (this.config.permissionsPolicy?.enabled) {
      headers['Permissions-Policy'] = this.generatePermissionsPolicy();
    }

    // Cross-Origin policies
    if (this.config.crossOrigin) {
      headers['Cross-Origin-Embedder-Policy'] = this.config.crossOrigin.embedderPolicy;
      headers['Cross-Origin-Opener-Policy'] = this.config.crossOrigin.openerPolicy;
      headers['Cross-Origin-Resource-Policy'] = this.config.crossOrigin.resourcePolicy;
    }

    // X-XSS-Protection (legacy but still useful for older browsers)
    headers['X-XSS-Protection'] = '1; mode=block';

    // X-Permitted-Cross-Domain-Policies
    headers['X-Permitted-Cross-Domain-Policies'] = 'none';

    // Server information hiding
    headers['Server'] = 'DotMac-Portal';

    // Custom headers
    if (this.config.customHeaders) {
      Object.assign(headers, this.config.customHeaders);
    }

    return headers;
  }

  /**
   * Generate Content Security Policy header value
   */
  private generateCSP(): string {
    const directives: string[] = [];
    
    for (const [directive, value] of Object.entries(this.config.csp!.directives)) {
      if (typeof value === 'boolean' && value) {
        directives.push(directive);
      } else if (Array.isArray(value) && value.length > 0) {
        directives.push(`${directive} ${value.join(' ')}`);
      }
    }

    return directives.join('; ');
  }

  /**
   * Generate HSTS header value
   */
  private generateHSTS(): string {
    const hsts = this.config.hsts!;
    let value = `max-age=${hsts.maxAge}`;
    
    if (hsts.includeSubDomains) {
      value += '; includeSubDomains';
    }
    
    if (hsts.preload) {
      value += '; preload';
    }
    
    return value;
  }

  /**
   * Generate X-Frame-Options header value
   */
  private generateFrameOptions(): string {
    const frameOptions = this.config.frameOptions!;
    
    if (frameOptions.policy === 'ALLOW-FROM' && frameOptions.allowFrom) {
      return `ALLOW-FROM ${frameOptions.allowFrom}`;
    }
    
    return frameOptions.policy;
  }

  /**
   * Generate Permissions Policy header value
   */
  private generatePermissionsPolicy(): string {
    const policies: string[] = [];
    
    for (const [directive, allowList] of Object.entries(this.config.permissionsPolicy!.directives)) {
      if (Array.isArray(allowList)) {
        if (allowList.length === 0 || allowList.includes('none')) {
          policies.push(`${directive}=()`);
        } else {
          const formattedList = allowList.map(origin => origin === 'self' ? 'self' : `"${origin}"`).join(' ');
          policies.push(`${directive}=(${formattedList})`);
        }
      }
    }
    
    return policies.join(', ');
  }

  /**
   * Validate current headers against security best practices
   */
  validateHeaders(headers: Record<string, string>): SecurityValidationResult {
    const issues: SecurityIssue[] = [];
    const recommendations: string[] = [];

    // Check for required headers
    if (!headers['Content-Security-Policy'] && !headers['Content-Security-Policy-Report-Only']) {
      issues.push({
        severity: 'high',
        type: 'missing-header',
        message: 'Content-Security-Policy header is missing',
        recommendation: 'Implement CSP to prevent XSS attacks',
      });
    }

    if (!headers['Strict-Transport-Security'] && this.environment === 'production') {
      issues.push({
        severity: 'high',
        type: 'missing-header',
        message: 'HSTS header is missing in production',
        recommendation: 'Enable HSTS to prevent protocol downgrade attacks',
      });
    }

    if (!headers['X-Frame-Options'] && !headers['Content-Security-Policy']?.includes('frame-ancestors')) {
      issues.push({
        severity: 'medium',
        type: 'missing-header',
        message: 'No clickjacking protection found',
        recommendation: 'Add X-Frame-Options or CSP frame-ancestors directive',
      });
    }

    if (!headers['X-Content-Type-Options']) {
      issues.push({
        severity: 'medium',
        type: 'missing-header',
        message: 'X-Content-Type-Options header is missing',
        recommendation: 'Add "nosniff" to prevent MIME type confusion attacks',
      });
    }

    // Check for weak configurations
    if (headers['Content-Security-Policy']?.includes("'unsafe-inline'")) {
      issues.push({
        severity: 'medium',
        type: 'weak-config',
        message: "CSP contains 'unsafe-inline' directive",
        recommendation: 'Use nonces or hashes instead of unsafe-inline',
      });
    }

    if (headers['Content-Security-Policy']?.includes("'unsafe-eval'")) {
      issues.push({
        severity: 'high',
        type: 'weak-config',
        message: "CSP contains 'unsafe-eval' directive",
        recommendation: 'Remove unsafe-eval and use safer alternatives',
      });
    }

    // Calculate overall score
    const totalChecks = 10;
    const passedChecks = totalChecks - issues.length;
    const score = Math.round((passedChecks / totalChecks) * 100);

    return {
      score,
      issues,
      recommendations,
      summary: {
        total: totalChecks,
        passed: passedChecks,
        failed: issues.length,
        criticalIssues: issues.filter(i => i.severity === 'high').length,
      },
    };
  }
}

interface SecurityIssue {
  severity: 'low' | 'medium' | 'high';
  type: 'missing-header' | 'weak-config' | 'deprecated-header';
  message: string;
  recommendation: string;
}

interface SecurityValidationResult {
  score: number;
  issues: SecurityIssue[];
  recommendations: string[];
  summary: {
    total: number;
    passed: number;
    failed: number;
    criticalIssues: number;
  };
}

/**
 * Pre-configured security headers for ISP customer portals
 */
export const ISP_PORTAL_SECURITY_CONFIG: SecurityHeadersConfig = {
  csp: {
    enabled: true,
    reportOnly: false,
    reportUri: '/api/security/csp-report',
    directives: {
      'default-src': ["'self'"],
      'script-src': [
        "'self'",
        "'strict-dynamic'",
        "https://www.google-analytics.com",
        "https://www.googletagmanager.com",
      ],
      'style-src': [
        "'self'",
        "'unsafe-inline'", // Required for CSS-in-JS libraries
        "https://fonts.googleapis.com",
      ],
      'img-src': [
        "'self'",
        "data:",
        "https:",
        "blob:",
      ],
      'font-src': [
        "'self'",
        "https://fonts.gstatic.com",
      ],
      'connect-src': [
        "'self'",
        "https://api.dotmac.com",
        "https://monitoring.dotmac.com",
        "wss://realtime.dotmac.com",
      ],
      'media-src': ["'self'"],
      'object-src': ["'none'"],
      'frame-src': ["'self'", "https://www.youtube.com"],
      'worker-src': ["'self'"],
      'manifest-src': ["'self'"],
      'form-action': ["'self'"],
      'frame-ancestors': ["'none'"],
      'base-uri': ["'self'"],
      'upgrade-insecure-requests': true,
      'block-all-mixed-content': true,
    },
  },
  hsts: {
    enabled: true,
    maxAge: 31536000, // 1 year
    includeSubDomains: true,
    preload: true,
  },
  frameOptions: {
    enabled: true,
    policy: 'DENY',
  },
  contentTypeOptions: {
    enabled: true,
    noSniff: true,
  },
  referrerPolicy: {
    enabled: true,
    policy: 'strict-origin-when-cross-origin',
  },
  permissionsPolicy: {
    enabled: true,
    directives: {
      camera: ['none'],
      microphone: ['none'],
      geolocation: ['self'],
      gyroscope: ['none'],
      magnetometer: ['none'],
      payment: ['self'],
      usb: ['none'],
      fullscreen: ['self'],
      'picture-in-picture': ['none'],
      accelerometer: ['none'],
      'ambient-light-sensor': ['none'],
      autoplay: ['none'],
      battery: ['none'],
      'clipboard-read': ['none'],
      'clipboard-write': ['self'],
      'display-capture': ['none'],
      'document-domain': ['none'],
      'encrypted-media': ['none'],
      gamepad: ['none'],
      hid: ['none'],
      'idle-detection': ['none'],
      'local-fonts': ['self'],
      midi: ['none'],
      'otp-credentials': ['self'],
      'publickey-credentials-get': ['self'],
      'screen-wake-lock': ['none'],
      serial: ['none'],
      'speaker-selection': ['none'],
      'sync-xhr': ['none'],
      'web-share': ['self'],
      'xr-spatial-tracking': ['none'],
    },
  },
  crossOrigin: {
    embedderPolicy: 'require-corp',
    openerPolicy: 'same-origin',
    resourcePolicy: 'same-origin',
  },
  customHeaders: {
    'X-Portal-Version': '2.0',
    'X-Security-Policy': 'https://dotmac.com/security-policy',
  },
};

/**
 * Development-friendly configuration with relaxed policies
 */
export const DEVELOPMENT_SECURITY_CONFIG: SecurityHeadersConfig = {
  ...ISP_PORTAL_SECURITY_CONFIG,
  csp: {
    ...ISP_PORTAL_SECURITY_CONFIG.csp!,
    reportOnly: true,
    directives: {
      ...ISP_PORTAL_SECURITY_CONFIG.csp!.directives,
      'script-src': [
        "'self'",
        "'unsafe-eval'", // Allow for development tools
        "'unsafe-inline'", // Allow for HMR
        "http://localhost:*",
        "ws://localhost:*",
      ],
      'connect-src': [
        "'self'",
        "http://localhost:*",
        "ws://localhost:*",
        "wss://localhost:*",
      ],
    },
  },
  hsts: {
    ...ISP_PORTAL_SECURITY_CONFIG.hsts!,
    enabled: false, // Disable for HTTP development
  },
};

export type { SecurityValidationResult, SecurityIssue };