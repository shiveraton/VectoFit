import { useEffect, useRef, useState } from "react";
import { getSessionResultFixture, type FixtureName } from "../model/fixtures";
import type { SessionResultState } from "../model/types";

export type PreviewScenario = FixtureName | "loading" | "tracking" | "counting" | "checking"
  | "network_error" | "processing_failed" | "unknown_error";

function previewState(scenario: PreviewScenario): SessionResultState {
  if (scenario === "loading") return { status: "loading" };
  if (scenario === "tracking" || scenario === "counting" || scenario === "checking") return { status: "loading", stage: scenario };
  if (scenario === "network_error") return { status: "error", error: { kind: "network" } };
  if (scenario === "processing_failed") return { status: "error", error: { kind: "processing_failed" } };
  if (scenario === "unknown_error") return { status: "error", error: { kind: "unknown" } };
  return { status: "ready", data: getSessionResultFixture(scenario) };
}

export default function useSessionResultPreview(initialFixture: FixtureName) {
  const [preview, setPreview] = useState(() => ({ scenario: initialFixture as PreviewScenario,
    state: __DEV__ ? previewState(initialFixture) : null, retrying: false }));
  const generation = useRef(0);
  const pending = useRef(false);
  useEffect(() => () => { generation.current++; }, []);
  const selectScenario = (scenario: PreviewScenario) => {
    if (!__DEV__) return;
    generation.current++;
    pending.current = false;
    setPreview({ scenario, state: previewState(scenario), retrying: false });
  };
  const retry = async () => {
    if (!__DEV__ || pending.current) return;
    pending.current = true;
    const request = ++generation.current;
    setPreview(current => ({ ...current, retrying: true }));
    // TODO(decision-17): Development retry loads a local fixture; it never retries production processing.
    try {
      const data = await Promise.resolve().then(() => getSessionResultFixture(initialFixture));
      if (generation.current !== request) return;
      pending.current = false;
      setPreview({ scenario: initialFixture, state: { status: "ready", data }, retrying: false });
    } catch {
      if (generation.current !== request) return;
      pending.current = false;
      setPreview(current => ({ ...current, state: { status: "error", error: { kind: "unknown" } }, retrying: false }));
    }
  };
  return { ...preview, selectScenario, retry };
}
