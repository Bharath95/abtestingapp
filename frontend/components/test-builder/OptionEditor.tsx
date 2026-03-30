// frontend/components/test-builder/OptionEditor.tsx
"use client";

import { useState, useId } from "react";
import ImageUploader from "./ImageUploader";
import Button from "@/components/shared/Button";

interface OptionEditorProps {
  optionId?: number;
  initialLabel: string;
  initialSourceType?: "upload" | "url";
  initialImageUrl?: string | null;
  initialSourceUrl?: string | null;
  onSave: (label: string, sourceType: "upload" | "url", imageFile: File | null, sourceUrl: string | null) => Promise<void>;
  onDelete?: () => Promise<void>;
  isNew?: boolean;
}

export default function OptionEditor({
  initialLabel,
  initialSourceType = "upload",
  initialImageUrl,
  initialSourceUrl,
  onSave,
  onDelete,
  isNew = false,
}: OptionEditorProps) {
  const uniqueId = useId();
  const [label, setLabel] = useState(initialLabel);
  const [sourceType, setSourceType] = useState<"upload" | "url">(initialSourceType);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [sourceUrl, setSourceUrl] = useState(initialSourceUrl || "");
  const [saving, setSaving] = useState(false);

  const canSave =
    label.trim() &&
    (sourceType === "upload" ? (imageFile || initialImageUrl) : sourceUrl.trim());

  async function handleSave() {
    if (!canSave) return;
    setSaving(true);
    try {
      await onSave(label.trim(), sourceType, imageFile, sourceType === "url" ? sourceUrl.trim() : null);
      if (isNew) {
        setLabel("");
        setImageFile(null);
        setSourceUrl("");
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="border border-gray-200 rounded-lg p-4 space-y-3">
      <div className="flex gap-2">
        <input
          type="text"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="Option label (e.g., Option A)"
          className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
          maxLength={200}
        />
        {onDelete && (
          <Button variant="danger" size="sm" onClick={onDelete}>
            Remove
          </Button>
        )}
      </div>

      {/* Source type toggle -- uses useId() for unique radio group name */}
      <div className="flex gap-4">
        <label className="flex items-center gap-2 text-sm text-gray-700">
          <input
            type="radio"
            name={`source-type-${uniqueId}`}
            checked={sourceType === "upload"}
            onChange={() => setSourceType("upload")}
            className="text-blue-600"
          />
          Image Upload
        </label>
        <label className="flex items-center gap-2 text-sm text-gray-700">
          <input
            type="radio"
            name={`source-type-${uniqueId}`}
            checked={sourceType === "url"}
            onChange={() => setSourceType("url")}
            className="text-blue-600"
          />
          URL
        </label>
      </div>

      {sourceType === "upload" ? (
        <ImageUploader currentImageUrl={initialImageUrl} onFileSelect={setImageFile} />
      ) : (
        <input
          type="url"
          value={sourceUrl}
          onChange={(e) => setSourceUrl(e.target.value)}
          placeholder="https://example.com/your-design"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
        />
      )}

      <Button size="sm" onClick={handleSave} disabled={saving || !canSave}>
        {saving ? "Saving..." : isNew ? "Add Option" : "Update"}
      </Button>
    </div>
  );
}
