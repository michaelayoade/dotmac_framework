"use client";

import {
	commissionEngine,
	usePartnerDashboard,
	usePartnerDataWithErrorBoundary,
	usePortalAuth,
} from "@dotmac/headless";
import { ErrorBoundary } from "@dotmac/primitives";
import { Card } from "@dotmac/styled-components/reseller";
import {
	AlertCircle,
	Award,
	BarChart3,
	Bell,
	Calendar,
	CheckCircle,
	Clock,
	DollarSign,
	Lightbulb,
	Mail,
	MapPin,
	Phone,
	Target,
	TrendingUp,
	UserPlus,
	Users,
} from "lucide-react";
import { useEffect, useState } from "react";
import type {
	Commission,
	Customer,
	DashboardMetrics,
	SalesGoal,
	SalesOpportunity,
} from "../../types";
import { logger } from "../../utils/logger";
import { ErrorBoundary } from "../common/ErrorBoundary";
import {
	CardLoading,
	PageLoading,
	RefreshLoading,
} from "../common/LoadingStates";
import { ResellerLayout } from "../layout/ResellerLayout";

export function ResellerDashboard() {
	const { user, currentPortal } = usePortalAuth();
	const [commissionData, setCommissionData] = useState<Commission[] | null>(
		null,
	);
	const [salesOpportunities, setSalesOpportunities] = useState<
		SalesOpportunity[] | null
	>(null);

	// Get partner ID from user context
	const partnerId = user?.partnerId || user?.id;

	// Use real API data instead of mock data
	const dashboardQuery = usePartnerDataWithErrorBoundary(
		usePartnerDashboard(partnerId),
	);

	const { data: dashboardData, isLoading, error } = dashboardQuery;

	// Load commission intelligence - now using secure API calls
	useEffect(() => {
		if (dashboardData?.partner?.id) {
			fetchCommissionIntelligence();
		}
	}, [dashboardData]);

	const fetchCommissionIntelligence = async () => {
		// Remove insecure localStorage token access
		// This will now be handled by the API client with proper authentication
		try {
			const commissionResponse = await fetch(
				`/api/v1/partners/${partnerId}/intelligence/commission-tracking`,
			);

			if (commissionResponse.ok) {
				const commissionData = await commissionResponse.json();
				setCommissionData(commissionData);
			}

			const opportunitiesResponse = await fetch(
				`/api/v1/partners/${partnerId}/intelligence/sales-opportunities`,
			);

			if (opportunitiesResponse.ok) {
				const opportunities = await opportunitiesResponse.json();
				setSalesOpportunities(opportunities);
			}
		} catch (error) {
			logger.error("Failed to fetch commission intelligence", error, {
				component: "dashboard",
			});
		}
	};

	// Show loading state
	if (isLoading) {
		return (
			<ResellerLayout>
				<PageLoading message="Loading your dashboard" />
			</ResellerLayout>
		);
	}

	// Show error state
	if (error) {
		return (
			<ResellerLayout>
				<div className="flex items-center justify-center h-full">
					<div className="text-center">
						<AlertCircle className="mx-auto h-12 w-12 text-red-500 mb-4" />
						<h3 className="text-lg font-medium text-gray-900 mb-2">
							Failed to load dashboard
						</h3>
						<p className="text-gray-600 mb-4">
							There was an error loading your partner dashboard.
						</p>
						<button
							onClick={() => window.location.reload()}
							className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
						>
							Retry
						</button>
					</div>
				</div>
			</ResellerLayout>
		);
	}

	// Show message if no data
	if (!dashboardData) {
		return (
			<ResellerLayout>
				<div className="flex items-center justify-center h-full">
					<p className="text-gray-600">No dashboard data available.</p>
				</div>
			</ResellerLayout>
		);
	}

	const getStatusColor = (status: string) => {
		switch (status) {
			case "active":
				return "text-green-600";
			case "pending":
				return "text-yellow-600";
			case "suspended":
				return "text-red-600";
			default:
				return "text-gray-600";
		}
	};

	const getStatusIcon = (status: string) => {
		switch (status) {
			case "active":
				return <CheckCircle className="h-4 w-4 text-green-600" />;
			case "pending":
				return <Clock className="h-4 w-4 text-yellow-600" />;
			case "suspended":
				return <AlertCircle className="h-4 w-4 text-red-600" />;
			default:
				return <AlertCircle className="h-4 w-4 text-gray-600" />;
		}
	};

	const formatCurrency = (amount: number) => {
		return new Intl.NumberFormat("en-US", {
			style: "currency",
			currency: "USD",
		}).format(amount);
	};

	const calculateProgress = (current: number, target: number) => {
		return Math.min((current / target) * 100, 100);
	};

	// Use dashboardData as the main data source (resellerData was a legacy reference)
	const resellerData = dashboardData;

	return (
		<ErrorBoundary componentName="ResellerDashboard" level="page">
			<div className="reseller-dashboard">
				<div className="space-y-6">
					{/* Welcome Header */}
					<div className="rounded-lg bg-gradient-to-r from-green-600 to-emerald-700 p-6 text-white">
						<div className="flex items-center justify-between">
							<div>
								<h1 className="font-bold text-2xl">
									Welcome back, {resellerData.partner.contact.name}!
								</h1>
								<p className="mt-1 text-green-100">
									{resellerData.partner.name} • {resellerData.partner.territory}
								</p>
								<div className="mt-2 flex items-center space-x-4">
									<div className="flex items-center">
										<Award className="mr-1 h-4 w-4" />
										<span className="text-sm">
											{resellerData.partner.tier} Partner
										</span>
									</div>
									<div className="flex items-center">
										<Target className="mr-1 h-4 w-4" />
										<span className="text-sm">
											Code: {resellerData.partner.partnerCode}
										</span>
									</div>
								</div>
							</div>
							<div className="text-right">
								<div className="text-green-100 text-sm">
									This Month&apos;s Commissions
								</div>
								<div className="font-bold text-3xl">
									{formatCurrency(
										resellerData.performance.commissions.thisMonth,
									)}
								</div>
							</div>
						</div>
					</div>

					{/* Commission Intelligence Alerts */}
					{commissionData && commissionData.commission_alerts.length > 0 && (
						<Card className="p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200">
							<div className="flex items-center mb-3">
								<Bell className="h-5 w-5 text-blue-600 mr-2" />
								<h3 className="font-semibold text-gray-900">
									Commission Updates
								</h3>
							</div>
							<div className="space-y-2">
								{commissionData.commission_alerts
									.slice(0, 2)
									.map((alert: any, index: number) => (
										<div
											key={index}
											className={`p-3 rounded-lg ${
												alert.priority === "high"
													? "bg-green-50 border border-green-200"
													: alert.priority === "medium"
														? "bg-yellow-50 border border-yellow-200"
														: "bg-blue-50 border border-blue-200"
											}`}
										>
											<div className="flex items-start">
												<div
													className={`w-2 h-2 rounded-full mt-2 mr-3 ${
														alert.priority === "high"
															? "bg-green-500"
															: alert.priority === "medium"
																? "bg-yellow-500"
																: "bg-blue-500"
													}`}
												></div>
												<div className="flex-1">
													<p className="font-medium text-gray-900 text-sm">
														{alert.title}
													</p>
													<p className="text-gray-600 text-sm">
														{alert.message}
													</p>
												</div>
												{alert.priority === "high" && (
													<span className="ml-3 px-2 py-1 bg-green-100 text-green-800 text-xs font-medium rounded-full">
														🎉 Great News!
													</span>
												)}
											</div>
										</div>
									))}
								{commissionData.commission_summary && (
									<div className="mt-3 pt-3 border-t border-blue-200 flex justify-between text-sm">
										<span className="text-gray-600">Pending:</span>
										<span className="font-semibold text-gray-900">
											{formatCurrency(
												commissionData.commission_summary.pending_amount,
											)}
										</span>
									</div>
								)}
							</div>
						</Card>
					)}

					{/* Sales Opportunities Intelligence */}
					{salesOpportunities &&
						salesOpportunities.sales_opportunities.length > 0 && (
							<Card className="p-4 bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200">
								<div className="flex items-center justify-between mb-3">
									<div className="flex items-center">
										<Lightbulb className="h-5 w-5 text-green-600 mr-2" />
										<h3 className="font-semibold text-gray-900">
											Sales Opportunities
										</h3>
									</div>
									<span className="text-sm font-medium text-green-600 bg-green-100 px-2 py-1 rounded-full">
										{salesOpportunities.sales_opportunities.length}{" "}
										opportunities
									</span>
								</div>
								<div className="space-y-2">
									{salesOpportunities.sales_opportunities
										.slice(0, 2)
										.map((opportunity: any, index: number) => (
											<div
												key={index}
												className="p-3 bg-white/60 rounded-lg border border-green-100"
											>
												<div className="flex items-start justify-between">
													<div className="flex-1">
														<p className="font-medium text-gray-900 text-sm">
															{opportunity.title}
														</p>
														<p className="text-gray-600 text-sm">
															{opportunity.message}
														</p>
														{opportunity.potential_value && (
															<p className="text-green-700 text-sm font-medium mt-1">
																💰 {opportunity.potential_value}
															</p>
														)}
													</div>
													<span
														className={`ml-3 px-2 py-1 text-xs font-medium rounded-full ${
															opportunity.priority === "high"
																? "bg-red-100 text-red-800"
																: "bg-yellow-100 text-yellow-800"
														}`}
													>
														{opportunity.priority === "high"
															? "🔥 High Priority"
															: "📈 Medium Priority"}
													</span>
												</div>
											</div>
										))}
								</div>
							</Card>
						)}

					{/* Key Performance Metrics */}
					<div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
						<Card className="p-6">
							<div className="flex items-center justify-between">
								<div>
									<p className="font-medium text-gray-600 text-sm">
										Total Customers
									</p>
									<p className="font-bold text-3xl text-gray-900">
										{resellerData.performance.customersTotal}
									</p>
									<p className="text-gray-500 text-sm">
										{resellerData.performance.customersActive} active
									</p>
								</div>
								<Users className="h-8 w-8 text-green-600" />
							</div>
						</Card>

						<Card className="p-6">
							<div className="flex items-center justify-between">
								<div>
									<p className="font-medium text-gray-600 text-sm">
										New This Month
									</p>
									<p className="font-bold text-3xl text-gray-900">
										{resellerData.performance.customersThisMonth}
									</p>
									<p className="text-green-600 text-sm">
										{resellerData.performance.targets.monthlyCustomers.target -
											resellerData.performance.targets.monthlyCustomers
												.current}{" "}
										to goal
									</p>
								</div>
								<UserPlus className="h-8 w-8 text-blue-600" />
							</div>
						</Card>

						<Card className="p-6">
							<div className="flex items-center justify-between">
								<div>
									<p className="font-medium text-gray-600 text-sm">
										Monthly Revenue
									</p>
									<p className="font-bold text-3xl text-gray-900">
										{formatCurrency(resellerData.performance.revenue.thisMonth)}
									</p>
									<p className="text-green-600 text-sm">
										+{resellerData.performance.revenue.growth}% vs last month
									</p>
								</div>
								<DollarSign className="h-8 w-8 text-purple-600" />
							</div>
						</Card>

						<Card className="p-6">
							<div className="flex items-center justify-between">
								<div>
									<p className="font-medium text-gray-600 text-sm">
										Pending Commissions
									</p>
									<p className="font-bold text-3xl text-gray-900">
										{formatCurrency(
											resellerData.performance.commissions.pending,
										)}
									</p>
									<p className="text-gray-500 text-sm">
										Payout on{" "}
										{new Date(
											resellerData.performance.commissions.nextPayoutDate,
										).toLocaleDateString()}
									</p>
								</div>
								<TrendingUp className="h-8 w-8 text-orange-600" />
							</div>
						</Card>
					</div>

					{/* Goals Progress & Recent Customers */}
					<div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
						{/* Sales Goals */}
						<Card className="p-6">
							<div className="mb-4 flex items-center justify-between">
								<h3 className="font-semibold text-gray-900 text-lg">
									Sales Goals
								</h3>
								<Target className="h-5 w-5 text-gray-400" />
							</div>
							<div className="space-y-4">
								{resellerData.salesGoals.map((goal: SalesGoal) => (
									<div key={goal.id} className="rounded-lg border p-4">
										<div className="mb-2 flex items-center justify-between">
											<h4 className="font-medium text-gray-900">
												{goal.title}
											</h4>
											<span className="text-gray-500 text-sm">
												{goal.title.includes("Revenue")
													? formatCurrency(goal.current)
													: goal.current}{" "}
												/{" "}
												{goal.title.includes("Revenue")
													? formatCurrency(goal.target)
													: goal.target}
											</span>
										</div>
										<div className="mb-2 h-2 w-full rounded-full bg-gray-200">
											<div
												className="h-2 rounded-full bg-green-600 transition-all duration-300"
												style={{
													width: `${calculateProgress(goal.current, goal.target)}%`,
												}}
											/>
										</div>
										<div className="flex justify-between text-gray-600 text-sm">
											<span>
												Due: {new Date(goal.deadline).toLocaleDateString()}
											</span>
											<span className="font-medium text-green-600">
												{goal.reward}
											</span>
										</div>
									</div>
								))}
							</div>
						</Card>

						{/* Recent Customers */}
						<Card className="p-6">
							<div className="mb-4 flex items-center justify-between">
								<h3 className="font-semibold text-gray-900 text-lg">
									Recent Customers
								</h3>
								<Users className="h-5 w-5 text-gray-400" />
							</div>
							<div className="space-y-3">
								{resellerData.recentCustomers.map((customer: Customer) => (
									<div
										key={customer.id}
										className="flex items-center justify-between rounded-lg border p-3"
									>
										<div className="flex-1">
											<div className="mb-1 flex items-center justify-between">
												<h4 className="font-medium text-gray-900">
													{customer.name}
												</h4>
												<div className="flex items-center">
													{getStatusIcon(customer.status)}
													<span
														className={`ml-1 text-xs capitalize ${getStatusColor(customer.status)}`}
													>
														{customer.status}
													</span>
												</div>
											</div>
											<p className="text-gray-600 text-sm">
												{customer.service}
											</p>
											<div className="mt-1 flex items-center justify-between">
												<span className="text-gray-500 text-xs">
													Signed:{" "}
													{new Date(customer.signupDate).toLocaleDateString()}
												</span>
												<div className="text-sm">
													<span className="text-gray-600">
														Rev: {formatCurrency(customer.revenue)}
													</span>
													<span className="ml-2 text-green-600">
														Com: {formatCurrency(customer.commission)}
													</span>
												</div>
											</div>
										</div>
									</div>
								))}
							</div>
							<button
								type="button"
								className="mt-4 w-full font-medium text-green-600 text-sm hover:text-green-700"
							>
								View All Customers
							</button>
						</Card>
					</div>

					{/* Commission Summary & Quick Actions */}
					<div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
						{/* Commission Breakdown */}
						<Card className="p-6">
							<div className="mb-4 flex items-center justify-between">
								<h3 className="font-semibold text-gray-900 text-lg">
									Commission Summary
								</h3>
								<DollarSign className="h-5 w-5 text-gray-400" />
							</div>
							<div className="space-y-4">
								<div className="grid grid-cols-2 gap-4 rounded-lg bg-gray-50 p-4">
									<div>
										<p className="text-gray-600 text-sm">Total Earned</p>
										<p className="font-bold text-gray-900 text-xl">
											{formatCurrency(
												resellerData.performance.commissions.earned,
											)}
										</p>
									</div>
									<div>
										<p className="text-gray-600 text-sm">This Month</p>
										<p className="font-bold text-green-600 text-xl">
											{formatCurrency(
												resellerData.performance.commissions.thisMonth,
											)}
										</p>
									</div>
								</div>

								<div className="grid grid-cols-2 gap-4">
									<div className="rounded-lg border p-3 text-center">
										<p className="text-gray-600 text-sm">Pending</p>
										<p className="font-bold text-lg text-yellow-600">
											{formatCurrency(
												resellerData.performance.commissions.pending,
											)}
										</p>
									</div>
									<div className="rounded-lg border p-3 text-center">
										<p className="text-gray-600 text-sm">Last Payout</p>
										<p className="font-bold text-gray-900 text-lg">
											{formatCurrency(
												resellerData.performance.commissions.lastPayout,
											)}
										</p>
									</div>
								</div>

								<div className="border-t pt-3">
									<p className="text-gray-600 text-sm">Next Payout Date</p>
									<p className="font-semibold text-gray-900 text-lg">
										{new Date(
											resellerData.performance.commissions.nextPayoutDate,
										).toLocaleDateString()}
									</p>
								</div>
							</div>
						</Card>

						{/* Quick Actions */}
						<Card className="p-6">
							<div className="mb-4 flex items-center justify-between">
								<h3 className="font-semibold text-gray-900 text-lg">
									Quick Actions
								</h3>
								<BarChart3 className="h-5 w-5 text-gray-400" />
							</div>
							<div className="space-y-3">
								<div className="grid grid-cols-2 gap-3">
									<button
										type="button"
										className="rounded-lg bg-green-600 px-4 py-3 font-medium text-sm text-white transition-colors hover:bg-green-700"
									>
										Add Customer
									</button>
									<button
										type="button"
										className="rounded-lg border border-gray-300 px-4 py-3 font-medium text-gray-700 text-sm transition-colors hover:bg-gray-50"
									>
										View Analytics
									</button>
									<button
										type="button"
										className="rounded-lg border border-gray-300 px-4 py-3 font-medium text-gray-700 text-sm transition-colors hover:bg-gray-50"
									>
										Commission Report
									</button>
									<button
										type="button"
										className="rounded-lg border border-gray-300 px-4 py-3 font-medium text-gray-700 text-sm transition-colors hover:bg-gray-50"
									>
										Marketing Tools
									</button>
								</div>

								{/* Partner Info */}
								<div className="mt-6 rounded-lg bg-green-50 p-4">
									<h4 className="mb-2 font-medium text-green-900">
										Partner Information
									</h4>
									<div className="space-y-1 text-green-800 text-sm">
										<div className="flex items-center">
											<Mail className="mr-2 h-4 w-4" />
											<span>{resellerData.partner.contact.email}</span>
										</div>
										<div className="flex items-center">
											<Phone className="mr-2 h-4 w-4" />
											<span>{resellerData.partner.contact.phone}</span>
										</div>
										<div className="flex items-center">
											<MapPin className="mr-2 h-4 w-4" />
											<span>{resellerData.partner.territory}</span>
										</div>
										<div className="flex items-center">
											<Calendar className="mr-2 h-4 w-4" />
											<span>
												Partner since{" "}
												{new Date(
													resellerData.partner.joinDate,
												).toLocaleDateString()}
											</span>
										</div>
									</div>
								</div>
							</div>
						</Card>
					</div>
				</div>
			</div>
		</ErrorBoundary>
	);
}
