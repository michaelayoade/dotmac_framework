"use client";

import { useAuthStore } from "@dotmac/headless";
import { type ReactNode, useEffect } from "react";

interface AuthProviderProps {
	children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
	const { initializeAuth } = useAuthStore();

	useEffect(() => {
		initializeAuth();
	}, [initializeAuth]);

	return <>{children}</>;
}
