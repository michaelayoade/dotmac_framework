"use client";

import { useCachedData } from "@dotmac/headless";
import { Card } from "@dotmac/ui/reseller";
import {
	type ColumnDef,
	flexRender,
	getCoreRowModel,
	getFilteredRowModel,
	getPaginationRowModel,
	getSortedRowModel,
	useReactTable,
} from "@tanstack/react-table";
import { format } from "date-fns";
import { AnimatePresence, motion } from "framer-motion";
import {
	Activity,
	AlertCircle,
	Building,
	Calendar,
	CheckCircle,
	Clock,
	DollarSign,
	Download,
	Edit3,
	Eye,
	Filter,
	Mail,
	MapPin,
	MoreHorizontal,
	Phone,
	Plus,
	Search,
	Star,
	Target,
	TrendingUp,
	Upload,
	Users,
	XCircle,
	Zap,
} from "lucide-react";
import { useMemo, useState } from "react";

interface Customer {
	id: string;
	name: string;
	company?: string;
	email: string;
	phone: string;
	address: string;
	city: string;
	state: string;
	zipCode: string;
	status:
		| "prospect"
		| "qualified"
		| "negotiating"
		| "active"
		| "inactive"
		| "churned";
	source:
		| "referral"
		| "website"
		| "campaign"
		| "cold-call"
		| "trade-show"
		| "partner";
	service?: string;
	monthlyRevenue: number;
	signupDate?: string;
	lastContact: string;
	nextFollowUp?: string;
	probability: number; // Conversion probability for prospects
	dealSize: number;
	salesRep: string;
	notes: string;
	tags: string[];
	lifetimeValue: number;
	contractLength?: number; // months
	paymentMethod?: string;
	creditScore?: number;
}

// Mock advanced customer data
const mockCustomers: Customer[] = [
	{
		id: "CUST-001",
		name: "Test User 001",
		company: "Test Company 001",
		email: "user001@dev.local",
		phone: "[REDACTED]",
		address: "123 Business Ave",
		city: "Seattle",
		state: "WA",
		zipCode: "98101",
		status: "active",
		source: "referral",
		service: "Fiber 1GB",
		monthlyRevenue: 299.99,
		signupDate: "2023-08-15",
		lastContact: "2024-01-20",
		probability: 100,
		dealSize: 299.99,
		salesRep: "Test Rep 001",
		notes: "Excellent customer, considering upgrade",
		tags: ["VIP", "High-Value", "Referrer"],
		lifetimeValue: 7199.76,
		contractLength: 24,
		paymentMethod: "ACH",
		creditScore: 750,
	},
	{
		id: "PROS-002",
		name: "Test User 002",
		company: "Rodriguez Consulting",
		email: "user002@dev.local",
		phone: "[REDACTED]",
		address: "456 Tech Park Dr",
		city: "Portland",
		state: "OR",
		zipCode: "97201",
		status: "qualified",
		source: "website",
		monthlyRevenue: 0,
		signupDate: "2024-01-15",
		lastContact: "2024-01-28",
		nextFollowUp: "2024-02-05",
		probability: 75,
		dealSize: 199.99,
		salesRep: "Test Rep 002",
		notes: "Interested in Fiber 500, budget approved",
		tags: ["Hot-Lead", "Decision-Maker"],
		lifetimeValue: 4799.76,
		contractLength: 12,
	},
	{
		id: "PROS-003",
		name: "Test User 003",
		company: "Kim Digital Agency",
		email: "user003@dev.local",
		phone: "[REDACTED]",
		address: "789 Creative Blvd",
		city: "San Francisco",
		state: "CA",
		zipCode: "94107",
		status: "prospect",
		source: "campaign",
		monthlyRevenue: 0,
		signupDate: "2024-01-15",
		lastContact: "2024-01-25",
		nextFollowUp: "2024-02-01",
		probability: 45,
		dealSize: 149.99,
		salesRep: "Test Rep 003",
		notes: "Needs dedicated IP, price-sensitive",
		tags: ["Price-Sensitive", "Tech-Savvy"],
		lifetimeValue: 3599.76,
		contractLength: 12,
	},
	{
		id: "CUST-004",
		name: "Test User 004",
		company: "Brown Medical Group",
		email: "user004@dev.local",
		phone: "[REDACTED]",
		address: "321 Health Way",
		city: "Denver",
		state: "CO",
		zipCode: "80202",
		status: "active",
		source: "trade-show",
		service: "Business 100MB",
		monthlyRevenue: 129.99,
		signupDate: "2023-11-10",
		lastContact: "2024-01-15",
		probability: 100,
		dealSize: 129.99,
		salesRep: "Test Rep 004",
		notes: "Healthcare client, compliance focused",
		tags: ["Healthcare", "Compliance"],
		lifetimeValue: 3119.76,
		contractLength: 36,
		paymentMethod: "Credit Card",
		creditScore: 720,
	},
	{
		id: "PROS-005",
		name: "Test User 005",
		company: "Wilson Manufacturing",
		email: "user005@dev.local",
		phone: "[REDACTED]",
		address: "654 Industrial Park",
		city: "Phoenix",
		state: "AZ",
		zipCode: "85001",
		status: "negotiating",
		source: "cold-call",
		monthlyRevenue: 0,
		signupDate: "2024-01-15",
		lastContact: "2024-01-30",
		nextFollowUp: "2024-02-03",
		probability: 80,
		dealSize: 399.99,
		salesRep: "Test Rep 001",
		notes: "Large contract, needs custom SLA",
		tags: ["Enterprise", "Custom-SLA"],
		lifetimeValue: 9599.76,
		contractLength: 12,
	},
];

export function CustomerManagementAdvanced() {
	const [searchTerm, setSearchTerm] = useState("");
	const [statusFilter, setStatusFilter] = useState<string>("all");
	const [sourceFilter, setSourceFilter] = useState<string>("all");
	const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(
		null,
	);
	const [showFilters, setShowFilters] = useState(false);

	const { data: customers = mockCustomers } = useCachedData(
		"customers-advanced",
		async () => mockCustomers,
		{
			ttl: 5 * 60 * 1000,
		},
	);

	const columns = useMemo<ColumnDef<Customer>[]>(
		() => [
			{
				accessorKey: "name",
				header: "Customer",
				cell: ({ row }) => (
					<div className="flex items-center space-x-3">
						<div className="flex-shrink-0">
							<div
								className={`w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-semibold ${
									row.original.status === "active"
										? "bg-green-500"
										: row.original.status === "prospect"
											? "bg-blue-500"
											: row.original.status === "qualified"
												? "bg-purple-500"
												: row.original.status === "negotiating"
													? "bg-orange-500"
													: "bg-gray-500"
								}`}
							>
								{row.original.name.charAt(0)}
							</div>
						</div>
						<div>
							<div className="text-sm font-medium text-gray-900">
								{row.original.name}
							</div>
							{row.original.company && (
								<div className="text-sm text-gray-500">
									{row.original.company}
								</div>
							)}
						</div>
					</div>
				),
			},
			{
				accessorKey: "status",
				header: "Status",
				cell: ({ row }) => (
					<span
						className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
							row.original.status === "active"
								? "bg-green-100 text-green-800"
								: row.original.status === "prospect"
									? "bg-blue-100 text-blue-800"
									: row.original.status === "qualified"
										? "bg-purple-100 text-purple-800"
										: row.original.status === "negotiating"
											? "bg-orange-100 text-orange-800"
											: row.original.status === "inactive"
												? "bg-gray-100 text-gray-800"
												: "bg-red-100 text-red-800"
						}`}
					>
						{row.original.status === "active" && (
							<CheckCircle className="w-3 h-3 mr-1" />
						)}
						{row.original.status === "prospect" && (
							<Eye className="w-3 h-3 mr-1" />
						)}
						{row.original.status === "qualified" && (
							<Star className="w-3 h-3 mr-1" />
						)}
						{row.original.status === "negotiating" && (
							<Target className="w-3 h-3 mr-1" />
						)}
						{row.original.status === "inactive" && (
							<Clock className="w-3 h-3 mr-1" />
						)}
						{row.original.status === "churned" && (
							<XCircle className="w-3 h-3 mr-1" />
						)}
						{row.original.status.replace("-", " ")}
					</span>
				),
			},
			{
				accessorKey: "source",
				header: "Source",
				cell: ({ row }) => (
					<span className="text-sm text-gray-600 capitalize">
						{row.original.source.replace("-", " ")}
					</span>
				),
			},
			{
				accessorKey: "probability",
				header: "Probability",
				cell: ({ row }) => (
					<div className="flex items-center space-x-2">
						<div className="flex-1">
							<div className="w-full bg-gray-200 rounded-full h-2">
								<div
									className={`h-2 rounded-full ${
										row.original.probability >= 75
											? "bg-green-500"
											: row.original.probability >= 50
												? "bg-yellow-500"
												: "bg-red-500"
									}`}
									style={{ width: `${row.original.probability}%` }}
								/>
							</div>
						</div>
						<span className="text-sm font-medium text-gray-900 w-10">
							{row.original.probability}%
						</span>
					</div>
				),
			},
			{
				accessorKey: "dealSize",
				header: "Deal Size",
				cell: ({ row }) => (
					<span className="text-sm font-medium text-gray-900">
						${row.original.dealSize.toFixed(2)}
					</span>
				),
			},
			{
				accessorKey: "lifetimeValue",
				header: "LTV",
				cell: ({ row }) => (
					<span className="text-sm font-medium text-green-600">
						${row.original.lifetimeValue.toLocaleString()}
					</span>
				),
			},
			{
				accessorKey: "lastContact",
				header: "Last Contact",
				cell: ({ row }) => (
					<span className="text-sm text-gray-600">
						{format(new Date(row.original.lastContact), "MMM dd, yyyy")}
					</span>
				),
			},
			{
				id: "actions",
				header: "",
				cell: ({ row }) => (
					<div className="flex items-center space-x-2">
						<button
							onClick={() => setSelectedCustomer(row.original)}
							className="p-1 text-gray-400 hover:text-gray-600"
						>
							<Eye className="w-4 h-4" />
						</button>
						<button className="p-1 text-gray-400 hover:text-gray-600">
							<Edit3 className="w-4 h-4" />
						</button>
						<button className="p-1 text-gray-400 hover:text-gray-600">
							<MoreHorizontal className="w-4 h-4" />
						</button>
					</div>
				),
			},
		],
		[],
	);

	const filteredData = useMemo(() => {
		return customers.filter((customer: any) => {
			const matchesSearch =
				customer.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
				customer.company?.toLowerCase().includes(searchTerm.toLowerCase()) ||
				customer.email.toLowerCase().includes(searchTerm.toLowerCase());

			const matchesStatus =
				statusFilter === "all" || customer.status === statusFilter;
			const matchesSource =
				sourceFilter === "all" || customer.source === sourceFilter;

			return matchesSearch && matchesStatus && matchesSource;
		});
	}, [customers, searchTerm, statusFilter, sourceFilter]);

	const table = useReactTable({
		data: filteredData,
		columns,
		getCoreRowModel: getCoreRowModel(),
		getFilteredRowModel: getFilteredRowModel(),
		getSortedRowModel: getSortedRowModel(),
		getPaginationRowModel: getPaginationRowModel(),
		initialState: {
			pagination: {
				pageSize: 10,
			},
		},
	});

	const getStatusIcon = (status: string) => {
		switch (status) {
			case "active":
				return <CheckCircle className="w-4 h-4 text-green-600" />;
			case "prospect":
				return <Eye className="w-4 h-4 text-blue-600" />;
			case "qualified":
				return <Star className="w-4 h-4 text-purple-600" />;
			case "negotiating":
				return <Target className="w-4 h-4 text-orange-600" />;
			case "inactive":
				return <Clock className="w-4 h-4 text-gray-600" />;
			default:
				return <XCircle className="w-4 h-4 text-red-600" />;
		}
	};

	const analytics = useMemo(() => {
		const total = customers.length;
		const active = customers.filter((c: any) => c.status === "active").length;
		const prospects = customers.filter((c: any) =>
			["prospect", "qualified", "negotiating"].includes(c.status),
		).length;
		const totalRevenue = customers.reduce(
			(sum: number, c: any) => sum + c.monthlyRevenue,
			0,
		);
		const avgDealSize =
			customers.reduce((sum: number, c: any) => sum + c.dealSize, 0) / total;
		const avgProbability =
			customers.reduce((sum: number, c: any) => sum + c.probability, 0) / total;

		return {
			total,
			active,
			prospects,
			totalRevenue,
			avgDealSize,
			avgProbability,
		};
	}, [customers]);

	return (
		<div className="space-y-6">
			{/* Analytics Overview */}
			<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
				<motion.div
					initial={{ opacity: 0, y: 20 }}
					animate={{ opacity: 1, y: 0 }}
					transition={{ duration: 0.5 }}
				>
					<Card className="p-6 bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
						<div className="flex items-center justify-between">
							<div>
								<p className="text-blue-700 text-sm font-medium">
									Total Customers
								</p>
								<p className="text-3xl font-bold text-blue-800">
									{analytics.total}
								</p>
								<p className="text-blue-600 text-sm">
									{analytics.active} active
								</p>
							</div>
							<Users className="h-8 w-8 text-blue-600" />
						</div>
					</Card>
				</motion.div>

				<motion.div
					initial={{ opacity: 0, y: 20 }}
					animate={{ opacity: 1, y: 0 }}
					transition={{ duration: 0.5, delay: 0.1 }}
				>
					<Card className="p-6 bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200">
						<div className="flex items-center justify-between">
							<div>
								<p className="text-purple-700 text-sm font-medium">
									Active Prospects
								</p>
								<p className="text-3xl font-bold text-purple-800">
									{analytics.prospects}
								</p>
								<p className="text-purple-600 text-sm">In pipeline</p>
							</div>
							<Target className="h-8 w-8 text-purple-600" />
						</div>
					</Card>
				</motion.div>

				<motion.div
					initial={{ opacity: 0, y: 20 }}
					animate={{ opacity: 1, y: 0 }}
					transition={{ duration: 0.5, delay: 0.2 }}
				>
					<Card className="p-6 bg-gradient-to-br from-green-50 to-green-100 border-green-200">
						<div className="flex items-center justify-between">
							<div>
								<p className="text-green-700 text-sm font-medium">
									Monthly Revenue
								</p>
								<p className="text-3xl font-bold text-green-800">
									${analytics.totalRevenue.toLocaleString()}
								</p>
								<p className="text-green-600 text-sm">Current MRR</p>
							</div>
							<DollarSign className="h-8 w-8 text-green-600" />
						</div>
					</Card>
				</motion.div>

				<motion.div
					initial={{ opacity: 0, y: 20 }}
					animate={{ opacity: 1, y: 0 }}
					transition={{ duration: 0.5, delay: 0.3 }}
				>
					<Card className="p-6 bg-gradient-to-br from-orange-50 to-orange-100 border-orange-200">
						<div className="flex items-center justify-between">
							<div>
								<p className="text-orange-700 text-sm font-medium">
									Avg Deal Size
								</p>
								<p className="text-3xl font-bold text-orange-800">
									${analytics.avgDealSize.toFixed(0)}
								</p>
								<p className="text-orange-600 text-sm">
									{analytics.avgProbability.toFixed(1)}% avg probability
								</p>
							</div>
							<TrendingUp className="h-8 w-8 text-orange-600" />
						</div>
					</Card>
				</motion.div>
			</div>

			{/* Controls */}
			<Card className="p-6">
				<div className="flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-4 lg:space-y-0">
					<div className="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-4">
						<div className="relative">
							<Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
							<input
								type="text"
								placeholder="Search customers..."
								value={searchTerm}
								onChange={(e) => setSearchTerm(e.target.value)}
								className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
							/>
						</div>

						<button
							onClick={() => setShowFilters(!showFilters)}
							className={`flex items-center space-x-2 px-4 py-2 border rounded-lg transition-colors ${
								showFilters
									? "border-green-500 bg-green-50 text-green-700"
									: "border-gray-300 text-gray-700 hover:bg-gray-50"
							}`}
						>
							<Filter className="w-4 h-4" />
							<span>Filters</span>
						</button>
					</div>

					<div className="flex space-x-2">
						<button className="flex items-center space-x-2 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50">
							<Download className="w-4 h-4" />
							<span>Export</span>
						</button>
						<button className="flex items-center space-x-2 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50">
							<Upload className="w-4 h-4" />
							<span>Import</span>
						</button>
						<button className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">
							<Plus className="w-4 h-4" />
							<span>Add Customer</span>
						</button>
					</div>
				</div>

				<AnimatePresence>
					{showFilters && (
						<motion.div
							initial={{ opacity: 0, height: 0 }}
							animate={{ opacity: 1, height: "auto" }}
							exit={{ opacity: 0, height: 0 }}
							className="mt-4 pt-4 border-t border-gray-200"
						>
							<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
								<div>
									<label className="block text-sm font-medium text-gray-700 mb-1">
										Status
									</label>
									<select
										value={statusFilter}
										onChange={(e) => setStatusFilter(e.target.value)}
										className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
									>
										<option value="all">All Statuses</option>
										<option value="prospect">Prospect</option>
										<option value="qualified">Qualified</option>
										<option value="negotiating">Negotiating</option>
										<option value="active">Active</option>
										<option value="inactive">Inactive</option>
										<option value="churned">Churned</option>
									</select>
								</div>

								<div>
									<label className="block text-sm font-medium text-gray-700 mb-1">
										Source
									</label>
									<select
										value={sourceFilter}
										onChange={(e) => setSourceFilter(e.target.value)}
										className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
									>
										<option value="all">All Sources</option>
										<option value="referral">Referral</option>
										<option value="website">Website</option>
										<option value="campaign">Campaign</option>
										<option value="cold-call">Cold Call</option>
										<option value="trade-show">Trade Show</option>
										<option value="partner">Partner</option>
									</select>
								</div>
							</div>
						</motion.div>
					)}
				</AnimatePresence>
			</Card>

			{/* Customer Table */}
			<Card className="p-6">
				<div className="overflow-x-auto">
					<table className="min-w-full divide-y divide-gray-200">
						<thead className="bg-gray-50">
							{table.getHeaderGroups().map((headerGroup) => (
								<tr key={headerGroup.id}>
									{headerGroup.headers.map((header) => (
										<th
											key={header.id}
											className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
											onClick={header.column.getToggleSortingHandler()}
										>
											{header.isPlaceholder ? null : (
												<div className="flex items-center space-x-1">
													{flexRender(
														header.column.columnDef.header,
														header.getContext(),
													)}
													{{
														asc: " 🔼",
														desc: " 🔽",
													}[header.column.getIsSorted() as string] ?? null}
												</div>
											)}
										</th>
									))}
								</tr>
							))}
						</thead>
						<tbody className="bg-white divide-y divide-gray-200">
							{table.getRowModel().rows.map((row) => (
								<motion.tr
									key={row.id}
									initial={{ opacity: 0 }}
									animate={{ opacity: 1 }}
									className="hover:bg-gray-50"
								>
									{row.getVisibleCells().map((cell) => (
										<td key={cell.id} className="px-6 py-4 whitespace-nowrap">
											{flexRender(
												cell.column.columnDef.cell,
												cell.getContext(),
											)}
										</td>
									))}
								</motion.tr>
							))}
						</tbody>
					</table>
				</div>

				{/* Pagination */}
				<div className="flex items-center justify-between px-4 py-3 border-t border-gray-200">
					<div className="flex items-center space-x-2">
						<span className="text-sm text-gray-700">
							Showing{" "}
							{table.getState().pagination.pageIndex *
								table.getState().pagination.pageSize +
								1}{" "}
							to{" "}
							{Math.min(
								(table.getState().pagination.pageIndex + 1) *
									table.getState().pagination.pageSize,
								table.getFilteredRowModel().rows.length,
							)}{" "}
							of {table.getFilteredRowModel().rows.length} results
						</span>
					</div>
					<div className="flex items-center space-x-2">
						<button
							onClick={() => table.previousPage()}
							disabled={!table.getCanPreviousPage()}
							className="px-3 py-1 border border-gray-300 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed"
						>
							Previous
						</button>
						<button
							onClick={() => table.nextPage()}
							disabled={!table.getCanNextPage()}
							className="px-3 py-1 border border-gray-300 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed"
						>
							Next
						</button>
					</div>
				</div>
			</Card>

			{/* Customer Detail Modal */}
			<AnimatePresence>
				{selectedCustomer && (
					<motion.div
						initial={{ opacity: 0 }}
						animate={{ opacity: 1 }}
						exit={{ opacity: 0 }}
						className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
						onClick={() => setSelectedCustomer(null)}
					>
						<motion.div
							initial={{ scale: 0.95, opacity: 0 }}
							animate={{ scale: 1, opacity: 1 }}
							exit={{ scale: 0.95, opacity: 0 }}
							className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
							onClick={(e) => e.stopPropagation()}
						>
							<div className="p-6">
								<div className="flex items-center justify-between mb-6">
									<div className="flex items-center space-x-3">
										{getStatusIcon(selectedCustomer.status)}
										<h2 className="text-xl font-semibold text-gray-900">
											{selectedCustomer.name}
										</h2>
									</div>
									<button
										onClick={() => setSelectedCustomer(null)}
										className="text-gray-400 hover:text-gray-600"
									>
										<XCircle className="w-6 h-6" />
									</button>
								</div>

								<div className="grid grid-cols-1 md:grid-cols-2 gap-6">
									<div className="space-y-4">
										<div>
											<h3 className="text-sm font-medium text-gray-700 mb-2">
												Contact Information
											</h3>
											<div className="space-y-2">
												<div className="flex items-center space-x-2">
													<Mail className="w-4 h-4 text-gray-400" />
													<span className="text-sm text-gray-600">
														{selectedCustomer.email}
													</span>
												</div>
												<div className="flex items-center space-x-2">
													<Phone className="w-4 h-4 text-gray-400" />
													<span className="text-sm text-gray-600">
														{selectedCustomer.phone}
													</span>
												</div>
												<div className="flex items-center space-x-2">
													<MapPin className="w-4 h-4 text-gray-400" />
													<span className="text-sm text-gray-600">
														{selectedCustomer.address}, {selectedCustomer.city},{" "}
														{selectedCustomer.state} {selectedCustomer.zipCode}
													</span>
												</div>
												{selectedCustomer.company && (
													<div className="flex items-center space-x-2">
														<Building className="w-4 h-4 text-gray-400" />
														<span className="text-sm text-gray-600">
															{selectedCustomer.company}
														</span>
													</div>
												)}
											</div>
										</div>

										<div>
											<h3 className="text-sm font-medium text-gray-700 mb-2">
												Deal Information
											</h3>
											<div className="space-y-2">
												<div className="flex justify-between">
													<span className="text-sm text-gray-600">
														Deal Size:
													</span>
													<span className="text-sm font-medium text-gray-900">
														${selectedCustomer.dealSize}
													</span>
												</div>
												<div className="flex justify-between">
													<span className="text-sm text-gray-600">
														Probability:
													</span>
													<span className="text-sm font-medium text-gray-900">
														{selectedCustomer.probability}%
													</span>
												</div>
												<div className="flex justify-between">
													<span className="text-sm text-gray-600">Source:</span>
													<span className="text-sm font-medium text-gray-900 capitalize">
														{selectedCustomer.source.replace("-", " ")}
													</span>
												</div>
												<div className="flex justify-between">
													<span className="text-sm text-gray-600">
														Sales Rep:
													</span>
													<span className="text-sm font-medium text-gray-900">
														{selectedCustomer.salesRep}
													</span>
												</div>
											</div>
										</div>
									</div>

									<div className="space-y-4">
										<div>
											<h3 className="text-sm font-medium text-gray-700 mb-2">
												Timeline
											</h3>
											<div className="space-y-2">
												<div className="flex justify-between">
													<span className="text-sm text-gray-600">
														Last Contact:
													</span>
													<span className="text-sm font-medium text-gray-900">
														{format(
															new Date(selectedCustomer.lastContact),
															"MMM dd, yyyy",
														)}
													</span>
												</div>
												{selectedCustomer.nextFollowUp && (
													<div className="flex justify-between">
														<span className="text-sm text-gray-600">
															Next Follow-up:
														</span>
														<span className="text-sm font-medium text-green-600">
															{format(
																new Date(selectedCustomer.nextFollowUp),
																"MMM dd, yyyy",
															)}
														</span>
													</div>
												)}
												{selectedCustomer.signupDate && (
													<div className="flex justify-between">
														<span className="text-sm text-gray-600">
															Signup Date:
														</span>
														<span className="text-sm font-medium text-gray-900">
															{format(
																new Date(selectedCustomer.signupDate),
																"MMM dd, yyyy",
															)}
														</span>
													</div>
												)}
											</div>
										</div>

										{selectedCustomer.status === "active" && (
											<div>
												<h3 className="text-sm font-medium text-gray-700 mb-2">
													Account Details
												</h3>
												<div className="space-y-2">
													<div className="flex justify-between">
														<span className="text-sm text-gray-600">
															Service:
														</span>
														<span className="text-sm font-medium text-gray-900">
															{selectedCustomer.service}
														</span>
													</div>
													<div className="flex justify-between">
														<span className="text-sm text-gray-600">
															Monthly Revenue:
														</span>
														<span className="text-sm font-medium text-green-600">
															${selectedCustomer.monthlyRevenue}
														</span>
													</div>
													<div className="flex justify-between">
														<span className="text-sm text-gray-600">
															Lifetime Value:
														</span>
														<span className="text-sm font-medium text-green-600">
															${selectedCustomer.lifetimeValue.toLocaleString()}
														</span>
													</div>
													{selectedCustomer.contractLength && (
														<div className="flex justify-between">
															<span className="text-sm text-gray-600">
																Contract:
															</span>
															<span className="text-sm font-medium text-gray-900">
																{selectedCustomer.contractLength} months
															</span>
														</div>
													)}
												</div>
											</div>
										)}
									</div>
								</div>

								{selectedCustomer.tags.length > 0 && (
									<div className="mt-6">
										<h3 className="text-sm font-medium text-gray-700 mb-2">
											Tags
										</h3>
										<div className="flex flex-wrap gap-2">
											{selectedCustomer.tags.map((tag) => (
												<span
													key={tag}
													className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
												>
													{tag}
												</span>
											))}
										</div>
									</div>
								)}

								{selectedCustomer.notes && (
									<div className="mt-6">
										<h3 className="text-sm font-medium text-gray-700 mb-2">
											Notes
										</h3>
										<p className="text-sm text-gray-600 bg-gray-50 p-3 rounded-lg">
											{selectedCustomer.notes}
										</p>
									</div>
								)}

								<div className="mt-6 flex justify-end space-x-3">
									<button className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50">
										Edit
									</button>
									<button className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">
										<Activity className="w-4 h-4" />
										<span>Create Activity</span>
									</button>
								</div>
							</div>
						</motion.div>
					</motion.div>
				)}
			</AnimatePresence>
		</div>
	);
}
