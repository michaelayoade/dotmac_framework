import { ResellerPortalAudit } from "@dotmac/headless";
import { ManagementProvider } from '@dotmac/headless/management';
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import type React from "react";

import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
	title: "DotMac Reseller Portal",
	description:
		"Partner portal for DotMac ISP resellers - manage customers, track commissions, and grow your business",
	keywords: [
		"ISP",
		"reseller portal",
		"partner program",
		"telecommunications",
		"sales",
	],
};

export default function RootLayout({
	children,
}: {
	children: React.ReactNode;
}) {
	const apiBaseUrl = process.env.NEXT_PUBLIC_ISP_API_URL || 'http://localhost:8000/api/v1';

	return (
		<html lang="en">
			<body className={inter.className}>
				<ManagementProvider
					portalType="reseller"
					apiBaseUrl={apiBaseUrl}
					enablePerformanceMonitoring={true}
					enableErrorBoundary={true}
					initialConfig={{
						enableOptimisticUpdates: true,
						enableRealTimeSync: true,
						autoRefreshInterval: 60000,
						retryFailedOperations: true
					}}
					features={{
						enableBatchOperations: false, // Simpler operations for resellers
						enableRealTimeSync: true,
						enableAdvancedAnalytics: false, // Limited analytics for resellers
						enableAuditLogging: true
					}}
				>
					{children}
				</ManagementProvider>
			</body>
		</html>
	);
}
