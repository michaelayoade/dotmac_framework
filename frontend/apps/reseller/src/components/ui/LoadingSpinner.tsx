"use client";

import { cva, type VariantProps } from "class-variance-authority";
import { clsx } from "clsx";
import type React from "react";

const spinnerVariants = cva(
	"animate-spin rounded-full border-2 border-current border-t-transparent",
	{
		variants: {
			size: {
				sm: "h-4 w-4",
				md: "h-6 w-6",
				lg: "h-8 w-8",
				xl: "h-12 w-12",
			},
			variant: {
				default: "text-green-600",
				secondary: "text-gray-400",
				white: "text-white",
			},
		},
		defaultVariants: {
			size: "md",
			variant: "default",
		},
	},
);

export interface LoadingSpinnerProps
	extends React.HTMLAttributes<HTMLDivElement>,
		VariantProps<typeof spinnerVariants> {
	label?: string;
}

export function LoadingSpinner({
	size,
	variant,
	label = "Loading...",
	className,
	...props
}: LoadingSpinnerProps) {
	return (
		<div
			role="alert"
			aria-live="polite"
			aria-label={label}
			className={clsx("inline-flex items-center gap-2", className)}
			{...props}
		>
			<div className={spinnerVariants({ size, variant })} />
			{label ? <span className="text-gray-600 text-sm">{label}</span> : null}
		</div>
	);
}
