import { ProjectFormData, TaskFormData, MilestoneFormData, TimeEntryCreate } from '../types';

export interface ValidationResult {
  isValid: boolean;
  errors: Record<string, string>;
}

export const projectValidators = {
  validateProject(data: Partial<ProjectFormData>): ValidationResult {
    const errors: Record<string, string> = {};

    // Required fields
    if (!data.project_name?.trim()) {
      errors.project_name = 'Project name is required';
    } else if (data.project_name.length < 3) {
      errors.project_name = 'Project name must be at least 3 characters';
    } else if (data.project_name.length > 200) {
      errors.project_name = 'Project name must be less than 200 characters';
    }

    if (!data.project_type) {
      errors.project_type = 'Project type is required';
    }

    if (!data.priority) {
      errors.priority = 'Priority is required';
    }

    // Description validation
    if (data.description && data.description.length > 2000) {
      errors.description = 'Description must be less than 2000 characters';
    }

    // Date validations
    if (data.planned_start_date && data.planned_end_date) {
      const startDate = new Date(data.planned_start_date);
      const endDate = new Date(data.planned_end_date);

      if (endDate <= startDate) {
        errors.planned_end_date = 'End date must be after start date';
      }
    }

    if (data.actual_start_date && data.actual_end_date) {
      const startDate = new Date(data.actual_start_date);
      const endDate = new Date(data.actual_end_date);

      if (endDate <= startDate) {
        errors.actual_end_date = 'Actual end date must be after actual start date';
      }
    }

    // Budget validations
    if (data.approved_budget !== undefined && data.approved_budget < 0) {
      errors.approved_budget = 'Budget cannot be negative';
    }

    if (data.actual_cost !== undefined && data.actual_cost < 0) {
      errors.actual_cost = 'Actual cost cannot be negative';
    }

    // Completion percentage
    if (data.completion_percentage !== undefined) {
      if (data.completion_percentage < 0 || data.completion_percentage > 100) {
        errors.completion_percentage = 'Completion percentage must be between 0 and 100';
      }
    }

    // Client name validation
    if (data.client_name && (data.client_name.length < 2 || data.client_name.length > 100)) {
      errors.client_name = 'Client name must be between 2 and 100 characters';
    }

    return {
      isValid: Object.keys(errors).length === 0,
      errors
    };
  },

  validateProjectDates(
    plannedStart?: string,
    plannedEnd?: string,
    actualStart?: string,
    actualEnd?: string
  ): ValidationResult {
    const errors: Record<string, string> = {};

    if (plannedStart && plannedEnd) {
      const start = new Date(plannedStart);
      const end = new Date(plannedEnd);

      if (end <= start) {
        errors.plannedDates = 'Planned end date must be after planned start date';
      }

      // Check if dates are too far in the future (more than 5 years)
      const fiveYearsFromNow = new Date();
      fiveYearsFromNow.setFullYear(fiveYearsFromNow.getFullYear() + 5);

      if (end > fiveYearsFromNow) {
        errors.plannedEnd = 'Planned end date cannot be more than 5 years in the future';
      }
    }

    if (actualStart && actualEnd) {
      const start = new Date(actualStart);
      const end = new Date(actualEnd);

      if (end <= start) {
        errors.actualDates = 'Actual end date must be after actual start date';
      }
    }

    if (plannedStart && actualStart) {
      const planned = new Date(plannedStart);
      const actual = new Date(actualStart);

      // Warning if actual start is significantly different from planned
      const daysDifference = Math.abs((actual.getTime() - planned.getTime()) / (1000 * 60 * 60 * 24));

      if (daysDifference > 30) {
        errors.startDateWarning = 'Actual start date differs significantly from planned start date';
      }
    }

    return {
      isValid: Object.keys(errors).length === 0,
      errors
    };
  }
};

export const taskValidators = {
  validateTask(data: Partial<TaskFormData>): ValidationResult {
    const errors: Record<string, string> = {};

    // Required fields
    if (!data.task_title?.trim()) {
      errors.task_title = 'Task title is required';
    } else if (data.task_title.length < 3) {
      errors.task_title = 'Task title must be at least 3 characters';
    } else if (data.task_title.length > 200) {
      errors.task_title = 'Task title must be less than 200 characters';
    }

    if (!data.task_priority) {
      errors.task_priority = 'Priority is required';
    }

    // Description validation
    if (data.task_description && data.task_description.length > 2000) {
      errors.task_description = 'Description must be less than 2000 characters';
    }

    // Due date validation
    if (data.due_date) {
      const dueDate = new Date(data.due_date);
      const now = new Date();

      // Check if due date is in the past (with some tolerance)
      const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);

      if (dueDate < oneDayAgo) {
        errors.due_date = 'Due date cannot be in the past';
      }
    }

    // Estimated hours validation
    if (data.estimated_hours !== undefined) {
      if (data.estimated_hours < 0) {
        errors.estimated_hours = 'Estimated hours cannot be negative';
      } else if (data.estimated_hours > 1000) {
        errors.estimated_hours = 'Estimated hours cannot exceed 1000';
      }
    }

    // Tags validation
    if (data.tags && Array.isArray(data.tags)) {
      if (data.tags.length > 10) {
        errors.tags = 'Cannot have more than 10 tags';
      }

      for (const tag of data.tags) {
        if (typeof tag !== 'string' || tag.length < 1 || tag.length > 50) {
          errors.tags = 'Each tag must be between 1 and 50 characters';
          break;
        }
      }
    }

    return {
      isValid: Object.keys(errors).length === 0,
      errors
    };
  },

  validateTaskDependencies(taskId: string, dependencies: string[]): ValidationResult {
    const errors: Record<string, string> = {};

    if (dependencies.includes(taskId)) {
      errors.dependencies = 'Task cannot depend on itself';
    }

    if (dependencies.length > 20) {
      errors.dependencies = 'Cannot have more than 20 dependencies';
    }

    // Check for duplicate dependencies
    const uniqueDeps = new Set(dependencies);
    if (uniqueDeps.size !== dependencies.length) {
      errors.dependencies = 'Duplicate dependencies are not allowed';
    }

    return {
      isValid: Object.keys(errors).length === 0,
      errors
    };
  },

  validateChecklistItems(items: Array<{ id: string; text: string; completed: boolean }>): ValidationResult {
    const errors: Record<string, string> = {};

    if (items.length > 50) {
      errors.checklist = 'Cannot have more than 50 checklist items';
    }

    for (let i = 0; i < items.length; i++) {
      const item = items[i];

      if (!item.text?.trim()) {
        errors[`checklist_${i}`] = `Checklist item ${i + 1} cannot be empty`;
      } else if (item.text.length > 200) {
        errors[`checklist_${i}`] = `Checklist item ${i + 1} must be less than 200 characters`;
      }
    }

    return {
      isValid: Object.keys(errors).length === 0,
      errors
    };
  }
};

export const milestoneValidators = {
  validateMilestone(data: Partial<MilestoneFormData>): ValidationResult {
    const errors: Record<string, string> = {};

    // Required fields
    if (!data.milestone_name?.trim()) {
      errors.milestone_name = 'Milestone name is required';
    } else if (data.milestone_name.length < 3) {
      errors.milestone_name = 'Milestone name must be at least 3 characters';
    } else if (data.milestone_name.length > 200) {
      errors.milestone_name = 'Milestone name must be less than 200 characters';
    }

    // Description validation
    if (data.description && data.description.length > 1000) {
      errors.description = 'Description must be less than 1000 characters';
    }

    // Due date validation
    if (data.due_date) {
      const dueDate = new Date(data.due_date);
      const now = new Date();

      if (dueDate < now) {
        errors.due_date = 'Due date cannot be in the past';
      }
    }

    return {
      isValid: Object.keys(errors).length === 0,
      errors
    };
  }
};

export const timeEntryValidators = {
  validateTimeEntry(data: Partial<TimeEntryCreate>): ValidationResult {
    const errors: Record<string, string> = {};

    // Required fields
    if (!data.description?.trim()) {
      errors.description = 'Description is required';
    } else if (data.description.length < 3) {
      errors.description = 'Description must be at least 3 characters';
    } else if (data.description.length > 500) {
      errors.description = 'Description must be less than 500 characters';
    }

    if (!data.activity_type) {
      errors.activity_type = 'Activity type is required';
    }

    // Time validations
    if (data.start_time && data.end_time) {
      const start = new Date(data.start_time);
      const end = new Date(data.end_time);

      if (end <= start) {
        errors.end_time = 'End time must be after start time';
      }

      const durationMs = end.getTime() - start.getTime();
      const durationHours = durationMs / (1000 * 60 * 60);

      // Check for unrealistic durations
      if (durationHours > 24) {
        errors.duration = 'Time entry cannot exceed 24 hours';
      }

      if (durationHours < 0.017) { // Less than 1 minute
        errors.duration = 'Time entry must be at least 1 minute';
      }
    }

    // Duration validation
    if (data.duration_minutes !== undefined) {
      if (data.duration_minutes <= 0) {
        errors.duration_minutes = 'Duration must be greater than 0';
      } else if (data.duration_minutes > 1440) { // 24 hours
        errors.duration_minutes = 'Duration cannot exceed 24 hours';
      }
    }

    // Hourly rate validation
    if (data.hourly_rate !== undefined) {
      if (data.hourly_rate < 0) {
        errors.hourly_rate = 'Hourly rate cannot be negative';
      } else if (data.hourly_rate > 10000) {
        errors.hourly_rate = 'Hourly rate seems unrealistic';
      }
    }

    return {
      isValid: Object.keys(errors).length === 0,
      errors
    };
  },

  validateTimeRange(startTime: string, endTime: string): ValidationResult {
    const errors: Record<string, string> = {};

    const start = new Date(startTime);
    const end = new Date(endTime);

    if (isNaN(start.getTime()) || isNaN(end.getTime())) {
      errors.timeRange = 'Invalid date/time format';
      return { isValid: false, errors };
    }

    if (end <= start) {
      errors.timeRange = 'End time must be after start time';
    }

    const now = new Date();
    if (start > now) {
      errors.startTime = 'Start time cannot be in the future';
    }

    const durationHours = (end.getTime() - start.getTime()) / (1000 * 60 * 60);
    if (durationHours > 24) {
      errors.duration = 'Time entry cannot exceed 24 hours';
    }

    return {
      isValid: Object.keys(errors).length === 0,
      errors
    };
  }
};

export const generalValidators = {
  validateEmail(email: string): boolean {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  },

  validateUrl(url: string): boolean {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  },

  validatePhoneNumber(phone: string): boolean {
    // Basic phone number validation
    const phoneRegex = /^\+?[\d\s\-\(\)]{10,}$/;
    return phoneRegex.test(phone);
  },

  validateRequired<T>(value: T, fieldName: string): ValidationResult {
    const errors: Record<string, string> = {};

    if (value === null || value === undefined || value === '') {
      errors[fieldName] = `${fieldName} is required`;
    }

    return {
      isValid: Object.keys(errors).length === 0,
      errors
    };
  },

  validateLength(
    value: string,
    minLength: number,
    maxLength: number,
    fieldName: string
  ): ValidationResult {
    const errors: Record<string, string> = {};

    if (value.length < minLength) {
      errors[fieldName] = `${fieldName} must be at least ${minLength} characters`;
    } else if (value.length > maxLength) {
      errors[fieldName] = `${fieldName} must be less than ${maxLength} characters`;
    }

    return {
      isValid: Object.keys(errors).length === 0,
      errors
    };
  },

  validateNumericRange(
    value: number,
    min: number,
    max: number,
    fieldName: string
  ): ValidationResult {
    const errors: Record<string, string> = {};

    if (value < min || value > max) {
      errors[fieldName] = `${fieldName} must be between ${min} and ${max}`;
    }

    return {
      isValid: Object.keys(errors).length === 0,
      errors
    };
  },

  combineValidationResults(...results: ValidationResult[]): ValidationResult {
    const combinedErrors: Record<string, string> = {};

    for (const result of results) {
      Object.assign(combinedErrors, result.errors);
    }

    return {
      isValid: Object.keys(combinedErrors).length === 0,
      errors: combinedErrors
    };
  }
};

export default {
  project: projectValidators,
  task: taskValidators,
  milestone: milestoneValidators,
  timeEntry: timeEntryValidators,
  general: generalValidators
};
