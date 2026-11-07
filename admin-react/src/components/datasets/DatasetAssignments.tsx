import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { datasetAssignmentService as service } from '../../services/datasetAssignmentService';
import styles from './DatasetAssignments.module.css';

function Pager({ page, next, previous, onChange }: { page: number; next?: string | null; previous?: string | null; onChange: (page: number) => void }) {
  return <div className={styles.pager}><button type="button" className="secondary-button" disabled={!previous} onClick={() => onChange(page - 1)}>Previous</button><span>Page {page}</span><button type="button" className="secondary-button" disabled={!next} onClick={() => onChange(page + 1)}>Next</button></div>;
}

export default function DatasetAssignments({ dataset, onClose }: { dataset: { id: number; name: string }; onClose: () => void }) {
  const cache = useQueryClient();
  const heading = useRef<HTMLHeadingElement>(null);
  const [page, setPage] = useState(1);
  const [eventPage, setEventPage] = useState(1);
  const [pickerPage, setPickerPage] = useState(1);
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState('');
  const [message, setMessage] = useState('');
  useEffect(() => { heading.current?.focus(); }, []);
  const key = ['dataset-assignments', dataset.id];
  const assignments = useQuery({ queryKey: [...key, 'list', page], queryFn: () => service.list(dataset.id, page), refetchOnMount: 'always' });
  const events = useQuery({ queryKey: [...key, 'events', eventPage], queryFn: () => service.events(dataset.id, eventPage) });
  const picker = useQuery({ queryKey: ['assignment-annotators', search, pickerPage], queryFn: () => service.annotators(search, pickerPage) });
  const update = useMutation({
    mutationFn: ({ userId, active }: { userId: number; active: boolean }) => service.set(dataset.id, userId, active),
    onSuccess: async (_, change) => {
      setMessage(change.active ? 'Access granted. The annotator can open this dataset when review samples are ready.' : 'Access revoked. Existing ratings are retained.');
      setSelected('');
      await cache.invalidateQueries({ queryKey: key });
      await cache.invalidateQueries({ queryKey: ['annotation-datasets'] });
    },
  });
  function change(userId: number, active: boolean) { setMessage(''); update.mutate({ userId, active }); }
  const mutationError = update.error ? 'Unable to change access. Refresh and try again; the account must be an active annotator to grant access.' : '';
  return <section className={`content-card ${styles.panel}`} aria-labelledby="assignment-title">
    <div className="section-header"><div><h2 id="assignment-title" ref={heading} tabIndex={-1}>Dataset access: {dataset.name}</h2><p>Grant access to registered annotators. Revoking access preserves their ratings.</p></div><button type="button" className="secondary-button" onClick={onClose}>Close access panel</button></div>
    <div className={styles.body}>
      <form className={styles.search} onSubmit={event => { event.preventDefault(); setSearch(searchInput.trim()); setPickerPage(1); setSelected(''); }}>
        <label htmlFor="annotator-search">Find an annotator<input id="annotator-search" type="search" value={searchInput} onChange={event => setSearchInput(event.target.value)} placeholder="Search by username" maxLength={150} /></label><button className="secondary-button" type="submit">Search</button>
      </form>
      {picker.isPending ? <p role="status">Loading annotators...</p> : picker.isError ? <p className="auth-error" role="alert">Unable to load annotators. <button type="button" className="secondary-button" onClick={() => { void picker.refetch(); }}>Retry</button></p> : <>
        <form className={styles.grant} onSubmit={event => { event.preventDefault(); if (selected && !update.isPending) change(Number(selected), true); }}>
          <label htmlFor="assignment-annotator">Annotator<select id="assignment-annotator" value={selected} onChange={event => setSelected(event.target.value)} required disabled={update.isPending}><option value="">Select an annotator</option>{picker.data?.results.map(user => <option key={user.id} value={user.id}>{user.username}</option>)}</select></label><button className="primary-button" type="submit" disabled={!selected || update.isPending}>Grant access</button>
        </form>
        {picker.data?.count === 0 ? <p>No active annotators match this search. Annotators must register before they can be assigned.</p> : picker.data && picker.data.count > 20 && <Pager page={pickerPage} next={picker.data?.next} previous={picker.data?.previous} onChange={value => { setPickerPage(value); setSelected(''); }} />}
      </>}
      <div aria-live="polite">{message && <p className={styles.notice}>{message}</p>}</div>
      {mutationError && <p className="auth-error" role="alert">{mutationError}</p>}
      <div className={styles.subheading}><h3>Assigned annotators</h3><button type="button" className="secondary-button" disabled={assignments.isFetching || update.isPending} onClick={() => { void cache.invalidateQueries({ queryKey: key }); }}>Refresh</button></div>
      {assignments.isPending ? <p role="status">Loading assignments...</p> : assignments.isError ? <p role="alert" className="auth-error">Unable to load assignments. Use Refresh to try again.</p> : <>
        {assignments.data.eligible_sample_count === 0 && <p className={styles.notice}>No ready samples are selected for manual review. Assignments can be prepared now; public access starts when eligible samples are available.</p>}
        {assignments.data.results.length === 0 ? <p>No annotators assigned. This dataset is hidden from public annotators.</p> : <div className={styles.table}><table><caption className={styles.caption}>Access and review progress for {dataset.name}</caption><thead><tr><th scope="col">Annotator</th><th scope="col">Access</th><th scope="col">Reviewed samples</th><th scope="col">Action</th></tr></thead><tbody>{assignments.data.results.map(row => <tr key={row.id}><th scope="row">{row.annotator.username}{!row.account_eligible && <small>Account ineligible</small>}</th><td>{row.is_active ? 'Granted' : 'Revoked'}</td><td>{row.reviewed_count} / {row.sample_count}</td><td><button type="button" className="secondary-button" disabled={update.isPending || (!row.is_active && !row.account_eligible)} aria-label={`${row.is_active ? 'Revoke' : 'Restore'} access for ${row.annotator.username}`} onClick={() => change(row.annotator.id, !row.is_active)}>{row.is_active ? 'Revoke access' : 'Restore access'}</button></td></tr>)}</tbody></table></div>}
        {assignments.data.count > 20 && <Pager page={page} next={assignments.data.next} previous={assignments.data.previous} onChange={setPage} />}
        <p className={styles.hint}>Progress counts each eligible sample's latest saved rating for that annotator. Clearing a rating removes it from the reviewed count.</p>
      </>}
      <h3>Access history</h3>
      {events.isPending ? <p role="status">Loading access history...</p> : events.isError ? <p role="alert">Unable to load history. <button type="button" className="secondary-button" onClick={() => { void events.refetch(); }}>Retry</button></p> : <>{events.data.results.length === 0 ? <p>No access changes recorded. Assignments created before audit history was introduced have no earlier events.</p> : <ul className={styles.history}>{events.data.results.map(event => <li key={event.id}><span>{event.annotator.username}: access {event.action} by {event.actor?.username ?? 'Deleted administrator'}</span><time dateTime={event.created_at}>{new Date(event.created_at).toLocaleString()}</time></li>)}</ul>}{events.data.count > 20 && <Pager page={eventPage} next={events.data.next} previous={events.data.previous} onChange={setEventPage} />}</>}
    </div>
  </section>;
}
