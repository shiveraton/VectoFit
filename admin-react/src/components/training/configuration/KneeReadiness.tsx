import { useQuery } from "@tanstack/react-query";
import client from "../../../config/client";
import styles from "./KneeReadiness.module.css";

type Counts = { eligible: number; good: number; bad: number; excluded: number };
type Readiness = {
  eligibility_policy_version: string;
  inspected_count: number;
  eligible_count: number;
  excluded_count: number;
  class_counts: { good: number; bad: number };
  exclusion_counts: Record<string, number>;
  participants: Record<string, Counts>;
  training_blockers: string[];
};

export default function KneeReadiness({
  datasetId,
  name,
}: {
  datasetId: number;
  name: string;
}) {
  const query = useQuery({
    queryKey: ["knee-readiness", datasetId],
    queryFn: async ({ signal }) =>
      (
        await client.get<Readiness>(`/datasets/${datasetId}/knee-readiness/`, {
          signal,
        })
      ).data,
    staleTime: 30000,
    retry: false,
  });
  const report = query.data;
  return (
    <section className={styles.report} aria-label={`${name} knee readiness`}>
      <h3>{name}: frontal knee readiness</h3>
      <button
        type="button"
        disabled={query.isFetching}
        onClick={() => void query.refetch()}
      >
        Refresh readiness
      </button>
      {query.isFetching && (
        <p role="status">Checking labels and landmark features...</p>
      )}
      {query.isError && (
        <p role="alert">
          Unable to check readiness. Retry using Refresh readiness.
        </p>
      )}
      {report && !query.isError && (
        <>
          <p>
            {report.inspected_count} inspected · {report.eligible_count}{" "}
            eligible ({report.class_counts.good} good, {report.class_counts.bad}{" "}
            bad) · {report.excluded_count} excluded
          </p>
          {report.eligible_count === 0 && (
            <p>
              No eligible frontal repetitions. Review the exclusion reasons
              below.
            </p>
          )}
          {Object.entries(report.exclusion_counts).length > 0 && (
            <ul>
              {Object.entries(report.exclusion_counts).map(
                ([reason, count]) => (
                  <li key={reason}>
                    {reason.replaceAll("_", " ")}: {count}
                  </li>
                ),
              )}
            </ul>
          )}
          <details>
            <summary>Participant counts</summary>
            <table>
              <thead>
                <tr>
                  <th scope="col">Participant ID</th>
                  <th scope="col">Good</th>
                  <th scope="col">Bad</th>
                  <th scope="col">Excluded</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(report.participants).map(
                  ([participant, counts]) => (
                    <tr key={participant}>
                      <th scope="row">{participant}</th>
                      <td>{counts.good}</td>
                      <td>{counts.bad}</td>
                      <td>{counts.excluded}</td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </details>
          {report.training_blockers.length > 0 && (
            <>
              <strong>Training blockers for this dataset</strong>
              <ul>
                {report.training_blockers.map((blocker) => (
                  <li key={blocker}>{blocker}</li>
                ))}
              </ul>
            </>
          )}
          <p>
            Policy: {report.eligibility_policy_version}. Combined-dataset
            coverage is checked when training starts.
          </p>
        </>
      )}
    </section>
  );
}
