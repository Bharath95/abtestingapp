// frontend/components/test-builder/QuestionEditor.tsx
"use client";

import { useState } from "react";
import type { Question } from "@/lib/types";
import OptionEditor from "./OptionEditor";
import Button from "@/components/shared/Button";
import {
  updateQuestion,
  deleteQuestion,
  createOption,
  updateOption,
  deleteOption,
} from "@/lib/api";

interface QuestionEditorProps {
  question: Question;
  testId: number;
  onUpdate: () => void;
  onDelete: () => void;
}

export default function QuestionEditor({
  question,
  testId,
  onUpdate,
  onDelete,
}: QuestionEditorProps) {
  const [title, setTitle] = useState(question.title);
  const [followupPrompt, setFollowupPrompt] = useState(question.followup_prompt);
  const [followupRequired, setFollowupRequired] = useState(question.followup_required);
  const [randomizeOptions, setRandomizeOptions] = useState(question.randomize_options);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSaveQuestion() {
    setSaving(true);
    setError(null);
    try {
      await updateQuestion(question.id, {
        title,
        followup_prompt: followupPrompt,
        followup_required: followupRequired,
        randomize_options: randomizeOptions,
      });
      onUpdate();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save question");
    } finally {
      setSaving(false);
    }
  }

  async function handleToggle(field: string, value: boolean) {
    setError(null);
    try {
      await updateQuestion(question.id, { [field]: value });
      onUpdate();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update setting");
    }
  }

  async function handleDeleteQuestion() {
    try {
      await deleteQuestion(question.id);
      onDelete();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete question");
    }
  }

  async function handleSaveOption(
    label: string,
    sourceType: "upload" | "url",
    imageFile: File | null,
    sourceUrl: string | null,
    optionId?: number,
  ) {
    setError(null);
    const formData = new FormData();
    formData.append("label", label);
    formData.append("source_type", sourceType);
    if (sourceType === "upload" && imageFile) {
      formData.append("image", imageFile);
    }
    if (sourceType === "url" && sourceUrl) {
      formData.append("source_url", sourceUrl);
    }

    try {
      if (optionId) {
        await updateOption(optionId, formData);
      } else {
        await createOption(question.id, formData);
      }
      onUpdate();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save option");
    }
  }

  async function handleDeleteOption(optionId: number) {
    try {
      await deleteOption(optionId);
      onUpdate();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete option");
    }
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 space-y-4">
      <div className="flex justify-between items-start">
        <h3 className="text-sm font-medium text-gray-500">Question {question.order + 1}</h3>
        <Button variant="danger" size="sm" onClick={handleDeleteQuestion}>
          Delete Question
        </Button>
      </div>

      {error && (
        <div className="bg-red-50 text-red-600 p-2 rounded text-sm">{error}</div>
      )}

      <input
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Question title (e.g., Which homepage do you prefer?)"
        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
        maxLength={500}
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Follow-up prompt</label>
          <input
            type="text"
            value={followupPrompt}
            onChange={(e) => setFollowupPrompt(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
            maxLength={500}
          />
        </div>
        <div className="flex items-end gap-4">
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={followupRequired}
              onChange={(e) => {
                setFollowupRequired(e.target.checked);
                handleToggle("followup_required", e.target.checked);
              }}
              className="rounded border-gray-300"
            />
            Follow-up required
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={randomizeOptions}
              onChange={(e) => {
                setRandomizeOptions(e.target.checked);
                handleToggle("randomize_options", e.target.checked);
              }}
              className="rounded border-gray-300"
            />
            Randomize options
          </label>
        </div>
      </div>

      <Button size="sm" onClick={handleSaveQuestion} disabled={saving || !title.trim()}>
        {saving ? "Saving..." : "Save Question"}
      </Button>

      <div className="border-t pt-4 mt-4">
        <h4 className="text-sm font-medium text-gray-700 mb-3">Options</h4>
        <div className="space-y-3">
          {question.options.map((opt) => (
            <OptionEditor
              key={opt.id}
              optionId={opt.id}
              initialLabel={opt.label}
              initialSourceType={opt.source_type}
              initialImageUrl={opt.image_url}
              initialSourceUrl={opt.source_url}
              onSave={(label, sourceType, file, sourceUrl) =>
                handleSaveOption(label, sourceType, file, sourceUrl, opt.id)
              }
              onDelete={() => handleDeleteOption(opt.id)}
            />
          ))}
          {/* Only show "Add Option" editor when fewer than 5 options */}
          {question.options.length < 5 && (
            <OptionEditor
              initialLabel=""
              isNew
              onSave={(label, sourceType, file, sourceUrl) =>
                handleSaveOption(label, sourceType, file, sourceUrl)
              }
            />
          )}
        </div>
      </div>
    </div>
  );
}
