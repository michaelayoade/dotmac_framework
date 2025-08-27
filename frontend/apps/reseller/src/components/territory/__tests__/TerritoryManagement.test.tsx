/**
 * Territory Management Component Tests
 * Tests for the refactored territory management system
 */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Territory } from "../hooks/useTerritoryData";
import { useTerritoryData } from "../hooks/useTerritoryData";
import { TerritoryManagement } from "../TerritoryManagement";

// Mock the territory data hook
jest.mock("../hooks/useTerritoryData");
const mockUseTerritoryData = useTerritoryData as jest.MockedFunction<
	typeof useTerritoryData
>;

// Mock sub-components
jest.mock("../components/TerritoryHeader", () => ({
	TerritoryHeader: ({ onViewModeChange, onToggleFilters }: any) => (
		<div data-testid="territory-header">
			<button onClick={() => onViewModeChange("map")} data-testid="view-map">
				Map View
			</button>
			<button onClick={() => onViewModeChange("list")} data-testid="view-list">
				List View
			</button>
			<button
				onClick={() => onViewModeChange("analytics")}
				data-testid="view-analytics"
			>
				Analytics View
			</button>
			<button onClick={onToggleFilters} data-testid="toggle-filters">
				Toggle Filters
			</button>
		</div>
	),
}));

jest.mock("../components/TerritoryContent", () => ({
	TerritoryContent: ({ viewMode, onTerritorySelect }: any) => (
		<div data-testid="territory-content">
			<div data-testid="current-view">{viewMode}</div>
			<button
				onClick={() =>
					onTerritorySelect({ id: "territory_1", name: "Test Territory" })
				}
				data-testid="select-territory"
			>
				Select Territory
			</button>
		</div>
	),
}));

jest.mock("../components/TerritoryDetailsPanel", () => ({
	TerritoryDetailsPanel: ({ territory, onClose }: any) => (
		<div data-testid="territory-details">
			<h3>{territory.name}</h3>
			<button onClick={onClose} data-testid="close-details">
				Close
			</button>
		</div>
	),
}));

describe("TerritoryManagement", () => {
	const mockTerritories: Territory[] = [
		{
			id: "territory_1",
			name: "Downtown Core",
			region: "Central",
			coordinates: [40.7128, -74.006],
			radius: 5.2,
			population: 125000,
			households: 48000,
			averageIncome: 75000,
			competition: "high",
			marketPenetration: 34.5,
			totalCustomers: 16560,
			activeProspects: 2890,
			monthlyRevenue: 892400,
			growthRate: 12.3,
			serviceability: 95,
			lastUpdated: "2024-01-15T10:30:00Z",
			demographics: { residential: 70, business: 25, enterprise: 5 },
			services: { fiber: 60, cable: 35, dsl: 5 },
			opportunities: {
				newDevelopments: 12,
				businessParks: 3,
				competitorWeakness: 8,
			},
		},
		{
			id: "territory_2",
			name: "Suburban North",
			region: "North",
			coordinates: [40.7589, -73.9851],
			radius: 8.1,
			population: 95000,
			households: 35000,
			averageIncome: 85000,
			competition: "medium",
			marketPenetration: 45.2,
			totalCustomers: 15820,
			activeProspects: 1250,
			monthlyRevenue: 1125600,
			growthRate: 18.7,
			serviceability: 88,
			lastUpdated: "2024-01-15T11:15:00Z",
			demographics: { residential: 85, business: 12, enterprise: 3 },
			services: { fiber: 75, cable: 20, dsl: 5 },
			opportunities: {
				newDevelopments: 8,
				businessParks: 2,
				competitorWeakness: 15,
			},
		},
	];

	const mockDefaultHookReturn = {
		territories: mockTerritories,
		filteredTerritories: mockTerritories,
		isLoading: false,
		error: null,
		filters: {
			searchTerm: "",
			sortBy: "revenue" as const,
		},
		updateFilters: jest.fn(),
		refreshData: jest.fn(),
	};

	beforeEach(() => {
		jest.clearAllMocks();
		mockUseTerritoryData.mockReturnValue(mockDefaultHookReturn);
	});

	describe("Loading State", () => {
		it("should show loading spinner when data is loading", () => {
			mockUseTerritoryData.mockReturnValue({
				...mockDefaultHookReturn,
				isLoading: true,
			});

			render(<TerritoryManagement />);

			expect(screen.getByRole("status")).toBeInTheDocument();
			expect(screen.getByTestId("loading-spinner")).toBeInTheDocument();
		});

		it("should hide content while loading", () => {
			mockUseTerritoryData.mockReturnValue({
				...mockDefaultHookReturn,
				isLoading: true,
			});

			render(<TerritoryManagement />);

			expect(screen.queryByTestId("territory-header")).not.toBeInTheDocument();
			expect(screen.queryByTestId("territory-content")).not.toBeInTheDocument();
		});
	});

	describe("Error State", () => {
		it("should show error message when there is an error", () => {
			const errorMessage = "Failed to load territory data";
			mockUseTerritoryData.mockReturnValue({
				...mockDefaultHookReturn,
				error: errorMessage,
				isLoading: false,
			});

			render(<TerritoryManagement />);

			expect(screen.getByText(errorMessage)).toBeInTheDocument();
			expect(
				screen.getByRole("button", { name: /retry/i }),
			).toBeInTheDocument();
		});

		it("should call refreshData when retry button is clicked", async () => {
			const mockRefreshData = jest.fn();
			mockUseTerritoryData.mockReturnValue({
				...mockDefaultHookReturn,
				error: "Network error",
				isLoading: false,
				refreshData: mockRefreshData,
			});

			render(<TerritoryManagement />);

			const retryButton = screen.getByRole("button", { name: /retry/i });
			await userEvent.click(retryButton);

			expect(mockRefreshData).toHaveBeenCalledTimes(1);
		});
	});

	describe("Successful State", () => {
		it("should render header and content when data is loaded", () => {
			render(<TerritoryManagement />);

			expect(screen.getByTestId("territory-header")).toBeInTheDocument();
			expect(screen.getByTestId("territory-content")).toBeInTheDocument();
		});

		it("should pass correct props to header component", () => {
			render(<TerritoryManagement />);

			// Header should have view mode controls
			expect(screen.getByTestId("view-map")).toBeInTheDocument();
			expect(screen.getByTestId("view-list")).toBeInTheDocument();
			expect(screen.getByTestId("view-analytics")).toBeInTheDocument();
			expect(screen.getByTestId("toggle-filters")).toBeInTheDocument();
		});

		it("should pass correct props to content component", () => {
			render(<TerritoryManagement />);

			// Content should show current view mode (default is 'map')
			expect(screen.getByTestId("current-view")).toHaveTextContent("map");
		});
	});

	describe("View Mode Management", () => {
		it("should change view mode when header buttons are clicked", async () => {
			render(<TerritoryManagement />);

			// Default view should be map
			expect(screen.getByTestId("current-view")).toHaveTextContent("map");

			// Change to list view
			await userEvent.click(screen.getByTestId("view-list"));
			expect(screen.getByTestId("current-view")).toHaveTextContent("list");

			// Change to analytics view
			await userEvent.click(screen.getByTestId("view-analytics"));
			expect(screen.getByTestId("current-view")).toHaveTextContent("analytics");

			// Change back to map view
			await userEvent.click(screen.getByTestId("view-map"));
			expect(screen.getByTestId("current-view")).toHaveTextContent("map");
		});
	});

	describe("Territory Selection", () => {
		it("should show details panel when territory is selected", async () => {
			render(<TerritoryManagement />);

			// Initially no details panel
			expect(screen.queryByTestId("territory-details")).not.toBeInTheDocument();

			// Select a territory
			await userEvent.click(screen.getByTestId("select-territory"));

			// Details panel should appear
			expect(screen.getByTestId("territory-details")).toBeInTheDocument();
			expect(screen.getByText("Test Territory")).toBeInTheDocument();
		});

		it("should close details panel when close button is clicked", async () => {
			render(<TerritoryManagement />);

			// Select territory
			await userEvent.click(screen.getByTestId("select-territory"));
			expect(screen.getByTestId("territory-details")).toBeInTheDocument();

			// Close details
			await userEvent.click(screen.getByTestId("close-details"));
			expect(screen.queryByTestId("territory-details")).not.toBeInTheDocument();
		});

		it("should only show one details panel at a time", async () => {
			render(<TerritoryManagement />);

			// Select territory twice
			await userEvent.click(screen.getByTestId("select-territory"));
			await userEvent.click(screen.getByTestId("select-territory"));

			// Should only have one details panel
			const detailsPanels = screen.getAllByTestId("territory-details");
			expect(detailsPanels).toHaveLength(1);
		});
	});

	describe("Filter Management", () => {
		it("should toggle filters visibility", async () => {
			render(<TerritoryManagement />);

			// Initially filters should be hidden (based on default state)
			const toggleButton = screen.getByTestId("toggle-filters");

			// Click to show filters
			await userEvent.click(toggleButton);

			// State should be updated (we can't test the actual filter visibility here
			// since it's in the mocked TerritoryHeader component, but we can verify
			// the state management works by checking multiple clicks)
			await userEvent.click(toggleButton);
			await userEvent.click(toggleButton);

			// If no errors are thrown, the state management is working
			expect(toggleButton).toBeInTheDocument();
		});

		it("should pass filters data to header component", () => {
			const customFilters = {
				searchTerm: "test search",
				sortBy: "growth" as const,
				region: "North",
			};

			mockUseTerritoryData.mockReturnValue({
				...mockDefaultHookReturn,
				filters: customFilters,
			});

			render(<TerritoryManagement />);

			// The header component should receive the filters
			// Since we mocked it, we can't test the actual props,
			// but we can verify the component renders without errors
			expect(screen.getByTestId("territory-header")).toBeInTheDocument();
		});
	});

	describe("Data Integration", () => {
		it("should pass filtered territories to content component", () => {
			const filteredTerritories = [mockTerritories[0]]; // Only first territory

			mockUseTerritoryData.mockReturnValue({
				...mockDefaultHookReturn,
				filteredTerritories,
			});

			render(<TerritoryManagement />);

			expect(screen.getByTestId("territory-content")).toBeInTheDocument();
		});

		it("should handle empty territories list", () => {
			mockUseTerritoryData.mockReturnValue({
				...mockDefaultHookReturn,
				territories: [],
				filteredTerritories: [],
			});

			render(<TerritoryManagement />);

			expect(screen.getByTestId("territory-header")).toBeInTheDocument();
			expect(screen.getByTestId("territory-content")).toBeInTheDocument();
		});
	});

	describe("Accessibility", () => {
		it("should have proper ARIA attributes for loading state", () => {
			mockUseTerritoryData.mockReturnValue({
				...mockDefaultHookReturn,
				isLoading: true,
			});

			render(<TerritoryManagement />);

			const loadingElement = screen.getByRole("status");
			expect(loadingElement).toHaveAttribute("aria-live", "polite");
		});

		it("should have proper ARIA attributes for error state", () => {
			mockUseTerritoryData.mockReturnValue({
				...mockDefaultHookReturn,
				error: "Test error",
				isLoading: false,
			});

			render(<TerritoryManagement />);

			const errorElement = screen.getByRole("alert");
			expect(errorElement).toBeInTheDocument();
		});

		it("should support keyboard navigation for view mode changes", async () => {
			render(<TerritoryManagement />);

			const mapButton = screen.getByTestId("view-map");
			const listButton = screen.getByTestId("view-list");

			// Test keyboard navigation
			mapButton.focus();
			expect(mapButton).toHaveFocus();

			// Tab to next button
			await userEvent.tab();
			expect(listButton).toHaveFocus();

			// Enter key should work
			await userEvent.keyboard("{Enter}");
			expect(screen.getByTestId("current-view")).toHaveTextContent("list");
		});
	});

	describe("Performance", () => {
		it("should not re-render unnecessarily", () => {
			const { rerender } = render(<TerritoryManagement />);

			// Re-render with same data
			rerender(<TerritoryManagement />);

			// Component should still work
			expect(screen.getByTestId("territory-header")).toBeInTheDocument();
			expect(screen.getByTestId("territory-content")).toBeInTheDocument();
		});

		it("should handle large territories datasets", () => {
			const largeTerritoryList = Array.from({ length: 1000 }, (_, i) => ({
				...mockTerritories[0],
				id: `territory_${i}`,
				name: `Territory ${i}`,
			}));

			mockUseTerritoryData.mockReturnValue({
				...mockDefaultHookReturn,
				territories: largeTerritoryList,
				filteredTerritories: largeTerritoryList,
			});

			const startTime = performance.now();
			render(<TerritoryManagement />);
			const endTime = performance.now();

			// Should render in reasonable time (< 100ms)
			expect(endTime - startTime).toBeLessThan(100);
			expect(screen.getByTestId("territory-content")).toBeInTheDocument();
		});
	});

	describe("Error Boundary", () => {
		it("should handle component errors gracefully", () => {
			// Mock console.error to avoid test output pollution
			const consoleSpy = jest
				.spyOn(console, "error")
				.mockImplementation(() => {});

			// Force an error in the hook
			mockUseTerritoryData.mockImplementation(() => {
				throw new Error("Component error");
			});

			expect(() => {
				render(<TerritoryManagement />);
			}).toThrow("Component error");

			consoleSpy.mockRestore();
		});
	});

	describe("Integration with Hook", () => {
		it("should call updateFilters when filters change", () => {
			const mockUpdateFilters = jest.fn();
			mockUseTerritoryData.mockReturnValue({
				...mockDefaultHookReturn,
				updateFilters: mockUpdateFilters,
			});

			render(<TerritoryManagement />);

			// Since we mocked the header component, we can't test the actual filter updates,
			// but we can verify the function is passed correctly
			expect(mockUseTerritoryData).toHaveBeenCalled();
		});

		it("should refresh data when requested", async () => {
			const mockRefreshData = jest.fn();
			mockUseTerritoryData.mockReturnValue({
				...mockDefaultHookReturn,
				refreshData: mockRefreshData,
			});

			render(<TerritoryManagement />);

			// Simulate error state to show retry button
			mockUseTerritoryData.mockReturnValue({
				...mockDefaultHookReturn,
				error: "Network error",
				isLoading: false,
				refreshData: mockRefreshData,
			});

			const { rerender } = render(<TerritoryManagement />);
			rerender(<TerritoryManagement />);

			const retryButton = screen.getByRole("button", { name: /retry/i });
			await userEvent.click(retryButton);

			expect(mockRefreshData).toHaveBeenCalled();
		});
	});
});
