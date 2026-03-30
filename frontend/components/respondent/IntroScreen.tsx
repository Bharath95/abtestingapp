// frontend/components/respondent/IntroScreen.tsx
"use client";

import Button from "@/components/shared/Button";

interface IntroScreenProps {
  name: string;
  description: string | null;
  onStart: () => void;
}

export default function IntroScreen({ name, description, onStart }: IntroScreenProps) {
  return (
    <div className="max-w-lg mx-auto text-center py-16">
      <h1 className="text-3xl font-bold text-gray-900 mb-4">{name}</h1>
      {description && <p className="text-gray-600 mb-8">{description}</p>}
      <Button size="lg" onClick={onStart}>
        Start
      </Button>
    </div>
  );
}
