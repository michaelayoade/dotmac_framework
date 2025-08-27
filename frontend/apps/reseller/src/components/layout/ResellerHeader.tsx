"use client";

import { usePortalAuth } from "@dotmac/headless";
import { OptimizedImage } from "@dotmac/primitives";
import { Avatar, Button } from "@dotmac/styled-components/reseller";
import {
	Award,
	Bell,
	ChevronDown,
	HelpCircle,
	LogOut,
	Settings,
	User,
} from "lucide-react";
import { useState } from "react";
import { logger } from "../../utils/logger";

export function ResellerHeader() {
	const { user, currentPortal, getPortalBranding, logout } = usePortalAuth();
	const [showUserMenu, setShowUserMenu] = useState(false);

	const branding = getPortalBranding();

	const handleLogout = async () => {
		try {
			await logout();
		} catch (error) {
			logger.error("Logout failed", error, {
				component: "header",
				action: "logout",
			});
		}
	};

	const handleUserMenuToggle = () => {
		setShowUserMenu(!showUserMenu);
	};

	return (
		<header className="reseller-header flex h-16 items-center justify-between px-6">
			{/* Logo and Company Name */}
			<div className="flex items-center space-x-4">
				<div className="flex items-center space-x-3">
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

				{/* Partner Status Badge */}
				<div className="hidden items-center rounded-full bg-green-100 px-3 py-1 font-medium text-green-800 text-sm sm:flex">
					<Award className="mr-1 h-4 w-4" />
					Gold Partner
				</div>
			</div>

			{/* Header Actions */}
			<div className="flex items-center space-x-4">
				{/* Partner Resources */}
				<Button
					variant="ghost"
					size="sm"
					className="text-gray-600 hover:text-gray-900"
				>
					<HelpCircle className="h-5 w-5" />
					<span className="ml-2 hidden sm:inline">Resources</span>
				</Button>

				{/* Notifications */}
				<Button
					variant="ghost"
					size="sm"
					className="relative text-gray-600 hover:text-gray-900"
				>
					<Bell className="h-5 w-5" />
					{/* Notification badge */}
					<span className="-top-1 -right-1 absolute flex h-5 w-5 items-center justify-center rounded-full bg-green-500 text-white text-xs">
						3
					</span>
				</Button>

				{/* User Menu */}
				<div className="relative">
					<button
						type="button"
						onClick={handleUserMenuToggle}
						onKeyDown={(e) => e.key === "Enter" && handleUserMenuToggle}
						className="flex items-center space-x-2 rounded-lg p-2 transition-colors hover:bg-gray-100"
					>
						<Avatar
							src={user?.avatar}
							alt={user?.name || "Partner"}
							fallback={user?.name?.charAt(0) || "P"}
							size="sm"
						/>
						<div className="hidden text-left sm:block">
							<div className="font-medium text-gray-900 text-sm">
								{user?.name || "Partner"}
							</div>
							<div className="text-gray-500 text-xs">
								{user?.company || "Partner Account"}
							</div>
						</div>
						<ChevronDown className="h-4 w-4 text-gray-400" />
					</button>

					{showUserMenu ? (
						<div className="absolute right-0 z-50 mt-2 w-56 rounded-md border border-gray-200 bg-white py-1 shadow-lg">
							<div className="border-gray-100 border-b px-4 py-2">
								<p className="font-medium text-gray-900 text-sm">
									{user?.name || "Partner"}
								</p>
								<p className="text-gray-500 text-xs">
									{user?.email || "partner@example.com"}
								</p>
								<p className="font-medium text-green-600 text-xs">
									Gold Partner • TS001
								</p>
							</div>

							<button
								type="button"
								onClick={() => {
									/* TODO: Implement profile navigation */
								}}
								className="flex w-full items-center px-4 py-2 text-left text-gray-700 text-sm hover:bg-gray-100"
							>
								<User className="mr-2 h-4 w-4" />
								Partner Profile
							</button>
							<button
								type="button"
								onClick={() => {
									/* TODO: Implement benefits navigation */
								}}
								className="flex w-full items-center px-4 py-2 text-left text-gray-700 text-sm hover:bg-gray-100"
							>
								<Award className="mr-2 h-4 w-4" />
								Partner Benefits
							</button>
							<button
								type="button"
								onClick={() => {
									/* TODO: Implement settings navigation */
								}}
								className="flex w-full items-center px-4 py-2 text-left text-gray-700 text-sm hover:bg-gray-100"
							>
								<Settings className="mr-2 h-4 w-4" />
								Account Settings
							</button>

							<hr className="my-1" />

							<button
								type="button"
								onClick={() => {
									/* TODO: Implement help navigation */
								}}
								className="flex w-full items-center px-4 py-2 text-left text-gray-700 text-sm hover:bg-gray-100"
							>
								<HelpCircle className="mr-2 h-4 w-4" />
								Partner Support
							</button>

							<hr className="my-1" />

							<button
								type="button"
								onClick={handleLogout}
								onKeyDown={(e) => e.key === "Enter" && handleLogout}
								className="flex w-full items-center px-4 py-2 text-gray-700 text-sm hover:bg-gray-100"
							>
								<LogOut className="mr-2 h-4 w-4" />
								Sign Out
							</button>
						</div>
					) : null}
				</div>
			</div>
		</header>
	);
}
