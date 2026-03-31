// frontend/lib/api.ts
import { API_BASE_URL } from "./constants";
import type { Test, TestDetail, RespondentTest, Analytics, Question, Option } from "./types";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// Tests
export async function fetchTests(): Promise<Test[]> {
  return apiFetch<Test[]>("/api/v1/tests");
}

export async function fetchTest(testId: number): Promise<TestDetail> {
  return apiFetch<TestDetail>(`/api/v1/tests/${testId}`);
}

export async function createTest(data: { name: string; description?: string }): Promise<Test> {
  return apiFetch<Test>("/api/v1/tests", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function updateTest(
  testId: number,
  data: { name?: string; description?: string; status?: string }
): Promise<Test> {
  return apiFetch<Test>(`/api/v1/tests/${testId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function deleteTest(testId: number): Promise<void> {
  return apiFetch<void>(`/api/v1/tests/${testId}`, { method: "DELETE" });
}

// Questions
export async function createQuestion(
  testId: number,
  data: { title: string; followup_prompt?: string; followup_required?: boolean; randomize_options?: boolean }
): Promise<Question> {
  return apiFetch<Question>(`/api/v1/tests/${testId}/questions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function updateQuestion(
  questionId: number,
  data: { title?: string; followup_prompt?: string; followup_required?: boolean; randomize_options?: boolean; order?: number }
): Promise<Question> {
  return apiFetch<Question>(`/api/v1/questions/${questionId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function deleteQuestion(questionId: number): Promise<void> {
  return apiFetch<void>(`/api/v1/questions/${questionId}`, { method: "DELETE" });
}

// Options (multipart -- do NOT set Content-Type header; browser sets it with boundary)
export async function createOption(
  questionId: number,
  formData: FormData
): Promise<Option> {
  return apiFetch<Option>(`/api/v1/questions/${questionId}/options`, {
    method: "POST",
    body: formData,
  });
}

export async function updateOption(
  optionId: number,
  formData: FormData
): Promise<Option> {
  return apiFetch<Option>(`/api/v1/options/${optionId}`, {
    method: "PATCH",
    body: formData,
  });
}

export async function deleteOption(optionId: number): Promise<void> {
  return apiFetch<void>(`/api/v1/options/${optionId}`, { method: "DELETE" });
}

// Respondent
export async function fetchTestForRespondent(slug: string): Promise<RespondentTest> {
  return apiFetch<RespondentTest>(`/api/v1/respond/${slug}`);
}

export async function submitAnswer(
  slug: string,
  data: { session_id: string; respondent_name?: string; question_id: number; option_id: number; followup_text?: string }
): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/api/v1/respond/${slug}/answers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

// Analytics
export async function fetchAnalytics(testId: number): Promise<Analytics> {
  return apiFetch<Analytics>(`/api/v1/tests/${testId}/analytics`);
}

export function getExportUrl(testId: number): string {
  return `${API_BASE_URL}/api/v1/tests/${testId}/export`;
}
