// frontend/app/respond/[slug]/page.tsx
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import type { RespondentTest } from "@/lib/types";
import { fetchTestForRespondent, submitAnswer } from "@/lib/api";
import IntroScreen from "@/components/respondent/IntroScreen";
import QuestionView from "@/components/respondent/QuestionView";
import FollowUpInput from "@/components/respondent/FollowUpInput";
import ProgressBar from "@/components/respondent/ProgressBar";
import Button from "@/components/shared/Button";

type Phase = "loading" | "error" | "intro" | "question" | "done";

export default function RespondPage() {
  const params = useParams();
  const slug = params?.slug as string | undefined;

  const [test, setTest] = useState<RespondentTest | null>(null);
  const [phase, setPhase] = useState<Phase>("loading");
  const [errorMsg, setErrorMsg] = useState("");
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedOptionId, setSelectedOptionId] = useState<number | null>(null);
  const [isLocked, setIsLocked] = useState(false);
  const [followupText, setFollowupText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [sessionId] = useState(() => crypto.randomUUID());
  const [respondentName, setRespondentName] = useState("");

  useEffect(() => {
    if (!slug) return;
    fetchTestForRespondent(slug)
      .then((data) => {
        setTest(data);
        setPhase("intro");
      })
      .catch((e) => {
        setErrorMsg(e instanceof Error ? e.message : "Failed to load test");
        setPhase("error");
      });
  }, [slug]);

  function handleSelect(optionId: number) {
    if (isLocked) return;
    setSelectedOptionId(optionId);
    setIsLocked(true);
  }

  async function handleNext() {
    if (!test || selectedOptionId === null || !slug) return;
    const question = test.questions[currentIndex];

    if (question.followup_required && !followupText.trim()) {
      return;
    }

    setSubmitting(true);
    try {
      await submitAnswer(slug, {
        session_id: sessionId,
        respondent_name: respondentName || undefined,
        question_id: question.id,
        option_id: selectedOptionId,
        followup_text: followupText.trim() || undefined,
      });

      if (currentIndex < test.questions.length - 1) {
        setCurrentIndex((i) => i + 1);
        setSelectedOptionId(null);
        setIsLocked(false);
        setFollowupText("");
      } else {
        setPhase("done");
      }
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : "Failed to submit answer");
    } finally {
      setSubmitting(false);
    }
  }

  // Null guard for useParams() during prerendering
  if (!slug) {
    return <p className="text-center text-gray-500 py-16">Loading...</p>;
  }

  if (phase === "loading") {
    return <p className="text-center text-gray-500 py-16">Loading...</p>;
  }

  if (phase === "error") {
    return (
      <div className="text-center py-16">
        <p className="text-red-600 text-lg">{errorMsg}</p>
      </div>
    );
  }

  if (phase === "intro" && test) {
    return (
      <IntroScreen
        name={test.name}
        description={test.description}
        onStart={(name) => {
          setRespondentName(name);
          setPhase("question");
        }}
      />
    );
  }

  if (phase === "done") {
    return (
      <div className="max-w-lg mx-auto text-center py-16">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">Thank you!</h1>
        <p className="text-gray-600">Your responses have been recorded.</p>
      </div>
    );
  }

  if (phase === "question" && test) {
    const question = test.questions[currentIndex];
    const canProceed =
      isLocked && (!question.followup_required || followupText.trim().length > 0);

    return (
      <div className="max-w-4xl mx-auto">
        <ProgressBar current={currentIndex} total={test.questions.length} />

        <QuestionView
          question={question}
          selectedOptionId={selectedOptionId}
          locked={isLocked}
          onSelect={handleSelect}
        />

        {isLocked && (
          <FollowUpInput
            prompt={question.followup_prompt}
            required={question.followup_required}
            value={followupText}
            onChange={setFollowupText}
          />
        )}

        {errorMsg && (
          <p className="text-red-500 text-sm mt-4">{errorMsg}</p>
        )}

        <div className="flex justify-end mt-6">
          <Button
            onClick={handleNext}
            disabled={!canProceed || submitting}
            size="lg"
          >
            {submitting
              ? "Saving..."
              : currentIndex < test.questions.length - 1
              ? "Next"
              : "Finish"}
          </Button>
        </div>
      </div>
    );
  }

  return null;
}
