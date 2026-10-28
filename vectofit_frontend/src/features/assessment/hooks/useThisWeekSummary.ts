import { useQuery } from "@tanstack/react-query";
import {
  getAssessmentSessions,
  type AssessmentSession,
} from "../services/assessmentSession";

export interface DayActivity {
  date: Date;
  day: string;
  reps: number;
}

export interface ThisWeekSummary {
  sessionsCompleted: number;
  repsCompleted: number;
  dailyActivity: DayActivity[];
  lastSession: AssessmentSession | null;
  lastSessionLabel: string;
}

function getMonday(date: Date): Date {
  const monday = new Date(date);
  monday.setHours(0, 0, 0, 0);

  const day = monday.getDay();
  monday.setDate(monday.getDate() - (day === 0 ? 6 : day - 1));

  return monday;
}

export function summarizeThisWeek(
  sessions: AssessmentSession[],
  referenceDate = new Date(),
): ThisWeekSummary {
  const monday = getMonday(referenceDate);

  const completedSessions = sessions.filter((session) => {
    const createdAt = new Date(session.created_at);

    return (
      session.status.toUpperCase() === "COMPLETED" &&
      !Number.isNaN(createdAt.getTime()) &&
      createdAt >= monday &&
      createdAt <= referenceDate
    );
  });

  const dailyActivity: DayActivity[] = Array.from({ length: 7 }, (_, index) => {
    const date = new Date(monday);
    date.setDate(monday.getDate() + index);

    const daySessions = completedSessions.filter((session) => {
      const createdAt = new Date(session.created_at);

      return (
        createdAt.getFullYear() === date.getFullYear() &&
        createdAt.getMonth() === date.getMonth() &&
        createdAt.getDate() === date.getDate()
      );
    });

    return {
      date,
      day: date.toLocaleDateString("en-US", {
        weekday: "short",
      }),
      reps: daySessions.reduce(
        (total, session) => total + (Number(session.rep_count) || 0),
        0,
      ),
    };
  });

  const lastSession: AssessmentSession | null =
    [...completedSessions].sort(
      (a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    )[0] ?? null;

  return {
    sessionsCompleted: completedSessions.length,
    repsCompleted: completedSessions.reduce(
      (total, session) => total + (Number(session.rep_count) || 0),
      0,
    ),

    dailyActivity,
    lastSession,

    lastSessionLabel: lastSession
      ? new Date(lastSession.created_at).toLocaleDateString()
      : "No completed sessions this week",
  };
}

export function useThisWeekSummary() {
  return useQuery({
    queryKey: ["assessments-sessions", "this-week"],
    queryFn: getAssessmentSessions,
    select: (sessions) => summarizeThisWeek(sessions),
  });
}
