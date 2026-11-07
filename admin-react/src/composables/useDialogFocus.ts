import { useEffect, type RefObject } from 'react';
export function useDialogFocus(isOpen: () => boolean, dialogRef: RefObject<HTMLElement | null>) {
  const open = isOpen();
  useEffect(() => {
    if (!open) return;
    const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const previousOverflow = document.body.style.overflow;
    const focusable = () => Array.from(dialogRef.current?.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])') ?? []).filter(element => element.getClientRects().length > 0);
    const containFocus = (event: KeyboardEvent) => {
      if (event.key !== 'Tab') return;
      const elements = focusable(), first = elements[0], last = elements.at(-1);
      if (!first || !last) { event.preventDefault(); dialogRef.current?.focus(); return; }
      if (!dialogRef.current?.contains(document.activeElement) || (event.shiftKey && document.activeElement === first) || (!event.shiftKey && document.activeElement === last)) { event.preventDefault(); (event.shiftKey ? last : first).focus(); }
    };
    document.body.style.overflow = 'hidden'; document.addEventListener('keydown', containFocus);
    const frame = requestAnimationFrame(() => (focusable()[0] ?? dialogRef.current)?.focus());
    return () => { cancelAnimationFrame(frame); document.removeEventListener('keydown', containFocus); document.body.style.overflow = previousOverflow; if (trigger?.isConnected) trigger.focus(); };
  }, [open, dialogRef]);
}
