import { useReportStore } from '../../stores/useReportStore';
import { useGenerateReport } from '../../hooks/useReport';
import { REPORT_SECTIONS } from '@nexus/shared-types';
import type { ReportFormat } from '@nexus/shared-types';

const FORMAT_OPTIONS: { value: ReportFormat; label: string }[] = [
  { value: 'json', label: 'JSON' },
  { value: 'html', label: 'HTML' },
  { value: 'pdf', label: 'PDF' },
  { value: 'stix', label: 'STIX 2.1' },
];

const CLASSIFICATIONS = ['UNCLASSIFIED', 'RESTRICTED', 'CONFIDENTIAL', 'SECRET', 'TOP SECRET'];

export function ReportBuilder() {
  const {
    selectedInvestigationId,
    selectedFormat,
    selectedSections,
    classification,
    isGenerating,
    setInvestigationId,
    setFormat,
    toggleSection,
    setClassification,
  } = useReportStore();

  const generateReport = useGenerateReport();

  const handleGenerate = () => {
    if (!selectedInvestigationId) return;
    generateReport.mutate({
      investigationId: selectedInvestigationId,
      format: selectedFormat,
      sections: selectedSections.join(','),
    });
  };

  return (
    <div className="space-y-5">
      {/* Investigation ID */}
      <div>
        <label className="block text-xs text-nexus-text-secondary mb-1 uppercase tracking-wide">
          Investigation ID
        </label>
        <input
          type="text"
          className="w-full bg-nexus-surface border border-nexus-border rounded px-3 py-2 text-sm text-nexus-text-primary font-mono focus:border-nexus-accent focus:outline-none"
          placeholder="inv-..."
          value={selectedInvestigationId || ''}
          onChange={(e) => setInvestigationId(e.target.value || null)}
        />
      </div>

      {/* Classification */}
      <div>
        <label className="block text-xs text-nexus-text-secondary mb-1 uppercase tracking-wide">
          Classification
        </label>
        <select
          className="w-full bg-nexus-surface border border-nexus-border rounded px-3 py-2 text-sm text-nexus-text-primary focus:border-nexus-accent focus:outline-none"
          value={classification}
          onChange={(e) => setClassification(e.target.value)}
        >
          {CLASSIFICATIONS.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      {/* Format */}
      <div>
        <label className="block text-xs text-nexus-text-secondary mb-1 uppercase tracking-wide">
          Output Format
        </label>
        <div className="grid grid-cols-2 gap-2">
          {FORMAT_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              className={`px-3 py-1.5 text-xs rounded border transition-colors ${
                selectedFormat === opt.value
                  ? 'bg-nexus-accent/20 border-nexus-accent text-nexus-accent'
                  : 'bg-nexus-surface border-nexus-border text-nexus-text-secondary hover:border-nexus-text-secondary'
              }`}
              onClick={() => setFormat(opt.value)}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Sections */}
      <div>
        <label className="block text-xs text-nexus-text-secondary mb-2 uppercase tracking-wide">
          Report Sections
        </label>
        <div className="space-y-1.5">
          {REPORT_SECTIONS.map((section) => (
            <label
              key={section.name}
              className="flex items-start gap-2 cursor-pointer group"
            >
              <input
                type="checkbox"
                className="mt-1 accent-nexus-accent"
                checked={selectedSections.includes(section.name)}
                onChange={() => toggleSection(section.name)}
              />
              <div>
                <span className="text-sm text-nexus-text-primary group-hover:text-nexus-accent transition-colors">
                  {section.label}
                </span>
                <p className="text-xs text-nexus-text-secondary">{section.description}</p>
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* Generate button */}
      <button
        className="w-full py-2.5 rounded bg-nexus-accent text-white text-sm font-medium hover:bg-nexus-accent/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        disabled={!selectedInvestigationId || isGenerating}
        onClick={handleGenerate}
      >
        {isGenerating ? 'Generating...' : 'Generate Report'}
      </button>
    </div>
  );
}
