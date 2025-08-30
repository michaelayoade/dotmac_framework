// Project Management Types for DotMac Framework

export enum ProjectType {
  // ISP/Telecom specific
  NEW_INSTALLATION = 'new_installation',
  SERVICE_UPGRADE = 'service_upgrade',
  NETWORK_EXPANSION = 'network_expansion',
  EQUIPMENT_REPLACEMENT = 'equipment_replacement',

  // Infrastructure
  DEPLOYMENT = 'deployment',
  MIGRATION = 'migration',
  MAINTENANCE = 'maintenance',
  REPAIR = 'repair',

  // Software/IT
  SOFTWARE_DEVELOPMENT = 'software_development',
  SYSTEM_INTEGRATION = 'system_integration',
  DATA_MIGRATION = 'data_migration',

  // General
  CONSULTING = 'consulting',
  TRAINING = 'training',
  AUDIT = 'audit',
  CUSTOM = 'custom'
}

export enum ProjectStatus {
  PLANNING = 'planning',
  APPROVED = 'approved',
  SCHEDULED = 'scheduled',
  IN_PROGRESS = 'in_progress',
  ON_HOLD = 'on_hold',
  TESTING = 'testing',
  COMPLETED = 'completed',
  CANCELLED = 'cancelled',
  FAILED = 'failed'
}

export enum PhaseStatus {
  PENDING = 'pending',
  SCHEDULED = 'scheduled',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  SKIPPED = 'skipped',
  FAILED = 'failed'
}

export enum MilestoneType {
  PLANNING_COMPLETE = 'planning_complete',
  APPROVAL_RECEIVED = 'approval_received',
  RESOURCES_ALLOCATED = 'resources_allocated',
  PROJECT_STARTED = 'project_started',
  PHASE_COMPLETE = 'phase_complete',
  TESTING_COMPLETE = 'testing_complete',
  DELIVERY_READY = 'delivery_ready',
  CLIENT_ACCEPTANCE = 'client_acceptance',
  PROJECT_COMPLETE = 'project_complete',
  CUSTOM = 'custom'
}

export enum ProjectPriority {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  URGENT = 'urgent',
  CRITICAL = 'critical'
}

export enum TaskStatus {
  TODO = 'todo',
  IN_PROGRESS = 'in_progress',
  REVIEW = 'review',
  DONE = 'done',
  BLOCKED = 'blocked',
  CANCELLED = 'cancelled'
}

export enum TaskPriority {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  URGENT = 'urgent'
}

// Core Project Interface
export interface Project {
  id: string;
  tenant_id: string;
  project_number: string;
  project_name: string;
  description?: string;
  project_type: ProjectType;
  project_status: ProjectStatus;
  priority: ProjectPriority;

  // Client information
  customer_id?: string;
  client_name?: string;
  client_email?: string;
  client_phone?: string;

  // Assignment
  project_manager?: string;
  assigned_team?: string[];

  // Timeline
  requested_date?: string;
  planned_start_date?: string;
  planned_end_date?: string;
  actual_start_date?: string;
  actual_end_date?: string;

  // Financial
  estimated_cost?: number;
  approved_budget?: number;
  actual_cost?: number;

  // Progress
  completion_percentage: number;
  total_phases: number;
  phases_completed: number;

  // Project details
  requirements?: string[];
  deliverables?: string[];
  success_criteria?: string[];
  project_location?: string;
  special_requirements?: string;

  // Metadata
  platform_data?: Record<string, any>;
  created_at: string;
  updated_at: string;
  created_by?: string;
  updated_by?: string;

  // Related data
  phases?: ProjectPhase[];
  milestones?: ProjectMilestone[];
  tasks?: ProjectTask[];
  updates?: ProjectUpdate[];
  resources?: ProjectResource[];
  documents?: ProjectDocument[];
  time_entries?: TimeEntry[];
}

export interface ProjectPhase {
  id: string;
  tenant_id: string;
  project_id: string;
  phase_name: string;
  phase_description?: string;
  phase_order: number;
  phase_status: PhaseStatus;
  phase_type?: string;

  // Flags
  is_critical_path: boolean;
  is_client_visible: boolean;

  // Timeline
  planned_start_date?: string;
  planned_end_date?: string;
  actual_start_date?: string;
  actual_end_date?: string;
  estimated_duration_hours?: number;
  actual_duration_hours?: number;

  // Assignment and details
  assigned_to?: string;
  work_instructions?: string;
  estimated_cost?: number;
  actual_cost?: number;
  completion_percentage: number;

  // Metadata
  created_at: string;
  updated_at: string;

  // Related data
  tasks?: ProjectTask[];
  dependencies?: PhaseDependency[];
}

export interface ProjectMilestone {
  id: string;
  tenant_id: string;
  project_id: string;
  milestone_name: string;
  milestone_description?: string;
  milestone_type: MilestoneType;

  // Timeline
  planned_date: string;
  actual_date?: string;

  // Flags
  is_critical: boolean;
  is_client_visible: boolean;
  is_completed: boolean;

  // Details
  success_criteria?: string;
  completion_notes?: string;

  // Metadata
  created_at: string;
  updated_at: string;
}

export interface ProjectTask {
  id: string;
  tenant_id: string;
  project_id: string;
  phase_id?: string;
  task_title: string;
  task_description?: string;
  task_status: TaskStatus;
  task_priority: TaskPriority;

  // Assignment
  assigned_to?: string;
  assigned_by?: string;

  // Timeline
  due_date?: string;
  start_date?: string;
  completed_date?: string;
  estimated_hours?: number;
  actual_hours?: number;

  // Details
  tags?: string[];
  checklist_items?: ChecklistItem[];
  attachments?: string[];

  // Metadata
  created_at: string;
  updated_at: string;
  created_by?: string;

  // Related data
  dependencies?: TaskDependency[];
  comments?: TaskComment[];
  time_entries?: TimeEntry[];
}

export interface ProjectUpdate {
  id: string;
  tenant_id: string;
  project_id: string;
  update_title: string;
  update_content: string;
  update_type: 'status' | 'progress' | 'issue' | 'milestone' | 'general';
  priority: ProjectPriority;

  // Visibility
  is_client_visible: boolean;

  // Author
  author_name: string;
  author_role?: string;

  // Progress
  progress_percentage?: number;
  next_steps?: string;
  estimated_completion?: string;

  // Issues and risks
  issues?: string[];
  risks?: string[];

  // Metadata
  created_at: string;
  updated_at: string;

  // Related data
  attachments?: string[];
  mentions?: string[];
}

export interface ProjectResource {
  id: string;
  tenant_id: string;
  project_id: string;
  resource_type: 'human' | 'equipment' | 'material' | 'service';
  resource_name: string;
  resource_description?: string;

  // Allocation
  allocated_quantity: number;
  used_quantity: number;
  unit_type: string;
  unit_cost?: number;
  total_cost?: number;

  // Timeline
  allocation_start: string;
  allocation_end?: string;

  // Details
  supplier?: string;
  location?: string;
  notes?: string;

  // Metadata
  created_at: string;
  updated_at: string;
}

export interface ProjectDocument {
  id: string;
  tenant_id: string;
  project_id: string;
  document_name: string;
  document_type: string;
  document_category: 'requirement' | 'design' | 'contract' | 'report' | 'other';

  // File info
  file_path: string;
  file_size: number;
  mime_type: string;
  version: string;

  // Access control
  is_client_visible: boolean;
  access_level: 'public' | 'team' | 'manager' | 'restricted';

  // Metadata
  uploaded_by: string;
  uploaded_at: string;
  last_modified: string;

  // Details
  description?: string;
  tags?: string[];
  approval_status?: 'pending' | 'approved' | 'rejected';
}

export interface TimeEntry {
  id: string;
  tenant_id: string;
  project_id: string;
  task_id?: string;
  phase_id?: string;

  // Time tracking
  user_id: string;
  user_name: string;
  start_time: string;
  end_time?: string;
  duration_minutes: number;

  // Details
  description: string;
  activity_type: 'development' | 'meeting' | 'documentation' | 'testing' | 'review' | 'other';
  billable: boolean;
  hourly_rate?: number;

  // Metadata
  created_at: string;
  updated_at: string;
  approved_by?: string;
  approved_at?: string;
}

// Supporting interfaces
export interface ChecklistItem {
  id: string;
  text: string;
  completed: boolean;
  completed_at?: string;
  completed_by?: string;
}

export interface TaskDependency {
  id: string;
  dependent_task_id: string;
  dependency_task_id: string;
  dependency_type: 'finish_to_start' | 'start_to_start' | 'finish_to_finish' | 'start_to_finish';
}

export interface PhaseDependency {
  id: string;
  dependent_phase_id: string;
  dependency_phase_id: string;
  dependency_type: 'finish_to_start' | 'start_to_start';
}

export interface TaskComment {
  id: string;
  task_id: string;
  user_id: string;
  user_name: string;
  comment: string;
  created_at: string;
  updated_at: string;
  parent_comment_id?: string;
}

// Create/Update DTOs
export interface ProjectCreate {
  project_name: string;
  description?: string;
  project_type: ProjectType;
  priority: ProjectPriority;
  customer_id?: string;
  client_name?: string;
  client_email?: string;
  client_phone?: string;
  project_manager?: string;
  assigned_team?: string[];
  requested_date?: string;
  planned_start_date?: string;
  planned_end_date?: string;
  estimated_cost?: number;
  approved_budget?: number;
  requirements?: string[];
  deliverables?: string[];
  success_criteria?: string[];
  project_location?: string;
  special_requirements?: string;
  platform_data?: Record<string, any>;
}

export interface ProjectUpdate {
  project_name?: string;
  description?: string;
  project_status?: ProjectStatus;
  priority?: ProjectPriority;
  client_name?: string;
  client_email?: string;
  client_phone?: string;
  project_manager?: string;
  assigned_team?: string[];
  planned_start_date?: string;
  planned_end_date?: string;
  estimated_cost?: number;
  approved_budget?: number;
  requirements?: string[];
  deliverables?: string[];
  success_criteria?: string[];
  project_location?: string;
  special_requirements?: string;
  completion_percentage?: number;
  platform_data?: Record<string, any>;
}

export interface TaskCreate {
  task_title: string;
  task_description?: string;
  task_priority: TaskPriority;
  phase_id?: string;
  assigned_to?: string;
  due_date?: string;
  start_date?: string;
  estimated_hours?: number;
  tags?: string[];
  checklist_items?: Omit<ChecklistItem, 'id'>[];
}

export interface TaskUpdate {
  task_title?: string;
  task_description?: string;
  task_status?: TaskStatus;
  task_priority?: TaskPriority;
  assigned_to?: string;
  due_date?: string;
  start_date?: string;
  completed_date?: string;
  estimated_hours?: number;
  actual_hours?: number;
  tags?: string[];
  checklist_items?: ChecklistItem[];
}

export interface PhaseCreate {
  phase_name: string;
  phase_description?: string;
  phase_order: number;
  phase_type?: string;
  is_critical_path: boolean;
  is_client_visible: boolean;
  planned_start_date?: string;
  planned_end_date?: string;
  estimated_duration_hours?: number;
  assigned_to?: string;
  work_instructions?: string;
  estimated_cost?: number;
}

export interface PhaseUpdate {
  phase_name?: string;
  phase_description?: string;
  phase_status?: PhaseStatus;
  phase_order?: number;
  is_critical_path?: boolean;
  is_client_visible?: boolean;
  planned_start_date?: string;
  planned_end_date?: string;
  actual_start_date?: string;
  actual_end_date?: string;
  estimated_duration_hours?: number;
  actual_duration_hours?: number;
  assigned_to?: string;
  work_instructions?: string;
  estimated_cost?: number;
  actual_cost?: number;
  completion_percentage?: number;
}

export interface MilestoneCreate {
  milestone_name: string;
  milestone_description?: string;
  milestone_type: MilestoneType;
  planned_date: string;
  is_critical: boolean;
  is_client_visible: boolean;
  success_criteria?: string;
}

export interface ProjectUpdateCreate {
  update_title: string;
  update_content: string;
  update_type: 'status' | 'progress' | 'issue' | 'milestone' | 'general';
  priority: ProjectPriority;
  is_client_visible: boolean;
  author_name: string;
  author_role?: string;
  progress_percentage?: number;
  next_steps?: string;
  estimated_completion?: string;
  issues?: string[];
  risks?: string[];
  attachments?: string[];
  mentions?: string[];
}

export interface TimeEntryCreate {
  task_id?: string;
  phase_id?: string;
  description: string;
  start_time: string;
  end_time?: string;
  duration_minutes?: number;
  activity_type: 'development' | 'meeting' | 'documentation' | 'testing' | 'review' | 'other';
  billable: boolean;
  hourly_rate?: number;
}

// Search and Filter types
export interface ProjectFilters {
  project_status?: ProjectStatus[];
  project_type?: ProjectType[];
  priority?: ProjectPriority[];
  project_manager?: string;
  customer_id?: string;
  assigned_team?: string[];
  search?: string;
  overdue_only?: boolean;
  created_after?: string;
  created_before?: string;
  due_after?: string;
  due_before?: string;
  completion_percentage_min?: number;
  completion_percentage_max?: number;
}

export interface TaskFilters {
  task_status?: TaskStatus[];
  task_priority?: TaskPriority[];
  assigned_to?: string;
  phase_id?: string;
  due_after?: string;
  due_before?: string;
  tags?: string[];
  search?: string;
  overdue_only?: boolean;
}

// Analytics types
export interface ProjectAnalytics {
  total_projects: number;
  status_breakdown: Record<ProjectStatus, number>;
  type_breakdown: Record<ProjectType, number>;
  priority_breakdown: Record<ProjectPriority, number>;
  avg_completion_days: number;
  overdue_count: number;
  on_time_completion_rate: number;
  budget_variance: number;
  resource_utilization: number;
  date_range?: {
    start: string;
    end: string;
  };
}

export interface TimeTrackingAnalytics {
  total_hours: number;
  billable_hours: number;
  hours_by_activity: Record<string, number>;
  hours_by_user: Record<string, number>;
  hours_by_project: Record<string, number>;
  average_daily_hours: number;
  utilization_rate: number;
}

// Hook return types
export interface UseProjectsResult {
  projects: Project[];
  loading: boolean;
  error: string | null;

  // CRUD operations
  createProject: (data: ProjectCreate) => Promise<Project>;
  updateProject: (projectId: string, data: ProjectUpdate) => Promise<Project>;
  deleteProject: (projectId: string) => Promise<void>;
  getProject: (projectId: string) => Promise<Project | null>;

  // Listing and filtering
  listProjects: (filters?: ProjectFilters, page?: number, pageSize?: number) => Promise<{ projects: Project[]; total: number }>;
  searchProjects: (query: string) => Promise<Project[]>;

  // Project management
  changeProjectStatus: (projectId: string, status: ProjectStatus) => Promise<void>;
  assignProjectManager: (projectId: string, managerId: string) => Promise<void>;

  // Analytics
  getProjectAnalytics: (filters?: ProjectFilters) => Promise<ProjectAnalytics>;

  // Utilities
  refreshProjects: () => Promise<void>;
  getProjectTypes: () => ProjectType[];
  getProjectStatuses: () => ProjectStatus[];
}

export interface UseTasksResult {
  tasks: ProjectTask[];
  loading: boolean;
  error: string | null;

  // Task management
  createTask: (projectId: string, data: TaskCreate) => Promise<ProjectTask>;
  updateTask: (taskId: string, data: TaskUpdate) => Promise<ProjectTask>;
  deleteTask: (taskId: string) => Promise<void>;

  // Task operations
  assignTask: (taskId: string, userId: string) => Promise<void>;
  changeTaskStatus: (taskId: string, status: TaskStatus) => Promise<void>;
  addTaskComment: (taskId: string, comment: string) => Promise<void>;

  // Filtering and search
  getTasksByProject: (projectId: string, filters?: TaskFilters) => Promise<ProjectTask[]>;
  getTasksByUser: (userId: string, filters?: TaskFilters) => Promise<ProjectTask[]>;

  // Utilities
  refreshTasks: () => Promise<void>;
}

export interface UseTimeTrackingResult {
  timeEntries: TimeEntry[];
  loading: boolean;
  error: string | null;
  currentEntry: TimeEntry | null;

  // Time tracking
  startTimer: (projectId: string, taskId?: string, description?: string) => Promise<TimeEntry>;
  stopTimer: () => Promise<TimeEntry>;
  createTimeEntry: (data: TimeEntryCreate) => Promise<TimeEntry>;
  updateTimeEntry: (entryId: string, data: Partial<TimeEntryCreate>) => Promise<TimeEntry>;
  deleteTimeEntry: (entryId: string) => Promise<void>;

  // Analytics
  getTimeTrackingAnalytics: (filters?: { projectId?: string; userId?: string; dateRange?: [string, string] }) => Promise<TimeTrackingAnalytics>;

  // Utilities
  isTimerRunning: boolean;
  currentDuration: number;
  refreshTimeEntries: () => Promise<void>;
}

// Component props types
export interface ProjectDashboardProps {
  showMetrics?: boolean;
  showRecentProjects?: boolean;
  showTaskSummary?: boolean;
  refreshInterval?: number;
}

export interface ProjectListProps {
  filters?: ProjectFilters;
  showFilters?: boolean;
  showActions?: boolean;
  allowBulkOperations?: boolean;
  onProjectSelect?: (project: Project) => void;
}

export interface ProjectKanbanProps {
  projectId: string;
  showPhases?: boolean;
  allowDragDrop?: boolean;
  showFilters?: boolean;
}

export interface ProjectGanttProps {
  projectId: string;
  showCriticalPath?: boolean;
  showMilestones?: boolean;
  allowEditing?: boolean;
}

export interface TaskBoardProps {
  projectId?: string;
  userId?: string;
  showFilters?: boolean;
  allowDragDrop?: boolean;
  groupBy?: 'status' | 'priority' | 'assignee' | 'phase';
}

export interface TimeTrackerProps {
  projectId?: string;
  taskId?: string;
  showHistory?: boolean;
  allowBulkEntry?: boolean;
}

export interface ProjectCalendarProps {
  projectIds?: string[];
  showMilestones?: boolean;
  showDeadlines?: boolean;
  showTimeEntries?: boolean;
  viewMode?: 'month' | 'week' | 'agenda';
}

// API types
export interface ProjectsAPI {
  // Projects
  getProjects: (filters?: ProjectFilters, page?: number, pageSize?: number) => Promise<{ projects: Project[]; total: number }>;
  getProject: (projectId: string) => Promise<Project>;
  createProject: (data: ProjectCreate) => Promise<Project>;
  updateProject: (projectId: string, data: ProjectUpdate) => Promise<Project>;
  deleteProject: (projectId: string) => Promise<void>;

  // Tasks
  getTasks: (projectId: string, filters?: TaskFilters) => Promise<ProjectTask[]>;
  createTask: (projectId: string, data: TaskCreate) => Promise<ProjectTask>;
  updateTask: (taskId: string, data: TaskUpdate) => Promise<ProjectTask>;
  deleteTask: (taskId: string) => Promise<void>;

  // Time tracking
  getTimeEntries: (filters?: { projectId?: string; taskId?: string; userId?: string }) => Promise<TimeEntry[]>;
  createTimeEntry: (data: TimeEntryCreate) => Promise<TimeEntry>;
  updateTimeEntry: (entryId: string, data: Partial<TimeEntryCreate>) => Promise<TimeEntry>;
  deleteTimeEntry: (entryId: string) => Promise<void>;

  // Analytics
  getProjectAnalytics: (filters?: ProjectFilters) => Promise<ProjectAnalytics>;
  getTimeTrackingAnalytics: (filters?: any) => Promise<TimeTrackingAnalytics>;
}
