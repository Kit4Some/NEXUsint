import { useState, useCallback } from 'react';
import { useMutation } from '@tanstack/react-query';
import { stix } from '@/services/api';
import { StixJsonPreview } from './StixJsonPreview';

export function StixPanel() {
  const [exportInvId, setExportInvId] = useState('');
  const [importText, setImportText] = useState('');
  const [exportedBundle, setExportedBundle] = useState<unknown>(null);
  const [validationResult, setValidationResult] = useState<{ valid: boolean; errors: string[] } | null>(null);

  const exportMutation = useMutation({
    mutationFn: (invId: string) => stix.exportInvestigation(invId),
    onSuccess: (data) => setExportedBundle(data),
  });

  const importMutation = useMutation({
    mutationFn: (bundle: unknown) => stix.importBundle(bundle),
  });

  const validateMutation = useMutation({
    mutationFn: (bundle: unknown) => stix.validate(bundle),
    onSuccess: (data) => setValidationResult(data as { valid: boolean; errors: string[] }),
  });

  const handleExport = () => {
    if (exportInvId.trim()) exportMutation.mutate(exportInvId.trim());
  };

  const handleDownload = () => {
    if (!exportedBundle) return;
    const blob = new Blob([JSON.stringify(exportedBundle, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `nexus_stix_${exportInvId || 'export'}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImport = () => {
    try {
      const parsed = JSON.parse(importText);
      importMutation.mutate(parsed);
    } catch {
      setValidationResult({ valid: false, errors: ['Invalid JSON'] });
    }
  };

  const handleValidate = () => {
    try {
      const parsed = JSON.parse(importText);
      validateMutation.mutate(parsed);
    } catch {
      setValidationResult({ valid: false, errors: ['Invalid JSON'] });
    }
  };

  const handleFileDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (ev) => {
        setImportText(ev.target?.result as string || '');
      };
      reader.readAsText(file);
    }
  }, []);

  return (
    <div className="h-full overflow-y-auto p-4 space-y-6">
      <h2 className="text-lg font-heading font-bold text-nexus-text">STIX 2.1 Interop</h2>

      {/* Export Section */}
      <section className="space-y-3">
        <h3 className="text-xs font-mono uppercase tracking-wider text-nexus-text-secondary">Export</h3>
        <div className="flex gap-2">
          <input
            type="text"
            value={exportInvId}
            onChange={(e) => setExportInvId(e.target.value)}
            placeholder="Investigation ID"
            className="flex-1 px-3 py-2 text-xs font-mono bg-nexus-bg border border-nexus-border rounded outline-none text-nexus-text placeholder:text-nexus-text-secondary focus:border-nexus-cyan/50"
          />
          <button
            onClick={handleExport}
            disabled={!exportInvId.trim() || exportMutation.isPending}
            className="px-4 py-2 text-xs font-mono bg-nexus-cyan/20 text-nexus-cyan rounded border border-nexus-cyan/30 hover:bg-nexus-cyan/30 disabled:opacity-30 transition-colors"
          >
            {exportMutation.isPending ? 'Exporting...' : 'Export'}
          </button>
        </div>

        {exportedBundle && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono text-nexus-text-secondary">Bundle Preview</span>
              <button
                onClick={handleDownload}
                className="text-[10px] font-mono text-nexus-cyan hover:text-nexus-cyan/80"
              >
                Download JSON
              </button>
            </div>
            <StixJsonPreview data={exportedBundle} />
          </div>
        )}
      </section>

      {/* Import Section */}
      <section className="space-y-3">
        <h3 className="text-xs font-mono uppercase tracking-wider text-nexus-text-secondary">Import</h3>

        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleFileDrop}
          className="border-2 border-dashed border-nexus-border rounded-lg p-4 text-center hover:border-nexus-cyan/30 transition-colors"
        >
          <p className="text-xs text-nexus-text-secondary mb-2">Drop a STIX JSON file here or paste below</p>
        </div>

        <textarea
          value={importText}
          onChange={(e) => setImportText(e.target.value)}
          placeholder='{"type": "bundle", "spec_version": "2.1", "objects": [...]}'
          className="w-full h-32 px-3 py-2 text-xs font-mono bg-nexus-bg border border-nexus-border rounded outline-none text-nexus-text placeholder:text-nexus-text-secondary resize-none focus:border-nexus-cyan/50"
        />

        <div className="flex gap-2">
          <button
            onClick={handleValidate}
            disabled={!importText.trim() || validateMutation.isPending}
            className="px-4 py-2 text-xs font-mono bg-nexus-amber/20 text-nexus-amber rounded border border-nexus-amber/30 hover:bg-nexus-amber/30 disabled:opacity-30 transition-colors"
          >
            Validate
          </button>
          <button
            onClick={handleImport}
            disabled={!importText.trim() || importMutation.isPending}
            className="px-4 py-2 text-xs font-mono bg-nexus-green/20 text-nexus-green rounded border border-nexus-green/30 hover:bg-nexus-green/30 disabled:opacity-30 transition-colors"
          >
            {importMutation.isPending ? 'Importing...' : 'Import'}
          </button>
        </div>

        {validationResult && (
          <div className={`p-3 rounded border text-xs font-mono ${validationResult.valid ? 'bg-nexus-green/10 border-nexus-green/30 text-nexus-green' : 'bg-nexus-red/10 border-nexus-red/30 text-nexus-red'}`}>
            <p className="font-bold mb-1">{validationResult.valid ? 'Valid STIX Bundle' : 'Validation Failed'}</p>
            {validationResult.errors.map((err, i) => (
              <p key={i} className="ml-2">{err}</p>
            ))}
          </div>
        )}

        {importMutation.isSuccess && (
          <div className="p-3 rounded border bg-nexus-green/10 border-nexus-green/30 text-xs font-mono text-nexus-green">
            Bundle imported successfully
          </div>
        )}
      </section>
    </div>
  );
}
