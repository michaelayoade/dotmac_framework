/**
 * Type definitions for the Reseller Portal
 */

// Base types
export interface BaseEntity {
	id: string;
	createdAt: string;
	updatedAt: string;
}

// User and Partner types
export interface User extends BaseEntity {
	email: string;
	name: string;
	role: "partner" | "reseller" | "admin";
	partnerId?: string;
	territory?: string;
	permissions: string[];
}

export interface Partner extends BaseEntity {
	name: string;
	email: string;
	phone: string;
	territory: string;
	status: "active" | "pending" | "suspended" | "cancelled";
	commissionRate: number;
	totalEarnings: number;
	customersCount: number;
}

// Customer types
export interface Customer extends BaseEntity {
	name: string;
	email: string;
	phone: string;
	company?: string;
	address?: string;
	city?: string;
	state?: string;
	zipCode?: string;
	status:
		| "active"
		| "pending"
		| "suspended"
		| "cancelled"
		| "prospect"
		| "qualified"
		| "negotiating";
	source: "website" | "referral" | "campaign" | "cold-call" | "social";
	plan: string;
	usage: number;
	mrr: number;
	monthlyRevenue: number;
	connectionStatus: "online" | "offline";
	joinDate: string;
	signupDate?: string;
	lastPayment?: string;
	lastContact?: string;
	nextFollowUp?: string;
	probability?: number;
	dealSize?: number;
	lifetimeValue?: number;
	contractLength?: number;
	notes?: string;
	tags?: string[];
}

// Commission types
export interface Commission extends BaseEntity {
	partnerId: string;
	customerId: string;
	amount: number;
	rate: number;
	period: string;
	status: "pending" | "paid" | "cancelled";
	paidAt?: string;
	invoiceId?: string;
}

export interface CommissionSummary {
	thisMonth: number;
	totalEarned: number;
	pending: number;
	nextPayout: {
		date: string;
		amount: number;
	};
}

// Analytics and Dashboard types
export interface DashboardMetrics {
	totalCustomers: number;
	activeCustomers: number;
	totalMRR: number;
	avgCustomerAge: number;
	conversionRate: number;
	churnRate: number;
}

export interface SalesGoal {
	id: string;
	title: string;
	target: number;
	current: number;
	progress: number;
	remaining: number;
	dueDate: string;
	type: "monthly" | "quarterly" | "yearly";
}

export interface SalesOpportunity {
	id: string;
	title: string;
	customer: string;
	value: number;
	probability: number;
	stage: string;
	expectedClose: string;
	lastActivity: string;
}

// Territory types
export interface Territory {
	id: string;
	name: string;
	partnerId: string;
	boundaries: {
		type: "polygon" | "circle" | "zip_codes";
		coordinates?: number[][];
		center?: [number, number];
		radius?: number;
		zipCodes?: string[];
	};
	population: number;
	customerCount: number;
	marketPenetration: number;
	averageIncome: number;
}

// Chart and Analytics types
export interface ChartDataPoint {
	date: string;
	value: number;
	label?: string;
}

export interface PieChartData {
	name: string;
	value: number;
	color: string;
}

export interface ServiceBreakdown {
	name: string;
	count: number;
	percentage: number;
	color: string;
}

// Form types
export interface FormField {
	name: string;
	label: string;
	type: "text" | "email" | "password" | "select" | "textarea" | "checkbox";
	required: boolean;
	placeholder?: string;
	options?: Array<{ value: string; label: string }>;
	validation?: {
		pattern?: RegExp;
		minLength?: number;
		maxLength?: number;
		custom?: (value: any) => boolean | string;
	};
}

export interface FormErrors {
	[key: string]: string;
}

// API Response types
export interface ApiResponse<T = any> {
	success: boolean;
	data?: T;
	error?: string;
	message?: string;
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
	pagination: {
		page: number;
		limit: number;
		total: number;
		totalPages: number;
	};
}

// Loading and Error states
export interface LoadingState {
	isLoading: boolean;
	error: string | null;
}

export interface AsyncState<T> extends LoadingState {
	data: T | null;
}
