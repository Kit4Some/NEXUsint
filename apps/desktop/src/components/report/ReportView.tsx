import { useReportStore } from '../../stores/useReportStore';
import { ReportBuilder } from './ReportBuilder';
import { ReportPreview } from './ReportPreview';
import { ReportExportBar } from './ReportExportBar';

export function ReportView() {
  const { selectedInvestigationId, reportData, previewHtml, isGenerating, error } = useReportStore();

  return (
    <div className="flex flex-col h-full bg-nexus-bg">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-nexus-border">
        <h2 className="text-lg font-heading text-nexus-text-primary">Intelligence Report</h2>
        {selectedInvestigationId && (
          <span className="text-xs text-nexus-text-secondary font-mono">
            INV: {selectedInvestigationId}
          </span>
        )}
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Left panel: Builder */}
        <div className="w-80 border-r border-nexus-border overflow-y-auto p-4">
          <ReportBuilder />
        </div>

        {/* Right panel: Preview / Data */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <ReportExportBar />

          {error && (
            <div className="mx-4 mt-2 px-3 py-2 bg-red-900/30 border border-red-700 rounded text-sm text-red-300">
              {error}
            </div>
          )}

          <div className="flex-1 overflow-auto p-4">
            {isGenerating ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <div className="w-8 h-8 border-2 border-nexus-accent border-t-transparent rounded-full animate-spin mx-auto" />
                  <p className="text-sm text-nexus-text-secondary mt-3">Generating report...</p>
                </div>
              </div>
            ) : previewHtml ? (
              <ReportPreview html={previewHtml} />
            ) : reportData ? (
              <pre className="text-xs text-nexus-text-secondary font-mono whitespace-pre-wrap">
                {JSON.stringify(reportData, null, 2)}
              </pre>
            ) : (
              <div className="flex items-center justify-center h-full text-nexus-text-secondary">
                <div className="text-center">
                  <p className="text-lg font-heading">No Report Generated</p>
                  <p className="text-sm mt-1">Select an investigation and configure sections to generate a report.</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
