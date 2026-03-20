/** Intelligence report types for NEXUS. */

export type ReportFormat = 'json' | 'html' | 'pdf' | 'stix';

export interface ReportSection {
  name: string;
  label: string;
  description: string;
}

export const REPORT_SECTIONS: ReportSection[] = [
  { name: 'executive_summary', label: 'Executive Summary', description: 'High-level investigation overview' },
  { name: 'entity_analysis', label: 'Entity Analysis', description: 'Entities grouped by type with confidence and risk' },
  { name: 'relationship_graph', label: 'Relationship Graph', description: 'Graph topology and key connections' },
  { name: 'timeline', label: 'Timeline', description: 'Temporal distribution of entities' },
  { name: 'risk_assessment', label: 'Risk Assessment', description: 'Risk matrix and high-risk entities' },
  { name: 'confidence_metrics', label: 'Confidence Metrics', description: 'Admiralty grade breakdown by INT' },
  { name: 'conflict_notes', label: 'Conflict Notes', description: 'Conflicting evidence and low-confidence entities' },
  { name: 'recommendations', label: 'Recommendations', description: 'Actionable intelligence recommendations' },
];

export interface IntelligenceReportData {
  format: string;
  version: string;
  generated_at: string;
  classification: string;
  title: string;
  investigation_id: string;
  sections: {
    executive_summary?: ExecutiveSummaryData;
    entity_analysis?: EntityAnalysisData;
    relationship_graph?: RelationshipGraphData;
    timeline?: TimelineData;
    risk_assessment?: RiskAssessmentData;
    confidence_metrics?: ConfidenceMetricsData;
    conflict_notes?: ConflictNotesData;
    recommendations?: RecommendationsData;
  };
}

export interface ExecutiveSummaryData {
  entity_count: number;
  relationship_count: number;
  entity_type_breakdown: Record<string, number>;
  average_confidence: number;
  high_risk_entity_count: number;
  summary: string;
  query?: string;
  status?: string;
  target_ints?: string[];
}

export interface EntityAnalysisData {
  groups: Record<string, EntityEntry[]>;
  total_types: number;
}

export interface EntityEntry {
  id: string;
  name: string;
  confidence: number;
  risk_score: number;
  source_int: string;
  reliability_grade: string;
}

export interface RelationshipGraphData {
  node_count: number;
  edge_count: number;
  relationship_type_breakdown: Record<string, number>;
  top_connected_nodes: Array<{ id: string; name: string; degree: number }>;
  density: number;
}

export interface TimelineData {
  event_count: number;
  events: Array<{ id: string; name: string; type: string; timestamp: string }>;
  earliest: string | null;
  latest: string | null;
}

export interface RiskAssessmentData {
  risk_distribution: Record<string, number>;
  risk_percentages: Record<string, number>;
  critical_entities: RiskEntity[];
  high_risk_entities: RiskEntity[];
}

export interface RiskEntity {
  id: string;
  name: string;
  type: string;
  risk_score: number;
  confidence: number;
}

export interface ConfidenceMetricsData {
  admiralty_grade_distribution: Record<string, number>;
  confidence_by_int: Record<string, number>;
  overall_average: number;
  entity_count_by_int: Record<string, number>;
}

export interface ConflictNotesData {
  conflicting_entities: Array<{
    name: string;
    entity_count: number;
    confidence_spread: number;
    sources: string[];
    note: string;
  }>;
  low_confidence_entities: Array<{
    id: string;
    name: string;
    confidence: number;
    source_int: string;
  }>;
  conflict_count: number;
  low_confidence_count: number;
}

export interface RecommendationsData {
  recommendations: Array<{
    priority: string;
    category: string;
    recommendation: string;
  }>;
  total_count: number;
}

export interface STIXBundle {
  type: 'bundle';
  id: string;
  spec_version: string;
  objects: STIXObject[];
}

export interface STIXObject {
  type: string;
  id: string;
  spec_version: string;
  created: string;
  modified: string;
  [key: string]: unknown;
}
