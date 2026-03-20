import { useRef, useEffect } from 'react';

interface ReportPreviewProps {
  html: string;
}

export function ReportPreview({ html }: ReportPreviewProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    if (iframeRef.current) {
      const doc = iframeRef.current.contentDocument;
      if (doc) {
        doc.open();
        doc.write(html);
        doc.close();
      }
    }
  }, [html]);

  return (
    <iframe
      ref={iframeRef}
      className="w-full h-full border border-nexus-border rounded bg-white"
      sandbox="allow-same-origin"
      title="Report Preview"
    />
  );
}
