// frontend/app/(designer)/tests/[testId]/analytics/page.tsx
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import type { Analytics } from "@/lib/types";
import { fetchAnalytics } from "@/lib/api";
import Card from "@/components/shared/Card";
import EmptyState from "@/components/shared/EmptyState";
import Button from "@/components/shared/Button";
import SummaryStats from "@/components/analytics/SummaryStats";
import VoteChart from "@/components/analytics/VoteChart";
import FollowUpList from "@/components/analytics/FollowUpList";
import ExportButton from "@/components/analytics/ExportButton";

export default function AnalyticsPage() {
  const params = useParams();
  const testId = params?.testId ? Number(params.testId) : null;

  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (testId === null) return;
    fetchAnalytics(testId)
      .then(setAnalytics)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load analytics"))
      .finally(() => setLoading(false));
  }, [testId]);

  // Null guard for useParams() during prerendering
  if (testId === null) return <p className="text-gray-500">Loading...</p>;

  if (loading) return <p className="text-gray-500">Loading analytics...</p>;
  if (error) return <p className="text-red-600">Error: {error}</p>;
  if (!analytics) return <p className="text-red-600">No data</p>;

  if (analytics.total_sessions === 0) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-gray-900">{analytics.test_name} -- Analytics</h1>
          <Link href={`/tests/${testId}`}>
            <Button variant="secondary">Back to Test</Button>
          </Link>
        </div>
        <EmptyState
          title="No responses yet"
          message="Share the test link to start collecting responses."
        />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">{analytics.test_name} -- Analytics</h1>
        <div className="flex gap-2">
          <ExportButton testId={testId} />
          <Link href={`/tests/${testId}`}>
            <Button variant="secondary">Back to Test</Button>
          </Link>
        </div>
      </div>

      <SummaryStats
        totalSessions={analytics.total_sessions}
        totalAnswers={analytics.total_answers}
        completedSessions={analytics.completed_sessions}
        completionRate={analytics.completion_rate}
      />

      {analytics.questions.map((q, index) => (
        <Card key={q.question_id}>
          <div className="mb-4">
            <span className="text-xs font-medium text-blue-600 uppercase tracking-wide">
              Question {index + 1} of {analytics.questions.length}
            </span>
            <span className="text-xs text-gray-400 ml-2">
              {q.total_votes} {q.total_votes === 1 ? "response" : "responses"}
            </span>
          </div>
          <VoteChart options={q.options} questionTitle={q.title} />
          <div className="border-t mt-6 pt-4">
            <FollowUpList options={q.options} />
          </div>
        </Card>
      ))}
    </div>
  );
}
