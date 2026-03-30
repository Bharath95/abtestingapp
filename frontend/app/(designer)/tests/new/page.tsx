// frontend/app/(designer)/tests/new/page.tsx
"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { createTest } from "@/lib/api";
import TestMetaForm from "@/components/test-builder/TestMetaForm";
import Card from "@/components/shared/Card";

export default function NewTestPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  async function handleCreate(name: string, description: string) {
    setError(null);
    try {
      const test = await createTest({ name, description: description || undefined });
      router.push(`/tests/${test.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create test");
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Create New Test</h1>
      {error && (
        <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-4 text-sm">{error}</div>
      )}
      <Card>
        <TestMetaForm onSave={handleCreate} submitLabel="Create Test" />
      </Card>
    </div>
  );
}
