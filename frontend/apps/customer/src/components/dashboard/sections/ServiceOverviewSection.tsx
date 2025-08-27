/**
 * Service Overview Section - Decomposed from CustomerDashboard
 */

import { Activity, Globe, TrendingUp, Wifi } from "lucide-react";
import React from "react";
import { StatusCard } from "../../ui/StatusCard";

interface NetworkStatus {
	connectionStatus: string;
	currentSpeed: {
		download: number;
		upload: number;
	};
	uptime: number;
	latency: number;
}

interface ServiceOverviewProps {
	networkStatus: NetworkStatus;
	dataUsage: {
		current: number;
		limit: number;
	};
	onRefreshStatus?: () => void;
	onViewDetails?: () => void;
	loading?: boolean;
}

export function ServiceOverviewSection({
	networkStatus,
	dataUsage,
	onRefreshStatus,
	onViewDetails,
	loading = false,
}: ServiceOverviewProps) {
	const getConnectionStatus = (status: string) => {
		switch (status) {
			case "connected":
				return "success" as const;
			case "disconnected":
				return "error" as const;
			case "limited":
				return "warning" as const;
			default:
				return "neutral" as const;
		}
	};

	const getSpeedStatus = (speed: number) => {
		if (speed >= 100) return "success" as const;
		if (speed >= 50) return "neutral" as const;
		if (speed >= 25) return "warning" as const;
		return "error" as const;
	};

	const getUsageStatus = (current: number, limit: number) => {
		const percentage = (current / limit) * 100;
		if (percentage >= 90) return "error" as const;
		if (percentage >= 75) return "warning" as const;
		return "neutral" as const;
	};

	return (
		<div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
			<StatusCard
				title="Connection Status"
				value={networkStatus.connectionStatus}
				icon={Wifi}
				status={getConnectionStatus(networkStatus.connectionStatus)}
				action={
					onRefreshStatus
						? {
								label: "Refresh",
								onClick: onRefreshStatus,
							}
						: undefined
				}
				loading={loading}
			/>

			<StatusCard
				title="Current Speed"
				value={networkStatus.currentSpeed.download}
				subtitle="Mbps"
				icon={TrendingUp}
				status={getSpeedStatus(networkStatus.currentSpeed.download)}
				action={
					onViewDetails
						? {
								label: "View Details",
								onClick: onViewDetails,
							}
						: undefined
				}
				loading={loading}
			/>

			<StatusCard
				title="Data Usage"
				value={`${dataUsage.current}/${dataUsage.limit}`}
				subtitle="GB"
				icon={Globe}
				status={getUsageStatus(dataUsage.current, dataUsage.limit)}
				loading={loading}
			/>

			<StatusCard
				title="Network Uptime"
				value={`${networkStatus.uptime}%`}
				icon={Activity}
				status={
					networkStatus.uptime >= 99.5
						? "success"
						: networkStatus.uptime >= 98
							? "neutral"
							: "warning"
				}
				loading={loading}
			/>
		</div>
	);
}
