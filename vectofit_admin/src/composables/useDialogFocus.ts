import { nextTick, onBeforeUnmount, watch, type Ref } from "vue";

export function useDialogFocus(isOpen: () => boolean, dialogRef: Readonly<Ref<HTMLElement | null>>) {
  let trigger: HTMLElement | null = null;
  let previousOverflow = "";
  let active = false;
  const focusable = () => Array.from(dialogRef.value?.querySelectorAll<HTMLElement>(
    'button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])',
  ) ?? []).filter(element => element.getClientRects().length > 0);

  const containFocus = (event: KeyboardEvent) => {
    if (event.key !== "Tab") return;
    const elements = focusable();
    const first = elements[0];
    const last = elements[elements.length - 1];
    if (!first || !last) { event.preventDefault(); dialogRef.value?.focus(); return; }
    if (!dialogRef.value?.contains(document.activeElement) ||
        (event.shiftKey && document.activeElement === first) ||
        (!event.shiftKey && document.activeElement === last)) {
      event.preventDefault();
      (event.shiftKey ? last : first).focus();
    }
  };
  const release = () => {
    if (!active) return;
    active = false;
    document.removeEventListener("keydown", containFocus);
    document.body.style.overflow = previousOverflow;
    if (trigger?.isConnected) trigger.focus();
  };
  watch(isOpen, async open => {
    if (!open) { release(); return; }
    trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    previousOverflow = document.body.style.overflow;
    active = true;
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", containFocus);
    await nextTick();
    if (isOpen()) (focusable()[0] ?? dialogRef.value)?.focus();
  });
  onBeforeUnmount(release);
}
