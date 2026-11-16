import styles from "../pages/views/Administration.module.css";

export default function AdministrationPagination({ page, count, hasNext, onChange }: {
  page: number;
  count: number;
  hasNext: boolean;
  onChange: (page: number) => void;
}) {
  return <nav className={styles.pagination} aria-label="Results pages">
    <span>{count} {count === 1 ? "result" : "results"} · Page {page}</span>
    <button type="button" className="secondary-button" disabled={page === 1} onClick={() => onChange(page - 1)}>Previous</button>
    <button type="button" className="secondary-button" disabled={!hasNext} onClick={() => onChange(page + 1)}>Next</button>
  </nav>;
}
