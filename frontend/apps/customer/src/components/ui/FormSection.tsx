/**
 * Reusable Form Section component for consistent form layouts
 */
import type { LucideIcon } from "lucide-react";
import type React from "react";

export interface FormSectionProps {
	title: string;
	description?: string;
	icon?: LucideIcon;
	children: React.ReactNode;
	isEditing?: boolean;
	onEdit?: () => void;
	onSave?: () => void;
	onCancel?: () => void;
	isSaving?: boolean;
	className?: string;
}

export function FormSection({
	title,
	description,
	icon: Icon,
	children,
	isEditing = false,
	onEdit,
	onSave,
	onCancel,
	isSaving = false,
	className = "",
}: FormSectionProps) {
	return (
		<div
			className={`bg-white border border-gray-200 rounded-lg shadow-sm ${className}`}
		>
			{/* Section Header */}
			<div className="px-6 py-4 border-b border-gray-200">
				<div className="flex items-center justify-between">
					<div className="flex items-center">
						{Icon && <Icon className="h-5 w-5 text-blue-600 mr-3" />}
						<div>
							<h3 className="font-semibold text-gray-900 text-lg">{title}</h3>
							{description && (
								<p className="text-gray-500 text-sm mt-1">{description}</p>
							)}
						</div>
					</div>

					{/* Edit/Save/Cancel Actions */}
					<div className="flex items-center space-x-3">
						{isEditing ? (
							<>
								<button
									type="button"
									onClick={onCancel}
									disabled={isSaving}
									className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
								>
									Cancel
								</button>
								<button
									type="button"
									onClick={onSave}
									disabled={isSaving}
									className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center"
								>
									{isSaving && (
										<div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
									)}
									{isSaving ? "Saving..." : "Save Changes"}
								</button>
							</>
						) : onEdit ? (
							<button
								type="button"
								onClick={onEdit}
								className="px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded-md hover:bg-blue-100"
							>
								Edit
							</button>
						) : null}
					</div>
				</div>
			</div>

			{/* Section Content */}
			<div className="px-6 py-6">{children}</div>
		</div>
	);
}
