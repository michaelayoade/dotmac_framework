/**
 * Reusable Status Card component for displaying service status information
 */
import type { LucideIcon } from "lucide-react";
import React from "react";

export interface StatusCardProps {
	title: string;
	value: string | number;
	icon: LucideIcon;
	status?: "success" | "warning" | "error" | "neutral";
	subtitle?: string;
	action?: {
		label: string;
		onClick: () => void;
	};
	loading?: boolean;
	className?: string;
}

const statusStyles = {
	success: {
		card: "border-green-200 bg-green-50",
		icon: "text-green-600",
		value: "text-green-900",
		title: "text-green-700",
	},
	warning: {
		card: "border-yellow-200 bg-yellow-50",
		icon: "text-yellow-600",
		value: "text-yellow-900",
		title: "text-yellow-700",
	},
	error: {
		card: "border-red-200 bg-red-50",
		icon: "text-red-600",
		value: "text-red-900",
		title: "text-red-700",
	},
	neutral: {
		card: "border-gray-200 bg-white",
		icon: "text-blue-600",
		value: "text-gray-900",
		title: "text-gray-600",
	},
};

export function StatusCard({
	title,
	value,
	icon: Icon,
	status = "neutral",
	subtitle,
	action,
	loading = false,
	className = "",
}: StatusCardProps) {
	const styles = statusStyles[status];

	return (
		<div
			className={`p-6 rounded-lg border shadow-sm hover:shadow-md transition-shadow ${styles.card} ${className}`}
		>
			<div className="flex items-center justify-between">
				<div className="flex-1">
					<p className={`font-medium text-sm ${styles.title}`}>{title}</p>
					<div className="mt-2 flex items-center">
						{loading ? (
							<div className="animate-pulse">
								<div className="h-8 w-20 bg-gray-200 rounded"></div>
							</div>
						) : (
							<div className="flex items-baseline">
								<span className={`font-bold text-2xl ${styles.value}`}>
									{value}
								</span>
								{subtitle && (
									<span className="ml-2 text-sm text-gray-500">{subtitle}</span>
								)}
							</div>
						)}
					</div>
					{action && (
						<button
							onClick={action.onClick}
							className="mt-3 text-sm font-medium text-blue-600 hover:text-blue-500"
						>
							{action.label}
						</button>
					)}
				</div>
				<Icon className={`h-8 w-8 ${styles.icon}`} />
			</div>
		</div>
	);
}
