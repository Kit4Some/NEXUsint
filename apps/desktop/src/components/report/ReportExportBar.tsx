import { useReportStore } from '../../stores/useReportStore';
import { useDownloadReport } from '../../hooks/useReport';

const EXPORT_FORMATS = [
  { format: 'pdf', label: 'PDF', icon: '↓' },
  { format: 'html', label: 'HTML', icon: '↓' },
  { format: 'json', label: 'JSON', icon: '↓' },
  { format: 'stix', label: 'STIX', icon: '↓' },
];

export function ReportExportBar() {
  const { selectedInvestigationId, isGenerating } = useReportStore();
  const downloadReport = useDownloadReport();

  const handleExport = (format: string) => {
    if (!selectedInvestigationId) return;
    downloadReport.mutate({ investigationId: selectedInvestigationId, format });
  };

  return (
    <div className="flex items-center gap-2 px-4 py-2 border-b border-nexus-border bg-nexus-surface/50">
      <span className="text-xs text-nexus-text-secondary mr-2">Export:</span>
      {EXPORT_FORMATS.map(({ format, label, icon }) => (
        <button
          key={format}
          className="px-3 py-1 text-xs rounded border border-nexus-border text-nexus-text-secondary hover:text-nexus-accent hover:border-nexus-accent transition-colors disabled:opacity-40"
          disabled={!selectedInvestigationId || isGenerating}
          onClick={() => handleExport(format)}
          title={`Download as ${label}`}
        >
          {icon} {label}
        </button>
      ))}
      {downloadReport.isPending && (
        <span className="text-xs text-nexus-accent ml-2">Downloading...</span>
      )}
    </div>
  );
}
