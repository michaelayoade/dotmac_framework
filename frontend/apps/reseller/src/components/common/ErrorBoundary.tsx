/**
 * Enhanced Error Boundary Component
 * Provides consistent error handling across the application
 */

"use client";

import { AlertCircle, Home, RefreshCw } from "lucide-react";
import type React from "react";
import { Component, type ReactNode } from "react";
import { logger } from "../../utils/logger";

interface Props {
	children: ReactNode;
	fallback?: ReactNode;
	level?: "page" | "component" | "section";
	componentName?: string;
	onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface State {
	hasError: boolean;
	error?: Error;
	errorInfo?: React.ErrorInfo;
	retryCount: number;
}

export class ErrorBoundary extends Component<Props, State> {
	private maxRetries = 3;

	constructor(props: Props) {
		super(props);
		this.state = {
			hasError: false,
			retryCount: 0,
		};
	}

	static getDerivedStateFromError(error: Error): State {
		return {
			hasError: true,
			error,
			retryCount: 0,
		};
	}

	componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
		// Log the error with context
		logger.error(`Error in ${this.props.componentName || "component"}`, error, {
			component: this.props.componentName || "unknown",
			level: this.props.level || "component",
			stack: error.stack,
			componentStack: errorInfo.componentStack,
			retryCount: this.state.retryCount,
		});

		this.setState({
			error,
			errorInfo,
		});

		// Call custom error handler if provided
		if (this.props.onError) {
			this.props.onError(error, errorInfo);
		}
	}

	handleRetry = () => {
		if (this.state.retryCount < this.maxRetries) {
			this.setState((prevState) => ({
				hasError: false,
				error: undefined,
				errorInfo: undefined,
				retryCount: prevState.retryCount + 1,
			}));
		} else {
			// Max retries reached, reload the page
			window.location.reload();
		}
	};

	handleGoHome = () => {
		window.location.href = "/";
	};

	render() {
		if (this.state.hasError) {
			// Use custom fallback if provided
			if (this.props.fallback) {
				return this.props.fallback;
			}

			const { level = "component" } = this.props;
			const canRetry = this.state.retryCount < this.maxRetries;

			// Different error UIs based on error level
			if (level === "page") {
				return (
					<div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
						<div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8 text-center">
							<AlertCircle className="mx-auto h-16 w-16 text-red-500 mb-6" />
							<h1 className="text-2xl font-bold text-gray-900 mb-4">
								Page Error
							</h1>
							<p className="text-gray-600 mb-6">
								Something went wrong while loading this page.
								{this.state.error?.message && (
									<>
										<br />
										<span className="text-sm mt-2 block font-mono bg-gray-100 p-2 rounded">
											{this.state.error.message}
										</span>
									</>
								)}
							</p>
							<div className="flex gap-4 justify-center">
								{canRetry ? (
									<button
										onClick={this.handleRetry}
										className="flex items-center px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
									>
										<RefreshCw className="h-4 w-4 mr-2" />
										Try Again ({this.maxRetries - this.state.retryCount} left)
									</button>
								) : (
									<button
										onClick={() => window.location.reload()}
										className="flex items-center px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
									>
										<RefreshCw className="h-4 w-4 mr-2" />
										Reload Page
									</button>
								)}
								<button
									onClick={this.handleGoHome}
									className="flex items-center px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300 transition-colors"
								>
									<Home className="h-4 w-4 mr-2" />
									Go Home
								</button>
							</div>
						</div>
					</div>
				);
			}

			if (level === "section") {
				return (
					<div className="bg-red-50 border border-red-200 rounded-lg p-6 my-4">
						<div className="flex items-center mb-4">
							<AlertCircle className="h-6 w-6 text-red-500 mr-3" />
							<h3 className="text-lg font-medium text-red-800">
								Section Error
							</h3>
						</div>
						<p className="text-red-700 mb-4">
							This section encountered an error and couldn't load properly.
							{this.state.error?.message && (
								<>
									<br />
									<span className="text-sm mt-2 block font-mono bg-red-100 p-2 rounded">
										{this.state.error.message}
									</span>
								</>
							)}
						</p>
						{canRetry && (
							<button
								onClick={this.handleRetry}
								className="flex items-center px-3 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors text-sm"
							>
								<RefreshCw className="h-4 w-4 mr-2" />
								Retry ({this.maxRetries - this.state.retryCount} left)
							</button>
						)}
					</div>
				);
			}

			// Component level error (default)
			return (
				<div className="bg-yellow-50 border border-yellow-200 rounded-md p-4 my-2">
					<div className="flex items-center">
						<AlertCircle className="h-5 w-5 text-yellow-500 mr-2" />
						<div className="flex-1">
							<p className="text-sm text-yellow-800">
								Component failed to load
								{this.props.componentName && `: ${this.props.componentName}`}
							</p>
							{this.state.error?.message && (
								<p className="text-xs text-yellow-700 mt-1 font-mono">
									{this.state.error.message}
								</p>
							)}
						</div>
						{canRetry && (
							<button
								onClick={this.handleRetry}
								className="ml-4 text-xs bg-yellow-600 text-white px-2 py-1 rounded hover:bg-yellow-700 transition-colors"
								title={`Retry (${this.maxRetries - this.state.retryCount} attempts left)`}
							>
								Retry
							</button>
						)}
					</div>
				</div>
			);
		}

		return this.props.children;
	}
}

// Higher-order component for easier wrapping
export function withErrorBoundary<T extends Record<string, any>>(
	Component: React.ComponentType<T>,
	options?: {
		componentName?: string;
		level?: "page" | "component" | "section";
		fallback?: ReactNode;
	},
) {
	const WrappedComponent = (props: T) => (
		<ErrorBoundary
			componentName={
				options?.componentName || Component.displayName || Component.name
			}
			level={options?.level}
			fallback={options?.fallback}
		>
			<Component {...props} />
		</ErrorBoundary>
	);

	WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`;
	return WrappedComponent;
}

// Async component error boundary for Suspense fallbacks
export function AsyncErrorBoundary({
	children,
	fallback,
	componentName = "AsyncComponent",
}: {
	children: ReactNode;
	fallback?: ReactNode;
	componentName?: string;
}) {
	return (
		<ErrorBoundary
			componentName={componentName}
			level="component"
			fallback={
				fallback || (
					<div className="animate-pulse bg-gray-200 rounded-md h-20 flex items-center justify-center">
						<span className="text-gray-500 text-sm">Loading...</span>
					</div>
				)
			}
		>
			{children}
		</ErrorBoundary>
	);
}
