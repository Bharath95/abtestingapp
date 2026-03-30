// frontend/components/analytics/ExportButton.tsx
"use client";

import { getExportUrl } from "@/lib/api";
import Button from "@/components/shared/Button";

interface ExportButtonProps {
  testId: number;
}

export default function ExportButton({ testId }: ExportButtonProps) {
  function handleExport() {
    window.open(getExportUrl(testId), "_blank", "noopener,noreferrer");
  }

  return (
    <Button variant="secondary" onClick={handleExport}>
      Export CSV
    </Button>
  );
}
