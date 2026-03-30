// frontend/app/(designer)/tests/[testId]/page.tsx
"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import type { TestDetail } from "@/lib/types";
import { API_BASE_URL } from "@/lib/constants";
import {
  fetchTest,
  updateTest,
  deleteTest,
  createQuestion,
} from "@/lib/api";
import Card from "@/components/shared/Card";
import Button from "@/components/shared/Button";
import StatusBadge from "@/components/shared/StatusBadge";
import ConfirmDialog from "@/components/shared/ConfirmDialog";
import TestMetaForm from "@/components/test-builder/TestMetaForm";
import QuestionEditor from "@/components/test-builder/QuestionEditor";

export default function TestDetailPage() {
  const params = useParams();
  const router = useRouter();

  // Null guard for useParams() during prerendering
  if (!params?.testId) return <p className="text-gray-500">Loading...</p>;

  const testId = Number(params.testId);

  const [test, setTest] = useState<TestDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const loadTest = useCallback(async () => {
    try {
      const data = await fetchTest(testId);
      setTest(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load test");
    } finally {
      setLoading(false);
    }
  }, [testId]);

  useEffect(() => {
    loadTest();
  }, [loadTest]);

  if (loading) return <p className="text-gray-500">Loading...</p>;
  if (error) return <p className="text-red-600">Error: {error}</p>;
  if (!test) return <p className="text-red-600">Test not found</p>;

  const isDraft = test.status === "draft";
  const canActivate = isDraft && test.questions.length > 0 && test.questions.every(
    (q) => q.options.length >= 2 && q.options.length <= 5
  );

  async function handleUpdateMeta(name: string, description: string) {
    await updateTest(testId, { name, description: description || undefined });
    loadTest();
  }

  async function handleStatusChange(newStatus: string) {
    setError(null);
    try {
      await updateTest(testId, { status: newStatus });
      loadTest();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update status");
    }
  }

  async function handleAddQuestion() {
    await createQuestion(testId, { title: "New question" });
    loadTest();
  }

  async function handleDelete() {
    await deleteTest(testId);
    router.push("/");
  }

  const respondUrl = `${typeof window !== "undefined" ? window.location.origin : ""}/respond/${test.slug}`;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-2xl font-bold text-gray-900">{test.name}</h1>
            <StatusBadge status={test.status} />
          </div>
          {test.status !== "draft" && (
            <p className="text-sm text-gray-500">
              Share: <code className="bg-gray-100 px-2 py-0.5 rounded text-xs">{respondUrl}</code>
            </p>
          )}
        </div>
        <div className="flex gap-2">
          <Link href={`/tests/${testId}/analytics`}>
            <Button variant="secondary">Analytics</Button>
          </Link>
          <Button variant="danger" size="sm" onClick={() => setShowDeleteDialog(true)}>
            Delete
          </Button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm">{error}</div>
      )}

      {/* Status controls */}
      <Card>
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-medium text-gray-700">Test Status</h2>
            <p className="text-xs text-gray-400 mt-1">
              {isDraft && "Draft -- add questions and options, then activate to start collecting responses."}
              {test.status === "active" && "Active -- respondents can take this test. Questions and options are locked."}
              {test.status === "closed" && "Closed -- no more responses accepted."}
            </p>
          </div>
          <div className="flex gap-2">
            {isDraft && (
              <Button
                onClick={() => handleStatusChange("active")}
                disabled={!canActivate}
                title={canActivate ? "" : "Need at least 1 question with 2-5 options each"}
              >
                Activate
              </Button>
            )}
            {test.status === "active" && (
              <Button variant="secondary" onClick={() => handleStatusChange("closed")}>
                Close Test
              </Button>
            )}
          </div>
        </div>
      </Card>

      {/* Meta form -- always editable for name/description */}
      <Card>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Test Details</h2>
        <TestMetaForm
          initialName={test.name}
          initialDescription={test.description || ""}
          onSave={handleUpdateMeta}
          submitLabel="Update"
        />
      </Card>

      {/* Questions -- only editable in draft */}
      <div>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Questions ({test.questions.length})
          </h2>
          {isDraft && (
            <Button size="sm" onClick={handleAddQuestion}>
              Add Question
            </Button>
          )}
        </div>
        {isDraft ? (
          <div className="space-y-4">
            {test.questions.map((q) => (
              <QuestionEditor
                key={q.id}
                question={q}
                testId={testId}
                onUpdate={loadTest}
                onDelete={loadTest}
              />
            ))}
          </div>
        ) : (
          <div className="space-y-4">
            {test.questions.map((q) => (
              <Card key={q.id}>
                <h3 className="font-medium text-gray-900">{q.title}</h3>
                <p className="text-sm text-gray-500 mt-1">
                  {q.options.length} options | Follow-up: {q.followup_required ? "required" : "optional"} | Randomize: {q.randomize_options ? "yes" : "no"}
                </p>
                <div className="flex gap-2 mt-3 flex-wrap">
                  {q.options.map((o) => (
                    <div key={o.id} className="text-center">
                      {o.source_type === "upload" && o.image_url && (
                        <img
                          src={`${API_BASE_URL}${o.image_url}`}
                          alt={o.label}
                          className="h-24 object-contain rounded border"
                        />
                      )}
                      {o.source_type === "url" && o.source_url && (
                        <a href={o.source_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 text-xs underline">
                          {o.source_url}
                        </a>
                      )}
                      <p className="text-xs text-gray-600 mt-1">{o.label}</p>
                    </div>
                  ))}
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Delete confirmation */}
      <ConfirmDialog
        open={showDeleteDialog}
        title="Delete Test"
        message="This will permanently delete this test, all questions, options, and responses. This cannot be undone."
        onConfirm={handleDelete}
        onCancel={() => setShowDeleteDialog(false)}
      />
    </div>
  );
}
