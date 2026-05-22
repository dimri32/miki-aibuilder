'use client';

import { useState, useCallback, useRef } from 'react';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { JobStatus, SubQueryResult, QueryConfig } from '@/lib/types';

// ── Markdown renderer ─────────────────────────────────────────────────────────

function MarkdownBody({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ children }) => (
          <h1 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#f1f5f9', marginBottom: '12px', marginTop: '20px', borderBottom: '1px solid #1e2535', paddingBottom: '8px' }}>{children}</h1>
        ),
        h2: ({ children }) => (
          <h2 style={{ fontSize: '1.05rem', fontWeight: 600, color: '#e2e8f0', marginBottom: '10px', marginTop: '18px' }}>{children}</h2>
        ),
        h3: ({ children }) => (
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#cbd5e1', marginBottom: '8px', marginTop: '14px' }}>{children}</h3>
        ),
        p: ({ children }) => (
          <p style={{ fontSize: '13px', lineHeight: '1.75', color: '#94a3b8', marginBottom: '12px' }}>{children}</p>
        ),
        ul: ({ children }) => (
          <ul style={{ paddingLeft: '20px', marginBottom: '12px', color: '#94a3b8' }}>{children}</ul>
        ),
        ol: ({ children }) => (
          <ol style={{ paddingLeft: '20px', marginBottom: '12px', color: '#94a3b8' }}>{children}</ol>
        ),
        li: ({ children }) => (
          <li style={{ fontSize: '13px', lineHeight: '1.7', marginBottom: '4px', color: '#94a3b8' }}>{children}</li>
        ),
        strong: ({ children }) => (
          <strong style={{ fontWeight: 600, color: '#e2e8f0' }}>{children}</strong>
        ),
        em: ({ children }) => (
          <em style={{ color: '#a5b4fc', fontStyle: 'italic' }}>{children}</em>
        ),
        code: ({ children, className }) => {
          const isBlock = !!className;
          return isBlock ? (
            <code style={{ display: 'block', background: '#0d1117', color: '#a5b4fc', padding: '16px', borderRadius: '8px', fontSize: '12px', fontFamily: 'JetBrains Mono, monospace', overflowX: 'auto', marginBottom: '12px', border: '1px solid #1e2535' }}>{children}</code>
          ) : (
            <code style={{ background: '#0d1117', color: '#a5b4fc', padding: '2px 6px', borderRadius: '4px', fontSize: '12px', fontFamily: 'JetBrains Mono, monospace' }}>{children}</code>
          );
        },
        pre: ({ children }) => (
          <pre style={{ background: '#0d1117', borderRadius: '8px', marginBottom: '12px', border: '1px solid #1e2535', overflow: 'auto' }}>{children}</pre>
        ),
        blockquote: ({ children }) => (
          <blockquote style={{ borderLeft: '3px solid #6366f1', paddingLeft: '16px', margin: '12px 0', color: '#64748b', fontStyle: 'italic' }}>{children}</blockquote>
        ),
        table: ({ children }) => (
          <div style={{ overflowX: 'auto', marginBottom: '12px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>{children}</table>
          </div>
        ),
        th: ({ children }) => (
          <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: '#e2e8f0', background: '#0d1117', borderBottom: '1px solid #2a3045' }}>{children}</th>
        ),
        td: ({ children }) => (
          <td style={{ padding: '8px 12px', color: '#94a3b8', borderBottom: '1px solid #1e2535' }}>{children}</td>
        ),
        hr: () => (
          <hr style={{ border: 'none', borderTop: '1px dashed #1e2535', margin: '16px 0' }} />
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

function ScoreBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    score >= 0.75 ? { bg: 'rgba(16,185,129,0.12)', text: '#34d399', border: 'rgba(16,185,129,0.25)' }
    : score >= 0.6 ? { bg: 'rgba(245,158,11,0.12)', text: '#fbbf24', border: 'rgba(245,158,11,0.25)' }
    :               { bg: 'rgba(100,116,139,0.12)', text: '#64748b', border: 'rgba(100,116,139,0.2)'  };

  return (
    <span className="shrink-0 text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded"
      style={{ background: color.bg, color: color.text, border: `1px solid ${color.border}` }}>
      {pct}%
    </span>
  );
}

const DEFAULT_CONFIG: QueryConfig = {
  tenant: 'ironclad',
  k: 10,
};

// ── helpers ───────────────────────────────────────────────────────────────────

function parseResults(
  primary: string,
  resultsMap: Record<string, string>,
  scoresMap: Record<string, number> = {},
): SubQueryResult[] {
  const prefix = primary + '~';
  return Object.entries(resultsMap)
    .map(([k, v]) => ({
      sub_query: k.startsWith(prefix) ? k.slice(prefix.length) : k,
      doc: v,
      priority: scoresMap[k] ?? 0,
    }))
    .sort((a, b) => b.priority - a.priority);
}

function downloadText(filename: string, content: string) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([content], { type: 'text/plain' }));
  a.download = filename;
  a.click();
}

function ts() {
  return new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
}

// ── sub-components ────────────────────────────────────────────────────────────

function Topbar({ onLogout }: { onLogout: () => void }) {
  return (
    <header className="h-14 flex items-center justify-between px-6 shrink-0"
      style={{ borderBottom: '1px solid var(--border)', background: 'var(--bg-sidebar)' }}>
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg flex items-center justify-center"
          style={{ background: 'linear-gradient(135deg,#6366f1,#4f46e5)' }}>
          <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round"
              d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
          </svg>
        </div>
        <div>
          <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>AI Builder</span>
          <span className="ml-2 text-xs px-2 py-0.5 rounded-full"
            style={{ background: '#1e2535', color: 'var(--text-secondary)' }}>Evaluator</span>
        </div>
      </div>

      <button onClick={onLogout}
        className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg transition-all"
        style={{ color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
        onMouseEnter={e => {
          e.currentTarget.style.borderColor = '#ef4444';
          e.currentTarget.style.color = '#f87171';
        }}
        onMouseLeave={e => {
          e.currentTarget.style.borderColor = 'var(--border)';
          e.currentTarget.style.color = 'var(--text-secondary)';
        }}>
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round"
            d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75" />
        </svg>
        Logout
      </button>
    </header>
  );
}

function ProgressBar({ progress, message }: { progress: number; message: string }) {
  return (
    <div className="space-y-3 p-6 rounded-xl fade-in"
      style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 animate-spin" style={{ color: 'var(--accent)' }} fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Processing Pipeline</span>
        </div>
        <span className="text-sm font-mono font-medium" style={{ color: 'var(--accent)' }}>{progress}%</span>
      </div>
      <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--bg-page)' }}>
        <div className="h-full rounded-full transition-all duration-500"
          style={{ width: `${progress}%`, background: 'linear-gradient(90deg,#6366f1,#818cf8)' }} />
      </div>
      {message && (
        <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{message}</p>
      )}
    </div>
  );
}

function QueryForm({
  config,
  setConfig,
  onSubmit,
  loading,
}: {
  config: QueryConfig;
  setConfig: (c: QueryConfig) => void;
  onSubmit: (query: string) => void;
  loading: boolean;
}) {
  const [query, setQuery] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const [kInput, setKInput] = useState(String(config.k));

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (query.trim()) onSubmit(query.trim());
  }

  const inputStyle = {
    background: 'var(--bg-page)',
    border: '1px solid var(--border)',
    color: 'var(--text-primary)',
    borderRadius: '8px',
    padding: '10px 14px',
    fontSize: '13px',
    outline: 'none',
    width: '100%',
  };

  return (
    <div className="fade-in max-w-3xl mx-auto">
      {/* Hero */}
      <div className="text-center mb-10 mt-6">
        <h2 className="text-3xl font-bold mb-2" style={{ color: 'var(--text-primary)' }}>
          Intelligence Query
        </h2>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          Enter a natural language query and the pipeline will retrieve the most relevant insights.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Query input */}
        <div className="rounded-xl overflow-hidden"
          style={{ border: '1px solid var(--border)', background: 'var(--bg-card)' }}>
          <textarea
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="e.g. Top 3 reasons reps win against DocuSign CLM in the last 12 months…"
            rows={5}
            disabled={loading}
            className="w-full resize-none p-5 text-sm transition-all outline-none"
            style={{
              background: 'transparent',
              color: 'var(--text-primary)',
              caretColor: 'var(--accent)',
            }}
            onKeyDown={e => {
              if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') handleSubmit(e as never);
            }}
          />
          <div className="flex items-center justify-between px-5 py-3"
            style={{ borderTop: '1px solid var(--border)' }}>
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
              ⌘ + Enter to run
            </span>
            <button type="submit" disabled={loading || !query.trim()}
              className="flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-semibold transition-all"
              style={{
                background: loading || !query.trim() ? '#1e2535' : 'var(--accent)',
                color: loading || !query.trim() ? 'var(--text-muted)' : '#fff',
                cursor: loading || !query.trim() ? 'not-allowed' : 'pointer',
              }}>
              {loading ? (
                <>
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Running…
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 010 1.972l-11.54 6.347a1.125 1.125 0 01-1.667-.986V5.653z" />
                  </svg>
                  Run Query
                </>
              )}
            </button>
          </div>
        </div>

        {/* Settings toggle */}
        <button type="button" onClick={() => setShowSettings(s => !s)}
          className="flex items-center gap-1.5 text-xs transition-colors"
          style={{ color: 'var(--text-muted)' }}
          onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-secondary)')}
          onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}>
          <svg className={`w-3.5 h-3.5 transition-transform ${showSettings ? 'rotate-90' : ''}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
          </svg>
          {showSettings ? 'Hide' : 'Show'} connection settings
        </button>

        {showSettings && (
          <div className="grid grid-cols-2 gap-3 fade-in">
            <div>
              <label className="block text-xs mb-1.5 uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Tenant</label>
              <input type="text" value={config.tenant} onChange={e => setConfig({ ...config, tenant: e.target.value })}
                style={inputStyle}
                onFocus={e => (e.currentTarget.style.borderColor = 'var(--border-focus)')}
                onBlur={e => (e.currentTarget.style.borderColor = 'var(--border)')} />
            </div>
            <div>
              <label className="block text-xs mb-1.5 uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Top K</label>
              <input type="text" inputMode="numeric" pattern="[0-9]*"
                value={kInput}
                onChange={e => {
                  const raw = e.target.value.replace(/[^0-9]/g, '');
                  setKInput(raw);
                  const n = parseInt(raw);
                  if (!isNaN(n) && n >= 1 && n <= 100) setConfig({ ...config, k: n });
                }}
                onFocus={e => (e.currentTarget.style.borderColor = 'var(--border-focus)')}
                onBlur={e => {
                  e.currentTarget.style.borderColor = 'var(--border)';
                  const n = parseInt(kInput);
                  if (isNaN(n) || n < 1) setKInput(String(config.k));
                }}
                style={inputStyle} />
            </div>
          </div>
        )}
      </form>
    </div>
  );
}

function ResultsView({
  rows,
  durationMs,
  onReset,
}: {
  rows: SubQueryResult[];
  durationMs: number;
  onReset: () => void;
}) {
  const [selected, setSelected] = useState(0);
  const [showModal, setShowModal] = useState(false);

  const current = rows[selected];
  const safeName = (s: string) => s.slice(0, 40).replace(/\s+/g, '_');

  const fullReport = rows.map(r => `## ${r.sub_query}\n\n${r.doc}`).join('\n\n---\n\n');
  const allDocs = rows.map(r => r.doc).join('\n\n---\n\n');

  return (
    <div className="flex h-full fade-in overflow-hidden">
      {/* Sidebar */}
      <aside className="w-72 shrink-0 flex flex-col overflow-hidden"
        style={{ borderRight: '1px solid var(--border)', background: 'var(--bg-sidebar)' }}>

        {/* Sidebar header */}
        <div className="px-4 py-3 flex items-center justify-between shrink-0"
          style={{ borderBottom: '1px solid var(--border)' }}>
          <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
            Sub-Queries
          </span>
          <span className="text-xs px-2 py-0.5 rounded-full font-mono"
            style={{ background: '#1e2535', color: 'var(--accent)' }}>
            {rows.length}
          </span>
        </div>

        {/* Query list */}
        <nav className="flex-1 overflow-y-auto py-2 space-y-0.5 px-2">
          {rows.map((r, i) => (
            <button key={i} onClick={() => setSelected(i)}
              className="w-full text-left px-3 py-2.5 rounded-lg text-xs transition-all"
              style={{
                background: selected === i ? 'rgba(99,102,241,0.12)' : 'transparent',
                borderLeft: selected === i ? '2px solid var(--accent)' : '2px solid transparent',
              }}
              onMouseEnter={e => {
                if (selected !== i) e.currentTarget.style.background = 'var(--bg-card-hover)';
              }}
              onMouseLeave={e => {
                if (selected !== i) e.currentTarget.style.background = 'transparent';
              }}>
              <div className="flex items-start justify-between gap-2">
                <span className="line-clamp-2 leading-relaxed flex-1"
                  style={{ color: selected === i ? '#a5b4fc' : 'var(--text-secondary)' }}>
                  {r.sub_query}
                </span>
                <ScoreBadge score={r.priority} />
              </div>
            </button>
          ))}
        </nav>

        {/* Bottom actions */}
        <div className="p-3 space-y-2 shrink-0" style={{ borderTop: '1px solid var(--border)' }}>
          <button onClick={() => setShowModal(true)}
            className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-all"
            style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
            onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--accent)')}
            onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border)')}>
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round"
                d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Preview All
          </button>
          <button onClick={onReset}
            className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-all"
            style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--text-muted)' }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-secondary)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}>
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
            </svg>
            New Search
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Content header */}
        <div className="flex items-center justify-between px-6 py-3 shrink-0"
          style={{ borderBottom: '1px solid var(--border)' }}>
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-2 h-2 rounded-full" style={{ background: '#10b981' }} />
            <span className="text-sm font-medium truncate" style={{ color: 'var(--text-primary)' }}>
              {current?.sub_query}
            </span>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <span className="text-xs px-2 py-1 rounded-md font-mono"
              style={{ background: '#0d1117', color: '#10b981', border: '1px solid rgba(16,185,129,0.2)' }}>
              ⏱ {(durationMs / 1000).toFixed(2)}s
            </span>
          </div>
        </div>

        {/* Document body */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="rounded-xl p-6 prose-dark"
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              minHeight: '300px',
            }}>
            {current?.doc
              ? <MarkdownBody content={current.doc} />
              : <p style={{ color: 'var(--text-muted)', fontSize: '13px' }}>No content available.</p>
            }
          </div>
        </div>

        {/* Export bar */}
        <div className="px-6 py-4 shrink-0"
          style={{ borderTop: '1px solid var(--border)' }}>
          <div className="flex items-center gap-2">
            <span className="text-xs uppercase tracking-wider mr-2" style={{ color: 'var(--text-muted)' }}>
              Export
            </span>
            <ExportBtn
              label="All Docs"
              onClick={() => downloadText(`all_docs_${ts()}.txt`, allDocs)}
            />
            <ExportBtn
              label="Full Report"
              onClick={() => downloadText(`report_${ts()}.txt`, fullReport)}
            />
            <ExportBtn
              label="This Selection"
              accent
              onClick={() => downloadText(`${safeName(current.sub_query)}_${ts()}.txt`, `Query: ${current.sub_query}\n\n${current.doc}`)}
            />
          </div>
        </div>
      </main>

      {/* Preview Modal */}
      {showModal && (
        <PreviewModal rows={rows} onClose={() => setShowModal(false)} />
      )}
    </div>
  );
}

function ExportBtn({
  label,
  onClick,
  accent = false,
}: {
  label: string;
  onClick: () => void;
  accent?: boolean;
}) {
  return (
    <button onClick={onClick}
      className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
      style={{
        background: accent ? 'rgba(99,102,241,0.12)' : 'var(--bg-card)',
        border: `1px solid ${accent ? 'rgba(99,102,241,0.3)' : 'var(--border)'}`,
        color: accent ? '#a5b4fc' : 'var(--text-secondary)',
      }}
      onMouseEnter={e => (e.currentTarget.style.opacity = '0.8')}
      onMouseLeave={e => (e.currentTarget.style.opacity = '1')}>
      ↓ {label}
    </button>
  );
}

function PreviewModal({ rows, onClose }: { rows: SubQueryResult[]; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6"
      style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)' }}>
      <div className="w-full max-w-3xl max-h-[80vh] flex flex-col rounded-2xl fade-in"
        style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}>

        {/* Modal header */}
        <div className="flex items-center justify-between px-6 py-4 shrink-0"
          style={{ borderBottom: '1px solid var(--border)' }}>
          <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
            Full Report Preview
          </span>
          <button onClick={onClose}
            className="w-8 h-8 rounded-lg flex items-center justify-center transition-all"
            style={{ background: 'var(--bg-sidebar)', color: 'var(--text-muted)' }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-primary)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Modal body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {rows.map((r, i) => (
            <div key={i}>
              <h3 className="text-sm font-semibold mb-3" style={{ color: '#a5b4fc' }}>{r.sub_query}</h3>
              <div className="rounded-lg p-4"
                style={{ background: 'var(--bg-page)', border: '1px solid var(--border)' }}>
                <MarkdownBody content={r.doc} />
              </div>
              {i < rows.length - 1 && (
                <div className="mt-6" style={{ borderBottom: '1px dashed var(--border)' }} />
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── main page ─────────────────────────────────────────────────────────────────

export default function DashboardPage() {

  const [config, setConfig] = useState<QueryConfig>(DEFAULT_CONFIG);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState('');
  const [rows, setRows] = useState<SubQueryResult[] | null>(null);
  const [primaryQuery, setPrimaryQuery] = useState('');
  const [durationMs, setDurationMs] = useState(0);
  const [error, setError] = useState('');
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  async function handleLogout() {
    await fetch('/api/auth', { method: 'DELETE' });
    window.location.href = '/';  // full reload so middleware re-checks the cleared cookie
  }

  const handleReset = useCallback(() => {
    if (pollRef.current) clearTimeout(pollRef.current);
    setRows(null);
    setLoading(false);
    setProgress(0);
    setMessage('');
    setError('');
  }, []);

  async function poll(jobId: string, t0: number) {
    try {
      const res = await fetch(`/api/job?id=${jobId}`);
      const job: JobStatus = await res.json();

      setProgress(job.progress ?? 0);
      setMessage(job.message ?? '');

      if (job.status === 'completed') {
        const elapsed = Date.now() - t0;
        setDurationMs(elapsed);
        setRows(parseResults(primaryQuery, job.results_map ?? {}, job.scores_map ?? {}));
        setLoading(false);
        return;
      }

      if (job.status === 'failed') {
        setError(job.error ?? 'Job failed');
        setLoading(false);
        return;
      }

      pollRef.current = setTimeout(() => poll(jobId, t0), 3000);
    } catch (e: unknown) {
      setError(String(e));
      setLoading(false);
    }
  }

  async function handleSubmit(query: string) {
    handleReset();
    setLoading(true);
    setPrimaryQuery(query);

    try {
      const res = await fetch('/api/job', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, k: config.k, tenant: config.tenant }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error ?? 'Failed to start job');
      }

      const { job_id } = await res.json();
      poll(job_id, Date.now());
    } catch (e: unknown) {
      setError(String(e));
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden" style={{ background: 'var(--bg-page)' }}>
      <Topbar onLogout={handleLogout} />

      <div className="flex-1 overflow-hidden">
        {rows ? (
          <ResultsView
            rows={rows}
            durationMs={durationMs}
            onReset={handleReset}
          />
        ) : (
          <div className="h-full overflow-y-auto px-6 py-8">
            <QueryForm
              config={config}
              setConfig={setConfig}
              onSubmit={handleSubmit}
              loading={loading}
            />

            {/* Progress / Error */}
            {loading && (
              <div className="max-w-3xl mx-auto mt-8">
                <ProgressBar progress={progress} message={message} />
              </div>
            )}
            {error && (
              <div className="max-w-3xl mx-auto mt-6 rounded-xl px-5 py-4 text-sm fade-in"
                style={{
                  background: 'rgba(239,68,68,0.08)',
                  border: '1px solid rgba(239,68,68,0.2)',
                  color: '#f87171',
                }}>
                <strong>Error:</strong> {error}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
