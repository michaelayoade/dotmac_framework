"use client";

import { useCachedData, usePortalAuth } from "@dotmac/headless";
import { Card } from "@dotmac/styled-components/reseller";
import { motion } from "framer-motion";
import {
	Activity,
	ArrowDown,
	ArrowUp,
	Award,
	Calendar,
	Clock,
	DollarSign,
	Target,
	TrendingDown,
	TrendingUp,
	Users,
	Zap,
} from "lucide-react";
import {
	Area,
	AreaChart,
	Bar,
	BarChart,
	CartesianGrid,
	Cell,
	Line,
	LineChart,
	Pie,
	PieChart,
	ResponsiveContainer,
	Tooltip,
	XAxis,
	YAxis,
} from "recharts";

// Mock advanced sales data
const mockSalesAnalytics = {
	performance: {
		totalRevenue: 487650,
		monthlyRevenue: 45780,
		quarterlyRevenue: 124560,
		yearlyRevenue: 487650,
		revenueGrowth: 8.6,
		customerAcquisitionCost: 85.5,
		lifetimeValue: 2850.0,
		conversionRate: 18.5,
		averageDealSize: 199.99,
		salesCycleLength: 14, // days
	},
	pipeline: [
		{ stage: "Leads", count: 124, value: 24800, color: "#3B82F6" },
		{ stage: "Qualified", count: 58, value: 17400, color: "#10B981" },
		{ stage: "Proposal", count: 23, value: 13800, color: "#F59E0B" },
		{ stage: "Negotiation", count: 12, value: 9600, color: "#EF4444" },
		{ stage: "Closed Won", count: 8, value: 1600, color: "#8B5CF6" },
	],
	monthlyTrends: [
		{ month: "Jul", revenue: 38250, customers: 18, deals: 24 },
		{ month: "Aug", revenue: 42100, customers: 21, deals: 28 },
		{ month: "Sep", revenue: 39800, customers: 19, deals: 26 },
		{ month: "Oct", revenue: 44200, customers: 23, deals: 31 },
		{ month: "Nov", revenue: 42150, customers: 20, deals: 29 },
		{ month: "Dec", revenue: 45780, customers: 23, deals: 33 },
		{ month: "Jan", revenue: 45780, customers: 23, deals: 33 },
	],
	serviceBreakdown: [
		{ name: "Fiber 1GB", value: 35, revenue: 17890, color: "#10B981" },
		{ name: "Fiber 500MB", value: 28, revenue: 13440, color: "#3B82F6" },
		{ name: "Business 100MB", value: 22, revenue: 8580, color: "#F59E0B" },
		{ name: "Basic 50MB", value: 15, revenue: 5870, color: "#EF4444" },
	],
	topPerformers: [
		{ name: "Sarah Johnson", deals: 8, revenue: 12500, growth: 15.2 },
		{ name: "Mike Chen", deals: 6, revenue: 9800, growth: 8.7 },
		{ name: "Lisa Park", deals: 5, revenue: 8200, growth: -2.1 },
		{ name: "John Smith", deals: 4, revenue: 6900, growth: 12.4 },
	],
	goals: {
		monthly: { target: 50000, current: 45780, progress: 91.6 },
		quarterly: { target: 150000, current: 124560, progress: 83.0 },
		yearly: { target: 600000, current: 487650, progress: 81.3 },
	},
	forecasting: {
		nextMonth: { predicted: 48200, confidence: 85 },
		nextQuarter: { predicted: 142000, confidence: 78 },
		trends: {
			customerGrowth: 12.5,
			revenueGrowth: 8.6,
			marketSaturation: 23.4,
		},
	},
};

export function SalesDashboard() {
	const { user } = usePortalAuth();

	const { data: analytics } = useCachedData(
		"sales-analytics",
		async () => mockSalesAnalytics,
		{
			ttl: 5 * 60 * 1000,
		},
	);

	if (!analytics) {
		return (
			<div className="flex h-64 items-center justify-center">
				<div className="h-8 w-8 animate-spin rounded-full border-green-600 border-b-2" />
			</div>
		);
	}

	const formatCurrency = (amount: number) => {
		return new Intl.NumberFormat("en-US", {
			style: "currency",
			currency: "USD",
			minimumFractionDigits: 0,
		}).format(amount);
	};

	const formatPercent = (value: number) => `${value.toFixed(1)}%`;

	return (
		<div className="space-y-6">
			{/* Performance Overview */}
			<motion.div
				initial={{ opacity: 0, y: 20 }}
				animate={{ opacity: 1, y: 0 }}
				transition={{ duration: 0.5 }}
				className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
			>
				<Card className="p-6 bg-gradient-to-br from-green-50 to-emerald-50 border-green-200">
					<div className="flex items-center justify-between">
						<div>
							<p className="text-green-700 text-sm font-medium">
								Monthly Revenue
							</p>
							<p className="text-3xl font-bold text-green-800">
								{formatCurrency(analytics.performance.monthlyRevenue)}
							</p>
							<div className="flex items-center mt-2">
								<ArrowUp className="h-4 w-4 text-green-600" />
								<span className="text-green-600 text-sm ml-1">
									{formatPercent(analytics.performance.revenueGrowth)}
								</span>
							</div>
						</div>
						<TrendingUp className="h-8 w-8 text-green-600" />
					</div>
				</Card>

				<Card className="p-6 bg-gradient-to-br from-blue-50 to-cyan-50 border-blue-200">
					<div className="flex items-center justify-between">
						<div>
							<p className="text-blue-700 text-sm font-medium">
								Conversion Rate
							</p>
							<p className="text-3xl font-bold text-blue-800">
								{formatPercent(analytics.performance.conversionRate)}
							</p>
							<div className="flex items-center mt-2">
								<Target className="h-4 w-4 text-blue-600" />
								<span className="text-blue-600 text-sm ml-1">
									Above Average
								</span>
							</div>
						</div>
						<Target className="h-8 w-8 text-blue-600" />
					</div>
				</Card>

				<Card className="p-6 bg-gradient-to-br from-purple-50 to-indigo-50 border-purple-200">
					<div className="flex items-center justify-between">
						<div>
							<p className="text-purple-700 text-sm font-medium">
								Avg Deal Size
							</p>
							<p className="text-3xl font-bold text-purple-800">
								{formatCurrency(analytics.performance.averageDealSize)}
							</p>
							<div className="flex items-center mt-2">
								<DollarSign className="h-4 w-4 text-purple-600" />
								<span className="text-purple-600 text-sm ml-1">
									LTV: {formatCurrency(analytics.performance.lifetimeValue)}
								</span>
							</div>
						</div>
						<DollarSign className="h-8 w-8 text-purple-600" />
					</div>
				</Card>

				<Card className="p-6 bg-gradient-to-br from-orange-50 to-red-50 border-orange-200">
					<div className="flex items-center justify-between">
						<div>
							<p className="text-orange-700 text-sm font-medium">Sales Cycle</p>
							<p className="text-3xl font-bold text-orange-800">
								{analytics.performance.salesCycleLength}d
							</p>
							<div className="flex items-center mt-2">
								<Clock className="h-4 w-4 text-orange-600" />
								<span className="text-orange-600 text-sm ml-1">Avg Length</span>
							</div>
						</div>
						<Activity className="h-8 w-8 text-orange-600" />
					</div>
				</Card>
			</motion.div>

			{/* Pipeline Visualization & Revenue Trends */}
			<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
				{/* Sales Pipeline */}
				<motion.div
					initial={{ opacity: 0, x: -20 }}
					animate={{ opacity: 1, x: 0 }}
					transition={{ duration: 0.5, delay: 0.2 }}
				>
					<Card className="p-6">
						<div className="flex items-center justify-between mb-6">
							<h3 className="text-lg font-semibold text-gray-900">
								Sales Pipeline
							</h3>
							<div className="text-sm text-gray-600">
								Total Value:{" "}
								{formatCurrency(
									analytics.pipeline.reduce(
										(sum: number, stage: any) => sum + stage.value,
										0,
									),
								)}
							</div>
						</div>
						<div className="space-y-4">
							{analytics.pipeline.map((stage: any, index: number) => (
								<div key={stage.stage} className="relative">
									<div className="flex items-center justify-between mb-2">
										<span className="text-sm font-medium text-gray-700">
											{stage.stage}
										</span>
										<div className="text-right">
											<div className="text-sm font-semibold text-gray-900">
												{stage.count} deals
											</div>
											<div className="text-xs text-gray-600">
												{formatCurrency(stage.value)}
											</div>
										</div>
									</div>
									<div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
										<motion.div
											initial={{ width: 0 }}
											animate={{ width: `${(stage.count / 124) * 100}%` }}
											transition={{ duration: 1, delay: index * 0.1 }}
											className="h-full rounded-full"
											style={{ backgroundColor: stage.color }}
										/>
									</div>
								</div>
							))}
						</div>
					</Card>
				</motion.div>

				{/* Revenue Trends */}
				<motion.div
					initial={{ opacity: 0, x: 20 }}
					animate={{ opacity: 1, x: 0 }}
					transition={{ duration: 0.5, delay: 0.3 }}
				>
					<Card className="p-6">
						<div className="flex items-center justify-between mb-6">
							<h3 className="text-lg font-semibold text-gray-900">
								Revenue Trends
							</h3>
							<div className="flex items-center text-sm text-green-600">
								<ArrowUp className="h-4 w-4 mr-1" />
								{formatPercent(analytics.performance.revenueGrowth)} vs last
								month
							</div>
						</div>
						<div className="h-64">
							<ResponsiveContainer width="100%" height="100%">
								<AreaChart data={analytics.monthlyTrends}>
									<CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
									<XAxis dataKey="month" tick={{ fontSize: 12 }} />
									<YAxis tick={{ fontSize: 12 }} />
									<Tooltip
										formatter={(value, name) => [
											name === "revenue"
												? formatCurrency(value as number)
												: value,
											name === "revenue" ? "Revenue" : name,
										]}
										labelStyle={{ color: "#374151" }}
									/>
									<Area
										type="monotone"
										dataKey="revenue"
										stroke="#10B981"
										fill="url(#revenueGradient)"
										strokeWidth={2}
									/>
									<defs>
										<linearGradient
											id="revenueGradient"
											x1="0"
											y1="0"
											x2="0"
											y2="1"
										>
											<stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
											<stop
												offset="95%"
												stopColor="#10B981"
												stopOpacity={0.05}
											/>
										</linearGradient>
									</defs>
								</AreaChart>
							</ResponsiveContainer>
						</div>
					</Card>
				</motion.div>
			</div>

			{/* Service Mix & Goals Progress */}
			<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
				{/* Service Breakdown */}
				<motion.div
					initial={{ opacity: 0, y: 20 }}
					animate={{ opacity: 1, y: 0 }}
					transition={{ duration: 0.5, delay: 0.4 }}
				>
					<Card className="p-6">
						<div className="flex items-center justify-between mb-6">
							<h3 className="text-lg font-semibold text-gray-900">
								Service Mix
							</h3>
							<Zap className="h-5 w-5 text-gray-400" />
						</div>
						<div className="grid grid-cols-2 gap-6">
							<div className="h-48">
								<ResponsiveContainer width="100%" height="100%">
									<PieChart>
										<Pie
											data={analytics.serviceBreakdown}
											dataKey="value"
											nameKey="name"
											cx="50%"
											cy="50%"
											outerRadius={80}
											label={({ name, percent }) =>
												`${(percent * 100).toFixed(0)}%`
											}
										>
											{analytics.serviceBreakdown.map(
												(entry: any, index: number) => (
													<Cell key={`cell-${index}`} fill={entry.color} />
												),
											)}
										</Pie>
										<Tooltip formatter={(value) => `${value} customers`} />
									</PieChart>
								</ResponsiveContainer>
							</div>
							<div className="space-y-3">
								{analytics.serviceBreakdown.map(
									(service: any, index: number) => (
										<motion.div
											key={service.name}
											initial={{ opacity: 0, x: 20 }}
											animate={{ opacity: 1, x: 0 }}
											transition={{ duration: 0.3, delay: 0.5 + index * 0.1 }}
											className="flex items-center justify-between"
										>
											<div className="flex items-center">
												<div
													className="w-3 h-3 rounded-full mr-2"
													style={{ backgroundColor: service.color }}
												/>
												<span className="text-sm text-gray-700">
													{service.name}
												</span>
											</div>
											<div className="text-right">
												<div className="text-sm font-semibold text-gray-900">
													{service.value}
												</div>
												<div className="text-xs text-gray-600">
													{formatCurrency(service.revenue)}
												</div>
											</div>
										</motion.div>
									),
								)}
							</div>
						</div>
					</Card>
				</motion.div>

				{/* Goals Progress */}
				<motion.div
					initial={{ opacity: 0, y: 20 }}
					animate={{ opacity: 1, y: 0 }}
					transition={{ duration: 0.5, delay: 0.5 }}
				>
					<Card className="p-6">
						<div className="flex items-center justify-between mb-6">
							<h3 className="text-lg font-semibold text-gray-900">
								Goals Progress
							</h3>
							<Award className="h-5 w-5 text-gray-400" />
						</div>
						<div className="space-y-6">
							{Object.entries(analytics.goals).map(
								([period, goal]: [string, any]) => (
									<div key={period} className="relative">
										<div className="flex items-center justify-between mb-2">
											<span className="text-sm font-medium text-gray-700 capitalize">
												{period}
											</span>
											<div className="text-right">
												<div className="text-sm font-semibold text-gray-900">
													{formatCurrency(goal.current)} /{" "}
													{formatCurrency(goal.target)}
												</div>
												<div className="text-xs text-gray-600">
													{formatPercent(goal.progress)}
												</div>
											</div>
										</div>
										<div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
											<motion.div
												initial={{ width: 0 }}
												animate={{ width: `${Math.min(goal.progress, 100)}%` }}
												transition={{ duration: 1, delay: 0.6 }}
												className={`h-full rounded-full ${
													goal.progress >= 100
														? "bg-green-500"
														: goal.progress >= 75
															? "bg-blue-500"
															: goal.progress >= 50
																? "bg-yellow-500"
																: "bg-red-500"
												}`}
											/>
										</div>
									</div>
								),
							)}
						</div>

						{/* Forecasting */}
						<div className="mt-6 pt-6 border-t border-gray-200">
							<h4 className="text-sm font-medium text-gray-900 mb-3">
								Forecasting
							</h4>
							<div className="grid grid-cols-2 gap-4">
								<div className="text-center p-3 bg-gray-50 rounded-lg">
									<div className="text-xs text-gray-600">Next Month</div>
									<div className="text-sm font-semibold text-gray-900">
										{formatCurrency(analytics.forecasting.nextMonth.predicted)}
									</div>
									<div className="text-xs text-green-600">
										{analytics.forecasting.nextMonth.confidence}% confidence
									</div>
								</div>
								<div className="text-center p-3 bg-gray-50 rounded-lg">
									<div className="text-xs text-gray-600">Next Quarter</div>
									<div className="text-sm font-semibold text-gray-900">
										{formatCurrency(
											analytics.forecasting.nextQuarter.predicted,
										)}
									</div>
									<div className="text-xs text-blue-600">
										{analytics.forecasting.nextQuarter.confidence}% confidence
									</div>
								</div>
							</div>
						</div>
					</Card>
				</motion.div>
			</div>

			{/* Performance Metrics */}
			<motion.div
				initial={{ opacity: 0, y: 20 }}
				animate={{ opacity: 1, y: 0 }}
				transition={{ duration: 0.5, delay: 0.6 }}
			>
				<Card className="p-6">
					<div className="flex items-center justify-between mb-6">
						<h3 className="text-lg font-semibold text-gray-900">
							Deal Performance
						</h3>
						<Calendar className="h-5 w-5 text-gray-400" />
					</div>
					<div className="h-64">
						<ResponsiveContainer width="100%" height="100%">
							<BarChart data={analytics.monthlyTrends}>
								<CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
								<XAxis dataKey="month" tick={{ fontSize: 12 }} />
								<YAxis tick={{ fontSize: 12 }} />
								<Tooltip
									formatter={(value, name) => [
										name === "revenue"
											? formatCurrency(value as number)
											: value,
										name === "revenue"
											? "Revenue"
											: name === "customers"
												? "Customers"
												: "Deals",
									]}
								/>
								<Bar dataKey="deals" fill="#3B82F6" radius={[4, 4, 0, 0]} />
								<Bar dataKey="customers" fill="#10B981" radius={[4, 4, 0, 0]} />
							</BarChart>
						</ResponsiveContainer>
					</div>
				</Card>
			</motion.div>
		</div>
	);
}
