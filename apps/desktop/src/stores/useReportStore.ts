import { create } from 'zustand';
import type { ReportFormat, IntelligenceReportData } from '@nexus/shared-types';

interface ReportState {
  selectedInvestigationId: string | null;
  selectedFormat: ReportFormat;
  selectedSections: string[];
  classification: string;
  previewHtml: string | null;
  reportData: IntelligenceReportData | null;
  isGenerating: boolean;
  error: string | null;

  setInvestigationId: (id: string | null) => void;
  setFormat: (format: ReportFormat) => void;
  toggleSection: (section: string) => void;
  setClassification: (classification: string) => void;
  setPreviewHtml: (html: string | null) => void;
  setReportData: (data: IntelligenceReportData | null) => void;
  setGenerating: (generating: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

const DEFAULT_SECTIONS = [
  'executive_summary',
  'entity_analysis',
  'relationship_graph',
  'timeline',
  'risk_assessment',
  'confidence_metrics',
  'conflict_notes',
  'recommendations',
];

export const useReportStore = create<ReportState>((set) => ({
  selectedInvestigationId: null,
  selectedFormat: 'json',
  selectedSections: [...DEFAULT_SECTIONS],
  classification: 'UNCLASSIFIED',
  previewHtml: null,
  reportData: null,
  isGenerating: false,
  error: null,

  setInvestigationId: (id) => set({ selectedInvestigationId: id, reportData: null, previewHtml: null }),
  setFormat: (format) => set({ selectedFormat: format }),
  toggleSection: (section) =>
    set((state) => ({
      selectedSections: state.selectedSections.includes(section)
        ? state.selectedSections.filter((s) => s !== section)
        : [...state.selectedSections, section],
    })),
  setClassification: (classification) => set({ classification }),
  setPreviewHtml: (html) => set({ previewHtml: html }),
  setReportData: (data) => set({ reportData: data }),
  setGenerating: (generating) => set({ isGenerating: generating }),
  setError: (error) => set({ error }),
  reset: () =>
    set({
      selectedInvestigationId: null,
      selectedFormat: 'json',
      selectedSections: [...DEFAULT_SECTIONS],
      classification: 'UNCLASSIFIED',
      previewHtml: null,
      reportData: null,
      isGenerating: false,
      error: null,
    }),
}));
