// frontend/components/respondent/OptionCard.tsx
"use client";

import { API_BASE_URL } from "@/lib/constants";

interface OptionCardProps {
  label: string;
  sourceType: "upload" | "url";
  imageUrl: string | null;
  sourceUrl: string | null;
  selected: boolean;
  locked: boolean;
  onClick: () => void;
}

export default function OptionCard({
  label,
  sourceType,
  imageUrl,
  sourceUrl,
  selected,
  locked,
  onClick,
}: OptionCardProps) {
  const borderClass = selected
    ? "border-blue-500 ring-2 ring-blue-200"
    : "border-gray-200 hover:border-gray-400";
  const cursorClass = locked ? "cursor-default" : "cursor-pointer";

  return (
    <div
      className={`relative border-2 rounded-lg overflow-hidden transition-all ${borderClass} ${cursorClass}`}
      onClick={locked ? undefined : onClick}
    >
      {sourceType === "upload" && imageUrl && (
        <div className="flex justify-center bg-gray-50 p-2">
          <img
            src={`${API_BASE_URL}${imageUrl}`}
            alt={label}
            className="object-contain max-h-64 sm:max-h-96"
          />
        </div>
      )}
      {sourceType === "url" && sourceUrl && (
        <div className="bg-gray-50 p-2">
          <iframe
            src={sourceUrl}
            title={label}
            className="w-full h-48 sm:h-64 rounded border"
            sandbox="allow-scripts allow-same-origin"
            style={{ pointerEvents: "none" }}
          />
          <a
            href={sourceUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="block text-center text-xs text-blue-600 underline mt-1"
            onClick={(e) => e.stopPropagation()}
          >
            Open in new tab
          </a>
        </div>
      )}
      <div className="p-3 text-center">
        <p className="text-sm font-medium text-gray-900">{label}</p>
        {selected && (
          <span className="inline-block mt-1 text-xs text-blue-600 font-medium">
            Locked in
          </span>
        )}
      </div>
    </div>
  );
}
