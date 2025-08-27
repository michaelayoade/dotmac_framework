"use client";

import {
	usePartnerCustomers,
	usePartnerDataWithErrorBoundary,
	usePortalAuth,
} from "@dotmac/headless";
import { ErrorBoundary } from "@dotmac/primitives";
import { Badge, Button, Card, Input } from "@dotmac/styled-components";
import {
	AlertCircle,
	Calendar,
	DollarSign,
	Download,
	Edit,
	Eye,
	Filter,
	Mail,
	MoreHorizontal,
	Phone,
	Plus,
	Search,
	Users,
	Wifi,
} from "lucide-react";
import { useMemo, useState } from "react";
import type { Customer } from "../../types";
import { ErrorBoundary } from "../common/ErrorBoundary";
import {
	InlineLoading,
	RefreshLoading,
	TableLoading,
} from "../common/LoadingStates";

type CustomerManagementProps = Record<string, never>;

export function CustomerManagement(_props: CustomerManagementProps) {
	const { user } = usePortalAuth();
	const [searchTerm, setSearchTerm] = useState("");
	const [statusFilter, setStatusFilter] = useState<string>("");
	const [currentPage, setCurrentPage] = useState(1);
	const [itemsPerPage] = useState(10);

	// Get partner ID from user context
	const partnerId = user?.partnerId || user?.id;

	// API parameters for customer query
	const queryParams = useMemo(
		() => ({
			page: currentPage,
			limit: itemsPerPage,
			search: searchTerm || undefined,
			status: statusFilter || undefined,
		}),
		[currentPage, itemsPerPage, searchTerm, statusFilter],
	);

	// Use real API data instead of mock data
	const customersQuery = usePartnerDataWithErrorBoundary(
		usePartnerCustomers(partnerId, queryParams),
	);

	const { data: customersData, isLoading, error } = customersQuery;
	const [sortBy, setSortBy] = useState<string>("name");
	const [selectedCustomers, setSelectedCustomers] = useState<string[]>([]);

	// Show loading state
	if (isLoading) {
		return (
			<ErrorBoundary componentName="CustomerManagement" level="section">
				<div className="space-y-6">
					<div className="flex items-center justify-between">
						<div>
							<h1 className="font-bold text-2xl text-gray-900">
								Customer Management
							</h1>
							<p className="mt-1 text-gray-600">
								Manage your customer base and track performance
							</p>
						</div>
					</div>
					<TableLoading rows={8} columns={6} />
				</div>
			</ErrorBoundary>
		);
	}

	// Show error state
	if (error) {
		return (
			<div className="flex items-center justify-center h-64">
				<div className="text-center">
					<AlertCircle className="mx-auto h-12 w-12 text-red-500 mb-4" />
					<h3 className="text-lg font-medium text-gray-900 mb-2">
						Failed to load customers
					</h3>
					<p className="text-gray-600 mb-4">
						There was an error loading your customer data.
					</p>
					<Button onClick={() => window.location.reload()}>Retry</Button>
				</div>
			</div>
		);
	}

	const customers = customersData?.customers || [];
	const totalCustomers = customersData?.total || 0;

	// Simple formatting utilities (to be replaced by actual implementation)
	const formatCurrency = (amount: number) => `$${amount.toFixed(2)}`;
	const formatDate = (date: string) => new Date(date).toLocaleDateString();
	const formatStatus = (status: string) =>
		status.charAt(0).toUpperCase() + status.slice(1);
	const formatPlan = (plan: string) => plan.replace(/_/g, " ").toUpperCase();

	const getConnectionColor = (status: string) => {
		switch (status) {
			case "online":
				return "text-green-600";
			case "offline":
				return "text-red-600";
			default:
				return "text-gray-600";
		}
	};

	// Note: Filtering is now handled server-side via API parameters
	// This local filtering is for client-side display only and should be minimal
	const filteredCustomers = customers.sort((a: Customer, b: Customer) => {
		switch (sortBy) {
			case "name":
				return a.name.localeCompare(b.name);
			case "mrr":
				return b.mrr - a.mrr;
			case "joinDate":
				return new Date(b.joinDate).getTime() - new Date(a.joinDate).getTime();
			default:
				return 0;
		}
	});

	const handleSelectCustomer = (customerId: string) => {
		setSelectedCustomers((prev) =>
			prev.includes(customerId)
				? prev.filter((id) => id !== customerId)
				: [...prev, customerId],
		);
	};

	const handleSelectAll = () => {
		if (selectedCustomers.length === filteredCustomers.length) {
			setSelectedCustomers([]);
		} else {
			setSelectedCustomers(filteredCustomers.map((c: Customer) => c.id));
		}
	};

	const totalMRR = customers.reduce(
		(sum: number, customer: Customer) => sum + customer.mrr,
		0,
	);
	const activeCustomers = customers.filter(
		(c: Customer) => c.status === "active",
	).length;

	return (
		<ErrorBoundary componentName="CustomerManagement" level="section">
			<div className="space-y-6">
				{/* Header */}
				<div className="flex items-center justify-between">
					<div>
						<h1 className="font-bold text-2xl text-gray-900">
							Customer Management
						</h1>
						<p className="mt-1 text-gray-600">
							Manage your customer base and track performance
						</p>
					</div>
					<Button variant="primary">
						<Plus className="mr-2 h-4 w-4" />
						Add Customer
					</Button>
				</div>

				{/* Summary Cards */}
				<div className="grid grid-cols-1 gap-6 md:grid-cols-4">
					<Card>
						<div className="flex items-center">
							<div className="rounded-full bg-blue-100 p-3">
								<Users className="h-6 w-6 text-blue-600" />
							</div>
							<div className="ml-4">
								<p className="font-medium text-gray-600 text-sm">
									Total Customers
								</p>
								<p className="font-bold text-2xl text-gray-900">
									{totalCustomers}
								</p>
							</div>
						</div>
					</Card>

					<Card>
						<div className="flex items-center">
							<div className="rounded-full bg-green-100 p-3">
								<Wifi className="h-6 w-6 text-green-600" />
							</div>
							<div className="ml-4">
								<p className="font-medium text-gray-600 text-sm">Active</p>
								<p className="font-bold text-2xl text-gray-900">
									{activeCustomers}
								</p>
							</div>
						</div>
					</Card>

					<Card>
						<div className="flex items-center">
							<div className="rounded-full bg-purple-100 p-3">
								<DollarSign className="h-6 w-6 text-purple-600" />
							</div>
							<div className="ml-4">
								<p className="font-medium text-gray-600 text-sm">Total MRR</p>
								<p className="font-bold text-2xl text-gray-900">
									{formatCurrency(totalMRR)}
								</p>
							</div>
						</div>
					</Card>

					<Card>
						<div className="flex items-center">
							<div className="rounded-full bg-orange-100 p-3">
								<Calendar className="h-6 w-6 text-orange-600" />
							</div>
							<div className="ml-4">
								<p className="font-medium text-gray-600 text-sm">
									Avg. Customer Age
								</p>
								<p className="font-bold text-2xl text-gray-900">
									8.5<span className="text-gray-600 text-sm">mo</span>
								</p>
							</div>
						</div>
					</Card>
				</div>

				{/* Filters and Search */}
				<Card>
					<div className="flex flex-col space-y-4 sm:flex-row sm:items-center sm:justify-between sm:space-y-0">
						<div className="flex flex-col space-y-4 sm:flex-row sm:space-x-4 sm:space-y-0">
							<div className="w-full sm:w-80">
								<Input
									leftIcon={<Search className="h-4 w-4" />}
									placeholder="Search customers..."
									value={searchTerm}
									onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
										setSearchTerm(e.target.value);
										setCurrentPage(1); // Reset to first page when searching
									}}
								/>
							</div>

							<div className="flex space-x-2">
								<select
									value={statusFilter}
									onChange={(e) => {
										setStatusFilter(e.target.value);
										setCurrentPage(1); // Reset to first page when filtering
									}}
									className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-blue-500"
								>
									<option value="">All Status</option>
									<option value="active">Active</option>
									<option value="pending">Pending</option>
									<option value="suspended">Suspended</option>
									<option value="cancelled">Cancelled</option>
								</select>

								<select
									value={sortBy}
									onChange={(e) => setSortBy(e.target.value)}
									className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-blue-500"
								>
									<option value="name">Sort by Name</option>
									<option value="mrr">Sort by MRR</option>
									<option value="joinDate">Sort by Join Date</option>
								</select>
							</div>
						</div>

						<div className="flex space-x-2">
							{selectedCustomers.length > 0 && (
								<Button variant="outline" size="sm">
									<Download className="mr-2 h-4 w-4" />
									Export ({selectedCustomers.length})
								</Button>
							)}
							<Button variant="outline" size="sm">
								<Filter className="mr-2 h-4 w-4" />
								Filters
							</Button>
						</div>
					</div>
				</Card>

				{/* Customer Table */}
				<Card>
					<div className="overflow-x-auto">
						<table className="min-w-full divide-y divide-gray-200">
							<thead className="bg-gray-50">
								<tr>
									<th className="px-6 py-3 text-left">
										<input
											type="checkbox"
											checked={
												selectedCustomers.length === filteredCustomers.length &&
												filteredCustomers.length > 0
											}
											onChange={handleSelectAll}
											className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
										/>
									</th>
									<th className="px-6 py-3 text-left font-medium text-gray-500 text-xs uppercase tracking-wider">
										Customer
									</th>
									<th className="px-6 py-3 text-left font-medium text-gray-500 text-xs uppercase tracking-wider">
										Plan & Usage
									</th>
									<th className="px-6 py-3 text-left font-medium text-gray-500 text-xs uppercase tracking-wider">
										Status
									</th>
									<th className="px-6 py-3 text-left font-medium text-gray-500 text-xs uppercase tracking-wider">
										MRR
									</th>
									<th className="px-6 py-3 text-left font-medium text-gray-500 text-xs uppercase tracking-wider">
										Last Payment
									</th>
									<th className="px-6 py-3 text-right font-medium text-gray-500 text-xs uppercase tracking-wider">
										Actions
									</th>
								</tr>
							</thead>
							<tbody className="divide-y divide-gray-200 bg-white">
								{filteredCustomers.map((customer: Customer) => (
									<tr key={customer.id} className="hover:bg-gray-50">
										<td className="px-6 py-4">
											<input
												type="checkbox"
												checked={selectedCustomers.includes(customer.id)}
												onChange={() => handleSelectCustomer(customer.id)}
												className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
											/>
										</td>

										<td className="px-6 py-4">
											<div className="flex items-center">
												<div className="flex-shrink-0">
													<div className="flex h-10 w-10 items-center justify-center rounded-full bg-gray-200">
														<Users className="h-5 w-5 text-gray-600" />
													</div>
												</div>
												<div className="ml-4">
													<div className="font-medium text-gray-900 text-sm">
														{customer.name}
													</div>
													<div className="flex items-center text-gray-500 text-sm">
														<Mail className="mr-1 h-3 w-3" />
														{customer.email}
													</div>
													<div className="flex items-center text-gray-500 text-sm">
														<Phone className="mr-1 h-3 w-3" />
														{customer.phone}
													</div>
												</div>
											</div>
										</td>

										<td className="px-6 py-4">
											<div className="font-medium text-gray-900 text-sm">
												{formatPlan(customer.plan)}
											</div>
											<div className="text-gray-500 text-sm">
												Usage: {customer.usage}%
											</div>
											<div className="flex items-center text-xs">
												<div
													className={`mr-2 h-2 w-2 rounded-full ${customer.connectionStatus === "online" ? "bg-green-400" : "bg-red-400"}`}
												/>
												<span
													className={getConnectionColor(
														customer.connectionStatus,
													)}
												>
													{customer.connectionStatus}
												</span>
											</div>
										</td>

										<td className="px-6 py-4">
											<Badge variant="default" size="sm">
												{formatStatus(customer.status)}
											</Badge>
										</td>

										<td className="px-6 py-4">
											<div className="font-medium text-gray-900 text-sm">
												{formatCurrency(customer.mrr)}
											</div>
											<div className="text-gray-500 text-xs">per month</div>
										</td>

										<td className="px-6 py-4 text-gray-900 text-sm">
											{customer.lastPayment
												? formatDate(customer.lastPayment)
												: "Never"}
										</td>

										<td className="px-6 py-4 text-right">
											<div className="flex items-center justify-end space-x-2">
												<Button variant="ghost" size="sm">
													<Eye className="h-4 w-4" />
												</Button>
												<Button variant="ghost" size="sm">
													<Edit className="h-4 w-4" />
												</Button>
												<Button variant="ghost" size="sm">
													<MoreHorizontal className="h-4 w-4" />
												</Button>
											</div>
										</td>
									</tr>
								))}
							</tbody>
						</table>
					</div>

					{filteredCustomers.length === 0 && (
						<div className="py-12 text-center">
							<Users className="mx-auto h-12 w-12 text-gray-400" />
							<h3 className="mt-2 font-medium text-gray-900 text-sm">
								No customers found
							</h3>
							<p className="mt-1 text-gray-500 text-sm">
								{searchTerm || statusFilter !== "all"
									? "Try adjusting your search or filter criteria."
									: "Get started by adding your first customer."}
							</p>
						</div>
					)}
				</Card>
			</div>
		</ErrorBoundary>
	);
}
