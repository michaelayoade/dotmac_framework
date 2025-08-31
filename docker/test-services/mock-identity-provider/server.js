/**
 * Mock Identity Provider for SSO E2E Testing
 * Provides OIDC and SAML endpoints for testing authentication flows
 */

const express = require('express');
const cors = require('cors');
const crypto = require('crypto');
const { URLSearchParams } = require('url');

class MockIdentityProvider {
  constructor() {
    this.app = express();
    this.port = process.env.PORT || 8040;
    
    // In-memory storage for test data
    this.authCodes = new Map(); // code -> user data
    this.accessTokens = new Map(); // token -> user data
    this.refreshTokens = new Map(); // refresh -> user data
    this.users = new Map(); // user id -> user data
    
    this.setupMiddleware();
    this.setupRoutes();
    this.initializeTestUsers();
  }

  setupMiddleware() {
    this.app.use(cors());
    this.app.use(express.json());
    this.app.use(express.urlencoded({ extended: true }));
    this.app.use(express.static('public'));
    
    // Request logging
    this.app.use((req, res, next) => {
      console.log(`${new Date().toISOString()} ${req.method} ${req.url}`);
      next();
    });
  }

  setupRoutes() {
    // OIDC Discovery endpoint
    this.app.get('/.well-known/openid_configuration', (req, res) => {
      const baseUrl = `${req.protocol}://${req.get('host')}`;
      
      res.json({
        issuer: baseUrl,
        authorization_endpoint: `${baseUrl}/oauth2/authorize`,
        token_endpoint: `${baseUrl}/oauth2/token`,
        userinfo_endpoint: `${baseUrl}/oauth2/userinfo`,
        jwks_uri: `${baseUrl}/.well-known/jwks.json`,
        end_session_endpoint: `${baseUrl}/oauth2/logout`,
        response_types_supported: ['code'],
        subject_types_supported: ['public'],
        id_token_signing_alg_values_supported: ['RS256'],
        scopes_supported: ['openid', 'email', 'profile', 'groups'],
        token_endpoint_auth_methods_supported: ['client_secret_basic', 'client_secret_post'],
        claims_supported: ['sub', 'email', 'given_name', 'family_name', 'name', 'groups']
      });
    });

    // OIDC Authorization endpoint
    this.app.get('/oauth2/authorize', (req, res) => {
      const {
        client_id,
        redirect_uri,
        response_type,
        scope,
        state,
        code_challenge,
        code_challenge_method
      } = req.query;

      // Validate required parameters
      if (!client_id || !redirect_uri || response_type !== 'code') {
        return res.status(400).json({
          error: 'invalid_request',
          error_description: 'Missing or invalid required parameters'
        });
      }

      // Show authorization page
      res.send(this.generateAuthorizationPage({
        client_id,
        redirect_uri,
        scope,
        state,
        code_challenge,
        code_challenge_method
      }));
    });

    // Handle authorization decision
    this.app.post('/oauth2/authorize/decision', (req, res) => {
      const { approve, client_id, redirect_uri, state, user_id } = req.body;
      
      if (approve === 'true') {
        // Generate authorization code
        const code = crypto.randomBytes(32).toString('hex');
        const user = this.users.get(user_id) || this.users.get('default-user');
        
        // Store auth code with expiration
        this.authCodes.set(code, {
          user,
          client_id,
          redirect_uri,
          expires_at: Date.now() + 600000, // 10 minutes
          scope: 'openid email profile'
        });

        // Redirect back to application
        const redirectUrl = new URL(redirect_uri);
        redirectUrl.searchParams.set('code', code);
        if (state) redirectUrl.searchParams.set('state', state);
        
        return res.redirect(redirectUrl.toString());
      } else {
        // User denied authorization
        const redirectUrl = new URL(redirect_uri);
        redirectUrl.searchParams.set('error', 'access_denied');
        if (state) redirectUrl.searchParams.set('state', state);
        
        return res.redirect(redirectUrl.toString());
      }
    });

    // OIDC Token endpoint
    this.app.post('/oauth2/token', (req, res) => {
      const {
        grant_type,
        code,
        redirect_uri,
        client_id,
        client_secret,
        refresh_token
      } = req.body;

      if (grant_type === 'authorization_code') {
        const authData = this.authCodes.get(code);
        
        if (!authData || authData.expires_at < Date.now()) {
          return res.status(400).json({
            error: 'invalid_grant',
            error_description: 'Invalid or expired authorization code'
          });
        }

        if (authData.client_id !== client_id || authData.redirect_uri !== redirect_uri) {
          return res.status(400).json({
            error: 'invalid_grant',
            error_description: 'Client ID or redirect URI mismatch'
          });
        }

        // Generate tokens
        const accessToken = crypto.randomBytes(32).toString('hex');
        const refreshToken = crypto.randomBytes(32).toString('hex');
        const idToken = this.generateIdToken(authData.user);

        // Store tokens
        this.accessTokens.set(accessToken, {
          user: authData.user,
          client_id,
          scope: authData.scope,
          expires_at: Date.now() + 3600000 // 1 hour
        });

        this.refreshTokens.set(refreshToken, {
          user: authData.user,
          client_id,
          expires_at: Date.now() + 86400000 // 24 hours
        });

        // Clean up auth code
        this.authCodes.delete(code);

        res.json({
          access_token: accessToken,
          token_type: 'Bearer',
          expires_in: 3600,
          refresh_token: refreshToken,
          id_token: idToken,
          scope: authData.scope
        });

      } else if (grant_type === 'refresh_token') {
        const refreshData = this.refreshTokens.get(refresh_token);
        
        if (!refreshData || refreshData.expires_at < Date.now()) {
          return res.status(400).json({
            error: 'invalid_grant',
            error_description: 'Invalid or expired refresh token'
          });
        }

        // Generate new access token
        const accessToken = crypto.randomBytes(32).toString('hex');
        const idToken = this.generateIdToken(refreshData.user);

        this.accessTokens.set(accessToken, {
          user: refreshData.user,
          client_id: refreshData.client_id,
          scope: 'openid email profile',
          expires_at: Date.now() + 3600000
        });

        res.json({
          access_token: accessToken,
          token_type: 'Bearer',
          expires_in: 3600,
          id_token: idToken,
          scope: 'openid email profile'
        });

      } else {
        res.status(400).json({
          error: 'unsupported_grant_type',
          error_description: 'Grant type not supported'
        });
      }
    });

    // OIDC UserInfo endpoint
    this.app.get('/oauth2/userinfo', (req, res) => {
      const authHeader = req.headers.authorization;
      
      if (!authHeader || !authHeader.startsWith('Bearer ')) {
        return res.status(401).json({ error: 'invalid_token' });
      }

      const token = authHeader.substring(7);
      const tokenData = this.accessTokens.get(token);

      if (!tokenData || tokenData.expires_at < Date.now()) {
        return res.status(401).json({ error: 'invalid_token' });
      }

      const user = tokenData.user;
      res.json({
        sub: user.id,
        email: user.email,
        email_verified: true,
        given_name: user.firstName,
        family_name: user.lastName,
        name: user.displayName,
        groups: user.groups || [],
        roles: user.roles || []
      });
    });

    // OIDC End Session (Logout) endpoint
    this.app.get('/oauth2/logout', (req, res) => {
      const { post_logout_redirect_uri, id_token_hint } = req.query;
      
      // In a real implementation, we would validate the id_token_hint
      // For testing, just redirect to the post logout URI
      if (post_logout_redirect_uri) {
        res.redirect(post_logout_redirect_uri);
      } else {
        res.send('<h1>Logged out successfully</h1><p>You have been logged out of the identity provider.</p>');
      }
    });

    // JWKS endpoint
    this.app.get('/.well-known/jwks.json', (req, res) => {
      res.json({
        keys: [
          {
            kty: 'RSA',
            use: 'sig',
            kid: 'mock-key-2024',
            alg: 'RS256',
            n: 'mock-rsa-modulus-for-testing-purposes-only',
            e: 'AQAB'
          }
        ]
      });
    });

    // SAML SSO endpoint
    this.app.post('/saml/sso', (req, res) => {
      // In a real SAML implementation, we would parse the SAML request
      // For testing, we'll generate a mock SAML response
      const samlResponse = this.generateSAMLResponse();
      
      res.send(`
        <!DOCTYPE html>
        <html>
          <head><title>SAML Response</title></head>
          <body onload="document.forms[0].submit()">
            <form method="post" action="${req.body.RelayState || '/auth/saml/acs'}">
              <input type="hidden" name="SAMLResponse" value="${Buffer.from(samlResponse).toString('base64')}" />
              <input type="hidden" name="RelayState" value="${req.body.RelayState || ''}" />
              <noscript>
                <p>JavaScript is disabled. Click the button below to continue.</p>
                <input type="submit" value="Continue" />
              </noscript>
            </form>
          </body>
        </html>
      `);
    });

    // SAML SLO endpoint
    this.app.get('/saml/slo', (req, res) => {
      // Mock SAML Single Logout
      res.redirect('/auth/login?logged_out=true');
    });

    // Health check
    this.app.get('/health', (req, res) => {
      res.json({
        status: 'healthy',
        service: 'mock-identity-provider',
        version: '1.0.0',
        timestamp: new Date().toISOString(),
        stats: {
          active_auth_codes: this.authCodes.size,
          active_access_tokens: this.accessTokens.size,
          active_refresh_tokens: this.refreshTokens.size,
          registered_users: this.users.size
        }
      });
    });

    // Admin endpoints for test control
    this.app.post('/admin/users', (req, res) => {
      const user = req.body;
      this.users.set(user.id, user);
      res.json({ message: 'User created', user_id: user.id });
    });

    this.app.delete('/admin/users/:id', (req, res) => {
      const deleted = this.users.delete(req.params.id);
      res.json({ message: deleted ? 'User deleted' : 'User not found' });
    });

    this.app.post('/admin/reset', (req, res) => {
      // Clear all tokens and codes for testing
      this.authCodes.clear();
      this.accessTokens.clear();
      this.refreshTokens.clear();
      res.json({ message: 'All tokens cleared' });
    });
  }

  generateAuthorizationPage(params) {
    return `
      <!DOCTYPE html>
      <html>
        <head>
          <title>Mock Identity Provider - Authorize Application</title>
          <style>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
            .auth-form { border: 1px solid #ddd; padding: 20px; border-radius: 8px; }
            .user-select { margin: 20px 0; }
            .user-option { margin: 10px 0; padding: 10px; border: 1px solid #eee; border-radius: 4px; }
            .user-option input { margin-right: 10px; }
            .actions { margin-top: 20px; text-align: center; }
            .btn { padding: 10px 20px; margin: 0 10px; border: none; border-radius: 4px; cursor: pointer; }
            .btn-primary { background: #007bff; color: white; }
            .btn-secondary { background: #6c757d; color: white; }
          </style>
        </head>
        <body>
          <div class="auth-form">
            <h2>🔐 Mock Identity Provider</h2>
            <p><strong>Application:</strong> ${params.client_id}</p>
            <p><strong>Requested Scopes:</strong> ${params.scope || 'openid email profile'}</p>
            <p>Do you want to grant access to this application?</p>
            
            <form method="post" action="/oauth2/authorize/decision">
              <input type="hidden" name="client_id" value="${params.client_id}" />
              <input type="hidden" name="redirect_uri" value="${params.redirect_uri}" />
              <input type="hidden" name="state" value="${params.state || ''}" />
              
              <div class="user-select">
                <h3>Select User to Authenticate:</h3>
                ${this.generateUserOptions()}
              </div>
              
              <div class="actions">
                <button type="submit" name="approve" value="true" class="btn btn-primary" id="authorize">
                  ✅ Authorize
                </button>
                <button type="submit" name="approve" value="false" class="btn btn-secondary" id="deny">
                  ❌ Deny
                </button>
              </div>
            </form>
          </div>
        </body>
      </html>
    `;
  }

  generateUserOptions() {
    let options = '';
    for (const [id, user] of this.users) {
      options += `
        <div class="user-option">
          <label>
            <input type="radio" name="user_id" value="${id}" ${id === 'default-user' ? 'checked' : ''} />
            <strong>${user.displayName}</strong> (${user.email})
            <br />
            <small>Roles: ${(user.roles || []).join(', ')} | Groups: ${(user.groups || []).join(', ')}</small>
          </label>
        </div>
      `;
    }
    return options;
  }

  generateIdToken(user) {
    const header = {
      alg: 'RS256',
      typ: 'JWT',
      kid: 'mock-key-2024'
    };

    const payload = {
      iss: `http://localhost:${this.port}`,
      sub: user.id,
      aud: 'mock-client-id',
      exp: Math.floor(Date.now() / 1000) + 3600,
      iat: Math.floor(Date.now() / 1000),
      auth_time: Math.floor(Date.now() / 1000),
      email: user.email,
      email_verified: true,
      given_name: user.firstName,
      family_name: user.lastName,
      name: user.displayName,
      groups: user.groups || [],
      roles: user.roles || []
    };

    // Mock JWT (not actually signed for testing)
    const encodedHeader = Buffer.from(JSON.stringify(header)).toString('base64url');
    const encodedPayload = Buffer.from(JSON.stringify(payload)).toString('base64url');
    const signature = 'mock_signature_for_testing_only';

    return `${encodedHeader}.${encodedPayload}.${signature}`;
  }

  generateSAMLResponse() {
    const now = new Date().toISOString();
    const notAfter = new Date(Date.now() + 3600000).toISOString(); // 1 hour
    const defaultUser = this.users.get('default-user');

    return `<?xml version="1.0" encoding="UTF-8"?>
      <saml2p:Response xmlns:saml2p="urn:oasis:names:tc:SAML:2.0:protocol"
                      xmlns:saml2="urn:oasis:names:tc:SAML:2.0:assertion"
                      Destination="/auth/saml/acs"
                      ID="mock_response_${Date.now()}"
                      InResponseTo="mock_request_id"
                      IssueInstant="${now}"
                      Version="2.0">
        <saml2:Issuer>http://localhost:${this.port}</saml2:Issuer>
        <saml2p:Status>
          <saml2p:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/>
        </saml2p:Status>
        <saml2:Assertion ID="mock_assertion_${Date.now()}"
                        IssueInstant="${now}"
                        Version="2.0">
          <saml2:Issuer>http://localhost:${this.port}</saml2:Issuer>
          <saml2:Subject>
            <saml2:NameID Format="urn:oasis:names:tc:SAML:2.0:nameid-format:email">${defaultUser.email}</saml2:NameID>
            <saml2:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
              <saml2:SubjectConfirmationData NotOnOrAfter="${notAfter}"
                                           Recipient="/auth/saml/acs"/>
            </saml2:SubjectConfirmation>
          </saml2:Subject>
          <saml2:Conditions NotBefore="${now}" NotOnOrAfter="${notAfter}">
            <saml2:AudienceRestriction>
              <saml2:Audience>mock-service-provider</saml2:Audience>
            </saml2:AudienceRestriction>
          </saml2:Conditions>
          <saml2:AttributeStatement>
            <saml2:Attribute Name="email">
              <saml2:AttributeValue>${defaultUser.email}</saml2:AttributeValue>
            </saml2:Attribute>
            <saml2:Attribute Name="firstName">
              <saml2:AttributeValue>${defaultUser.firstName}</saml2:AttributeValue>
            </saml2:Attribute>
            <saml2:Attribute Name="lastName">
              <saml2:AttributeValue>${defaultUser.lastName}</saml2:AttributeValue>
            </saml2:Attribute>
            <saml2:Attribute Name="displayName">
              <saml2:AttributeValue>${defaultUser.displayName}</saml2:AttributeValue>
            </saml2:Attribute>
            <saml2:Attribute Name="groups">
              ${(defaultUser.groups || []).map(group => `<saml2:AttributeValue>${group}</saml2:AttributeValue>`).join('')}
            </saml2:Attribute>
            <saml2:Attribute Name="roles">
              ${(defaultUser.roles || []).map(role => `<saml2:AttributeValue>${role}</saml2:AttributeValue>`).join('')}
            </saml2:Attribute>
          </saml2:AttributeStatement>
          <saml2:AuthnStatement AuthnInstant="${now}">
            <saml2:AuthnContext>
              <saml2:AuthnContextClassRef>urn:oasis:names:tc:SAML:2.0:ac:classes:Password</saml2:AuthnContextClassRef>
            </saml2:AuthnContext>
          </saml2:AuthnStatement>
        </saml2:Assertion>
      </saml2p:Response>
    `;
  }

  initializeTestUsers() {
    // Create default test users for each portal role
    const testUsers = [
      {
        id: 'admin-123',
        email: 'admin@dotmac.local',
        firstName: 'Admin',
        lastName: 'User',
        displayName: 'Admin User',
        groups: ['admins', 'users'],
        roles: ['admin', 'user']
      },
      {
        id: 'customer-456',
        email: 'customer@dotmac.local',
        firstName: 'Customer',
        lastName: 'User',
        displayName: 'Customer User',
        groups: ['customers', 'users'],
        roles: ['customer']
      },
      {
        id: 'tech-789',
        email: 'technician@dotmac.local',
        firstName: 'Tech',
        lastName: 'User',
        displayName: 'Tech User',
        groups: ['technicians', 'users'],
        roles: ['technician']
      },
      {
        id: 'reseller-101',
        email: 'reseller@dotmac.local',
        firstName: 'Reseller',
        lastName: 'User',
        displayName: 'Reseller User',
        groups: ['resellers', 'users'],
        roles: ['reseller']
      }
    ];

    testUsers.forEach(user => {
      this.users.set(user.id, user);
    });

    // Set default user
    this.users.set('default-user', testUsers[0]);

    console.log(`Initialized ${testUsers.length} test users`);
  }

  start() {
    this.app.listen(this.port, () => {
      console.log(`🔐 Mock Identity Provider running on port ${this.port}`);
      console.log(`📋 OIDC Discovery: http://localhost:${this.port}/.well-known/openid_configuration`);
      console.log(`🏥 Health Check: http://localhost:${this.port}/health`);
      console.log(`👤 Test Users: ${this.users.size} users loaded`);
    });

    // Clean up expired tokens every minute
    setInterval(() => {
      this.cleanupExpiredTokens();
    }, 60000);
  }

  cleanupExpiredTokens() {
    const now = Date.now();
    let cleaned = 0;

    // Clean up expired auth codes
    for (const [code, data] of this.authCodes) {
      if (data.expires_at < now) {
        this.authCodes.delete(code);
        cleaned++;
      }
    }

    // Clean up expired access tokens
    for (const [token, data] of this.accessTokens) {
      if (data.expires_at < now) {
        this.accessTokens.delete(token);
        cleaned++;
      }
    }

    // Clean up expired refresh tokens
    for (const [token, data] of this.refreshTokens) {
      if (data.expires_at < now) {
        this.refreshTokens.delete(token);
        cleaned++;
      }
    }

    if (cleaned > 0) {
      console.log(`🧹 Cleaned up ${cleaned} expired tokens`);
    }
  }
}

// Start the mock identity provider
const mockIdP = new MockIdentityProvider();
mockIdP.start();