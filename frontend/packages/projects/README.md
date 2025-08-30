# @dotmac/projects

A comprehensive project management package for the DotMac ISP framework, providing React components, hooks, and utilities for managing projects, tasks, milestones, and time tracking.

## Features

### Core Functionality

- **Project Management**: Complete CRUD operations for projects with status tracking, budget management, and timeline visualization
- **Task Management**: Kanban-style task boards with drag-and-drop, dependencies, checklists, and priority management
- **Time Tracking**: Real-time timer, manual time entry, and comprehensive time analytics
- **Milestone Tracking**: Project milestone management with progress visualization
- **Analytics & Reporting**: Project health scoring, time utilization reports, and performance metrics

### Components

- **ProjectDashboard**: Overview dashboard with metrics, recent projects, and quick actions
- **ProjectList**: Filterable and searchable project listing with bulk operations
- **TaskBoard**: Kanban-style task management with drag-and-drop functionality
- **TimeTracker**: Timer interface with manual entry and historical time tracking

### Hooks

- **useProjects**: Project management with CRUD operations and analytics
- **useTasks**: Task management with status changes and dependency handling
- **useTimeTracking**: Time tracking with real-time timer and time entry management

### Utilities

- **Calculations**: Project health, task complexity, time efficiency, and progress calculations
- **Formatters**: Date/time formatting, status displays, currency formatting, and smart text formatting
- **Validators**: Comprehensive form validation for projects, tasks, and time entries

## Installation

```bash
npm install @dotmac/projects
# or
pnpm add @dotmac/projects
```

## Usage

### Basic Project Dashboard

```tsx
import { ProjectDashboard } from '@dotmac/projects';

export function Dashboard() {
  return (
    <ProjectDashboard
      showMetrics={true}
      showRecentProjects={true}
      showTaskSummary={true}
      refreshInterval={30000}
    />
  );
}
```

### Project List with Filtering

```tsx
import { ProjectList } from '@dotmac/projects';
import type { ProjectFilters } from '@dotmac/projects';

export function Projects() {
  const initialFilters: ProjectFilters = {
    project_status: ['in_progress', 'planning'],
    priority: ['high', 'urgent']
  };

  const handleProjectSelect = (project) => {
    // Navigate to project details
    router.push(`/projects/${project.id}`);
  };

  return (
    <ProjectList
      filters={initialFilters}
      showFilters={true}
      showActions={true}
      allowBulkOperations={true}
      onProjectSelect={handleProjectSelect}
    />
  );
}
```

### Task Board (Kanban)

```tsx
import { TaskBoard } from '@dotmac/projects';

export function ProjectTasks({ projectId }: { projectId: string }) {
  return (
    <TaskBoard
      projectId={projectId}
      showFilters={true}
      allowDragDrop={true}
      groupBy="status"
    />
  );
}
```

### Time Tracking

```tsx
import { TimeTracker } from '@dotmac/projects';

export function TimeTracking({ projectId, taskId }: {
  projectId: string;
  taskId?: string;
}) {
  return (
    <TimeTracker
      projectId={projectId}
      taskId={taskId}
      showHistory={true}
      allowBulkEntry={true}
    />
  );
}
```

### Using Hooks

#### Project Management

```tsx
import { useProjects } from '@dotmac/projects';

export function ProjectManager() {
  const {
    projects,
    loading,
    error,
    createProject,
    updateProject,
    deleteProject,
    getProjectAnalytics
  } = useProjects();

  const handleCreateProject = async () => {
    await createProject({
      project_name: 'New Project',
      project_type: 'development',
      priority: 'medium',
      planned_start_date: '2024-01-01',
      planned_end_date: '2024-12-31'
    });
  };

  if (loading) return <div>Loading projects...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      <button onClick={handleCreateProject}>Create Project</button>
      {projects.map(project => (
        <div key={project.id}>{project.project_name}</div>
      ))}
    </div>
  );
}
```

#### Task Management

```tsx
import { useTasks } from '@dotmac/projects';

export function TaskManager({ projectId }: { projectId: string }) {
  const {
    tasks,
    loading,
    createTask,
    updateTask,
    changeTaskStatus
  } = useTasks();

  const handleCreateTask = async () => {
    await createTask({
      project_id: projectId,
      task_title: 'New Task',
      task_priority: 'medium',
      task_status: 'todo'
    });
  };

  return (
    <div>
      <button onClick={handleCreateTask}>Add Task</button>
      {tasks.map(task => (
        <div key={task.id}>
          <span>{task.task_title}</span>
          <button
            onClick={() => changeTaskStatus(task.id, 'done')}
          >
            Mark Complete
          </button>
        </div>
      ))}
    </div>
  );
}
```

#### Time Tracking

```tsx
import { useTimeTracking } from '@dotmac/projects';

export function TimerWidget({ projectId }: { projectId: string }) {
  const {
    isTimerRunning,
    currentDuration,
    startTimer,
    stopTimer,
    currentEntry
  } = useTimeTracking();

  const handleTimerToggle = async () => {
    if (isTimerRunning) {
      await stopTimer();
    } else {
      await startTimer(projectId, undefined, 'Working on project tasks');
    }
  };

  return (
    <div className="timer-widget">
      <div className="timer-display">
        {Math.floor(currentDuration / 60)}:{(currentDuration % 60).toString().padStart(2, '0')}
      </div>
      <button onClick={handleTimerToggle}>
        {isTimerRunning ? 'Stop Timer' : 'Start Timer'}
      </button>
      {currentEntry && (
        <div className="current-task">
          {currentEntry.description}
        </div>
      )}
    </div>
  );
}
```

### Utility Functions

#### Project Calculations

```tsx
import { projectCalculations, formatters } from '@dotmac/projects';

export function ProjectHealth({ project, tasks }) {
  const health = projectCalculations.calculateProjectHealth(project, tasks);
  const healthDisplay = formatters.project.formatProjectHealth(health.score);

  return (
    <div className={`health-indicator health-${healthDisplay.color}`}>
      <span className="score">{health.score}</span>
      <span className="label">{healthDisplay.label}</span>
      <div className="description">{healthDisplay.description}</div>
      {health.issues.length > 0 && (
        <ul className="issues">
          {health.issues.map((issue, index) => (
            <li key={index}>{issue}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

#### Date and Time Formatting

```tsx
import { formatters } from '@dotmac/projects';

export function ProjectCard({ project }) {
  return (
    <div className="project-card">
      <h3>{project.project_name}</h3>
      <div className="project-meta">
        <span>
          Created: {formatters.date.formatSmartDate(project.created_at)}
        </span>
        <span>
          Due: {formatters.date.formatRelativeTime(project.planned_end_date)}
        </span>
        <span>
          Budget: {formatters.number.formatCurrency(project.approved_budget)}
        </span>
        <span className={`status status-${formatters.status.getStatusColor(project.project_status)}`}>
          {formatters.status.formatProjectStatus(project.project_status)}
        </span>
      </div>
    </div>
  );
}
```

#### Form Validation

```tsx
import { validators } from '@dotmac/projects';
import type { ProjectFormData } from '@dotmac/projects';

export function ProjectForm() {
  const [formData, setFormData] = useState<ProjectFormData>({
    project_name: '',
    project_type: 'development',
    priority: 'medium'
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const validation = validators.project.validateProject(formData);

    if (!validation.isValid) {
      setErrors(validation.errors);
      return;
    }

    // Submit form
    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <label>Project Name</label>
        <input
          value={formData.project_name}
          onChange={(e) => setFormData(prev => ({ ...prev, project_name: e.target.value }))}
        />
        {errors.project_name && <span className="error">{errors.project_name}</span>}
      </div>

      <div>
        <label>Project Type</label>
        <select
          value={formData.project_type}
          onChange={(e) => setFormData(prev => ({ ...prev, project_type: e.target.value }))}
        >
          <option value="development">Development</option>
          <option value="maintenance">Maintenance</option>
          <option value="infrastructure">Infrastructure</option>
        </select>
        {errors.project_type && <span className="error">{errors.project_type}</span>}
      </div>

      <button type="submit">Create Project</button>
    </form>
  );
}
```

## TypeScript Support

The package is written in TypeScript and provides comprehensive type definitions:

```tsx
import type {
  Project,
  ProjectTask,
  TimeEntry,
  Milestone,
  ProjectFilters,
  TaskFilters,
  ProjectFormData,
  TaskFormData,
  TimeEntryCreate,
  ProjectAnalytics,
  TimeTrackingAnalytics,
  UseProjectsResult,
  UseTasksResult,
  UseTimeTrackingResult
} from '@dotmac/projects';
```

## API Integration

The package integrates with the DotMac ISP backend through standardized API endpoints:

- **Projects**: `/api/projects/*`
- **Tasks**: `/api/projects/tasks/*`
- **Time Tracking**: `/api/projects/time-entries/*`
- **Analytics**: `/api/projects/analytics/*`

All hooks use the `@dotmac/headless` API client for consistent authentication and error handling.

## Testing

The package includes comprehensive test coverage:

```bash
# Run tests
npm test

# Run tests with coverage
npm run test:coverage

# Run tests in watch mode
npm run test:watch
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make your changes and add tests
4. Run tests: `npm test`
5. Commit your changes: `git commit -am 'Add new feature'`
6. Push to the branch: `git push origin feature/new-feature`
7. Submit a pull request

## License

This package is part of the DotMac ISP Framework and is licensed under the MIT License.

## Dependencies

- React 18+
- TypeScript 5+
- date-fns for date manipulation
- lucide-react for icons
- @dotmac/ui for base components
- @dotmac/headless for API integration

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- iOS Safari 14+
- Android Chrome 90+
