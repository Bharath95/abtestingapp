// frontend/components/respondent/QuestionView.tsx
"use client";

import { useMemo } from "react";
import type { Question } from "@/lib/types";
import OptionCard from "./OptionCard";

interface QuestionViewProps {
  question: Question;
  selectedOptionId: number | null;
  locked: boolean;
  onSelect: (optionId: number) => void;
}

function shuffleArray<T>(arr: T[]): T[] {
  const shuffled = [...arr];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}

export default function QuestionView({
  question,
  selectedOptionId,
  locked,
  onSelect,
}: QuestionViewProps) {
  const displayOptions = useMemo(() => {
    if (question.randomize_options) {
      return shuffleArray(question.options);
    }
    return [...question.options].sort((a, b) => a.order - b.order);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [question.id, question.randomize_options, question.options.length]);

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 mb-6 text-center">
        {question.title}
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {displayOptions.map((option) => (
          <OptionCard
            key={option.id}
            label={option.label}
            sourceType={option.source_type}
            imageUrl={option.image_url}
            sourceUrl={option.source_url}
            selected={selectedOptionId === option.id}
            locked={locked}
            onClick={() => onSelect(option.id)}
          />
        ))}
      </div>
    </div>
  );
}
