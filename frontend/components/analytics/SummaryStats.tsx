// frontend/components/analytics/SummaryStats.tsx
"use client";

interface SummaryStatsProps {
  totalSessions: number;
  totalAnswers: number;
  completedSessions: number;
  completionRate: number;
}

export default function SummaryStats({
  totalSessions,
  totalAnswers,
  completedSessions,
  completionRate,
}: SummaryStatsProps) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
      <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
        <p className="text-3xl font-bold text-gray-900">{totalSessions}</p>
        <p className="text-sm text-gray-500">Respondents</p>
      </div>
      <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
        <p className="text-3xl font-bold text-gray-900">{totalAnswers}</p>
        <p className="text-sm text-gray-500">Total Answers</p>
      </div>
      <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
        <p className="text-3xl font-bold text-gray-900">{completedSessions}</p>
        <p className="text-sm text-gray-500">Completed</p>
      </div>
      <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
        <p className="text-3xl font-bold text-gray-900">{completionRate}%</p>
        <p className="text-sm text-gray-500">Completion Rate</p>
      </div>
    </div>
  );
}
