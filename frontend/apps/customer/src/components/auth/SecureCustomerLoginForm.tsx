"use client";

import {
	AlertCircle,
	CheckCircle,
	Eye,
	EyeOff,
	Lock,
	Mail,
	Shield,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useStandardErrorHandler } from '@dotmac/headless';
import {
	inputValidator,
	validateLoginForm,
} from "../../lib/validation/inputValidator";
import { useAuthActions } from "./SecureAuthProvider";

export function SecureCustomerLoginForm() {
	const router = useRouter();
	const { login } = useAuthActions();

	const [formData, setFormData] = useState({
		email: "",
		password: "",
		portalId: "",
		rememberMe: false,
	});

	const [showPassword, setShowPassword] = useState(false);
	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [success, setSuccess] = useState(false);
	const [validationErrors, setValidationErrors] = useState<
		Record<string, string[]>
	>({});
	const errorHandler = useStandardErrorHandler();
	const [attemptCount, setAttemptCount] = useState(0);

	// Rate limiting is handled server-side, frontend only tracks attempts for UI feedback

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setIsLoading(true);
		setError(null);
		setValidationErrors({});

		try {
			// Client-side validation
			const validation = validateLoginForm(formData.email, formData.password);
			if (!validation.isValid) {
				setValidationErrors(validation.errors);
				setIsLoading(false);
				return;
			}

			const result = await login({
				email: validation.sanitizedData.email,
				password: formData.password, // Don't use sanitized password
				portalId: formData.portalId || undefined,
			});

			if (result.success) {
				setSuccess(true);
				setAttemptCount(0); // Reset attempt count on success

				// Redirect to dashboard after successful login
				setTimeout(() => {
					router.push("/dashboard");
				}, 1500);
			} else {
				setAttemptCount(prev => prev + 1);
				const errorMessage = result.error || "Login failed";
				
				// Handle specific error types with user-friendly messages
				if (result.error?.includes('rate limit') || result.error?.includes('too many')) {
					setError("Too many login attempts. Please try again later.");
				} else if (result.error?.includes('credentials') || result.error?.includes('invalid')) {
					setError("Invalid email or password. Please check your credentials and try again.");
				} else {
					setError(errorMessage);
				}
			}
		} catch (err: any) {
			setAttemptCount(prev => prev + 1);
			
			// Use the standard error handler for consistent error processing
			const errorInfo = errorHandler.handleError(err, 'Login attempt');
			
			if (err.status === 429) {
				setError("Too many login attempts. Please try again later.");
			} else if (err.status >= 500) {
				setError("Server error. Please try again in a moment.");
			} else {
				setError(errorInfo.message || "Network error. Please try again.");
			}
		} finally {
			setIsLoading(false);
		}
	};

	const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
		const { name, value, type, checked } = e.target;

		// Basic client-side sanitization as user types
		let sanitizedValue = value;
		if (type !== "checkbox" && typeof value === "string") {
			// Remove potentially dangerous characters while typing
			sanitizedValue = value.replace(/<[^>]*>/g, ""); // Remove HTML tags
		}

		setFormData((prev) => ({
			...prev,
			[name]: type === "checkbox" ? checked : sanitizedValue,
		}));

		// Clear errors when user starts typing
		if (error) {
			setError(null);
		}
		if (validationErrors[name]) {
			setValidationErrors((prev) => {
				const updated = { ...prev };
				delete updated[name];
				return updated;
			});
		}
	};

	const togglePasswordVisibility = () => {
		setShowPassword(!showPassword);
	};

	if (success) {
		return (
			<div className="mx-auto max-w-md rounded-lg border border-green-200 bg-white p-8 shadow-sm">
				<div className="text-center">
					<CheckCircle className="mx-auto h-12 w-12 text-green-500 mb-4" />
					<h2 className="text-xl font-semibold text-gray-900 mb-2">
						Login Successful!
					</h2>
					<p className="text-gray-600">Redirecting you to your dashboard...</p>
				</div>
			</div>
		);
	}

	return (
		<div className="mx-auto max-w-md rounded-lg border border-gray-200 bg-white p-8 shadow-sm">
			<div className="mb-8 text-center">
				<div className="mb-4 flex items-center justify-center">
					<div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
						<span className="font-bold text-sm text-white">DM</span>
					</div>
					<h1 className="ml-2 font-semibold text-gray-900 text-xl">DotMac</h1>
				</div>
				<h2 className="font-bold text-2xl text-gray-900">Welcome Back</h2>
				<p className="mt-2 text-gray-600">Sign in to your customer portal</p>
			</div>

			{/* Attempt Warning */}
			{attemptCount > 0 && attemptCount < 5 && (
				<div className="mb-6 rounded-md border border-orange-200 bg-orange-50 p-4">
					<div className="flex">
						<AlertCircle className="h-5 w-5 text-orange-400" />
						<div className="ml-3">
							<p className="text-orange-800 text-sm">
								<span className="font-medium">Security Notice:</span>{" "}
								Please check your credentials. Multiple failed attempts may result in temporary account restrictions.
							</p>
						</div>
					</div>
				</div>
			)}

			{error && (
				<div className="mb-6 rounded-md border border-red-200 bg-red-50 p-4">
					<div className="flex">
						<AlertCircle className="h-5 w-5 text-red-400" />
						<div className="ml-3">
							<p className="text-red-700 text-sm">{error}</p>
						</div>
					</div>
				</div>
			)}

			<form onSubmit={handleSubmit} className="space-y-6">
				{/* Email Input */}
				<div>
					<label
						htmlFor="email"
						className="mb-2 block font-medium text-gray-700 text-sm"
					>
						Email Address
					</label>
					<div className="relative">
						<div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
							<Mail className="h-5 w-5 text-gray-400" />
						</div>
						<input
							id="email"
							name="email"
							type="email"
							autoComplete="email"
							required
							value={formData.email}
							onChange={handleChange}
							placeholder="your@email.com"
							className={`w-full rounded-md border pl-10 pr-3 py-2 text-sm focus:outline-none focus:ring-1 ${
								validationErrors.email
									? "border-red-300 focus:border-red-500 focus:ring-red-500"
									: "border-gray-300 focus:border-blue-500 focus:ring-blue-500"
							}`}
						/>
					</div>
					{validationErrors.email && (
						<div className="mt-2">
							{validationErrors.email.map((error, index) => (
								<p
									key={index}
									className="text-red-600 text-sm flex items-center"
								>
									<AlertCircle className="h-4 w-4 mr-1" />
									{error}
								</p>
							))}
						</div>
					)}
				</div>

				{/* Portal ID (Optional) */}
				<div>
					<label
						htmlFor="portalId"
						className="mb-2 block font-medium text-gray-700 text-sm"
					>
						Portal ID <span className="text-gray-400">(Optional)</span>
					</label>
					<input
						id="portalId"
						name="portalId"
						type="text"
						value={formData.portalId}
						onChange={handleChange}
						placeholder="Enter your portal ID if available"
						className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
					/>
				</div>

				{/* Password Input */}
				<div>
					<label
						htmlFor="password"
						className="mb-2 block font-medium text-gray-700 text-sm"
					>
						Password
					</label>
					<div className="relative">
						<div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
							<Lock className="h-5 w-5 text-gray-400" />
						</div>
						<input
							id="password"
							name="password"
							type={showPassword ? "text" : "password"}
							autoComplete="current-password"
							required
							value={formData.password}
							onChange={handleChange}
							placeholder="••••••••"
							className={`w-full rounded-md border pl-10 pr-10 py-2 text-sm focus:outline-none focus:ring-1 ${
								validationErrors.password
									? "border-red-300 focus:border-red-500 focus:ring-red-500"
									: "border-gray-300 focus:border-blue-500 focus:ring-blue-500"
							}`}
						/>
						<button
							type="button"
							className="absolute inset-y-0 right-0 flex items-center pr-3"
							onClick={togglePasswordVisibility}
						>
							{showPassword ? (
								<EyeOff className="h-5 w-5 text-gray-400 hover:text-gray-600" />
							) : (
								<Eye className="h-5 w-5 text-gray-400 hover:text-gray-600" />
							)}
						</button>
					</div>
					{validationErrors.password && (
						<div className="mt-2">
							{validationErrors.password.map((error, index) => (
								<p
									key={index}
									className="text-red-600 text-sm flex items-center"
								>
									<AlertCircle className="h-4 w-4 mr-1" />
									{error}
								</p>
							))}
						</div>
					)}
				</div>

				{/* Remember Me & Forgot Password */}
				<div className="flex items-center justify-between">
					<div className="flex items-center">
						<input
							id="rememberMe"
							name="rememberMe"
							type="checkbox"
							checked={formData.rememberMe}
							onChange={handleChange}
							className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
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
						onClick={() => router.push("/forgot-password")}
						className="font-medium text-blue-600 text-sm hover:text-blue-500"
					>
						Forgot password?
					</button>
				</div>

				{/* Submit Button */}
				<button
					type="submit"
					disabled={isLoading}
					className={`w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed bg-blue-600 hover:bg-blue-700 focus:ring-blue-500`}
				>
					{isLoading ? (
						<>
							<div className="h-4 w-4 animate-spin rounded-full border-white border-b-2 mr-2" />
							Signing in...
						</>
					) : (
						"Sign In"
					)}
				</button>
			</form>

			{/* Security Notice */}
			<div className="mt-6 rounded-md bg-blue-50 p-4">
				<div className="flex">
					<Lock className="h-5 w-5 text-blue-400" />
					<div className="ml-3">
						<p className="text-blue-800 text-sm">
							<span className="font-medium">Secure Login:</span> Your connection
							is encrypted and your credentials are protected with advanced
							security measures.
						</p>
					</div>
				</div>
			</div>

			{/* Help Links */}
			<div className="mt-6 space-y-2 text-center">
				<p className="text-gray-600 text-sm">
					Don't have an account?{" "}
					<button
						type="button"
						onClick={() => router.push("/contact")}
						className="font-medium text-blue-600 hover:text-blue-500"
					>
						Contact us to get started
					</button>
				</p>

				<div className="border-gray-200 border-t pt-4">
					<p className="text-gray-500 text-xs">
						Need help? Contact support at{" "}
						<a
							href="mailto:support@dotmac.com"
							className="text-blue-600 hover:text-blue-500"
						>
							support@dotmac.com
						</a>{" "}
						or call{" "}
						<a
							href="tel:+1-555-DOTMAC"
							className="text-blue-600 hover:text-blue-500"
						>
							+1 (555) DOT-MAC
						</a>
					</p>
				</div>
			</div>
		</div>
	);
}
