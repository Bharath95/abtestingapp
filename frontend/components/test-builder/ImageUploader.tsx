// frontend/components/test-builder/ImageUploader.tsx
"use client";

import { useRef, useState } from "react";
import { API_BASE_URL } from "@/lib/constants";

interface ImageUploaderProps {
  currentImageUrl?: string | null;
  onFileSelect: (file: File) => void;
}

const MAX_SIZE = 10 * 1024 * 1024; // 10MB
const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp", "image/gif"];

export default function ImageUploader({ currentImageUrl, onFileSelect }: ImageUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function handleFile(file: File) {
    setError(null);
    if (!ALLOWED_TYPES.includes(file.type)) {
      setError("Invalid file type. Use JPEG, PNG, WebP, or GIF.");
      return;
    }
    if (file.size > MAX_SIZE) {
      setError("File too large. Maximum size is 10MB.");
      return;
    }
    setPreview(URL.createObjectURL(file));
    onFileSelect(file);
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  }

  const displayUrl = preview || (currentImageUrl ? `${API_BASE_URL}${currentImageUrl}` : null);

  return (
    <div>
      <div
        className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center cursor-pointer hover:border-blue-400 transition-colors"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
      >
        {displayUrl ? (
          <img src={displayUrl} alt="Preview" className="max-h-40 mx-auto object-contain" />
        ) : (
          <div className="text-gray-400 py-4">
            <p className="text-sm">Click or drag to upload an image</p>
            <p className="text-xs mt-1">JPEG, PNG, WebP, GIF (max 10MB)</p>
          </div>
        )}
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/gif"
        className="hidden"
        onChange={handleChange}
      />
      {error && <p className="text-red-500 text-xs mt-1">{error}</p>}
    </div>
  );
}
