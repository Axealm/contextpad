import React, { useEffect, useRef } from "react";
import { Loader2 } from "lucide-react";

export function ConfirmationDialog({ title, action, busy, destructive, error, onCancel, onConfirm, children }: {
  title: string; action: string; busy: boolean; destructive?: boolean; error: string | null;
  onCancel: () => void; onConfirm: () => void; children: React.ReactNode;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const element = dialog.current;
    element?.showModal();
    return () => { element?.close(); if (previous?.isConnected) previous.focus(); };
  }, []);
  return <dialog ref={dialog} className="confirmation-dialog" aria-labelledby="confirmation-title"
    onCancel={(event) => { event.preventDefault(); if (!busy) onCancel(); }}>
    <h2 id="confirmation-title">{title}</h2>
    <div className="confirmation-body">{children}</div>
    {error && <p className="confirmation-error" role="alert">{error}</p>}
    <footer>
      <button type="button" className="dialog-cancel" autoFocus disabled={busy} onClick={onCancel}>キャンセル</button>
      <button type="button" className={destructive ? "danger-button" : "save-button"} disabled={busy} onClick={onConfirm}>
        {busy && <Loader2 size={14} className="spin" />}{action}
      </button>
    </footer>
  </dialog>;
}
