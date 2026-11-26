import type { FixtureName } from "../features/session-results/model/fixtures";

export type InsightsStackParamList = {
  SessionHistory: undefined;
  SessionResult: { sessionId: number; previewFixture?: FixtureName };
};
