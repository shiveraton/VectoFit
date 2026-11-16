import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { AxiosError } from "axios";
import { accountService, type CurrentUser } from "../../services/accountService";
import { queryKeys } from "../../query";
import { messageFromError } from "../../hooks/errors";
import styles from "./Administration.module.css";

type AccountChanges = Pick<CurrentUser, "username" | "email">;
type AccountErrors = { username?: string[]; email?: string[]; detail?: string };

function AccountForm({ user }: { user: CurrentUser }) {
  const cache = useQueryClient();
  const [username, setUsername] = useState(user.username);
  const [email, setEmail] = useState(user.email);
  const save = useMutation<CurrentUser, AxiosError<AccountErrors>, AccountChanges>({
    mutationFn: changes => accountService.updateCurrentUser(user.id, changes),
    onSuccess: async updatedUser => {
      cache.setQueryData(queryKeys.currentUser, updatedUser);
      cache.setQueriesData({ queryKey: queryKeys.session }, updatedUser);
      await Promise.all([
        cache.invalidateQueries({ queryKey: queryKeys.users }),
        cache.invalidateQueries({ queryKey: queryKeys.activityLogs }),
      ]);
    },
  });
  const errors = save.error?.response?.data;
  const unchanged = username.trim() === user.username && email.trim() === user.email;
  return <form className={styles.form} onSubmit={event => { event.preventDefault(); save.mutate({ username: username.trim(), email: email.trim() }); }}>
    <div className={styles.field}><label htmlFor="settings-username">Username</label><input id="settings-username" autoComplete="username" required maxLength={150} value={username} disabled={save.isPending} aria-invalid={Boolean(errors?.username)} aria-describedby={errors?.username ? "username-error" : undefined} onChange={event => { setUsername(event.target.value); save.reset(); }} />
      {errors?.username && <p id="username-error" className={styles.fieldError}>{errors.username.join(" ")}</p>}
    </div>
    <div className={styles.field}><label htmlFor="settings-email">Email (optional)</label><input id="settings-email" type="email" autoComplete="email" maxLength={254} value={email} disabled={save.isPending} aria-invalid={Boolean(errors?.email)} aria-describedby={errors?.email ? "email-error" : undefined} onChange={event => { setEmail(event.target.value); save.reset(); }} />
      {errors?.email && <p id="email-error" className={styles.fieldError}>{errors.email.join(" ")}</p>}
    </div>
    {save.isError && <p role="alert" className={styles.fieldError}>{errors?.username || errors?.email ? "Check the highlighted fields." : messageFromError(save.error, "Unable to save account settings.")}</p>}
    {save.isSuccess && <p role="status" className={styles.help}>Account settings saved.</p>}
    <div><button type="submit" className="primary-button" disabled={save.isPending || unchanged || !username.trim()}>{save.isPending ? "Saving…" : "Save changes"}</button></div>
  </form>;
}

export default function Settings() {
  const query = useQuery({ queryKey: queryKeys.currentUser, queryFn: accountService.getCurrentUser });
  return <div className={styles.page}>
    <header className="page-header"><div><h1>Settings</h1><p>Update your own account details.</p></div></header>
    <section className="content-card" aria-labelledby="account-settings-heading">
      <div className="section-header"><h2 id="account-settings-heading">Account</h2></div>
      <div className="card-body">{query.isError ? <div role="alert">{messageFromError(query.error, "Unable to load account settings.")} <button type="button" className="secondary-button" onClick={() => void query.refetch()}>Retry</button></div>
        : query.isPending ? <p role="status">Loading account settings…</p> : <AccountForm key={query.data.id} user={query.data} />}</div>
    </section>
  </div>;
}
