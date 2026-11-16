import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { administrationService } from "../../services/administrationService";
import AdministrationPagination from "../../components/AdministrationPagination";
import { queryKeys } from "../../query";
import { messageFromError } from "../../hooks/errors";
import styles from "./Administration.module.css";

export default function ActivityLogs() {
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [action, setAction] = useState("");
  const [page, setPage] = useState(1);
  const query = useQuery({ queryKey: [...queryKeys.activityLogs, page, search, action], queryFn: () => administrationService.getActivity(page, search, action) });
  return <div className={styles.page}>
    <header className="page-header"><div><h1>Activity Logs</h1><p>Sign-ins, account registrations, and username or email changes recorded since activity logging was enabled.</p></div>
      <button type="button" className="secondary-button" disabled={query.isFetching} onClick={() => void query.refetch()}>{query.isFetching ? "Refreshing…" : "Refresh"}</button>
    </header>
    <section className="content-card" aria-label="Account activity">
      <form className={styles.toolbar} role="search" onSubmit={event => { event.preventDefault(); setSearch(searchInput.trim()); setPage(1); }}>
        <div className={styles.field}><label htmlFor="activity-search">Username or details</label><input id="activity-search" type="search" value={searchInput} onChange={event => setSearchInput(event.target.value)} /></div>
        <div className={styles.field}><label htmlFor="activity-action">Activity</label><select id="activity-action" value={action} onChange={event => { setAction(event.target.value); setPage(1); }}><option value="">All activities</option><option value="sign_in">Signed in</option><option value="registered">Account registered</option><option value="account_updated">Account updated</option></select></div>
        <button type="submit" className="secondary-button">Search</button>
      </form>
      {query.isError ? <div className="error-banner" role="alert">{messageFromError(query.error, "Unable to load activity logs.")} <button type="button" className="secondary-button" onClick={() => void query.refetch()}>Retry</button></div>
        : query.isPending ? <p className={styles.message} role="status">Loading activity logs…</p>
        : <>{query.data.results.length ? <div className={styles.tableWrap}><table className={styles.table}>
          <thead><tr><th scope="col">Date and time</th><th scope="col">Username at event</th><th scope="col">Activity</th><th scope="col">Details</th></tr></thead>
          <tbody>{query.data.results.map(entry => <tr key={entry.id}><td>{new Date(entry.created_at).toLocaleString()}</td><td>{entry.actor_username}</td><td>{entry.action_label}</td><td>{entry.details || "—"}</td></tr>)}</tbody>
        </table></div> : <p className={styles.message}>{search || action ? "No activity matches these filters." : "No account activity recorded yet."}</p>}
          <AdministrationPagination page={page} count={query.data.count} hasNext={Boolean(query.data.next)} onChange={setPage} />
        </>}
    </section>
  </div>;
}
