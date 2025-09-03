// Helpdesk type definitions for Admin Portal

export type TicketPriority = 'low' | 'medium' | 'high' | 'urgent';
export type AgentStatus = 'offline' | 'online' | 'away' | 'busy';
export type AutomationStatus = 'active' | 'inactive';

export interface Agent {
  id: string;
  name: string;
  email: string;
  role: string;
  status: AgentStatus;
  currentLoad: number;
  maxLoad: number;
  skills: string[];
  metrics: {
    avgFirstResponse: number;
    avgResolutionTime: number;
    customerSatisfaction: number;
    ticketsResolved: number;
    ticketsAssigned: number;
  };
}

export interface Automation {
  id: string;
  name: string;
  description: string;
  trigger: string;
  condition: string;
  action: string;
  status: AutomationStatus;
  executions: number;
  successRate: number;
}

// Update the existing Ticket interface with proper priority type
export interface TicketUpdate {
  priority: TicketPriority;
}
