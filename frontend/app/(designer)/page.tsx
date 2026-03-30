// frontend/app/(designer)/page.tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchTests } from "@/lib/api";
import type { Test } from "@/lib/types";
import Card from "@/components/shared/Card";
import StatusBadge from "@/components/shared/StatusBadge";
import EmptyState from "@/components/shared/EmptyState";

export default function DashboardPage() {
  const [tests, setTests] = useState<Test[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTests()
      .then(setTests)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load tests"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-gray-500">Loading...</p>;

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600">Error: {error}</p>
        <p className="text-gray-500 mt-2">Make sure the backend is running on port 8000.</p>
      </div>
    );
  }

  if (tests.length === 0) {
    return (
      <EmptyState
        title="No tests yet"
        message="Create your first A/B test to get started."
        action={
          <Link
            href="/tests/new"
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            Create Test
          </Link>
        }
      />
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">My Tests</h1>
      </div>
      <div className="grid gap-4">
        {tests.map((test) => (
          <Link key={test.id} href={`/tests/${test.id}`}>
            <Card className="hover:shadow-md transition-shadow cursor-pointer">
              <div className="flex justify-between items-start">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <h2 className="text-lg font-semibold text-gray-900">{test.name}</h2>
                    <StatusBadge status={test.status} />
                  </div>
                  {test.description && (
                    <p className="text-gray-500 text-sm line-clamp-2">{test.description}</p>
                  )}
                  <div className="flex gap-4 mt-2 text-sm text-gray-400">
                    <span>{test.question_count} question{test.question_count !== 1 ? "s" : ""}</span>
                    <span>{test.response_count} response{test.response_count !== 1 ? "s" : ""}</span>
                  </div>
                </div>
                <span className="text-gray-400 text-sm">
                  {new Date(test.created_at).toLocaleDateString()}
                </span>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
