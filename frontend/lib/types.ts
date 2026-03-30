// frontend/lib/types.ts

export interface Test {
  id: number;
  slug: string;
  name: string;
  description: string | null;
  status: "draft" | "active" | "closed";
  created_at: string;
  updated_at: string;
  question_count: number;
  response_count: number;
}

export interface Option {
  id: number;
  label: string;
  source_type: "upload" | "url";
  image_url: string | null;
  source_url: string | null;
  order: number;
  created_at: string;
}

export interface Question {
  id: number;
  order: number;
  title: string;
  followup_prompt: string;
  followup_required: boolean;
  randomize_options: boolean;
  options: Option[];
}

export interface TestDetail {
  id: number;
  slug: string;
  name: string;
  description: string | null;
  status: "draft" | "active" | "closed";
  created_at: string;
  updated_at: string;
  questions: Question[];
}

export interface RespondentTest {
  id: number;
  name: string;
  description: string | null;
  questions: Question[];
}

export interface FollowUpEntry {
  text: string;
  created_at: string;
}

export interface OptionAnalytics {
  option_id: number;
  label: string;
  source_type: "upload" | "url";
  image_url: string | null;
  source_url: string | null;
  votes: number;
  percentage: number;
  is_winner: boolean;
  followup_texts: FollowUpEntry[];
}

export interface QuestionAnalytics {
  question_id: number;
  title: string;
  total_votes: number;
  options: OptionAnalytics[];
}

export interface Analytics {
  test_id: number;
  test_name: string;
  total_sessions: number;
  total_answers: number;
  completed_sessions: number;
  completion_rate: number;
  questions: QuestionAnalytics[];
}
