import { Project, ProjectTask, TimeEntry, Milestone } from '../types';
import { differenceInDays, addDays, isAfter, isBefore, startOfDay, endOfDay } from 'date-fns';

export const projectCalculations = {
  calculateProjectProgress(project: Project, tasks: ProjectTask[] = []): number {
    if (!tasks.length) return project.completion_percentage || 0;

    const completedTasks = tasks.filter(task => task.task_status === 'done');
    const totalTasks = tasks.length;

    return totalTasks > 0 ? Math.round((completedTasks.length / totalTasks) * 100) : 0;
  },

  calculateProjectDuration(project: Project): number | null {
    if (!project.planned_start_date || !project.planned_end_date) return null;

    const start = new Date(project.planned_start_date);
    const end = new Date(project.planned_end_date);

    return differenceInDays(end, start) + 1;
  },

  calculateActualDuration(project: Project): number | null {
    if (!project.actual_start_date || !project.actual_end_date) return null;

    const start = new Date(project.actual_start_date);
    const end = new Date(project.actual_end_date);

    return differenceInDays(end, start) + 1;
  },

  calculateDaysRemaining(project: Project): number | null {
    if (!project.planned_end_date) return null;

    const endDate = new Date(project.planned_end_date);
    const today = new Date();

    const remaining = differenceInDays(endDate, today);
    return remaining > 0 ? remaining : 0;
  },

  isProjectOverdue(project: Project): boolean {
    if (!project.planned_end_date) return false;
    if (['completed', 'cancelled'].includes(project.project_status)) return false;

    const endDate = new Date(project.planned_end_date);
    const today = new Date();

    return isBefore(endDate, startOfDay(today));
  },

  calculateBudgetUtilization(project: Project): {
    utilized: number;
    remaining: number;
    percentageUsed: number;
  } {
    const approved = project.approved_budget || 0;
    const spent = project.actual_cost || 0;

    return {
      utilized: spent,
      remaining: Math.max(0, approved - spent),
      percentageUsed: approved > 0 ? Math.round((spent / approved) * 100) : 0
    };
  },

  calculateProjectHealth(project: Project, tasks: ProjectTask[] = []): {
    score: number;
    status: 'excellent' | 'good' | 'warning' | 'critical';
    issues: string[];
  } {
    const issues: string[] = [];
    let score = 100;

    // Check if overdue
    if (this.isProjectOverdue(project)) {
      score -= 30;
      issues.push('Project is overdue');
    }

    // Check budget
    const budgetHealth = this.calculateBudgetUtilization(project);
    if (budgetHealth.percentageUsed > 90) {
      score -= 20;
      issues.push('Budget utilization is high');
    } else if (budgetHealth.percentageUsed > 100) {
      score -= 40;
      issues.push('Project is over budget');
    }

    // Check progress vs time
    const daysRemaining = this.calculateDaysRemaining(project);
    const totalDuration = this.calculateProjectDuration(project);

    if (daysRemaining !== null && totalDuration !== null) {
      const timeElapsedPercent = ((totalDuration - daysRemaining) / totalDuration) * 100;
      const progressGap = timeElapsedPercent - (project.completion_percentage || 0);

      if (progressGap > 20) {
        score -= 15;
        issues.push('Progress is behind schedule');
      }
    }

    // Check overdue tasks
    const overdueTasks = tasks.filter(task =>
      task.due_date &&
      isBefore(new Date(task.due_date), new Date()) &&
      !['done', 'cancelled'].includes(task.task_status)
    );

    if (overdueTasks.length > 0) {
      score -= overdueTasks.length * 5;
      issues.push(`${overdueTasks.length} overdue tasks`);
    }

    // Determine status
    let status: 'excellent' | 'good' | 'warning' | 'critical';
    if (score >= 90) status = 'excellent';
    else if (score >= 70) status = 'good';
    else if (score >= 50) status = 'warning';
    else status = 'critical';

    return {
      score: Math.max(0, score),
      status,
      issues
    };
  }
};

export const taskCalculations = {
  calculateTaskProgress(tasks: ProjectTask[]): {
    total: number;
    completed: number;
    inProgress: number;
    todo: number;
    percentageComplete: number;
  } {
    const total = tasks.length;
    const completed = tasks.filter(t => t.task_status === 'done').length;
    const inProgress = tasks.filter(t => t.task_status === 'in_progress').length;
    const todo = tasks.filter(t => t.task_status === 'todo').length;

    return {
      total,
      completed,
      inProgress,
      todo,
      percentageComplete: total > 0 ? Math.round((completed / total) * 100) : 0
    };
  },

  calculateTaskVelocity(tasks: ProjectTask[], daysBack: number = 30): {
    tasksCompletedPerDay: number;
    totalCompleted: number;
    averageCompletionTime: number;
  } {
    const cutoffDate = addDays(new Date(), -daysBack);

    const recentlyCompleted = tasks.filter(task =>
      task.task_status === 'done' &&
      task.updated_at &&
      isAfter(new Date(task.updated_at), cutoffDate)
    );

    const totalCompleted = recentlyCompleted.length;
    const tasksCompletedPerDay = totalCompleted / daysBack;

    // Calculate average completion time
    const completionTimes = recentlyCompleted
      .filter(task => task.created_at && task.updated_at)
      .map(task => differenceInDays(
        new Date(task.updated_at!),
        new Date(task.created_at!)
      ));

    const averageCompletionTime = completionTimes.length > 0
      ? completionTimes.reduce((sum, time) => sum + time, 0) / completionTimes.length
      : 0;

    return {
      tasksCompletedPerDay,
      totalCompleted,
      averageCompletionTime
    };
  },

  getOverdueTasks(tasks: ProjectTask[]): ProjectTask[] {
    const today = new Date();

    return tasks.filter(task =>
      task.due_date &&
      isBefore(new Date(task.due_date), startOfDay(today)) &&
      !['done', 'cancelled'].includes(task.task_status)
    );
  },

  getUpcomingTasks(tasks: ProjectTask[], daysAhead: number = 7): ProjectTask[] {
    const today = new Date();
    const futureDate = addDays(today, daysAhead);

    return tasks.filter(task =>
      task.due_date &&
      isAfter(new Date(task.due_date), today) &&
      isBefore(new Date(task.due_date), endOfDay(futureDate)) &&
      !['done', 'cancelled'].includes(task.task_status)
    );
  },

  calculateTaskComplexity(task: ProjectTask): {
    score: number;
    level: 'simple' | 'moderate' | 'complex' | 'very_complex';
    factors: string[];
  } {
    let score = 1;
    const factors: string[] = [];

    // Estimated hours
    if (task.estimated_hours) {
      if (task.estimated_hours > 40) {
        score += 3;
        factors.push('High time estimate');
      } else if (task.estimated_hours > 16) {
        score += 2;
        factors.push('Moderate time estimate');
      } else if (task.estimated_hours > 8) {
        score += 1;
        factors.push('Above average time estimate');
      }
    }

    // Dependencies
    if (task.dependencies && task.dependencies.length > 0) {
      score += task.dependencies.length;
      factors.push(`${task.dependencies.length} dependencies`);
    }

    // Checklist items
    if (task.checklist_items && task.checklist_items.length > 0) {
      const checklistScore = Math.floor(task.checklist_items.length / 5);
      score += checklistScore;
      factors.push(`${task.checklist_items.length} checklist items`);
    }

    // Priority
    if (task.task_priority === 'urgent') {
      score += 2;
      factors.push('Urgent priority');
    } else if (task.task_priority === 'high') {
      score += 1;
      factors.push('High priority');
    }

    // Determine complexity level
    let level: 'simple' | 'moderate' | 'complex' | 'very_complex';
    if (score <= 2) level = 'simple';
    else if (score <= 4) level = 'moderate';
    else if (score <= 7) level = 'complex';
    else level = 'very_complex';

    return { score, level, factors };
  }
};

export const timeCalculations = {
  calculateTotalTime(timeEntries: TimeEntry[]): {
    totalMinutes: number;
    billableMinutes: number;
    nonBillableMinutes: number;
    totalHours: number;
    billableHours: number;
  } {
    const totalMinutes = timeEntries.reduce((sum, entry) => sum + entry.duration_minutes, 0);
    const billableMinutes = timeEntries
      .filter(entry => entry.billable)
      .reduce((sum, entry) => sum + entry.duration_minutes, 0);

    return {
      totalMinutes,
      billableMinutes,
      nonBillableMinutes: totalMinutes - billableMinutes,
      totalHours: Math.round((totalMinutes / 60) * 100) / 100,
      billableHours: Math.round((billableMinutes / 60) * 100) / 100
    };
  },

  calculateTimeByActivity(timeEntries: TimeEntry[]): Record<string, number> {
    return timeEntries.reduce((acc, entry) => {
      const activity = entry.activity_type;
      acc[activity] = (acc[activity] || 0) + entry.duration_minutes;
      return acc;
    }, {} as Record<string, number>);
  },

  calculateTimeByUser(timeEntries: TimeEntry[]): Record<string, {
    totalMinutes: number;
    billableMinutes: number;
    entries: number;
  }> {
    return timeEntries.reduce((acc, entry) => {
      const user = entry.user_name;
      if (!acc[user]) {
        acc[user] = { totalMinutes: 0, billableMinutes: 0, entries: 0 };
      }

      acc[user].totalMinutes += entry.duration_minutes;
      if (entry.billable) {
        acc[user].billableMinutes += entry.duration_minutes;
      }
      acc[user].entries += 1;

      return acc;
    }, {} as Record<string, { totalMinutes: number; billableMinutes: number; entries: number }>);
  },

  calculateEstimatedRevenue(timeEntries: TimeEntry[]): number {
    return timeEntries.reduce((sum, entry) => {
      if (entry.billable && entry.hourly_rate) {
        const hours = entry.duration_minutes / 60;
        return sum + (hours * entry.hourly_rate);
      }
      return sum;
    }, 0);
  },

  calculateTimeEfficiency(planned: number, actual: number): {
    efficiency: number;
    variance: number;
    status: 'under' | 'on_track' | 'over';
  } {
    const efficiency = planned > 0 ? (planned / actual) * 100 : 0;
    const variance = actual - planned;

    let status: 'under' | 'on_track' | 'over';
    if (variance < -planned * 0.1) status = 'under';
    else if (variance > planned * 0.1) status = 'over';
    else status = 'on_track';

    return { efficiency, variance, status };
  }
};

export const milestoneCalculations = {
  getMilestonesByStatus(milestones: Milestone[]): Record<string, Milestone[]> {
    return milestones.reduce((acc, milestone) => {
      const status = milestone.milestone_status;
      if (!acc[status]) acc[status] = [];
      acc[status].push(milestone);
      return acc;
    }, {} as Record<string, Milestone[]>);
  },

  getOverdueMilestones(milestones: Milestone[]): Milestone[] {
    const today = new Date();

    return milestones.filter(milestone =>
      milestone.due_date &&
      isBefore(new Date(milestone.due_date), startOfDay(today)) &&
      milestone.milestone_status !== 'completed'
    );
  },

  getUpcomingMilestones(milestones: Milestone[], daysAhead: number = 14): Milestone[] {
    const today = new Date();
    const futureDate = addDays(today, daysAhead);

    return milestones.filter(milestone =>
      milestone.due_date &&
      isAfter(new Date(milestone.due_date), today) &&
      isBefore(new Date(milestone.due_date), endOfDay(futureDate)) &&
      milestone.milestone_status !== 'completed'
    );
  },

  calculateMilestoneProgress(milestone: Milestone, tasks: ProjectTask[] = []): {
    totalTasks: number;
    completedTasks: number;
    percentageComplete: number;
  } {
    const milestoneTasks = tasks.filter(task => task.milestone_id === milestone.id);
    const completedTasks = milestoneTasks.filter(task => task.task_status === 'done').length;

    return {
      totalTasks: milestoneTasks.length,
      completedTasks,
      percentageComplete: milestoneTasks.length > 0
        ? Math.round((completedTasks / milestoneTasks.length) * 100)
        : 0
    };
  }
};
