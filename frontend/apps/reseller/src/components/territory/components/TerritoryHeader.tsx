/**
 * Territory Management Header Component
 * Handles header, search, filters, and view controls
 */

import { motion } from "framer-motion";
import {
	Eye,
	Filter,
	LayoutGrid,
	Map as MapIcon,
	MapPin,
	Search,
} from "lucide-react";
import type {
	Territory,
	TerritoryFilters as TerritoryFiltersType,
} from "../hooks/useTerritoryData";
import { TerritoryFilters } from "./TerritoryFilters";

type ViewMode = "map" | "list" | "analytics";

interface TerritoryHeaderProps {
	viewMode: ViewMode;
	onViewModeChange: (mode: ViewMode) => void;
	filters: TerritoryFiltersType;
	onFiltersChange: (updates: Partial<TerritoryFiltersType>) => void;
	territories: Territory[];
	showFilters: boolean;
	onToggleFilters: () => void;
}

export function TerritoryHeader({
	viewMode,
	onViewModeChange,
	filters,
	onFiltersChange,
	territories,
	showFilters,
	onToggleFilters,
}: TerritoryHeaderProps) {
	return (
		<motion.div
			initial={{ opacity: 0, y: 20 }}
			animate={{ opacity: 1, y: 0 }}
			className="bg-white rounded-lg border border-gray-200 p-6"
		>
			<div className="flex items-center justify-between">
				<div>
					<h2 className="text-2xl font-bold text-gray-900 flex items-center">
						<MapPin className="w-8 h-8 text-blue-600 mr-3" />
						Territory Management
					</h2>
					<p className="text-gray-600 mt-1">
						Analyze and optimize your sales territories
					</p>
				</div>

				{/* View Mode Controls */}
				<div className="flex items-center space-x-2">
					<button
						onClick={() => onViewModeChange("map")}
						className={`p-2 rounded-lg ${viewMode === "map" ? "bg-blue-100 text-blue-600" : "text-gray-600 hover:bg-gray-100"}`}
					>
						<MapIcon className="w-5 h-5" />
					</button>
					<button
						onClick={() => onViewModeChange("list")}
						className={`p-2 rounded-lg ${viewMode === "list" ? "bg-blue-100 text-blue-600" : "text-gray-600 hover:bg-gray-100"}`}
					>
						<LayoutGrid className="w-5 h-5" />
					</button>
					<button
						onClick={() => onViewModeChange("analytics")}
						className={`p-2 rounded-lg ${viewMode === "analytics" ? "bg-blue-100 text-blue-600" : "text-gray-600 hover:bg-gray-100"}`}
					>
						<Eye className="w-5 h-5" />
					</button>
				</div>
			</div>

			{/* Search and Filters */}
			<div className="flex items-center space-x-4 mt-4">
				<div className="relative flex-1">
					<Search className="w-5 h-5 text-gray-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
					<input
						type="text"
						placeholder="Search territories..."
						value={filters.searchTerm}
						onChange={(e) => onFiltersChange({ searchTerm: e.target.value })}
						className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
					/>
				</div>

				<button
					onClick={onToggleFilters}
					className={`px-4 py-2 border rounded-lg flex items-center space-x-2 ${
						showFilters
							? "bg-blue-50 border-blue-300 text-blue-700"
							: "border-gray-300 text-gray-700 hover:bg-gray-50"
					}`}
				>
					<Filter className="w-4 h-4" />
					<span>Filters</span>
				</button>
			</div>

			{/* Filters Panel */}
			{showFilters && (
				<TerritoryFilters
					filters={filters}
					onFiltersChange={onFiltersChange}
					territories={territories}
				/>
			)}
		</motion.div>
	);
}
