// frontend/components/respondent/FollowUpInput.tsx
"use client";

interface FollowUpInputProps {
  prompt: string;
  required: boolean;
  value: string;
  onChange: (value: string) => void;
}

export default function FollowUpInput({ prompt, required, value, onChange }: FollowUpInputProps) {
  const maxLength = 500;
  return (
    <div className="mt-6">
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {prompt}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={3}
        maxLength={maxLength}
        placeholder="Share your reasoning..."
        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none resize-none"
      />
      <div className="text-xs text-gray-400 text-right mt-1">
        {value.length}/{maxLength}
      </div>
    </div>
  );
}
