import {
  projectValidators,
  taskValidators,
  timeEntryValidators,
  generalValidators,
} from '../../utils/validators';
import { ProjectFormData, TaskFormData, TimeEntryCreate } from '../../types';

describe('projectValidators', () => {
  const validProjectData: Partial<ProjectFormData> = {
    project_name: 'Test Project',
    project_type: 'development',
    priority: 'medium',
    description: 'A test project description',
    planned_start_date: '2024-01-01',
    planned_end_date: '2024-12-31',
    approved_budget: 100000,
    completion_percentage: 50,
    client_name: 'Test Client',
  };

  describe('validateProject', () => {
    it('should pass validation for valid project data', () => {
      const result = projectValidators.validateProject(validProjectData);
      expect(result.isValid).toBe(true);
      expect(Object.keys(result.errors)).toHaveLength(0);
    });

    it('should fail validation when project name is missing', () => {
      const invalidData = { ...validProjectData, project_name: '' };
      const result = projectValidators.validateProject(invalidData);
      expect(result.isValid).toBe(false);
      expect(result.errors.project_name).toBeDefined();
    });

    it('should fail validation when project name is too short', () => {
      const invalidData = { ...validProjectData, project_name: 'Ab' };
      const result = projectValidators.validateProject(invalidData);
      expect(result.isValid).toBe(false);
      expect(result.errors.project_name).toContain('at least 3 characters');
    });

    it('should fail validation when project name is too long', () => {
      const invalidData = { ...validProjectData, project_name: 'A'.repeat(201) };
      const result = projectValidators.validateProject(invalidData);
      expect(result.isValid).toBe(false);
      expect(result.errors.project_name).toContain('less than 200 characters');
    });

    it('should fail validation when project type is missing', () => {
      const invalidData = { ...validProjectData, project_type: undefined };
      const result = projectValidators.validateProject(invalidData);
      expect(result.isValid).toBe(false);
      expect(result.errors.project_type).toBeDefined();
    });

    it('should fail validation when end date is before start date', () => {
      const invalidData = {
        ...validProjectData,
        planned_start_date: '2024-12-31',
        planned_end_date: '2024-01-01',
      };
      const result = projectValidators.validateProject(invalidData);
      expect(result.isValid).toBe(false);
      expect(result.errors.planned_end_date).toContain('after start date');
    });

    it('should fail validation for negative budget', () => {
      const invalidData = { ...validProjectData, approved_budget: -1000 };
      const result = projectValidators.validateProject(invalidData);
      expect(result.isValid).toBe(false);
      expect(result.errors.approved_budget).toContain('cannot be negative');
    });

    it('should fail validation for completion percentage out of range', () => {
      const invalidData = { ...validProjectData, completion_percentage: 150 };
      const result = projectValidators.validateProject(invalidData);
      expect(result.isValid).toBe(false);
      expect(result.errors.completion_percentage).toContain('between 0 and 100');
    });
  });

  describe('validateProjectDates', () => {
    it('should pass validation for valid date ranges', () => {
      const result = projectValidators.validateProjectDates(
        '2024-01-01',
        '2024-12-31',
        '2024-01-01',
        '2024-11-30'
      );
      expect(result.isValid).toBe(true);
    });

    it('should fail validation when planned end is before planned start', () => {
      const result = projectValidators.validateProjectDates('2024-12-31', '2024-01-01');
      expect(result.isValid).toBe(false);
      expect(result.errors.plannedDates).toBeDefined();
    });
  });
});

describe('taskValidators', () => {
  const validTaskData: Partial<TaskFormData> = {
    task_title: 'Test Task',
    task_priority: 'medium',
    task_description: 'A test task description',
    due_date: '2024-12-31',
    estimated_hours: 8,
    tags: ['frontend', 'react'],
  };

  describe('validateTask', () => {
    it('should pass validation for valid task data', () => {
      const result = taskValidators.validateTask(validTaskData);
      expect(result.isValid).toBe(true);
      expect(Object.keys(result.errors)).toHaveLength(0);
    });

    it('should fail validation when task title is missing', () => {
      const invalidData = { ...validTaskData, task_title: '' };
      const result = taskValidators.validateTask(invalidData);
      expect(result.isValid).toBe(false);
      expect(result.errors.task_title).toBeDefined();
    });

    it('should fail validation when task title is too short', () => {
      const invalidData = { ...validTaskData, task_title: 'AB' };
      const result = taskValidators.validateTask(invalidData);
      expect(result.isValid).toBe(false);
      expect(result.errors.task_title).toContain('at least 3 characters');
    });

    it('should fail validation when estimated hours is negative', () => {
      const invalidData = { ...validTaskData, estimated_hours: -5 };
      const result = taskValidators.validateTask(invalidData);
      expect(result.isValid).toBe(false);
      expect(result.errors.estimated_hours).toContain('cannot be negative');
    });

    it('should fail validation when estimated hours exceeds limit', () => {
      const invalidData = { ...validTaskData, estimated_hours: 1001 };
      const result = taskValidators.validateTask(invalidData);
      expect(result.isValid).toBe(false);
      expect(result.errors.estimated_hours).toContain('cannot exceed 1000');
    });

    it('should fail validation when too many tags', () => {
      const invalidData = { ...validTaskData, tags: Array(11).fill('tag') };
      const result = taskValidators.validateTask(invalidData);
      expect(result.isValid).toBe(false);
      expect(result.errors.tags).toContain('more than 10 tags');
    });
  });

  describe('validateTaskDependencies', () => {
    it('should pass validation for valid dependencies', () => {
      const result = taskValidators.validateTaskDependencies('task1', ['task2', 'task3']);
      expect(result.isValid).toBe(true);
    });

    it('should fail validation when task depends on itself', () => {
      const result = taskValidators.validateTaskDependencies('task1', ['task1', 'task2']);
      expect(result.isValid).toBe(false);
      expect(result.errors.dependencies).toContain('cannot depend on itself');
    });

    it('should fail validation when too many dependencies', () => {
      const dependencies = Array(21)
        .fill(0)
        .map((_, i) => `task${i}`);
      const result = taskValidators.validateTaskDependencies('task1', dependencies);
      expect(result.isValid).toBe(false);
      expect(result.errors.dependencies).toContain('more than 20 dependencies');
    });

    it('should fail validation for duplicate dependencies', () => {
      const result = taskValidators.validateTaskDependencies('task1', ['task2', 'task2']);
      expect(result.isValid).toBe(false);
      expect(result.errors.dependencies).toContain('Duplicate dependencies');
    });
  });

  describe('validateChecklistItems', () => {
    it('should pass validation for valid checklist items', () => {
      const items = [
        { id: '1', text: 'Item 1', completed: false },
        { id: '2', text: 'Item 2', completed: true },
      ];
      const result = taskValidators.validateChecklistItems(items);
      expect(result.isValid).toBe(true);
    });

    it('should fail validation when too many items', () => {
      const items = Array(51)
        .fill(0)
        .map((_, i) => ({
          id: i.toString(),
          text: `Item ${i}`,
          completed: false,
        }));
      const result = taskValidators.validateChecklistItems(items);
      expect(result.isValid).toBe(false);
      expect(result.errors.checklist).toContain('more than 50');
    });

    it('should fail validation when item text is empty', () => {
      const items = [{ id: '1', text: '', completed: false }];
      const result = taskValidators.validateChecklistItems(items);
      expect(result.isValid).toBe(false);
      expect(result.errors.checklist_0).toBeDefined();
    });
  });
});

describe('timeEntryValidators', () => {
  const validTimeEntryData: Partial<TimeEntryCreate> = {
    description: 'Working on feature development',
    activity_type: 'development',
    start_time: '2024-01-01T09:00:00Z',
    end_time: '2024-01-01T17:00:00Z',
    duration_minutes: 480,
    billable: true,
    hourly_rate: 100,
  };

  describe('validateTimeEntry', () => {
    it('should pass validation for valid time entry data', () => {
      const result = timeEntryValidators.validateTimeEntry(validTimeEntryData);
      expect(result.isValid).toBe(true);
      expect(Object.keys(result.errors)).toHaveLength(0);
    });

    it('should fail validation when description is missing', () => {
      const invalidData = { ...validTimeEntryData, description: '' };
      const result = timeEntryValidators.validateTimeEntry(invalidData);
      expect(result.isValid).toBe(false);
      expect(result.errors.description).toBeDefined();
    });

    it('should fail validation when description is too short', () => {
      const invalidData = { ...validTimeEntryData, description: 'AB' };
      const result = timeEntryValidators.validateTimeEntry(invalidData);
      expect(result.isValid).toBe(false);
      expect(result.errors.description).toContain('at least 3 characters');
    });

    it('should fail validation when end time is before start time', () => {
      const invalidData = {
        ...validTimeEntryData,
        start_time: '2024-01-01T17:00:00Z',
        end_time: '2024-01-01T09:00:00Z',
      };
      const result = timeEntryValidators.validateTimeEntry(invalidData);
      expect(result.isValid).toBe(false);
      expect(result.errors.end_time).toContain('after start time');
    });

    it('should fail validation when duration exceeds 24 hours', () => {
      const invalidData = {
        ...validTimeEntryData,
        start_time: '2024-01-01T09:00:00Z',
        end_time: '2024-01-02T10:00:00Z', // 25 hours
      };
      const result = timeEntryValidators.validateTimeEntry(invalidData);
      expect(result.isValid).toBe(false);
      expect(result.errors.duration).toContain('cannot exceed 24 hours');
    });

    it('should fail validation for negative duration minutes', () => {
      const invalidData = { ...validTimeEntryData, duration_minutes: -60 };
      const result = timeEntryValidators.validateTimeEntry(invalidData);
      expect(result.isValid).toBe(false);
      expect(result.errors.duration_minutes).toContain('greater than 0');
    });

    it('should fail validation for negative hourly rate', () => {
      const invalidData = { ...validTimeEntryData, hourly_rate: -50 };
      const result = timeEntryValidators.validateTimeEntry(invalidData);
      expect(result.isValid).toBe(false);
      expect(result.errors.hourly_rate).toContain('cannot be negative');
    });
  });

  describe('validateTimeRange', () => {
    it('should pass validation for valid time range', () => {
      const result = timeEntryValidators.validateTimeRange(
        '2024-01-01T09:00:00Z',
        '2024-01-01T17:00:00Z'
      );
      expect(result.isValid).toBe(true);
    });

    it('should fail validation for invalid date format', () => {
      const result = timeEntryValidators.validateTimeRange('invalid-date', '2024-01-01T17:00:00Z');
      expect(result.isValid).toBe(false);
      expect(result.errors.timeRange).toContain('Invalid date/time format');
    });
  });
});

describe('generalValidators', () => {
  describe('validateEmail', () => {
    it('should validate correct email addresses', () => {
      expect(generalValidators.validateEmail('test@example.com')).toBe(true);
      expect(generalValidators.validateEmail('user.name@domain.co.uk')).toBe(true);
    });

    it('should reject invalid email addresses', () => {
      expect(generalValidators.validateEmail('invalid-email')).toBe(false);
      expect(generalValidators.validateEmail('test@')).toBe(false);
      expect(generalValidators.validateEmail('@example.com')).toBe(false);
    });
  });

  describe('validateUrl', () => {
    it('should validate correct URLs', () => {
      expect(generalValidators.validateUrl('https://example.com')).toBe(true);
      expect(generalValidators.validateUrl('http://localhost:3000')).toBe(true);
    });

    it('should reject invalid URLs', () => {
      expect(generalValidators.validateUrl('not-a-url')).toBe(false);
      expect(generalValidators.validateUrl('ftp://')).toBe(false);
    });
  });

  describe('validateRequired', () => {
    it('should pass validation for non-empty values', () => {
      const result = generalValidators.validateRequired('test value', 'testField');
      expect(result.isValid).toBe(true);
    });

    it('should fail validation for empty values', () => {
      const result = generalValidators.validateRequired('', 'testField');
      expect(result.isValid).toBe(false);
      expect(result.errors.testField).toContain('is required');
    });

    it('should fail validation for null values', () => {
      const result = generalValidators.validateRequired(null, 'testField');
      expect(result.isValid).toBe(false);
      expect(result.errors.testField).toContain('is required');
    });
  });

  describe('validateLength', () => {
    it('should pass validation for correct length', () => {
      const result = generalValidators.validateLength('test', 3, 10, 'testField');
      expect(result.isValid).toBe(true);
    });

    it('should fail validation for too short values', () => {
      const result = generalValidators.validateLength('ab', 3, 10, 'testField');
      expect(result.isValid).toBe(false);
      expect(result.errors.testField).toContain('at least 3 characters');
    });

    it('should fail validation for too long values', () => {
      const result = generalValidators.validateLength('this is too long', 3, 10, 'testField');
      expect(result.isValid).toBe(false);
      expect(result.errors.testField).toContain('less than 10 characters');
    });
  });

  describe('validateNumericRange', () => {
    it('should pass validation for values within range', () => {
      const result = generalValidators.validateNumericRange(5, 1, 10, 'testField');
      expect(result.isValid).toBe(true);
    });

    it('should fail validation for values outside range', () => {
      const result = generalValidators.validateNumericRange(15, 1, 10, 'testField');
      expect(result.isValid).toBe(false);
      expect(result.errors.testField).toContain('between 1 and 10');
    });
  });

  describe('combineValidationResults', () => {
    it('should combine multiple validation results', () => {
      const result1 = { isValid: false, errors: { field1: 'Error 1' } };
      const result2 = { isValid: false, errors: { field2: 'Error 2' } };

      const combined = generalValidators.combineValidationResults(result1, result2);

      expect(combined.isValid).toBe(false);
      expect(combined.errors).toEqual({
        field1: 'Error 1',
        field2: 'Error 2',
      });
    });

    it('should return valid result when all inputs are valid', () => {
      const result1 = { isValid: true, errors: {} };
      const result2 = { isValid: true, errors: {} };

      const combined = generalValidators.combineValidationResults(result1, result2);

      expect(combined.isValid).toBe(true);
      expect(Object.keys(combined.errors)).toHaveLength(0);
    });
  });
});
