"use client";

import { Card } from "@dotmac/ui/reseller";
import {
	endOfMonth,
	endOfYear,
	format,
	startOfMonth,
	startOfYear,
	subMonths,
} from "date-fns";
import { motion } from "framer-motion";
import {
	AlertCircle,
	ArrowDown,
	ArrowUp,
	Award,
	BarChart3,
	Calendar,
	CheckCircle,
	Clock,
	DollarSign,
	Download,
	Eye,
	Filter,
	Percent,
	Target,
	TrendingDown,
	TrendingUp,
	Users,
	Zap,
} from "lucide-react";
import { useMemo, useState } from "react";
import {
	Area,
	AreaChart,
	Bar,
	BarChart,
	CartesianGrid,
	Cell,
	ComposedChart,
	Line,
	LineChart,
	Pie,
	PieChart,
	ResponsiveContainer,
	Tooltip,
	XAxis,
	YAxis,
} from "recharts";

// Mock commission data
const mockCommissionData = {
	summary: {
		totalEarned: 127850.0,
		thisMonth: 8945.0,
		lastMonth: 7650.0,
		pending: 3250.0,
		nextPayoutDate: "2024-02-15",
		ytdEarnings: 127850.0,
		averageMonthly: 10654.17,
		growth: 16.9,
		rank: 3,
		totalResellers: 47,
	},
	monthlyHistory: [
		{
			month: "Feb 23",
			revenue: 32500,
			commission: 3250,
			customers: 18,
			tier: "Silver",
			rate: 10.0,
		},
		{
			month: "Mar 23",
			revenue: 38200,
			commission: 3820,
			customers: 21,
			tier: "Silver",
			rate: 10.0,
		},
		{
			month: "Apr 23",
			revenue: 41800,
			commission: 4180,
			customers: 23,
			tier: "Gold",
			rate: 10.5,
		},
		{
			month: "May 23",
			revenue: 45600,
			commission: 4788,
			customers: 26,
			tier: "Gold",
			rate: 10.5,
		},
		{
			month: "Jun 23",
			revenue: 52300,
			commission: 5492,
			customers: 29,
			tier: "Gold",
			rate: 10.5,
		},
		{
			month: "Jul 23",
			revenue: 58900,
			commission: 6184,
			customers: 32,
			tier: "Gold",
			rate: 10.5,
		},
		{
			month: "Aug 23",
			revenue: 62400,
			commission: 6552,
			customers: 35,
			tier: "Platinum",
			rate: 11.0,
		},
		{
			month: "Sep 23",
			revenue: 69800,
			commission: 7678,
			customers: 38,
			tier: "Platinum",
			rate: 11.0,
		},
		{
			month: "Oct 23",
			revenue: 73500,
			commission: 8085,
			customers: 41,
			tier: "Platinum",
			rate: 11.0,
		},
		{
			month: "Nov 23",
			revenue: 76200,
			commission: 8382,
			customers: 43,
			tier: "Platinum",
			rate: 11.0,
		},
		{
			month: "Dec 23",
			revenue: 78900,
			commission: 8679,
			customers: 45,
			tier: "Platinum",
			rate: 11.0,
		},
		{
			month: "Jan 24",
			revenue: 81200,
			commission: 8932,
			customers: 47,
			tier: "Platinum",
			rate: 11.0,
		},
	],
	tierProgress: {
		current: "Platinum",
		nextTier: "Diamond",
		progress: 73,
		currentThreshold: 75000,
		nextThreshold: 100000,
		benefits: {
			current: [
				"11% commission rate",
				"Priority support",
				"Quarterly bonuses",
				"Marketing co-op",
			],
			next: [
				"12.5% commission rate",
				"Dedicated account manager",
				"Custom pricing",
				"Lead sharing program",
			],
		},
	},
	commissionBreakdown: [
		{
			service: "Fiber 1GB",
			count: 18,
			revenue: 23400,
			commission: 2574,
			rate: 11.0,
		},
		{
			service: "Fiber 500MB",
			count: 15,
			revenue: 18750,
			commission: 2063,
			rate: 11.0,
		},
		{
			service: "Business 100MB",
			count: 12,
			revenue: 15600,
			commission: 1716,
			rate: 11.0,
		},
		{
			service: "Basic 50MB",
			count: 2,
			revenue: 1200,
			commission: 132,
			rate: 11.0,
		},
	],
	forecasting: {
		nextMonth: {
			predictedRevenue: 84500,
			predictedCommission: 9295,
			confidence: 87,
			factors: ["Historical growth", "Pipeline deals", "Seasonal trends"],
		},
		nextQuarter: {
			predictedRevenue: 268000,
			predictedCommission: 29480,
			confidence: 78,
			seasonalAdjustment: 1.05,
		},
		yearEnd: {
			predictedTotal: 145000,
			targetTotal: 150000,
			probabilityOfTarget: 82,
		},
	},
	payoutHistory: [
		{
			date: "2024-01-15",
			amount: 8382.0,
			period: "November 2023",
			status: "paid",
			method: "ACH",
		},
		{
			date: "2024-02-15",
			amount: 8679.0,
			period: "December 2023",
			status: "pending",
			method: "ACH",
		},
		{
			date: "2024-03-15",
			amount: 8932.0,
			period: "January 2024",
			status: "processing",
			method: "ACH",
		},
	],
	incentives: [
		{
			id: 1,
			name: "Q1 Growth Bonus",
			description: "Achieve 15% growth over Q4",
			progress: 73,
			reward: 2500,
			deadline: "2024-03-31",
			status: "active",
		},
		{
			id: 2,
			name: "Fiber Customer Bonus",
			description: "Sign 25 new fiber customers",
			progress: 84,
			reward: 1500,
			deadline: "2024-02-29",
			status: "active",
		},
		{
			id: 3,
			name: "Referral Champion",
			description: "Generate 10 partner referrals",
			progress: 60,
			reward: 1000,
			deadline: "2024-04-30",
			status: "active",
		},
	],
};

export function CommissionTracker() {
	const [dateRange, setDateRange] = useState<"month" | "quarter" | "year">(
		"year",
	);
	const [viewType, setViewType] = useState<
		"overview" | "breakdown" | "forecast" | "incentives"
	>("overview");

	const data = mockCommissionData;

	const formatCurrency = (amount: number) => {
		return new Intl.NumberFormat("en-US", {
			style: "currency",
			currency: "USD",
			minimumFractionDigits: 0,
		}).format(amount);
	};

	const formatPercent = (value: number) => `${value.toFixed(1)}%`;

	const getTierColor = (tier: string) => {
		switch (tier.toLowerCase()) {
			case "bronze":
				return "text-orange-600 bg-orange-100";
			case "silver":
				return "text-gray-600 bg-gray-100";
			case "gold":
				return "text-yellow-600 bg-yellow-100";
			case "platinum":
				return "text-purple-600 bg-purple-100";
			case "diamond":
				return "text-blue-600 bg-blue-100";
			default:
				return "text-gray-600 bg-gray-100";
		}
	};

	const filteredData = useMemo(() => {
		const now = new Date();
		let startDate: Date;

		switch (dateRange) {
			case "month":
				startDate = startOfMonth(subMonths(now, 1));
				break;
			case "quarter":
				startDate = subMonths(now, 3);
				break;
			case "year":
			default:
				startDate = startOfYear(now);
				break;
		}

		return data.monthlyHistory.filter((item) => {
			const itemDate = new Date(item.month + " 1");
			return itemDate >= startDate;
		});
	}, [dateRange, data.monthlyHistory]);

	return (
		<div className="space-y-6">
			{/* Header with Controls */}
			<Card className="p-6">
				<div className="flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-4 lg:space-y-0">
					<div>
						<h2 className="text-2xl font-bold text-gray-900">
							Commission Tracker
						</h2>
						<p className="text-gray-600 mt-1">
							Monitor your earnings, growth, and performance incentives
						</p>
					</div>

					<div className="flex flex-wrap items-center space-x-4">
						<div className="flex bg-gray-100 rounded-lg p-1">
							{[
								{ key: "overview", label: "Overview" },
								{ key: "breakdown", label: "Breakdown" },
								{ key: "forecast", label: "Forecast" },
								{ key: "incentives", label: "Incentives" },
							].map((tab) => (
								<button
									key={tab.key}
									onClick={() => setViewType(tab.key as any)}
									className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
										viewType === tab.key
											? "bg-white text-green-700 shadow-sm"
											: "text-gray-600 hover:text-gray-900"
									}`}
								>
									{tab.label}
								</button>
							))}
						</div>

						<div className="flex space-x-2">
							<select
								value={dateRange}
								onChange={(e) => setDateRange(e.target.value as any)}
								className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:border-transparent"
							>
								<option value="month">Last Month</option>
								<option value="quarter">Last Quarter</option>
								<option value="year">This Year</option>
							</select>

							<button className="flex items-center space-x-2 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50">
								<Download className="w-4 h-4" />
								<span className="hidden sm:inline">Export</span>
							</button>
						</div>
					</div>
				</div>
			</Card>

			{/* Overview Section */}
			{viewType === "overview" && (
				<motion.div
					initial={{ opacity: 0, y: 20 }}
					animate={{ opacity: 1, y: 0 }}
					transition={{ duration: 0.5 }}
					className="space-y-6"
				>
					{/* Key Metrics */}
					<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
						<Card className="p-6 bg-gradient-to-br from-green-50 to-emerald-50 border-green-200">
							<div className="flex items-center justify-between">
								<div>
									<p className="text-green-700 text-sm font-medium">
										Total Earned
									</p>
									<p className="text-3xl font-bold text-green-800">
										{formatCurrency(data.summary.totalEarned)}
									</p>
									<div className="flex items-center mt-2">
										<ArrowUp className="h-4 w-4 text-green-600" />
										<span className="text-green-600 text-sm ml-1">
											{formatPercent(data.summary.growth)} YoY
										</span>
									</div>
								</div>
								<DollarSign className="h-8 w-8 text-green-600" />
							</div>
						</Card>

						<Card className="p-6 bg-gradient-to-br from-blue-50 to-cyan-50 border-blue-200">
							<div className="flex items-center justify-between">
								<div>
									<p className="text-blue-700 text-sm font-medium">
										This Month
									</p>
									<p className="text-3xl font-bold text-blue-800">
										{formatCurrency(data.summary.thisMonth)}
									</p>
									<div className="flex items-center mt-2">
										<TrendingUp className="h-4 w-4 text-blue-600" />
										<span className="text-blue-600 text-sm ml-1">
											vs {formatCurrency(data.summary.lastMonth)}
										</span>
									</div>
								</div>
								<Calendar className="h-8 w-8 text-blue-600" />
							</div>
						</Card>

						<Card className="p-6 bg-gradient-to-br from-purple-50 to-indigo-50 border-purple-200">
							<div className="flex items-center justify-between">
								<div>
									<p className="text-purple-700 text-sm font-medium">
										Tier Ranking
									</p>
									<p className="text-3xl font-bold text-purple-800">
										#{data.summary.rank}
									</p>
									<div className="flex items-center mt-2">
										<Award className="h-4 w-4 text-purple-600" />
										<span className="text-purple-600 text-sm ml-1">
											of {data.summary.totalResellers}
										</span>
									</div>
								</div>
								<Target className="h-8 w-8 text-purple-600" />
							</div>
						</Card>

						<Card className="p-6 bg-gradient-to-br from-orange-50 to-red-50 border-orange-200">
							<div className="flex items-center justify-between">
								<div>
									<p className="text-orange-700 text-sm font-medium">
										Pending Payout
									</p>
									<p className="text-3xl font-bold text-orange-800">
										{formatCurrency(data.summary.pending)}
									</p>
									<div className="flex items-center mt-2">
										<Clock className="h-4 w-4 text-orange-600" />
										<span className="text-orange-600 text-sm ml-1">
											{format(new Date(data.summary.nextPayoutDate), "MMM dd")}
										</span>
									</div>
								</div>
								<CheckCircle className="h-8 w-8 text-orange-600" />
							</div>
						</Card>
					</div>

					{/* Commission Trend Chart */}
					<Card className="p-6">
						<div className="flex items-center justify-between mb-6">
							<h3 className="text-lg font-semibold text-gray-900">
								Commission Trends
							</h3>
							<div className="flex items-center space-x-2 text-sm text-gray-600">
								<span>Avg Monthly:</span>
								<span className="font-semibold">
									{formatCurrency(data.summary.averageMonthly)}
								</span>
							</div>
						</div>
						<div className="h-80">
							<ResponsiveContainer width="100%" height="100%">
								<ComposedChart data={filteredData}>
									<CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
									<XAxis dataKey="month" tick={{ fontSize: 12 }} />
									<YAxis yAxisId="left" tick={{ fontSize: 12 }} />
									<YAxis
										yAxisId="right"
										orientation="right"
										tick={{ fontSize: 12 }}
									/>
									<Tooltip
										formatter={(value, name) => [
											name === "commission" || name === "revenue"
												? formatCurrency(value as number)
												: value,
											name === "commission"
												? "Commission"
												: name === "revenue"
													? "Revenue"
													: "Customers",
										]}
										labelStyle={{ color: "#374151" }}
									/>
									<Area
										yAxisId="left"
										type="monotone"
										dataKey="revenue"
										fill="url(#revenueGradient)"
										stroke="#3B82F6"
										strokeWidth={2}
									/>
									<Line
										yAxisId="left"
										type="monotone"
										dataKey="commission"
										stroke="#10B981"
										strokeWidth={3}
										dot={{ fill: "#10B981", strokeWidth: 2, r: 4 }}
									/>
									<Bar
										yAxisId="right"
										dataKey="customers"
										fill="#F59E0B"
										opacity={0.7}
									/>
									<defs>
										<linearGradient
											id="revenueGradient"
											x1="0"
											y1="0"
											x2="0"
											y2="1"
										>
											<stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
											<stop
												offset="95%"
												stopColor="#3B82F6"
												stopOpacity={0.05}
											/>
										</linearGradient>
									</defs>
								</ComposedChart>
							</ResponsiveContainer>
						</div>
					</Card>

					{/* Tier Progress & Recent Payouts */}
					<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
						{/* Tier Progress */}
						<Card className="p-6">
							<div className="flex items-center justify-between mb-4">
								<h3 className="text-lg font-semibold text-gray-900">
									Tier Progress
								</h3>
								<span
									className={`px-3 py-1 rounded-full text-sm font-medium ${getTierColor(
										data.tierProgress.current,
									)}`}
								>
									{data.tierProgress.current}
								</span>
							</div>

							<div className="space-y-4">
								<div>
									<div className="flex justify-between text-sm mb-2">
										<span>Progress to {data.tierProgress.nextTier}</span>
										<span className="font-medium">
											{data.tierProgress.progress}%
										</span>
									</div>
									<div className="w-full bg-gray-200 rounded-full h-3">
										<motion.div
											initial={{ width: 0 }}
											animate={{ width: `${data.tierProgress.progress}%` }}
											transition={{ duration: 1, delay: 0.5 }}
											className="bg-gradient-to-r from-green-500 to-blue-500 h-3 rounded-full"
										/>
									</div>
									<div className="flex justify-between text-xs text-gray-600 mt-1">
										<span>
											{formatCurrency(data.tierProgress.currentThreshold)}
										</span>
										<span>
											{formatCurrency(data.tierProgress.nextThreshold)}
										</span>
									</div>
								</div>

								<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
									<div>
										<h4 className="font-medium text-gray-900 mb-2">
											Current Benefits
										</h4>
										<div className="space-y-1">
											{data.tierProgress.benefits.current.map(
												(benefit, index) => (
													<div
														key={index}
														className="flex items-center text-xs text-gray-600"
													>
														<CheckCircle className="w-3 h-3 text-green-500 mr-2 flex-shrink-0" />
														<span>{benefit}</span>
													</div>
												),
											)}
										</div>
									</div>

									<div>
										<h4 className="font-medium text-gray-900 mb-2">
											Next Tier Benefits
										</h4>
										<div className="space-y-1">
											{data.tierProgress.benefits.next.map((benefit, index) => (
												<div
													key={index}
													className="flex items-center text-xs text-gray-600"
												>
													<Zap className="w-3 h-3 text-blue-500 mr-2 flex-shrink-0" />
													<span>{benefit}</span>
												</div>
											))}
										</div>
									</div>
								</div>
							</div>
						</Card>

						{/* Recent Payouts */}
						<Card className="p-6">
							<div className="flex items-center justify-between mb-4">
								<h3 className="text-lg font-semibold text-gray-900">
									Recent Payouts
								</h3>
								<button className="text-green-600 hover:text-green-700 text-sm font-medium">
									View All
								</button>
							</div>

							<div className="space-y-3">
								{data.payoutHistory.map((payout, index) => (
									<motion.div
										key={index}
										initial={{ opacity: 0, x: -20 }}
										animate={{ opacity: 1, x: 0 }}
										transition={{ duration: 0.3, delay: index * 0.1 }}
										className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
									>
										<div className="flex items-center space-x-3">
											{payout.status === "paid" && (
												<CheckCircle className="w-5 h-5 text-green-600" />
											)}
											{payout.status === "pending" && (
												<Clock className="w-5 h-5 text-yellow-600" />
											)}
											{payout.status === "processing" && (
												<AlertCircle className="w-5 h-5 text-blue-600" />
											)}
											<div>
												<div className="font-medium text-gray-900">
													{formatCurrency(payout.amount)}
												</div>
												<div className="text-sm text-gray-600">
													{payout.period}
												</div>
											</div>
										</div>
										<div className="text-right">
											<div
												className={`text-xs font-medium px-2 py-1 rounded-full ${
													payout.status === "paid"
														? "bg-green-100 text-green-800"
														: payout.status === "pending"
															? "bg-yellow-100 text-yellow-800"
															: "bg-blue-100 text-blue-800"
												}`}
											>
												{payout.status.charAt(0).toUpperCase() +
													payout.status.slice(1)}
											</div>
											<div className="text-xs text-gray-500 mt-1">
												{format(new Date(payout.date), "MMM dd, yyyy")}
											</div>
										</div>
									</motion.div>
								))}
							</div>
						</Card>
					</div>
				</motion.div>
			)}

			{/* Service Breakdown Section */}
			{viewType === "breakdown" && (
				<motion.div
					initial={{ opacity: 0, y: 20 }}
					animate={{ opacity: 1, y: 0 }}
					transition={{ duration: 0.5 }}
					className="space-y-6"
				>
					<Card className="p-6">
						<h3 className="text-lg font-semibold text-gray-900 mb-6">
							Commission by Service Type
						</h3>

						<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
							{/* Service Breakdown Chart */}
							<div className="h-64">
								<ResponsiveContainer width="100%" height="100%">
									<PieChart>
										<Pie
											data={data.commissionBreakdown}
											dataKey="commission"
											nameKey="service"
											cx="50%"
											cy="50%"
											outerRadius={80}
											label={({ name, percent }) =>
												`${name}: ${(percent * 100).toFixed(0)}%`
											}
										>
											{data.commissionBreakdown.map((entry, index) => (
												<Cell
													key={`cell-${index}`}
													fill={
														["#10B981", "#3B82F6", "#F59E0B", "#EF4444"][index]
													}
												/>
											))}
										</Pie>
										<Tooltip
											formatter={(value) => formatCurrency(value as number)}
											labelStyle={{ color: "#374151" }}
										/>
									</PieChart>
								</ResponsiveContainer>
							</div>

							{/* Service Details */}
							<div className="space-y-4">
								{data.commissionBreakdown.map((service, index) => (
									<motion.div
										key={service.service}
										initial={{ opacity: 0, x: 20 }}
										animate={{ opacity: 1, x: 0 }}
										transition={{ duration: 0.3, delay: index * 0.1 }}
										className="bg-gray-50 rounded-lg p-4"
									>
										<div className="flex items-center justify-between mb-2">
											<h4 className="font-medium text-gray-900">
												{service.service}
											</h4>
											<span className="text-sm font-semibold text-green-600">
												{formatPercent(service.rate)}
											</span>
										</div>
										<div className="grid grid-cols-3 gap-4 text-sm">
											<div>
												<div className="text-gray-600">Customers</div>
												<div className="font-semibold">{service.count}</div>
											</div>
											<div>
												<div className="text-gray-600">Revenue</div>
												<div className="font-semibold">
													{formatCurrency(service.revenue)}
												</div>
											</div>
											<div>
												<div className="text-gray-600">Commission</div>
												<div className="font-semibold text-green-600">
													{formatCurrency(service.commission)}
												</div>
											</div>
										</div>
									</motion.div>
								))}
							</div>
						</div>
					</Card>
				</motion.div>
			)}

			{/* Forecasting Section */}
			{viewType === "forecast" && (
				<motion.div
					initial={{ opacity: 0, y: 20 }}
					animate={{ opacity: 1, y: 0 }}
					transition={{ duration: 0.5 }}
					className="space-y-6"
				>
					<div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
						{/* Next Month Forecast */}
						<Card className="p-6 bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
							<div className="text-center">
								<div className="text-2xl font-bold text-blue-800 mb-2">
									{formatCurrency(
										data.forecasting.nextMonth.predictedCommission,
									)}
								</div>
								<div className="text-blue-700 text-sm mb-4">
									Next Month Forecast
								</div>
								<div className="text-xs text-blue-600">
									{data.forecasting.nextMonth.confidence}% confidence
								</div>
								<div className="mt-4 space-y-1">
									{data.forecasting.nextMonth.factors.map((factor, index) => (
										<div key={index} className="text-xs text-blue-700">
											• {factor}
										</div>
									))}
								</div>
							</div>
						</Card>

						{/* Quarter Forecast */}
						<Card className="p-6 bg-gradient-to-br from-green-50 to-green-100 border-green-200">
							<div className="text-center">
								<div className="text-2xl font-bold text-green-800 mb-2">
									{formatCurrency(
										data.forecasting.nextQuarter.predictedCommission,
									)}
								</div>
								<div className="text-green-700 text-sm mb-4">
									Next Quarter Forecast
								</div>
								<div className="text-xs text-green-600">
									{data.forecasting.nextQuarter.confidence}% confidence
								</div>
								<div className="mt-4">
									<div className="text-xs text-green-700">
										Seasonal Adjustment: +
										{formatPercent(
											(data.forecasting.nextQuarter.seasonalAdjustment - 1) *
												100,
										)}
									</div>
								</div>
							</div>
						</Card>

						{/* Year-end Target */}
						<Card className="p-6 bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200">
							<div className="text-center">
								<div className="text-2xl font-bold text-purple-800 mb-2">
									{formatCurrency(data.forecasting.yearEnd.predictedTotal)}
								</div>
								<div className="text-purple-700 text-sm mb-4">
									Year-end Projection
								</div>
								<div className="text-xs text-purple-600 mb-2">
									Target: {formatCurrency(data.forecasting.yearEnd.targetTotal)}
								</div>
								<div className="w-full bg-purple-200 rounded-full h-2 mb-2">
									<div
										className="bg-purple-600 h-2 rounded-full"
										style={{
											width: `${data.forecasting.yearEnd.probabilityOfTarget}%`,
										}}
									/>
								</div>
								<div className="text-xs text-purple-700">
									{data.forecasting.yearEnd.probabilityOfTarget}% chance of
									hitting target
								</div>
							</div>
						</Card>
					</div>

					{/* Forecast Chart */}
					<Card className="p-6">
						<h3 className="text-lg font-semibold text-gray-900 mb-6">
							Commission Forecast
						</h3>
						<div className="h-80">
							<ResponsiveContainer width="100%" height="100%">
								<LineChart
									data={[
										...filteredData,
										{
											month: "Feb 24",
											commission:
												data.forecasting.nextMonth.predictedCommission,
											forecast: true,
										},
										{
											month: "Mar 24",
											commission:
												data.forecasting.nextMonth.predictedCommission * 1.05,
											forecast: true,
										},
										{
											month: "Apr 24",
											commission:
												data.forecasting.nextMonth.predictedCommission * 1.08,
											forecast: true,
										},
									]}
								>
									<CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
									<XAxis dataKey="month" tick={{ fontSize: 12 }} />
									<YAxis tick={{ fontSize: 12 }} />
									<Tooltip
										formatter={(value) => [
											formatCurrency(value as number),
											"Commission",
										]}
										labelStyle={{ color: "#374151" }}
									/>
									<Line
										type="monotone"
										dataKey="commission"
										stroke="#10B981"
										strokeWidth={3}
										strokeDasharray="0"
										dot={{ fill: "#10B981", strokeWidth: 2, r: 4 }}
									/>
								</LineChart>
							</ResponsiveContainer>
						</div>
					</Card>
				</motion.div>
			)}

			{/* Incentives Section */}
			{viewType === "incentives" && (
				<motion.div
					initial={{ opacity: 0, y: 20 }}
					animate={{ opacity: 1, y: 0 }}
					transition={{ duration: 0.5 }}
					className="space-y-6"
				>
					<Card className="p-6">
						<div className="flex items-center justify-between mb-6">
							<h3 className="text-lg font-semibold text-gray-900">
								Active Incentives
							</h3>
							<div className="text-sm text-gray-600">
								Total Potential:{" "}
								{formatCurrency(
									data.incentives.reduce((sum, inc) => sum + inc.reward, 0),
								)}
							</div>
						</div>

						<div className="space-y-6">
							{data.incentives.map((incentive, index) => (
								<motion.div
									key={incentive.id}
									initial={{ opacity: 0, y: 20 }}
									animate={{ opacity: 1, y: 0 }}
									transition={{ duration: 0.3, delay: index * 0.1 }}
									className="bg-gray-50 rounded-lg p-6"
								>
									<div className="flex items-center justify-between mb-4">
										<div className="flex items-center space-x-3">
											<div
												className={`w-10 h-10 rounded-full flex items-center justify-center ${
													incentive.progress >= 100
														? "bg-green-100"
														: incentive.progress >= 75
															? "bg-yellow-100"
															: "bg-blue-100"
												}`}
											>
												{incentive.progress >= 100 ? (
													<CheckCircle className="w-5 h-5 text-green-600" />
												) : incentive.progress >= 75 ? (
													<AlertCircle className="w-5 h-5 text-yellow-600" />
												) : (
													<Target className="w-5 h-5 text-blue-600" />
												)}
											</div>
											<div>
												<h4 className="font-semibold text-gray-900">
													{incentive.name}
												</h4>
												<p className="text-gray-600 text-sm">
													{incentive.description}
												</p>
											</div>
										</div>
										<div className="text-right">
											<div className="text-lg font-bold text-green-600">
												{formatCurrency(incentive.reward)}
											</div>
											<div className="text-sm text-gray-600">
												Due: {format(new Date(incentive.deadline), "MMM dd")}
											</div>
										</div>
									</div>

									<div className="space-y-2">
										<div className="flex justify-between text-sm">
											<span>Progress</span>
											<span className="font-medium">{incentive.progress}%</span>
										</div>
										<div className="w-full bg-gray-200 rounded-full h-3">
											<motion.div
												initial={{ width: 0 }}
												animate={{
													width: `${Math.min(incentive.progress, 100)}%`,
												}}
												transition={{ duration: 1, delay: 0.5 + index * 0.1 }}
												className={`h-3 rounded-full ${
													incentive.progress >= 100
														? "bg-green-500"
														: incentive.progress >= 75
															? "bg-yellow-500"
															: "bg-blue-500"
												}`}
											/>
										</div>
									</div>
								</motion.div>
							))}
						</div>
					</Card>
				</motion.div>
			)}
		</div>
	);
}
