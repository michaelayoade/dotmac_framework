import { NextResponse } from "next/server";

/**
 * Health check endpoint for Kubernetes probes and monitoring
 */
export async function GET() {
	try {
		const health = {
			status: "ok",
			timestamp: new Date().toISOString(),
			service: "reseller-portal",
			version: process.env.npm_package_version || "1.0.0",
			uptime: process.uptime(),
			memory: process.memoryUsage(),
			environment: process.env.NODE_ENV || "development",
		};

		return NextResponse.json(health, { status: 200 });
	} catch (error) {
		return NextResponse.json(
			{
				status: "error",
				timestamp: new Date().toISOString(),
				service: "reseller-portal",
				error: error instanceof Error ? error.message : "Unknown error",
			},
			{ status: 503 },
		);
	}
}
