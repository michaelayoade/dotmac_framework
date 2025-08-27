import { type JWTPayload, jwtVerify } from "jose";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
// Simple logging utilities - can be enhanced later
const logger = {
  error: (message: string, error?: any, meta?: any) => console.error(message, error, meta)
};

const logSecurityEvent = (event: string, meta: any) => {
  console.warn(`🚨 Security Event: ${event}`, meta);
};

// CSRF Protection - simplified for now
const csrfMiddleware = {
  middleware: async (request: NextRequest) => {
    // Basic CSRF protection placeholder - can be enhanced later
    return null; // No blocking for now
  }
};

// Simple CSP utilities (can be moved to shared package later)
function generateNonce(): string {
	const array = new Uint8Array(16);
	crypto.getRandomValues(array);
	return Array.from(array, (byte) => byte.toString(16).padStart(2, "0")).join(
		"",
	);
}

function generateCSP(nonce: string, isDev: boolean = false): string {
	const devSources = isDev ? " 'unsafe-eval' 'unsafe-inline'" : "";
	return `
    default-src 'self';
    script-src 'self' 'nonce-${nonce}'${devSources};
    style-src 'self' 'nonce-${nonce}' 'unsafe-inline';
    img-src 'self' data: https:;
    connect-src 'self' https:;
    font-src 'self' https:;
    object-src 'none';
    base-uri 'self';
    form-action 'self';
    frame-ancestors 'none';
    upgrade-insecure-requests;
  `
		.replace(/\s+/g, " ")
		.trim();
}

// Public routes that don't require authentication
const publicRoutes = [
	"/",
	"/login",
	"/apply",
	"/forgot-password",
	"/reset-password",
];

interface TokenPayload extends JWTPayload {
	userId: string;
	userType: string;
	partnerId?: string;
	territory?: string;
}

async function validatePartnerToken(
	token: string,
): Promise<TokenPayload | null> {
	try {
		const jwtSecret = process.env.JWT_SECRET_KEY || process.env.NEXTAUTH_SECRET;
		if (!jwtSecret) {
			logger.error("JWT_SECRET_KEY not configured", undefined, {
				component: "middleware",
			});
			return null;
		}

		// Secure JWT validation with signature verification
		const secret = new TextEncoder().encode(jwtSecret);
		const { payload } = await jwtVerify(token, secret);

		const tokenPayload = payload as TokenPayload;

		// Validate required fields
		if (!tokenPayload.userId || !tokenPayload.userType) {
			return null;
		}

		// Validate user type for reseller portal
		if (
			tokenPayload.userType !== "partner" &&
			tokenPayload.userType !== "reseller"
		) {
			return null;
		}

		return tokenPayload;
	} catch (error) {
		// Log security-related errors for monitoring
		logSecurityEvent("JWT validation failed", {
			error: error instanceof Error ? error.message : "Unknown error",
			userAgent: "", // Would need request context
		});
		return null;
	}
}

export async function middleware(request: NextRequest) {
	const { pathname } = request.nextUrl;
	
	// Apply CSRF protection first
	const csrfResponse = await csrfMiddleware.middleware(request);
	if (csrfResponse && csrfResponse.status !== 200) {
		// Log CSRF failures for security monitoring
		logSecurityEvent("CSRF protection failed", {
			pathname,
			method: request.method,
			userAgent: request.headers.get('user-agent') || '',
			ip: request.ip || request.headers.get('x-forwarded-for') || 'unknown'
		});
		return csrfResponse;
	}

	const authToken = request.cookies.get("auth-token");
	const portalType = request.cookies.get("portal-type");

	// Check if it's a public route
	const isPublicRoute = publicRoutes.some(
		(route) => pathname === route || pathname.startsWith("/api/auth"),
	);

	// If no auth token and trying to access protected route, redirect to login
	if (!authToken && !isPublicRoute) {
		const loginUrl = new URL("/", request.url);
		loginUrl.searchParams.set("redirect", pathname);
		return NextResponse.redirect(loginUrl);
	}

	// Enhanced partner token validation
	let partnerContext: TokenPayload | null = null;
	if (authToken && !isPublicRoute) {
		partnerContext = await validatePartnerToken(authToken.value);
		if (!partnerContext) {
			// Log authentication failures
			logSecurityEvent("Partner token validation failed", {
				pathname,
				userAgent: request.headers.get('user-agent') || '',
				ip: request.ip || request.headers.get('x-forwarded-for') || 'unknown'
			});
			return NextResponse.redirect(new URL("/login", request.url));
		}

		// Verify portal type matches token
		if (portalType?.value !== "reseller") {
			logSecurityEvent("Portal type mismatch", {
				pathname,
				expectedPortal: "reseller",
				actualPortal: portalType?.value || 'none',
				userId: partnerContext.userId
			});
			return NextResponse.redirect(new URL("/unauthorized", request.url));
		}
	}

	// Generate a unique nonce for this request
	const nonce = generateNonce();

	// Clone the request headers and add nonce + partner context
	const requestHeaders = new Headers(request.headers);
	requestHeaders.set("x-nonce", nonce);

	// Add partner context for API calls
	if (partnerContext) {
		requestHeaders.set("X-Partner-ID", partnerContext.partnerId || "");
		requestHeaders.set("X-Territory", partnerContext.territory || "");
		requestHeaders.set("X-User-Type", partnerContext.userType);
	}

	// Create response with modified request
	const response = csrfResponse || NextResponse.next({
		request: {
			headers: requestHeaders,
		},
	});

	// Generate CSP with nonce
	const csp = generateCSP(nonce, process.env.NODE_ENV === "development");

	// Add security headers including CSP with nonce
	response.headers.set("Content-Security-Policy", csp);
	response.headers.set("X-Frame-Options", "DENY");
	response.headers.set("X-Content-Type-Options", "nosniff");
	response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
	response.headers.set("X-XSS-Protection", "1; mode=block");
	
	// Only set HSTS in production
	if (process.env.NODE_ENV === "production") {
		response.headers.set(
			"Strict-Transport-Security",
			"max-age=31536000; includeSubDomains; preload",
		);
	}
	
	response.headers.set(
		"Permissions-Policy",
		"camera=(), microphone=(), geolocation=(), payment=()",
	);

	// Add CSRF token to response headers for client access
	if (csrfResponse?.headers.get('x-csrf-token-generated')) {
		response.headers.set('x-csrf-token', csrfResponse.headers.get('x-csrf-token-generated') || '');
	}

	return response;
}

export const config = {
	matcher: [
		/*
		 * Match all request paths except for the ones starting with:
		 * - _next/static (static files)
		 * - _next/image (image optimization files)
		 * - favicon.ico (favicon file)
		 * - public folder
		 */
		"/((?!_next/static|_next/image|favicon.ico|public).*)",
	],
};