import {
  projectCalculations,
  taskCalculations,
  timeCalculations,
  milestoneCalculations,
} from '../../utils/calculations';
import { Project, ProjectTask, TimeEntry, Milestone } from '../../types';

describe('projectCalculations', () => {
  const mockProject: Project = {
    id: '1',
    project_number: 'PRJ-001',
    project_name: 'Test Project',
    project_type: 'development',
    project_status: 'in_progress',
    priority: 'high',
    completion_percentage: 50,
    planned_start_date: '2024-01-01',
    planned_end_date: '2024-12-31',
    actual_start_date: '2024-01-01',
    approved_budget: 100000,
    actual_cost: 60000,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  };

  const mockTasks: ProjectTask[] = [
    {
      id: '1',
      project_id: '1',
      task_title: 'Task 1',
      task_status: 'done',
      task_priority: 'medium',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
    {
      id: '2',
      project_id: '1',
      task_title: 'Task 2',
      task_status: 'in_progress',
      task_priority: 'high',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
  ];

  describe('calculateProjectProgress', () => {
    it('should calculate progress based on tasks', () => {
      const progress = projectCalculations.calculateProjectProgress(mockProject, mockTasks);
      expect(progress).toBe(50); // 1 out of 2 tasks completed
    });

    it('should return project completion percentage when no tasks provided', () => {
      const progress = projectCalculations.calculateProjectProgress(mockProject, []);
      expect(progress).toBe(50);
    });
  });

  describe('calculateProjectDuration', () => {
    it('should calculate duration in days', () => {
      const duration = projectCalculations.calculateProjectDuration(mockProject);
      expect(duration).toBe(366); // 2024 is a leap year
    });

    it('should return null when dates are missing', () => {
      const projectWithoutDates = { ...mockProject, planned_end_date: undefined };
      const duration = projectCalculations.calculateProjectDuration(projectWithoutDates);
      expect(duration).toBeNull();
    });
  });

  describe('isProjectOverdue', () => {
    it('should return false for completed projects', () => {
      const completedProject = { ...mockProject, project_status: 'completed' as const };
      const isOverdue = projectCalculations.isProjectOverdue(completedProject);
      expect(isOverdue).toBe(false);
    });

    it('should return true for overdue projects', () => {
      const overdueProject = { ...mockProject, planned_end_date: '2020-01-01' };
      const isOverdue = projectCalculations.isProjectOverdue(overdueProject);
      expect(isOverdue).toBe(true);
    });
  });

  describe('calculateBudgetUtilization', () => {
    it('should calculate budget utilization', () => {
      const utilization = projectCalculations.calculateBudgetUtilization(mockProject);
      expect(utilization).toEqual({
        utilized: 60000,
        remaining: 40000,
        percentageUsed: 60,
      });
    });
  });

  describe('calculateProjectHealth', () => {
    it('should calculate project health score', () => {
      const health = projectCalculations.calculateProjectHealth(mockProject, mockTasks);
      expect(health.score).toBeGreaterThan(0);
      expect(health.status).toBeDefined();
      expect(Array.isArray(health.issues)).toBe(true);
    });
  });
});

describe('taskCalculations', () => {
  const mockTasks: ProjectTask[] = [
    {
      id: '1',
      project_id: '1',
      task_title: 'Task 1',
      task_status: 'done',
      task_priority: 'low',
      estimated_hours: 8,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-15T00:00:00Z',
    },
    {
      id: '2',
      project_id: '1',
      task_title: 'Task 2',
      task_status: 'in_progress',
      task_priority: 'high',
      estimated_hours: 16,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
    {
      id: '3',
      project_id: '1',
      task_title: 'Task 3',
      task_status: 'todo',
      task_priority: 'medium',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
  ];

  describe('calculateTaskProgress', () => {
    it('should calculate task progress correctly', () => {
      const progress = taskCalculations.calculateTaskProgress(mockTasks);
      expect(progress).toEqual({
        total: 3,
        completed: 1,
        inProgress: 1,
        todo: 1,
        percentageComplete: 33, // Rounded
      });
    });
  });

  describe('calculateTaskVelocity', () => {
    it('should calculate task velocity', () => {
      const velocity = taskCalculations.calculateTaskVelocity(mockTasks, 30);
      expect(velocity.totalCompleted).toBe(1);
      expect(velocity.tasksCompletedPerDay).toBeCloseTo(0.033, 2);
      expect(velocity.averageCompletionTime).toBe(14); // Days from creation to completion
    });
  });

  describe('calculateTaskComplexity', () => {
    it('should calculate task complexity', () => {
      const task = {
        ...mockTasks[1],
        estimated_hours: 40,
        task_priority: 'urgent' as const,
        dependencies: ['task1', 'task2'],
        checklist_items: Array(10).fill({ text: 'Item', completed: false }),
      };

      const complexity = taskCalculations.calculateTaskComplexity(task);
      expect(complexity.score).toBeGreaterThan(1);
      expect(complexity.level).toBeDefined();
      expect(Array.isArray(complexity.factors)).toBe(true);
    });
  });
});

describe('timeCalculations', () => {
  const mockTimeEntries: TimeEntry[] = [
    {
      id: '1',
      project_id: '1',
      user_id: 'user1',
      user_name: 'John Doe',
      description: 'Development work',
      duration_minutes: 120,
      activity_type: 'development',
      billable: true,
      hourly_rate: 100,
      start_time: '2024-01-01T09:00:00Z',
      end_time: '2024-01-01T11:00:00Z',
      created_at: '2024-01-01T09:00:00Z',
      updated_at: '2024-01-01T11:00:00Z',
    },
    {
      id: '2',
      project_id: '1',
      user_id: 'user1',
      user_name: 'John Doe',
      description: 'Meeting',
      duration_minutes: 60,
      activity_type: 'meeting',
      billable: false,
      start_time: '2024-01-01T14:00:00Z',
      end_time: '2024-01-01T15:00:00Z',
      created_at: '2024-01-01T14:00:00Z',
      updated_at: '2024-01-01T15:00:00Z',
    },
  ];

  describe('calculateTotalTime', () => {
    it('should calculate total time correctly', () => {
      const totals = timeCalculations.calculateTotalTime(mockTimeEntries);
      expect(totals).toEqual({
        totalMinutes: 180,
        billableMinutes: 120,
        nonBillableMinutes: 60,
        totalHours: 3,
        billableHours: 2,
      });
    });
  });

  describe('calculateTimeByActivity', () => {
    it('should group time by activity type', () => {
      const byActivity = timeCalculations.calculateTimeByActivity(mockTimeEntries);
      expect(byActivity).toEqual({
        development: 120,
        meeting: 60,
      });
    });
  });

  describe('calculateTimeByUser', () => {
    it('should group time by user', () => {
      const byUser = timeCalculations.calculateTimeByUser(mockTimeEntries);
      expect(byUser).toEqual({
        'John Doe': {
          totalMinutes: 180,
          billableMinutes: 120,
          entries: 2,
        },
      });
    });
  });

  describe('calculateEstimatedRevenue', () => {
    it('should calculate estimated revenue from billable hours', () => {
      const revenue = timeCalculations.calculateEstimatedRevenue(mockTimeEntries);
      expect(revenue).toBe(200); // 2 hours * $100/hour
    });
  });

  describe('calculateTimeEfficiency', () => {
    it('should calculate time efficiency', () => {
      const efficiency = timeCalculations.calculateTimeEfficiency(120, 180);
      expect(efficiency.efficiency).toBeCloseTo(66.67, 2);
      expect(efficiency.variance).toBe(60);
      expect(efficiency.status).toBe('over');
    });
  });
});

describe('milestoneCalculations', () => {
  const mockMilestones: Milestone[] = [
    {
      id: '1',
      project_id: '1',
      milestone_name: 'Phase 1 Complete',
      milestone_status: 'completed',
      due_date: '2024-01-31',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-31T00:00:00Z',
    },
    {
      id: '2',
      project_id: '1',
      milestone_name: 'Phase 2 Complete',
      milestone_status: 'in_progress',
      due_date: '2024-02-28',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
  ];

  describe('getMilestonesByStatus', () => {
    it('should group milestones by status', () => {
      const byStatus = milestoneCalculations.getMilestonesByStatus(mockMilestones);
      expect(byStatus.completed).toHaveLength(1);
      expect(byStatus.in_progress).toHaveLength(1);
    });
  });

  describe('getOverdueMilestones', () => {
    it('should return overdue milestones', () => {
      const overdueMilestones = [
        {
          ...mockMilestones[0],
          due_date: '2020-01-01',
          milestone_status: 'in_progress' as const,
        },
      ];

      const overdue = milestoneCalculations.getOverdueMilestones(overdueMilestones);
      expect(overdue).toHaveLength(1);
    });
  });

  describe('calculateMilestoneProgress', () => {
    it('should calculate milestone progress based on tasks', () => {
      const tasks: ProjectTask[] = [
        {
          id: '1',
          project_id: '1',
          milestone_id: '1',
          task_title: 'Task 1',
          task_status: 'done',
          task_priority: 'medium',
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        },
        {
          id: '2',
          project_id: '1',
          milestone_id: '1',
          task_title: 'Task 2',
          task_status: 'in_progress',
          task_priority: 'high',
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        },
      ];

      const progress = milestoneCalculations.calculateMilestoneProgress(mockMilestones[0], tasks);
      expect(progress).toEqual({
        totalTasks: 2,
        completedTasks: 1,
        percentageComplete: 50,
      });
    });
  });
});
