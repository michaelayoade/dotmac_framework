/**
 * Refactored Customer Dashboard - Using composed sections for better maintainability
 */
"use client";

import { AlertCircle, Lightbulb, RefreshCw } from "lucide-react";
import React, { useEffect, useState } from "react";
import {
	customerAPI,
	useCustomerDashboardData,
} from "../../lib/api/customerApi";
import { useSecureAuth } from "../auth/SecureAuthProvider";
import { CustomerLayout } from "../layout/CustomerLayout";
// Import UI components
import { LinearProgress } from "../ui/ProgressIndicator";
import { NotificationsSection } from "./sections/NotificationsSection";
import { QuickActionsSection } from "./sections/QuickActionsSection";
// Import composed sections
import { ServiceOverviewSection } from "./sections/ServiceOverviewSection";
import { UsageChartsSection } from "./sections/UsageChartsSection";

interface CustomerDashboardProps {
	data?: any; // Override data from props if provided
}

export function CustomerDashboardRefactored({
	data: propData,
}: CustomerDashboardProps) {
	const { user, isAuthenticated } = useSecureAuth();
	const [serviceNotifications, setServiceNotifications] = useState<any>(null);
	const [usageInsights, setUsageInsights] = useState<any>(null);
	const [error, setError] = useState<string | null>(null);
	const [isRefreshing, setIsRefreshing] = useState(false);
	const [speedTestRunning, setSpeedTestRunning] = useState(false);
	const [equipmentRestarting, setEquipmentRestarting] = useState(false);

	// Use secure API for data fetching
	const {
		data: dashboardData,
		isLoading,
		error: apiError,
		isUsingMockData,
		refetch,
	} = useCustomerDashboardData();

	// Use prop data if provided, otherwise fall back to API data
	const customerData = propData || dashboardData;

	// Load intelligence data using secure API
	useEffect(() => {
		if (isAuthenticated && customerData?.account?.id) {
			fetchServiceIntelligence();
		}
	}, [customerData, isAuthenticated]);

	const fetchServiceIntelligence = async () => {
		try {
			const [notifications, insights] = await Promise.all([
				customerAPI.getServiceNotifications(),
				customerAPI.getUsageInsights(),
			]);

			setServiceNotifications(notifications);
			setUsageInsights(insights);
		} catch (error) {
			console.error("Failed to fetch service intelligence:", error);
			setError("Failed to load service insights");
		}
	};

	const handleRefreshStatus = async () => {
		setIsRefreshing(true);
		try {
			await refetch();
			await fetchServiceIntelligence();
		} catch (error) {
			console.error("Failed to refresh data:", error);
		} finally {
			setIsRefreshing(false);
		}
	};

	const handleRunSpeedTest = async () => {
		setSpeedTestRunning(true);
		try {
			// Simulate speed test
			await new Promise((resolve) => setTimeout(resolve, 15000));
			// In a real implementation, this would call an API to run the speed test
			console.log("Speed test completed");
		} catch (error) {
			console.error("Speed test failed:", error);
		} finally {
			setSpeedTestRunning(false);
		}
	};

	const handleRestartEquipment = async () => {
		setEquipmentRestarting(true);
		try {
			// Simulate equipment restart
			await customerAPI.restartEquipment();
			await new Promise((resolve) => setTimeout(resolve, 30000));
			await refetch(); // Refresh data after restart
		} catch (error) {
			console.error("Equipment restart failed:", error);
		} finally {
			setEquipmentRestarting(false);
		}
	};

	const handleDismissNotification = async (notificationId: string) => {
		try {
			await customerAPI.dismissNotification(notificationId);
			// Remove from local state
			if (serviceNotifications) {
				setServiceNotifications((prev) => ({
					...prev,
					service_notifications: prev.service_notifications.filter(
						(n: any) => n.id !== notificationId,
					),
				}));
			}
		} catch (error) {
			console.error("Failed to dismiss notification:", error);
		}
	};

	// Show loading state
	if (isLoading) {
		return (
			<CustomerLayout>
				<div className="space-y-6">
					<div className="text-center py-12">
						<div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
						<p className="text-gray-600 mt-4">Loading your dashboard...</p>
					</div>
				</div>
			</CustomerLayout>
		);
	}

	// Show error state
	if (apiError || error) {
		return (
			<CustomerLayout>
				<div className="text-center py-12">
					<AlertCircle className="h-12 w-12 text-red-600 mx-auto mb-4" />
					<h2 className="text-xl font-semibold text-gray-900 mb-2">
						Unable to load dashboard
					</h2>
					<p className="text-gray-600 mb-6">{apiError || error}</p>
					<button
						onClick={handleRefreshStatus}
						disabled={isRefreshing}
						className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
					>
						{isRefreshing && (
							<RefreshCw className="animate-spin h-4 w-4 mr-2" />
						)}
						Try Again
					</button>
				</div>
			</CustomerLayout>
		);
	}

	if (!customerData) {
		return (
			<CustomerLayout>
				<div className="text-center py-12">
					<p className="text-gray-600">No data available</p>
				</div>
			</CustomerLayout>
		);
	}

	return (
		<CustomerLayout>
			<div className="space-y-8">
				{/* Page Header */}
				<div className="flex items-center justify-between">
					<div>
						<h1 className="text-2xl font-bold text-gray-900">
							Welcome back,{" "}
							{user?.name || customerData.account?.name || "Customer"}
						</h1>
						<p className="text-gray-600">
							Account: {customerData.account?.number}
							{isUsingMockData && (
								<span className="ml-2 text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded">
									Demo Mode
								</span>
							)}
						</p>
					</div>

					<button
						onClick={handleRefreshStatus}
						disabled={isRefreshing}
						className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
					>
						<RefreshCw
							className={`h-4 w-4 mr-2 ${isRefreshing ? "animate-spin" : ""}`}
						/>
						Refresh
					</button>
				</div>

				{/* Service Notifications */}
				{serviceNotifications?.service_notifications &&
					serviceNotifications.service_notifications.length > 0 && (
						<NotificationsSection
							notifications={serviceNotifications.service_notifications.map(
								(notif: any) => ({
									id: notif.id,
									type: notif.severity || "info",
									title: notif.title,
									message: notif.message,
									timestamp: notif.created_at,
									action: notif.action_url
										? {
												label: "Learn More",
												onClick: () => window.open(notif.action_url, "_blank"),
											}
										: undefined,
								}),
							)}
							onDismiss={handleDismissNotification}
						/>
					)}

				{/* Usage Insights - Smart Recommendations */}
				{usageInsights?.usage_insights &&
					usageInsights.usage_insights.length > 0 && (
						<div className="p-4 bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-lg">
							<div className="flex items-center justify-between mb-3">
								<div className="flex items-center">
									<Lightbulb className="h-5 w-5 text-green-600 mr-2" />
									<h3 className="font-semibold text-gray-900">
										Smart Insights
									</h3>
								</div>
								{usageInsights.summary?.potential_monthly_impact && (
									<span className="text-sm font-medium text-green-600 bg-green-100 px-2 py-1 rounded-full">
										{usageInsights.summary.potential_monthly_impact}
									</span>
								)}
							</div>
							<div className="bg-white/60 rounded-lg border border-green-100 p-3">
								<p className="font-medium text-gray-900 text-sm">
									{usageInsights.usage_insights[0].title}
								</p>
								<p className="text-gray-600 text-sm">
									{usageInsights.usage_insights[0].message}
								</p>
								{usageInsights.usage_insights[0].recommendation && (
									<p className="text-green-700 text-sm font-medium mt-1">
										💡 {usageInsights.usage_insights[0].recommendation}
									</p>
								)}
							</div>
						</div>
					)}

				{/* Service Overview */}
				<ServiceOverviewSection
					networkStatus={customerData.networkStatus}
					dataUsage={{
						current: customerData.services[0]?.usage?.current || 0,
						limit: customerData.services[0]?.usage?.limit || 1000,
					}}
					onRefreshStatus={handleRefreshStatus}
					loading={isRefreshing}
				/>

				{/* Usage Charts and Quick Actions */}
				<div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
					<UsageChartsSection
						currentUsage={{
							download: customerData.services[0]?.usage?.current * 0.7 || 0,
							upload: customerData.services[0]?.usage?.current * 0.3 || 0,
							total: customerData.services[0]?.usage?.current || 0,
							limit: customerData.services[0]?.usage?.limit || 1000,
						}}
						historicalData={customerData.services[0]?.usage?.history || []}
						billingPeriod={{
							start:
								customerData.billing?.currentPeriod?.start ||
								new Date().toISOString(),
							end:
								customerData.billing?.currentPeriod?.end ||
								new Date().toISOString(),
							daysRemaining: customerData.billing?.daysUntilDue || 15,
						}}
					/>

					<QuickActionsSection
						onPayBill={() => console.log("Pay bill clicked")}
						onContactSupport={() => console.log("Contact support clicked")}
						onManageServices={() => console.log("Manage services clicked")}
						onRunSpeedTest={handleRunSpeedTest}
						onRestartEquipment={handleRestartEquipment}
						onViewBilling={() => console.log("View billing clicked")}
						onAccessSupport={() => console.log("Access support clicked")}
						onScheduleService={() => console.log("Schedule service clicked")}
						isSpeedTestRunning={speedTestRunning}
						isEquipmentRestarting={equipmentRestarting}
					/>
				</div>

				{/* System Status Footer */}
				<div className="text-center text-sm text-gray-500">
					<p>
						Last updated: {new Date().toLocaleTimeString()}
						{isUsingMockData && " • Using demo data"}
					</p>
				</div>
			</div>
		</CustomerLayout>
	);
}
