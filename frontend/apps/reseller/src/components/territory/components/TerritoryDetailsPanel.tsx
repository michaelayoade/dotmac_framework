/**
 * Territory Details Panel Component
 * Shows detailed information for selected territory
 */

import { motion } from "framer-motion";
import type { Territory } from "../hooks/useTerritoryData";

interface TerritoryDetailsPanelProps {
	territory: Territory;
	onClose: () => void;
}

export function TerritoryDetailsPanel({
	territory,
	onClose,
}: TerritoryDetailsPanelProps) {
	return (
		<motion.div
			initial={{ opacity: 0, y: 20 }}
			animate={{ opacity: 1, y: 0 }}
			className="bg-white rounded-lg border border-gray-200 p-6"
		>
			<div className="flex items-center justify-between mb-4">
				<h3 className="text-lg font-semibold text-gray-900">
					{territory.name} - {territory.region}
				</h3>
				<button onClick={onClose} className="text-gray-400 hover:text-gray-600">
					✕
				</button>
			</div>

			{/* Territory details */}
			<div className="grid grid-cols-3 gap-4 text-sm">
				<div>
					<span className="text-gray-600">Population:</span>
					<div className="font-semibold">
						{territory.population.toLocaleString()}
					</div>
				</div>
				<div>
					<span className="text-gray-600">Avg Income:</span>
					<div className="font-semibold">
						${territory.averageIncome.toLocaleString()}
					</div>
				</div>
				<div>
					<span className="text-gray-600">Serviceability:</span>
					<div className="font-semibold">{territory.serviceability}%</div>
				</div>
			</div>
		</motion.div>
	);
}
