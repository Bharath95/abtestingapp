// frontend/components/analytics/FollowUpList.tsx
"use client";

import { useState } from "react";
import type { OptionAnalytics } from "@/lib/types";

interface FollowUpListProps {
  options: OptionAnalytics[];
}

export default function FollowUpList({ options }: FollowUpListProps) {
  const optionsWithFollowups = options.filter((o) => o.followup_texts.length > 0);
  const [expandedOption, setExpandedOption] = useState<number | null>(
    optionsWithFollowups.length > 0 ? optionsWithFollowups[0].option_id : null
  );

  if (optionsWithFollowups.length === 0) {
    return <p className="text-gray-400 text-sm">No follow-up responses.</p>;
  }

  return (
    <div className="space-y-3">
      <h4 className="text-sm font-medium text-gray-700">Follow-up Responses</h4>
      {optionsWithFollowups.map((option) => (
        <div key={option.option_id} className="border border-gray-200 rounded-lg">
          <button
            className="w-full text-left px-4 py-3 flex justify-between items-center text-sm font-medium text-gray-800 hover:bg-gray-50"
            onClick={() =>
              setExpandedOption(expandedOption === option.option_id ? null : option.option_id)
            }
          >
            <span>
              {option.label}
              {option.is_winner && (
                <span className="ml-2 text-xs text-green-600 font-normal">(winner)</span>
              )}
            </span>
            <span className="text-gray-400">{option.followup_texts.length} responses</span>
          </button>
          {expandedOption === option.option_id && (
            <div className="px-4 pb-3 space-y-2">
              {option.followup_texts.map((f, i) => (
                <div key={i} className="bg-gray-50 rounded p-2 text-sm text-gray-700">
                  &ldquo;{f.text}&rdquo;
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
