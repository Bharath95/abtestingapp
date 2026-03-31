"use client";

import { useState } from "react";
import Button from "@/components/shared/Button";

interface IntroScreenProps {
  name: string;
  description: string | null;
  onStart: (respondentName: string) => void;
}

export default function IntroScreen({ name, description, onStart }: IntroScreenProps) {
  const [respondentName, setRespondentName] = useState("");

  return (
    <div className="max-w-lg mx-auto text-center py-16">
      <h1 className="text-3xl font-bold text-gray-900 mb-4">{name}</h1>
      {description && <p className="text-gray-600 mb-8">{description}</p>}
      <div className="mb-6 text-left">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Your Name
        </label>
        <input
          type="text"
          value={respondentName}
          onChange={(e) => setRespondentName(e.target.value)}
          placeholder="Enter your name"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
          maxLength={200}
        />
      </div>
      <Button size="lg" onClick={() => onStart(respondentName.trim())} disabled={!respondentName.trim()}>
        Start
      </Button>
    </div>
  );
}
