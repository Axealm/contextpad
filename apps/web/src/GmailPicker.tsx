import React, { useEffect, useRef, useState } from "react";
import { ArrowLeft, Check, ChevronDown, ExternalLink, Link2Off, Loader2, Mail, RefreshCw, Search, X } from "lucide-react";
import { ApiError, EmailLink, request } from "./api";
import setupGuideUrl from "../../../docs/gmail-setup.md?url";

type Connection = { configured: boolean; connected: boolean; pending: boolean; error: string | null };
type MailPage = { messages: EmailLink[]; next_page_token: string | null };
type MailDetail = { email: EmailLink; truncated: boolean; snippet_only: boolean };
const PREFIX = "/api/v1/gmail";
const errors: Record<string, string> = {
  gmail_not_configured: "Google Cloudの接続設定が必要です。",
  origin_not_allowed: "アプリを設定済みのURLで開いてください。既定は http://127.0.0.1:5173/ です。",
  consent_denied: "Googleでの接続がキャンセルされました。",
  oauth_expired: "接続の有効時間が過ぎました。もう一度接続してください。",
  oauth_failed: "Googleとの認証に失敗しました。接続設定を確認してください。",
  reconnect_required: "Gmailへの再接続が必要です。",
  scope_missing: "メールの読み取り権限が許可されていません。",
  access_denied: "Gmailを読み取れません。APIの有効化・権限・組織の設定を確認してください。",
  message_not_found: "このメールは見つかりません。削除された可能性があります。",
  rate_limited: "Gmailの利用上限に達しました。時間を置いて再度お試しください。",
};

function dateLabel(value?: string | null) {
  return value ? new Intl.DateTimeFormat("ja-JP", { month: "numeric", day: "numeric" }).format(new Date(value)) : "";
}

export function GmailPicker({ disabled, replacing, onSelect }: {
  disabled: boolean; replacing: boolean; onSelect: (email: EmailLink) => void;
}) {
  const [open, setOpen] = useState(false);
  return <>
    <button type="button" className="gmail-trigger" title="Gmailからメールを選ぶ" disabled={disabled} onClick={() => setOpen(true)}>
      <Mail size={14} />Gmail
    </button>
    {open && <PickerDialog replacing={replacing} onSelect={(email) => { onSelect(email); setOpen(false); }} onClose={() => setOpen(false)} />}
  </>;
}

function PickerDialog({ replacing, onSelect, onClose }: { replacing: boolean; onSelect: (email: EmailLink) => void; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const popup = useRef<Window | null>(null);
  const mounted = useRef(true);
  const [connection, setConnection] = useState<Connection | null>(null);
  const [busy, setBusy] = useState<string | null>("status");
  const [waiting, setWaiting] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [activeQuery, setActiveQuery] = useState("");
  const [messages, setMessages] = useState<EmailLink[]>([]);
  const [nextPage, setNextPage] = useState<string | null>(null);
  const [selected, setSelected] = useState<MailDetail | null>(null);

  function failure(error: unknown) {
    if (!mounted.current) return;
    setNotice(error instanceof ApiError ? errors[error.code] ?? "Gmailと通信できませんでした。もう一度お試しください。" : "通信が完了しませんでした。接続を確認して再度お試しください。");
    if (error instanceof ApiError && error.status === 401) {
      setConnection((previous) => previous ? { ...previous, connected: false } : previous);
      setMessages([]); setSelected(null); setNextPage(null);
    }
  }

  async function loadMessages(search: string, page?: string) {
    setBusy("list"); setNotice(null);
    const params = new URLSearchParams({ q: search });
    if (page) params.set("page_token", page);
    try {
      const result = await request<MailPage>(`${PREFIX}/messages?${params}`);
      if (!mounted.current) return;
      setMessages((previous) => page ? [...previous, ...result.messages.filter((email) => !previous.some((item) => item.provider_message_id === email.provider_message_id))] : result.messages);
      setNextPage(result.next_page_token); setActiveQuery(search);
      if (!page) setSelected(null);
    } catch (error) { failure(error); }
    finally { if (mounted.current) setBusy(null); }
  }

  async function refreshStatus() {
    setBusy("status"); setNotice(null);
    try {
      const result = await request<Connection>(`${PREFIX}/status`);
      if (!mounted.current) return;
      setConnection(result);
      if (result.connected) await loadMessages("");
    } catch (error) { failure(error); }
    finally { if (mounted.current) setBusy(null); }
  }

  useEffect(() => {
    dialog.current?.showModal();
    void refreshStatus();
    return () => { mounted.current = false; popup.current?.close(); };
  }, []);

  useEffect(() => {
    if (!waiting) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const deadline = Date.now() + 10 * 60 * 1000;
    const poll = async () => {
      try {
        const result = await request<Connection>(`${PREFIX}/status`);
        if (cancelled) return;
        setConnection(result);
        if (result.connected) {
          setWaiting(false); popup.current?.close();
          void loadMessages(""); return;
        }
        if (result.error || Date.now() > deadline) {
          setWaiting(false);
          setNotice(result.error ? errors[result.error] ?? "Gmailに接続できませんでした。" : "接続を確認できませんでした。もう一度お試しください。");
          return;
        }
      } catch (error) {
        if (cancelled) return;
        failure(error); setWaiting(false); return;
      }
      timer = setTimeout(poll, 2000);
    };
    timer = setTimeout(poll, 1500);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [waiting]);

  async function connect() {
    setNotice(null);
    popup.current = window.open("about:blank", "_blank", "popup,width=540,height=720");
    if (!popup.current) { setNotice("ポップアップがブロックされました。このサイトのポップアップを許可してください。"); return; }
    popup.current.opener = null;
    setBusy("connect");
    try {
      const result = await request<{ authorization_url: string }>(`${PREFIX}/connect`, "POST");
      if (!mounted.current) { popup.current?.close(); return; }
      const destination = new URL(result.authorization_url);
      if (destination.origin !== "https://accounts.google.com") throw new Error("invalid_authorization_url");
      if (popup.current.closed) throw new Error("popup_closed");
      popup.current.location.href = destination.href;
      setWaiting(true);
    } catch (error) { popup.current?.close(); failure(error); }
    finally { if (mounted.current) setBusy(null); }
  }

  async function selectEmail(email: EmailLink) {
    setBusy("detail"); setNotice(null);
    try {
      const result = await request<MailDetail>(`${PREFIX}/messages/${encodeURIComponent(email.provider_message_id!)}`);
      if (mounted.current) setSelected(result);
    } catch (error) { failure(error); }
    finally { if (mounted.current) setBusy(null); }
  }

  async function disconnect() {
    if (!window.confirm("Gmail接続を解除しますか？紐づけたメールはメモに残ります。")) return;
    setBusy("disconnect"); setNotice(null);
    try {
      const result = await request<{ revoked: boolean }>(`${PREFIX}/disconnect`, "POST");
      if (!mounted.current) return;
      setConnection((previous) => previous ? { ...previous, connected: false } : previous);
      setMessages([]); setSelected(null); setNextPage(null);
      setNotice(result.revoked ? "Gmail接続を解除しました。" : "この端末から切断しました。Google側の権限解除は確認できませんでした。Googleアカウントの接続管理も確認してください。");
    } catch (error) { failure(error); }
    finally { if (mounted.current) setBusy(null); }
  }

  return <dialog ref={dialog} className={`gmail-dialog ${connection?.connected ? "" : "gmail-dialog-setup"}`} aria-labelledby="gmail-title" onCancel={(event) => { event.preventDefault(); onClose(); }}>
    <header className="gmail-dialog-heading"><div><Mail size={19} /><h2 id="gmail-title">Gmail</h2><span>{connection?.connected ? "接続済み" : "未接続"}</span></div>
      <button type="button" className="icon-button" aria-label="メール選択を閉じる" title="閉じる" onClick={onClose}><X size={18} /></button></header>
    {notice && <p className="gmail-notice" role="alert">{notice}</p>}
    {connection?.connected ? <>
      <form className="gmail-search" onSubmit={(event) => { event.preventDefault(); void loadMessages(query); }}>
        <label><Search size={16} /><input autoComplete="off" aria-label="Gmailを検索" placeholder="メールを検索" maxLength={500} value={query} onChange={(event) => setQuery(event.target.value)} disabled={!!busy} /></label>
        <button className="icon-button" title="Gmailを検索" aria-label="Gmailを検索する" disabled={!!busy}><Search size={17} /></button>
        <button type="button" className="icon-button" title="一覧を更新" aria-label="メール一覧を更新" disabled={!!busy} onClick={() => loadMessages(activeQuery)}><RefreshCw size={16} /></button>
      </form>
      <div className={`gmail-browser ${selected ? "has-selection" : ""}`} aria-busy={!!busy}>
        <div className="gmail-results" aria-label="Gmailのメール一覧">
          {messages.map((email) => <button key={email.provider_message_id} type="button" className="gmail-message" aria-pressed={selected?.email.provider_message_id === email.provider_message_id} disabled={!!busy} onClick={() => selectEmail(email)}>
            <span className="gmail-message-meta"><span>{email.sender || "送信者不明"}</span><time dateTime={email.received_at ?? undefined}>{dateLabel(email.received_at)}</time></span>
            <strong>{email.subject || "件名なし"}</strong><span className="gmail-snippet">{email.snippet}</span>
          </button>)}
          {!messages.length && <p className="gmail-empty">{busy ? "メールを読み込み中" : "メールはありません"}</p>}
          {nextPage && <button type="button" className="gmail-more" disabled={!!busy} onClick={() => loadMessages(activeQuery, nextPage)}><ChevronDown size={15} />さらに読み込む</button>}
        </div>
        <section className="gmail-preview" aria-label="メールのプレビュー">
          {selected ? <><button type="button" className="gmail-back" onClick={() => setSelected(null)}><ArrowLeft size={15} />メール一覧</button>
            <h3>{selected.email.subject || "件名なし"}</h3><p className="gmail-preview-sender">{selected.email.sender}</p>
            {(selected.truncated || selected.snippet_only) && <p className="gmail-limitation">{selected.truncated ? "長い本文のため、先頭20,000文字を表示しています。" : "本文を取得できないため、短い抜粋を表示しています。"}</p>}
            <p className="gmail-preview-body">{selected.email.snippet || "本文なし"}</p></> : <div className="gmail-empty"><Mail size={28} /><p>未選択</p></div>}
        </section>
      </div>
      <footer className="gmail-dialog-footer"><button type="button" className="gmail-disconnect" disabled={!!busy} onClick={disconnect}><Link2Off size={14} />接続を解除</button>
        <button type="button" className="save-button gmail-attach" disabled={!selected || !!busy} onClick={() => selected && onSelect(selected.email)}><Check size={15} />{replacing ? "関連メールを置き換える" : "メールを紐づける"}</button></footer>
    </> : <div className="gmail-connect-state">
      {busy === "status" ? <Loader2 className="spin" size={25} aria-label="接続状態を確認中" /> : <>
        <Mail size={32} /><h3>{connection?.configured ? "Gmailへの接続" : "Gmailの接続設定"}</h3>
        <p>{waiting ? "Googleでの許可を待っています" : connection?.configured ? "未接続" : "Google Cloudの認証設定が必要です"}</p>
        {connection?.configured && <button type="button" className="save-button" disabled={!!busy || waiting} onClick={connect}>{waiting || busy ? <Loader2 size={15} className="spin" /> : <ExternalLink size={15} />}Gmailに接続</button>}
        {waiting && <button type="button" className="gmail-disconnect" onClick={() => { setWaiting(false); popup.current?.close(); }}><X size={14} />接続待ちをやめる</button>}
        <div className="gmail-setup-actions"><a href={setupGuideUrl} target="_blank" rel="noreferrer">設定手順<ExternalLink size={13} /></a><button type="button" disabled={!!busy || waiting} onClick={refreshStatus}><RefreshCw size={14} />設定を再確認</button></div>
      </>}
    </div>}
    {busy && busy !== "status" && <span className="gmail-loading" role="status"><Loader2 size={14} className="spin" />{busy === "disconnect" ? "接続を解除中" : busy === "connect" ? "接続を準備中" : "読み込み中"}</span>}
  </dialog>;
}
