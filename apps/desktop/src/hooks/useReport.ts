import { useQuery, useMutation } from '@tanstack/react-query';
import { reports } from '../services/api';
import { useReportStore } from '../stores/useReportStore';
import type { IntelligenceReportData } from '@nexus/shared-types';

export function useReportPreview(investigationId: string | null) {
  return useQuery({
    queryKey: ['report', 'preview', investigationId],
    queryFn: () => reports.preview(investigationId!) as Promise<string>,
    enabled: !!investigationId,
    staleTime: 30_000,
  });
}

export function useGenerateReport() {
  const { setGenerating, setReportData, setPreviewHtml, setError } = useReportStore();

  return useMutation({
    mutationFn: async ({
      investigationId,
      format,
      sections,
    }: {
      investigationId: string;
      format: string;
      sections?: string;
    }) => {
      setGenerating(true);
      setError(null);
      return reports.generate(investigationId, format, sections);
    },
    onSuccess: (data, variables) => {
      if (variables.format === 'html') {
        setPreviewHtml(data as unknown as string);
      } else {
        setReportData(data as IntelligenceReportData);
      }
      setGenerating(false);
    },
    onError: (error: Error) => {
      setError(error.message);
      setGenerating(false);
    },
  });
}

export function useDownloadReport() {
  return useMutation({
    mutationFn: async ({
      investigationId,
      format,
    }: {
      investigationId: string;
      format: string;
    }) => {
      const response = await fetch(
        `http://localhost:8000/api/v1/reports/generate/${investigationId}?format=${format}`,
        { method: 'POST' },
      );
      if (!response.ok) throw new Error(`Download failed: ${response.statusText}`);

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report-${investigationId}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },
  });
}
