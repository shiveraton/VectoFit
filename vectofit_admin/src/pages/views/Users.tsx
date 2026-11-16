import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { administrationService } from "../../services/administrationService";
import AdministrationPagination from "../../components/AdministrationPagination";
import { queryKeys } from "../../query";
import { messageFromError } from "../../hooks/errors";
import styles from "./Administration.module.css";

export default function Users() {
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const query = useQuery({ queryKey: [...queryKeys.users, page, search], queryFn: () => administrationService.getUsers(page, search) });
  return <div className={styles.page}>
    <header className="page-header"><div><h1>Users</h1><p>Registered accounts, workspace roles, and account status.</p></div>
      <button type="button" className="secondary-button" disabled={query.isFetching} onClick={() => void query.refetch()}>{query.isFetching ? "Refreshing…" : "Refresh"}</button>
    </header>
    <section className="content-card" aria-label="User directory">
      <form className={styles.toolbar} role="search" onSubmit={event => { event.preventDefault(); setSearch(searchInput.trim()); setPage(1); }}>
        <div className={styles.field}><label htmlFor="user-search">Username or email</label><input id="user-search" type="search" value={searchInput} onChange={event => setSearchInput(event.target.value)} /></div>
        <button className="secondary-button" type="submit">Search</button>
      </form>
      {query.isError ? <div className="error-banner" role="alert">{messageFromError(query.error, "Unable to load users.")} <button type="button" className="secondary-button" onClick={() => void query.refetch()}>Retry</button></div>
        : query.isPending ? <p className={styles.message} role="status">Loading users…</p>
        : <>{query.data.results.length ? <div className={styles.tableWrap}><table className={styles.table}>
          <thead><tr><th scope="col">Username</th><th scope="col">Email</th><th scope="col">Roles</th><th scope="col">Status</th><th scope="col">Joined</th></tr></thead>
          <tbody>{query.data.results.map(user => <tr key={user.id}>
            <td>{user.username}</td><td>{user.email || "Not provided"}</td>
            <td>{[user.is_staff && "Administrator", user.is_validator && "Validator", user.is_annotator && "Annotator"].filter(Boolean).join(", ") || "User"}</td>
            <td><span className={`status-badge${user.is_active ? " is-active" : ""}`}>{user.is_active ? "Active" : "Inactive"}</span></td>
            <td>{new Date(user.date_joined).toLocaleDateString()}</td>
          </tr>)}</tbody>
        </table></div> : <p className={styles.message}>{search ? "No users match your search." : "No users found."}</p>}
          <AdministrationPagination page={page} count={query.data.count} hasNext={Boolean(query.data.next)} onChange={setPage} />
        </>}
    </section>
  </div>;
}
