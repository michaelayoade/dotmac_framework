"use client";

import { Eye, Plus, Save, Trash2 } from "lucide-react";
import type React from "react";
import { useCallback, useState } from "react";
import type {
	BusinessRule,
	PortalType,
	RuleAction,
	RuleCondition,
} from "../types";
import { ActionBuilder } from "./ActionBuilder";
import { ConditionBuilder } from "./ConditionBuilder";
import { RulePreview } from "./RulePreview";

interface RuleBuilderProps {
	rule?: Partial<BusinessRule>;
	onSave?: (rule: BusinessRule) => void;
	onCancel?: () => void;
	isEditing?: boolean;
}

// Simple Button component
const Button = ({
	children,
	onClick,
	variant = "default",
	className = "",
	disabled = false,
}: {
	children: React.ReactNode;
	onClick?: () => void;
	variant?: "default" | "outline";
	className?: string;
	disabled?: boolean;
}) => (
	<button
		onClick={onClick}
		disabled={disabled}
		className={`px-4 py-2 rounded-md font-medium transition-colors ${
			variant === "outline"
				? "border border-gray-300 text-gray-700 hover:bg-gray-50"
				: "bg-blue-600 text-white hover:bg-blue-700"
		} ${disabled ? "opacity-50 cursor-not-allowed" : ""} ${className}`}
	>
		{children}
	</button>
);

// Simple Card component
const Card = ({
	children,
	className = "",
}: {
	children: React.ReactNode;
	className?: string;
}) => (
	<div className={`border border-gray-200 rounded-lg ${className}`}>
		{children}
	</div>
);

export function RuleBuilder({
	rule: initialRule,
	onSave,
	onCancel,
	isEditing = false,
}: RuleBuilderProps) {
	const [rule, setRule] = useState<Partial<BusinessRule>>(() => ({
		id: "",
		name: "",
		description: "",
		category: "general",
		conditions: [],
		conditionLogic: "all",
		actions: [],
		priority: 100,
		status: "draft",
		portalScope: [],
		tags: [],
		createdAt: new Date(),
		updatedAt: new Date(),
		createdBy: "current_user",
		updatedBy: "current_user",
		...initialRule,
	}));

	const [showPreview, setShowPreview] = useState(false);

	const updateRule = useCallback((updates: Partial<BusinessRule>) => {
		setRule((prev) => ({
			...prev,
			...updates,
			updatedAt: new Date(),
		}));
	}, []);

	const addCondition = useCallback(() => {
		const newCondition: RuleCondition = {
			id: `condition_${Date.now()}`,
			field: "",
			operator: "equals",
			value: "",
		};

		updateRule({
			conditions: [...(rule.conditions || []), newCondition],
		});
	}, [rule.conditions, updateRule]);

	const updateCondition = useCallback(
		(index: number, condition: RuleCondition) => {
			const conditions = [...(rule.conditions || [])];
			conditions[index] = condition;
			updateRule({ conditions });
		},
		[rule.conditions, updateRule],
	);

	const removeCondition = useCallback(
		(index: number) => {
			const conditions = [...(rule.conditions || [])];
			conditions.splice(index, 1);
			updateRule({ conditions });
		},
		[rule.conditions, updateRule],
	);

	const addAction = useCallback(() => {
		const newAction: RuleAction = {
			id: `action_${Date.now()}`,
			type: "set_value",
			target: "",
			value: "",
		};

		updateRule({
			actions: [...(rule.actions || []), newAction],
		});
	}, [rule.actions, updateRule]);

	const updateAction = useCallback(
		(index: number, action: RuleAction) => {
			const actions = [...(rule.actions || [])];
			actions[index] = action;
			updateRule({ actions });
		},
		[rule.actions, updateRule],
	);

	const removeAction = useCallback(
		(index: number) => {
			const actions = [...(rule.actions || [])];
			actions.splice(index, 1);
			updateRule({ actions });
		},
		[rule.actions, updateRule],
	);

	const handleSave = useCallback(() => {
		if (rule.name && onSave) {
			const completeRule: BusinessRule = {
				id: rule.id || `rule_${Date.now()}`,
				name: rule.name,
				description: rule.description || "",
				category: rule.category || "general",
				conditions: rule.conditions || [],
				conditionLogic: rule.conditionLogic || "all",
				actions: rule.actions || [],
				priority: rule.priority || 100,
				status: rule.status || "draft",
				portalScope: rule.portalScope || [],
				tags: rule.tags || [],
				createdAt: rule.createdAt || new Date(),
				updatedAt: new Date(),
				createdBy: rule.createdBy || "current_user",
				updatedBy: rule.updatedBy || "current_user",
			};
			onSave(completeRule);
		}
	}, [rule, onSave]);

	return (
		<div className="space-y-6">
			{/* Header */}
			<div className="flex items-center justify-between">
				<h2 className="text-2xl font-bold text-gray-900">
					{isEditing ? "Edit Business Rule" : "Create Business Rule"}
				</h2>
				<div className="flex gap-2">
					<Button
						variant="outline"
						onClick={() => setShowPreview(!showPreview)}
						className="flex items-center gap-2"
					>
						<Eye className="h-4 w-4" />
						{showPreview ? "Hide Preview" : "Preview"}
					</Button>
					<Button onClick={handleSave} className="flex items-center gap-2">
						<Save className="h-4 w-4" />
						Save Rule
					</Button>
					{onCancel && (
						<Button variant="outline" onClick={onCancel}>
							Cancel
						</Button>
					)}
				</div>
			</div>

			<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
				{/* Main Form */}
				<div className="space-y-6">
					{/* Basic Information */}
					<Card className="p-6">
						<h3 className="text-lg font-medium mb-4">Basic Information</h3>
						<div className="space-y-4">
							<div>
								<label className="block text-sm font-medium text-gray-700 mb-1">
									Rule Name *
								</label>
								<input
									type="text"
									value={rule.name || ""}
									onChange={(e) => updateRule({ name: e.target.value })}
									className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
									placeholder="Enter rule name"
								/>
							</div>

							<div>
								<label className="block text-sm font-medium text-gray-700 mb-1">
									Description
								</label>
								<textarea
									value={rule.description || ""}
									onChange={(e) => updateRule({ description: e.target.value })}
									className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
									placeholder="Describe what this rule does"
									rows={3}
								/>
							</div>
						</div>
					</Card>

					{/* Conditions */}
					<Card className="p-6">
						<div className="flex items-center justify-between mb-4">
							<h3 className="text-lg font-medium">Conditions</h3>
							<Button
								variant="outline"
								onClick={addCondition}
								className="flex items-center gap-2 text-sm px-3 py-1"
							>
								<Plus className="h-4 w-4" />
								Add Condition
							</Button>
						</div>

						<div className="space-y-4">
							{rule.conditions?.map((condition, index) => (
								<div key={condition.id} className="relative">
									<ConditionBuilder
										condition={condition}
										onChange={(updatedCondition) =>
											updateCondition(index, updatedCondition)
										}
									/>
									<button
										onClick={() => removeCondition(index)}
										className="absolute top-2 right-2 p-1 text-red-600 hover:text-red-800 border border-red-200 rounded hover:bg-red-50"
									>
										<Trash2 className="h-4 w-4" />
									</button>
								</div>
							))}
						</div>

						{!rule.conditions?.length && (
							<p className="text-gray-500 text-center py-8">
								No conditions added yet. Click "Add Condition" to get started.
							</p>
						)}
					</Card>

					{/* Actions */}
					<Card className="p-6">
						<div className="flex items-center justify-between mb-4">
							<h3 className="text-lg font-medium">Actions</h3>
							<Button
								variant="outline"
								onClick={addAction}
								className="flex items-center gap-2 text-sm px-3 py-1"
							>
								<Plus className="h-4 w-4" />
								Add Action
							</Button>
						</div>

						<div className="space-y-4">
							{rule.actions?.map((action, index) => (
								<div key={action.id} className="relative">
									<ActionBuilder
										action={action}
										onChange={(updatedAction) =>
											updateAction(index, updatedAction)
										}
									/>
									<button
										onClick={() => removeAction(index)}
										className="absolute top-2 right-2 p-1 text-red-600 hover:text-red-800 border border-red-200 rounded hover:bg-red-50"
									>
										<Trash2 className="h-4 w-4" />
									</button>
								</div>
							))}
						</div>

						{!rule.actions?.length && (
							<p className="text-gray-500 text-center py-8">
								No actions added yet. Click "Add Action" to get started.
							</p>
						)}
					</Card>
				</div>

				{/* Preview Panel */}
				{showPreview && rule.name && (
					<div className="lg:sticky lg:top-6">
						<RulePreview rule={rule as BusinessRule} />
					</div>
				)}
			</div>
		</div>
	);
}
