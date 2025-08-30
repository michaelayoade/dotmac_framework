"use client";

import { usePortalAuth, useSecureForm } from "@dotmac/headless";
import { CSRFToken, OptimizedImage } from "@dotmac/providers";
import { Button, Card, Input } from "@dotmac/ui/reseller";
import {
	AlertCircle,
	DollarSign,
	Eye,
	EyeOff,
	TrendingUp,
	Users,
} from "lucide-react";
import { useId, useState } from "react";
import type { FormField } from "../../types";
import { logger } from "../../utils/logger";
import { AccessibleInput, useFormValidation } from "../common/AccessibleForm";

// Partner login form fields with validation
const loginFields: FormField[] = [
	{
		name: "email",
		label: "Email Address",
		type: "email",
		required: true,
		placeholder: "Enter your partner email address",
		validation: {
			pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
			maxLength: 254,
		},
	},
	{
		name: "password",
		label: "Password",
		type: "password",
		required: true,
		placeholder: "Enter your password",
		validation: {
			minLength: 8,
			maxLength: 128,
		},
	},
];

export function ResellerLogin() {
	const id = useId();

	const {
		loginWithPortal,
		isLoading,
		error,
		currentPortal,
		getLoginMethods,
		getPortalBranding,
	} = usePortalAuth();

	// Form validation hook
	const { values, errors, isSubmitting, setValue, handleSubmit } =
		useFormValidation(loginFields);

	const availableLoginMethods = getLoginMethods();
	const branding = getPortalBranding();
	const requiresPartnerCode = availableLoginMethods.includes("partner_code");

	// Use secure form with validation
	const form = useSecureForm({
		schema: PartnerLoginSchema,
		onSubmit: async (data: any) => {
			try {
				await loginWithPortal(data);
			} catch (error) {
				logger.error("Login failed", error, { component: "login" });
			}
		},
		initialValues: {
			email: "",
			partnerCode: "",
			password: "",
			territory: "",
			rememberMe: false,
		},
		validateOnBlur: true,
		enableCSRFProtection: true,
	});

	const { values, handleChange, handleSubmit, getFieldError, hasFieldError } =
		form;

	// Local state for UI
	const [showPassword, setShowPassword] = useState(false);

	const handlePasswordToggle = () => {
		setShowPassword(!showPassword);
	};

	if (!currentPortal) {
		return (
			<div className="flex min-h-screen items-center justify-center">
				<div className="text-center">
					<div className="mx-auto h-8 w-8 animate-spin rounded-full border-green-600 border-b-2" />
					<p className="mt-4 text-gray-600">Loading partner portal...</p>
				</div>
			</div>
		);
	}

	return (
		<div className="min-h-screen bg-gradient-to-br from-green-50 to-emerald-100">
			{/* Header */}
			<header className="bg-white shadow-sm">
				<div className="container mx-auto px-4 py-4">
					<div className="flex items-center space-x-2">
						{branding?.logo ? (
							<OptimizedImage
								src={branding.logo}
								alt={branding.companyName}
								className="h-8"
							/>
						) : (
							<div
								className="flex h-8 w-8 items-center justify-center rounded-lg"
								style={{ backgroundColor: branding?.primaryColor }}
							>
								<span className="font-bold text-sm text-white">
									{branding?.companyName?.charAt(0) || "D"}
								</span>
							</div>
						)}
						<h1 className="font-semibold text-gray-900 text-xl">
							{branding?.companyName || "Partner Portal"}
						</h1>
					</div>
				</div>
			</header>

			<div className="container mx-auto px-4 py-16">
				<div className="mx-auto max-w-6xl">
					<div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-2">
						{/* Left side - Partner benefits */}
						<div>
							<h1 className="mb-6 font-bold text-4xl text-gray-900">
								Partner Portal Access
							</h1>
							<p className="mb-8 text-gray-600 text-xl">
								Manage your customers, track commissions, and grow your business
								with our comprehensive partner tools.
							</p>

							<div className="space-y-6">
								<div className="flex items-start space-x-4">
									<div className="rounded-lg bg-green-100 p-3">
										<Users className="h-6 w-6 text-green-600" />
									</div>
									<div>
										<h3 className="font-semibold text-gray-900">
											Customer Management
										</h3>
										<p className="text-gray-600">
											Onboard new customers and manage existing accounts with
											ease
										</p>
									</div>
								</div>

								<div className="flex items-start space-x-4">
									<div className="rounded-lg bg-green-100 p-3">
										<DollarSign className="h-6 w-6 text-green-600" />
									</div>
									<div>
										<h3 className="font-semibold text-gray-900">
											Commission Tracking
										</h3>
										<p className="text-gray-600">
											Real-time commission tracking and transparent payout
											schedules
										</p>
									</div>
								</div>

								<div className="flex items-start space-x-4">
									<div className="rounded-lg bg-green-100 p-3">
										<TrendingUp className="h-6 w-6 text-green-600" />
									</div>
									<div>
										<h3 className="font-semibold text-gray-900">
											Sales Analytics
										</h3>
										<p className="text-gray-600">
											Detailed performance metrics and growth opportunities
										</p>
									</div>
								</div>
							</div>
						</div>

						{/* Right side - Login form */}
						<div>
							<Card className="p-8">
								<div className="mb-8 text-center">
									<h2 className="font-bold text-2xl text-gray-900">
										Partner Sign In
									</h2>
									<p className="mt-2 text-gray-600">
										Access your partner dashboard
									</p>
								</div>

								{error ? (
									<div className="mb-6 rounded-md border border-red-200 bg-red-50 p-4">
										<p className="text-red-700 text-sm">{error}</p>
									</div>
								) : null}

								<form onSubmit={handleSubmit} className="space-y-6">
									{/* CSRF Protection */}
									<CSRFToken />

									{/* Email */}
									<div>
										<label
											htmlFor="email"
											className="mb-2 block font-medium text-gray-700 text-sm"
										>
											Email Address
										</label>
										<Input
											id={`${id}-email`}
											name="email"
											type="email"
											autoComplete="email"
											required
											value={(values as any)?.email || ""}
											onChange={handleChange}
											placeholder="partner@yourcompany.com"
											className={`w-full ${hasFieldError("email") ? "border-red-500" : ""}`}
										/>
										{hasFieldError("email") && (
											<div className="mt-1 flex items-center text-red-600 text-sm">
												<AlertCircle className="h-4 w-4 mr-1" />
												{getFieldError("email")}
											</div>
										)}
									</div>

									{/* Partner Code (if required) */}
									{requiresPartnerCode ? (
										<div>
											<label
												htmlFor="partnerCode"
												className="mb-2 block font-medium text-gray-700 text-sm"
											>
												Partner Code
											</label>
											<Input
												id={`${id}-partnerCode`}
												name="partnerCode"
												type="text"
												autoComplete="organization"
												required={requiresPartnerCode}
												value={(values as any)?.partnerCode || ""}
												onChange={handleChange}
												placeholder="Your partner code"
												className={`w-full ${hasFieldError("partnerCode") ? "border-red-500" : ""}`}
											/>
											{hasFieldError("partnerCode") && (
												<div className="mt-1 flex items-center text-red-600 text-sm">
													<AlertCircle className="h-4 w-4 mr-1" />
													{getFieldError("partnerCode")}
												</div>
											)}
										</div>
									) : null}

									{/* Territory (optional) */}
									{requiresPartnerCode ? (
										<div>
											<label
												htmlFor="territory"
												className="mb-2 block font-medium text-gray-700 text-sm"
											>
												Territory{" "}
												<span className="text-gray-400">(optional)</span>
											</label>
											<Input
												id={`${id}-territory`}
												name="territory"
												type="text"
												value={(values as any)?.territory || ""}
												onChange={handleChange}
												placeholder="Your assigned territory"
												className="w-full"
											/>
										</div>
									) : null}

									{/* Password */}
									<div>
										<label
											htmlFor="password"
											className="mb-2 block font-medium text-gray-700 text-sm"
										>
											Password
										</label>
										<div className="relative">
											<Input
												id={`${id}-password`}
												name="password"
												type={showPassword ? "text" : "password"}
												autoComplete="current-password"
												required
												value={(values as any)?.password || ""}
												onChange={handleChange}
												placeholder="••••••••"
												className={`w-full pr-10 ${hasFieldError("password") ? "border-red-500" : ""}`}
											/>
											<button
												type="button"
												className="absolute inset-y-0 right-0 flex items-center pr-3"
												onClick={handlePasswordToggle}
												onKeyDown={(e) =>
													e.key === "Enter" && handlePasswordToggle
												}
											>
												{showPassword ? (
													<EyeOff className="h-5 w-5 text-gray-400" />
												) : (
													<Eye className="h-5 w-5 text-gray-400" />
												)}
											</button>
										</div>
										{hasFieldError("password") && (
											<div className="mt-1 flex items-center text-red-600 text-sm">
												<AlertCircle className="h-4 w-4 mr-1" />
												{getFieldError("password")}
											</div>
										)}
									</div>

									{/* Remember Me & Forgot Password */}
									<div className="flex items-center justify-between">
										<div className="flex items-center">
											<input
												id={`${id}-rememberMe`}
												name="rememberMe"
												type="checkbox"
												checked={(values as any)?.rememberMe || false}
												onChange={handleChange}
												className="h-4 w-4 rounded border-gray-300 text-green-600 focus:ring-green-500"
											/>
											<label
												htmlFor="rememberMe"
												className="ml-2 block text-gray-900 text-sm"
											>
												Remember me
											</label>
										</div>

										<button
											type="button"
											onClick={() => {
												/* TODO: Implement forgot password */
											}}
											className="font-medium text-sm hover:opacity-80"
											style={{ color: branding?.primaryColor }}
										>
											Forgot password?
										</button>
									</div>

									{/* Submit Button */}
									<Button
										type="submit"
										disabled={isLoading}
										className="w-full"
										size="lg"
										style={{ backgroundColor: branding?.primaryColor }}
									>
										{isLoading ? "Signing in..." : "Sign In"}
									</Button>
								</form>

								{/* Help Links */}
								<div className="mt-6 space-y-2 text-center">
									<p className="text-gray-600 text-sm">
										Not a partner yet?{" "}
										<button
											type="button"
											onClick={() => {
												/* TODO: Implement partner application */
											}}
											className="font-medium hover:opacity-80"
											style={{ color: branding?.primaryColor }}
										>
											Apply to become a partner
										</button>
									</p>

									<div className="border-gray-200 border-t pt-4">
										<p className="text-gray-500 text-xs">
											Partner support:{" "}
											<a
												href={`mailto:${process.env.NEXT_PUBLIC_SUPPORT_EMAIL || "partners@example.com"}`}
												className="text-green-600 hover:text-green-500"
											>
												{process.env.NEXT_PUBLIC_SUPPORT_EMAIL ||
													"partners@example.com"}
											</a>{" "}
											|{" "}
											<a
												href={`tel:+${process.env.NEXT_PUBLIC_SUPPORT_PHONE || "1-555-PARTNER"}`}
												className="text-green-600 hover:text-green-500"
											>
												{process.env.NEXT_PUBLIC_SUPPORT_PHONE ||
													"1-555-PARTNER"}
											</a>
										</p>
									</div>
								</div>
							</Card>
						</div>
					</div>
				</div>
			</div>
		</div>
	);
}
