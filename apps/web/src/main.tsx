import React, { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowDownToLine, CalendarDays, Check, ChevronDown, ChevronRight, Clock3,
  FileText, ListFilter, Loader2, Mail, MapPin, Menu, NotebookPen, Pencil,
  Plus, Search, Users, X,
} from "lucide-react";
import "./styles.css";
import { EmailLink, request } from "./api";
import { GmailPicker } from "./GmailPicker";

type ExtractedContext = {
  summary: string;
  event_datetime: string | null;
  location: string | null;
  deadline: string | null;
  people: string[];
  tasks: string[];
  review_status: "ai_generated" | "human_reviewed";
};
type WorkNote = {
  id: string; title: string; memo: string; email: EmailLink | null;
  context: ExtractedContext; updated_at: string;
};
type Document = Omit<WorkNote, "context"> & {
  context: ExtractedContext | null; saved: boolean; dirty: boolean;
};
const emptyEmail: EmailLink = { provider: "gmail", subject: "", sender: "", snippet: "" };
const example: Document = {
  id: "draft-example", title: "9/17 取引先A 打ち合わせ", saved: false, dirty: true,
  updated_at: new Date().toISOString(), context: null,
  email: {
    provider: "gmail", subject: "9/17 取引先A打ち合わせについて", sender: "contact@example.invalid",
    snippet: "9/17 14:00からオンラインで取引先Aとの打ち合わせです。\nSaaS管理高度化の現状課題について整理をお願いします。\n前日までに資料ドラフトを共有してください。",
  },
  memo: "担当Aさん参加\n前回資料確認\nSaaS棚卸しのところ聞く\n業務ツールの利用状況も確認\n明日午前中ドラフト作る",
};

function IconButton({ label, children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { label: string }) {
  return <button type="button" className="icon-button" aria-label={label} title={label} {...props}>{children}</button>;
}

function GrowingTextarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const ref = useRef<HTMLTextAreaElement>(null);
  useLayoutEffect(() => {
    const element = ref.current;
    if (!element) return;
    const resize = () => { element.style.height = "0px"; element.style.height = `${element.scrollHeight}px`; };
    resize();
    window.addEventListener("resize", resize);
    return () => window.removeEventListener("resize", resize);
  }, [props.value]);
  return <textarea ref={ref} rows={1} {...props} />;
}

function App() {
  const [documents, setDocuments] = useState<Document[]>([example]);
  const [selectedId, setSelectedId] = useState(example.id);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<"all" | "reviewed">("all");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [busy, setBusy] = useState<"save" | "extract" | "review" | null>(null);
  const [notice, setNotice] = useState<{ text: string; error: boolean } | null>(null);
  const [loading, setLoading] = useState(true);
  const interacted = useRef(false);
  const searchInput = useRef<HTMLInputElement>(null);
  const current = documents.find((note) => note.id === selectedId) ?? documents[0];

  useEffect(() => {
    let active = true;
    request<WorkNote[]>("/api/v1/notes").then((notes) => {
      if (!active || notes.length === 0) return;
      const saved = notes.map((note) => ({ ...note, saved: true, dirty: false }));
      setDocuments((existing) => interacted.current
        ? [...existing, ...saved.filter((note) => !existing.some((item) => item.id === note.id))]
        : saved);
      if (!interacted.current) setSelectedId(notes[0].id);
    }).catch(() => {
      if (active) setNotice({ text: "保存済みのメモを読み込めませんでした。", error: true });
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    const beforeUnload = (event: BeforeUnloadEvent) => {
      if (!interacted.current || !documents.some((note) => note.dirty)) return;
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", beforeUnload);
    return () => window.removeEventListener("beforeunload", beforeUnload);
  }, [documents]);

  useEffect(() => {
    if (!sidebarOpen) return;
    searchInput.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setSidebarOpen(false);
    };
    const onResize = () => { if (window.innerWidth > 680) setSidebarOpen(false); };
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("resize", onResize);
    };
  }, [sidebarOpen]);

  function updateCurrent(patch: Partial<Document>) {
    interacted.current = true;
    setNotice(null);
    setDocuments((notes) => notes.map((note) => note.id === current.id
      ? { ...note, ...patch, dirty: true, context: null } : note));
  }

  function newNote() {
    interacted.current = true;
    const note: Document = {
      id: `draft-${crypto.randomUUID()}`, title: "", memo: "", email: null,
      context: null, saved: false, dirty: true, updated_at: new Date().toISOString(),
    };
    setDocuments((notes) => [note, ...notes]);
    setSelectedId(note.id);
    setFilter("all");
    setQuery("");
    setSidebarOpen(false);
    setNotice(null);
  }

  async function perform(action: "save" | "extract" | "review") {
    if (busy) return;
    interacted.current = true;
    const id = current.id;
    setBusy(action);
    setNotice(null);
    try {
      if (action === "extract") {
        const context = await request<ExtractedContext>("/api/v1/extract", "POST", { memo: current.memo, email: current.email });
        setDocuments((notes) => notes.map((note) => note.id === id ? { ...note, context, dirty: true } : note));
      } else {
        const result = action === "review"
          ? await request<WorkNote>(`/api/v1/notes/${id}/review`, "POST")
          : await request<WorkNote>(current.saved ? `/api/v1/notes/${id}` : "/api/v1/notes", current.saved ? "PUT" : "POST", {
              title: current.title.trim() || "無題のメモ", memo: current.memo, email: current.email,
            });
        setDocuments((notes) => notes.map((note) => note.id === id ? { ...result, saved: true, dirty: false } : note));
        setSelectedId((selected) => selected === id ? result.id : selected);
        setNotice({ text: action === "review" ? "確認済みにしました。" : "保存しました。", error: false });
      }
    } catch {
      setNotice({ text: action === "save" ? "保存できませんでした。内容はこの画面に残っています。"
        : action === "review" ? "確認状態を更新できませんでした。"
        : "整理できませんでした。もう一度お試しください。", error: true });
    } finally { setBusy(null); }
  }

  const visibleNotes = documents.filter((note) => {
    const matches = `${note.title} ${note.memo} ${note.email?.subject ?? ""}`.toLowerCase().includes(query.toLowerCase());
    return matches && (filter === "all" || note.context?.review_status === "human_reviewed");
  });
  const reviewed = current.context?.review_status === "human_reviewed";

  return <div className="app-shell">
    {sidebarOpen && <button className="sidebar-backdrop" aria-label="メモ一覧を閉じる" onClick={() => setSidebarOpen(false)} />}
    <aside className={`sidebar ${sidebarOpen ? "is-open" : ""}`} aria-label="メモ一覧">
      <div className="brand"><NotebookPen size={21} strokeWidth={1.6} /><h1>ContextPad</h1><span className="sidebar-close"><IconButton label="メモ一覧を閉じる" onClick={() => setSidebarOpen(false)}><X size={18} /></IconButton></span></div>
      <div className="library-heading"><h2>メモ</h2><IconButton label="新しいメモ" onClick={newNote} disabled={!!busy}><Plus size={19} /></IconButton></div>
      <label className="search-field"><Search size={15} /><input ref={searchInput} aria-label="メモを検索" placeholder="メモを検索" value={query} onChange={(event) => setQuery(event.target.value)} />
        {query && <IconButton label="検索をクリア" onClick={() => setQuery("")}><X size={13} /></IconButton>}</label>
      <div className="list-tabs" role="group" aria-label="メモの絞り込み">
        <button type="button" aria-pressed={filter === "all"} onClick={() => setFilter("all")}>すべて<span>{documents.length}</span></button>
        <button type="button" aria-pressed={filter === "reviewed"} onClick={() => setFilter("reviewed")}>確認済み</button>
      </div>
      <nav className="note-list" aria-label="メモを選択">
        {visibleNotes.map((note) => <button type="button" key={note.id} className={`note-item ${note.id === current.id ? "selected" : ""}`}
          aria-current={note.id === current.id ? "page" : undefined} disabled={!!busy}
          onClick={() => { interacted.current = true; setSelectedId(note.id); setSidebarOpen(false); setNotice(null); }}>
          <span className="note-item-title"><FileText size={15} /><span>{note.title || "無題のメモ"}</span></span>
          <span className="note-preview">{note.memo.split("\n").filter(Boolean).slice(0, 2).join(" / ") || "空のメモ"}</span>
          <span className="note-meta"><span>{note.dirty ? "下書き" : new Intl.DateTimeFormat("ja-JP", { month: "numeric", day: "numeric" }).format(new Date(note.updated_at))}</span>
            {note.email && <Mail size={12} aria-label="関連メールあり" />}{note.context?.review_status === "human_reviewed" && <Check size={12} aria-label="確認済み" />}</span>
        </button>)}
        {visibleNotes.length === 0 && <p className="list-empty">{query ? "一致するメモはありません" : "確認済みのメモはありません"}</p>}
      </nav>
      <footer className="sidebar-footer"><span className="workspace-dot" />個人のワークスペース{loading && <Loader2 size={13} className="spin" aria-label="読み込み中" />}</footer>
    </aside>
    <main className="workspace">
      <header className="toolbar">
        <div className="breadcrumb"><span className="mobile-menu"><IconButton label="メモ一覧を開く" onClick={() => setSidebarOpen(true)}><Menu size={18} /></IconButton></span><span>メモ</span><ChevronRight size={13} /><span>{current.saved ? "保存済み" : "下書き"}</span></div>
        <div className="toolbar-actions"><span className={`save-status ${current.dirty ? "unsaved" : ""}`}>{current.dirty ? "未保存" : <><Check size={12} />保存済み</>}</span>
          <button className="save-button" type="button" disabled={!!busy || !current.memo.trim() || !current.dirty} onClick={() => perform("save")}>
            {busy === "save" ? <Loader2 size={15} className="spin" /> : <ArrowDownToLine size={15} />}<span>{busy === "save" ? "保存中" : "保存"}</span></button>
        </div>
      </header>
      {notice && <div className={`notice ${notice.error ? "error" : ""}`} role={notice.error ? "alert" : "status"}><span>{notice.text}</span><IconButton label="通知を閉じる" onClick={() => setNotice(null)}><X size={14} /></IconButton></div>}
      <div className="workbench">
        <article className="document">
          <div className="document-heading"><span className="document-kind"><FileText size={14} />作業メモ</span><span className="document-state">{reviewed ? "確認済み" : "編集中"}</span></div>
          <GrowingTextarea className="document-title" aria-label="メモの件名" placeholder="無題のメモ" value={current.title} readOnly={!!busy} onChange={(event) => updateCurrent({ title: event.target.value })} />
          <EmailSection key={current.id} email={current.email} disabled={!!busy} onChange={(email) => updateCurrent({ email })} />
          <section className="memo-section" aria-label="メモ本文"><div className="section-caption"><h2>メモ</h2><Pencil size={13} /></div>
            <GrowingTextarea className="memo-editor" aria-label="雑メモ" placeholder="ここにメモを書く…" value={current.memo} readOnly={!!busy} onChange={(event) => updateCurrent({ memo: event.target.value })} /></section>
          <footer className="document-footer"><span>{current.memo.length.toLocaleString()}文字</span><span>{current.email ? "メール 1件" : "関連メールなし"}</span></footer>
        </article>
        <aside className="inspector" aria-label="整理結果">
          <header className="inspector-heading"><h2>整理結果</h2><button type="button" className="organize-button" disabled={!!busy || !current.memo.trim()} onClick={() => perform("extract")}>
            {busy === "extract" ? <Loader2 size={14} className="spin" /> : <ListFilter size={14} />} {busy === "extract" ? "整理中" : "整理する"}</button></header>
          <div className={`review-status ${reviewed ? "reviewed" : ""}`}><span />{current.context ? reviewed ? "確認済み" : "内容の確認待ち" : "未整理"}</div>
          <section className="detail-section"><h3>予定と期限</h3><dl className="details-list">
            <Detail label="日時" icon={<CalendarDays />} value={current.context?.event_datetime} />
            <Detail label="場所" icon={<MapPin />} value={current.context?.location} />
            <Detail label="期限" icon={<Clock3 />} value={current.context?.deadline} accent />
            <Detail label="関係者" icon={<Users />} value={current.context?.people.join("、")} /></dl></section>
          <section className="detail-section"><div className="section-caption"><h3>やること</h3><span>{current.context?.tasks.length ?? 0}</span></div>
            {current.context?.tasks.length ? <ol className="task-list">{current.context.tasks.map((task, index) => <li key={`${index}-${task}`}><span className="task-number">{String(index + 1).padStart(2, "0")}</span><span>{task}</span></li>)}</ol>
              : <p className="empty-copy">タスクはまだありません</p>}</section>
          {current.context && <section className="detail-section summary-section"><h3>要点</h3><p>{current.context.summary}</p></section>}
          {current.context && <div className="review-action"><button type="button" className="review-button" onClick={() => perform("review")}
            disabled={!!busy || current.dirty || !current.saved || reviewed} title={current.dirty ? "メモを保存すると確認済みにできます" : undefined}>
            {busy === "review" ? <Loader2 size={14} className="spin" /> : <Check size={14} />}{reviewed ? "確認済み" : "確認済みにする"}</button>
            {current.dirty && <p>未保存の変更があります</p>}</div>}
        </aside>
      </div>
    </main>
  </div>;
}

function EmailSection({ email, disabled, onChange }: { email: EmailLink | null; disabled: boolean; onChange: (email: EmailLink | null) => void }) {
  const [editing, setEditing] = useState(false);
  const [expanded, setExpanded] = useState(true);
  const gmailPicker = <GmailPicker disabled={disabled} replacing={!!email} onSelect={(selected) => { onChange(selected); setEditing(false); setExpanded(true); }} />;
  if (!email) return <div className="email-add-actions">{gmailPicker}<button type="button" className="link-email-button" disabled={disabled} onClick={() => { onChange({ ...emptyEmail }); setEditing(true); }}><Plus size={14} />メールを手入力</button></div>;
  return <section className="email-section" aria-label="関連メール">
    <div className="email-heading"><button type="button" className="email-toggle" aria-expanded={expanded} onClick={() => setExpanded(!expanded)}><Mail size={15} /><span>関連メール</span><ChevronDown size={13} className={expanded ? "" : "collapsed"} /></button>
      <div className="email-tools">{gmailPicker}<IconButton label={editing ? "メールの編集を完了" : "関連メールを編集"} disabled={disabled} onClick={() => { setExpanded(true); setEditing(!editing); }}>{editing ? <Check size={14} /> : <Pencil size={14} />}</IconButton>
        {editing && <IconButton label="メールの紐づけを解除" disabled={disabled} onClick={() => onChange(null)}><X size={14} /></IconButton>}</div></div>
    {expanded && (editing ? <div className="email-edit-fields">
      <label>メールの件名<input value={email.subject} disabled={disabled} onChange={(event) => onChange({ ...email, subject: event.target.value })} /></label>
      <label>送信者<input value={email.sender} disabled={disabled} onChange={(event) => onChange({ ...email, sender: event.target.value })} /></label>
      <label>メール本文<textarea rows={4} value={email.snippet} disabled={disabled} onChange={(event) => onChange({ ...email, snippet: event.target.value })} /></label>
    </div> : <div className="email-content"><h3>{email.subject || "件名なし"}</h3><p className="email-sender">{email.sender || "送信者未設定"}</p><p className="email-body">{email.snippet || "本文なし"}</p></div>)}
  </section>;
}

function Detail({ label, value, icon, accent = false }: { label: string; value?: string | null; icon: React.ReactNode; accent?: boolean }) {
  return <div className="detail-row"><dt>{icon}<span>{label}</span></dt><dd className={!value ? "not-set" : accent ? "deadline-value" : ""}>{value || "未整理"}</dd></div>;
}

createRoot(document.getElementById("root")!).render(<App />);
