export enum InvestigationStatus {
  Created = 'created',
  Collecting = 'collecting',
  Extracting = 'extracting',
  Analyzing = 'analyzing',
  Verifying = 'verifying',
  Completed = 'completed',
  Failed = 'failed',
  Cancelled = 'cancelled',
}

export enum AgentName {
  Collector = 'collector',
  Extractor = 'extractor',
  Analyst = 'analyst',
  Verifier = 'verifier',
}

export interface AgentState {
  name: AgentName;
  status: 'waiting' | 'running' | 'completed' | 'failed';
  itemsProcessed: number;
  startedAt: string | null;
  completedAt: string | null;
  error: string | null;
}

export interface Investigation {
  id: string;
  query: string;
  targetInts: string[];
  status: InvestigationStatus;
  priority: 'low' | 'medium' | 'high' | 'critical';
  agentStates: AgentState[];
  entityCount: number;
  relationshipCount: number;
  progress: number;
  report: IntelligenceReport | null;
  createdAt: string;
  updatedAt: string;
}

export interface InvestigationCreate {
  query: string;
  targetInts: string[];
  seedEntities?: string[];
  timeRange?: { start: string; end: string };
  priority?: 'low' | 'medium' | 'high' | 'critical';
}

export interface IntelligenceReport {
  id: string;
  investigationId: string;
  title: string;
  summary: string;
  body: string;
  entities: string[];
  relationships: string[];
  confidenceOverall: number;
  verificationStatus: 'passed' | 'failed' | 'needs_review';
  verificationNotes: string[];
  generatedAt: string;
}

export interface Alert {
  id: string;
  type: 'threat' | 'entity_discovered' | 'geofence' | 'anomaly' | 'correlation';
  severity: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  description: string;
  entityId: string | null;
  sourceInt: string;
  timestamp: string;
  read: boolean;
}

export interface ProgressUpdate {
  investigationId: string;
  agentName: AgentName;
  status: string;
  progress: number;
  message: string;
  timestamp: string;
}

export interface LogEntry {
  timestamp: string;
  level: 'info' | 'warn' | 'error' | 'debug';
  agent: AgentName | 'system';
  source: string;
  message: string;
}
