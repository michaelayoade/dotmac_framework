"use client";

import { NotificationProvider } from "@dotmac/primitives";
import { ThemeProvider } from "@dotmac/styled-components";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { AuthProvider } from "../components/auth/AuthProvider";

const queryClient = new QueryClient({
	defaultOptions: {
		queries: {
			staleTime: 5 * 60 * 1000, // 5 minutes
			retry: (failureCount, error: unknown) => {
				if ((error as any)?.status === 401 || (error as any)?.status === 403) {
					return false;
				}
				return failureCount < 3;
			},
		},
	},
});

interface ProvidersProps {
	children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
	return (
		<QueryClientProvider client={queryClient}>
			<ThemeProvider portal="reseller">
				<AuthProvider>
					<NotificationProvider 
						websocketUrl={process.env.NEXT_PUBLIC_WS_URL}
						apiKey={process.env.NEXT_PUBLIC_API_KEY}
						onError={(error) => console.error('Notification system error:', error)}
					>
						{children}
					</NotificationProvider>
				</AuthProvider>
			</ThemeProvider>
		</QueryClientProvider>
	);
}
