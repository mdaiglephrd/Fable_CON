/*
 * CON WIKI (/wiki, /wiki/:articleId) — the practitioner's encyclopedia:
 * grouped article index with the pending-edit banner, and the article
 * reader (segment-format body, "on this page" TOC, related authorities,
 * revision timeline) with the suggested-edit review modal (approve/reject
 * via the wiki API; in-memory in fixture mode). From the comp's
 * <!-- CON WIKI --> and <!-- WIKI SUGGESTED EDIT REVIEW --> sections.
 */
import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { Breadcrumb } from '../components/Breadcrumb';
import { PageHeader } from '../components/PageHeader';
import { useToast } from '../components/Toast';
import * as api from '../lib/api';
import { renderSegs } from '../lib/segments';
import type { WikiArticleDetail, WikiIndex, WikiPendingEdit, WikiRelatedLink } from '../lib/types';

function relatedTo(link: WikiRelatedLink): string {
  switch (link.kind) {
    case 'statute':
      return `/statute/${link.target}`;
    case 'topic':
      return `/topics/${link.target}`;
    case 'wiki':
      return `/wiki/${link.target}`;
    case 'search':
      return `/results?q=${encodeURIComponent(link.target)}&scope=all`;
    default:
      return link.target; // tool: an app route
  }
}

// ---------------------------------------------------------------------------
// Review modal (suggested wiki update)
// ---------------------------------------------------------------------------

function ReviewModal({
  pending,
  articleTitle,
  onClose,
  onReviewed,
}: {
  pending: WikiPendingEdit;
  articleTitle: string;
  onClose: () => void;
  onReviewed: (action: 'approve' | 'reject') => void;
}) {
  return (
    <div
      style={{ position: 'fixed', inset: 0, background: 'rgba(2,6,23,.65)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}
      onClick={onClose}
    >
      <div
        className="card"
        style={{ borderRadius: 5, boxShadow: '0 8px 40px rgba(0,0,0,.5)', width: '100%', maxWidth: 640, maxHeight: '82vh', display: 'flex', flexDirection: 'column' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '18px 24px', borderBottom: '1px solid var(--surface2)', flexShrink: 0 }}>
          <div>
            <div className="label-upper" style={{ color: 'var(--accent-text)', fontSize: 10.5, letterSpacing: 1.2, marginBottom: 4 }}>
              Suggested Wiki update
            </div>
            <h3 className="serif" style={{ fontSize: 17, fontWeight: 600, color: 'var(--text)', margin: 0 }}>{articleTitle}</h3>
          </div>
          <button onClick={onClose} style={{ color: 'var(--text3)', fontSize: 18, lineHeight: 1 }} aria-label="Close review">
            ×
          </button>
        </div>
        <div style={{ padding: '20px 24px', overflowY: 'auto', flex: 1 }}>
          {pending.sourceLabel && (
            <div style={{ fontSize: 11.5, color: 'var(--text2)', marginBottom: 16 }}>
              Generated from completed research: <strong style={{ color: 'var(--text)' }}>{pending.sourceLabel}</strong>
            </div>
          )}
          <div className="label-upper" style={{ fontSize: 10, letterSpacing: 1, marginBottom: 8 }}>Proposed addition</div>
          <div style={{ background: 'rgba(16,185,129,.08)', border: '1px solid rgba(16,185,129,.3)', borderRadius: 4, padding: '14px 16px' }}>
            <div className="serif" style={{ fontSize: 15, fontWeight: 600, color: 'var(--text)', marginBottom: 8 }}>+ {pending.newHeading}</div>
            <div style={{ fontSize: 13.5, color: 'var(--text2)', lineHeight: 1.65 }}>+ {pending.newText}</div>
          </div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, padding: '16px 24px', borderTop: '1px solid var(--surface2)', flexShrink: 0 }}>
          <button className="btn-outline" onClick={() => onReviewed('reject')}>
            Discard
          </button>
          <button
            onClick={() => onReviewed('approve')}
            style={{ padding: '9px 16px', background: '#10B981', color: '#052E1F', borderRadius: 3, fontSize: 13, fontWeight: 600 }}
          >
            Approve &amp; publish
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Index
// ---------------------------------------------------------------------------

function WikiIndexView({ index, onOpenReview }: { index: WikiIndex; onOpenReview: () => void }) {
  return (
    <>
      {index.pendingArticleId && (
        <div
          style={{
            background: 'rgba(245,158,11,.1)',
            borderBottom: '1px solid rgba(245,158,11,.35)',
            padding: '10px 32px',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            fontSize: 12.5,
            color: '#B45309',
          }}
        >
          <svg width="13" height="13" viewBox="0 0 16 16" style={{ flexShrink: 0 }} aria-hidden>
            <path d="M8 2 L15 14 L1 14 Z M8 6 L8 10 M8 12 L8 12.3" stroke="currentColor" strokeWidth={1.4} fill="none" strokeLinejoin="round" />
          </svg>
          <span>
            <strong>1 suggested update</strong> from a completed research project is pending review — “{index.pendingArticleTitle}”
          </span>
          <button onClick={onOpenReview} style={{ marginLeft: 'auto', color: '#B45309', fontWeight: 600, textDecoration: 'underline' }}>
            Review diff →
          </button>
        </div>
      )}
      <PageHeader
        crumbs={[{ label: 'Home', to: '/' }, { label: 'Knowledge Base', to: '/kb' }, { label: 'CON Wiki' }]}
        title="CON Wiki"
        titleSize={26}
        sub="A practitioner's encyclopedia of Georgia Certificate of Need law. Each article links to the controlling statutes, key numbers, and leading decisions."
      />
      <div style={{ padding: '32px 32px 60px' }}>
        <div className="list-card" style={{ maxWidth: 760 }}>
          <div style={{ padding: '16px 26px', borderBottom: '1px solid var(--surface2)', fontSize: 11, fontWeight: 700, color: 'var(--text)', textTransform: 'uppercase', letterSpacing: 0.8 }}>
            Contents
          </div>
          {index.groups.map((g, gi) => (
            <div key={g.group} style={{ padding: '18px 26px 6px' }}>
              <div className="serif" style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)', marginBottom: 8 }}>
                {gi + 1}&nbsp;&nbsp;{g.group}
              </div>
              {g.articles.map((a, ai) => (
                <Link
                  key={a.id}
                  to={`/wiki/${a.id}`}
                  className="list-row"
                  style={{ display: 'flex', alignItems: 'baseline', gap: 10, width: '100%', padding: '7px 0 7px 22px' }}
                >
                  <span className="mono" style={{ fontSize: 11.5, color: 'var(--text3)', flexShrink: 0 }}>
                    {gi + 1}.{ai + 1}
                  </span>
                  <span style={{ flex: 1, fontSize: 13.5, color: 'var(--accent-text)' }}>{a.title}</span>
                  {a.readTime && <span style={{ flexShrink: 0, fontSize: 10.5, color: 'var(--text3)' }}>{a.readTime} read</span>}
                  {a.justUpdated && (
                    <span style={{ flexShrink: 0, color: '#10B981', fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.4, fontSize: 9.5 }}>
                      ● Updated
                    </span>
                  )}
                </Link>
              ))}
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Article
// ---------------------------------------------------------------------------

function WikiArticleView({ article, onOpenReview }: { article: WikiArticleDetail; onOpenReview: () => void }) {
  const headings = (article.body ?? []).filter((b) => b.h).map((b) => b.h as string);
  return (
    <>
      {article.pending && (
        <div
          style={{
            background: 'rgba(245,158,11,.1)',
            borderBottom: '1px solid rgba(245,158,11,.35)',
            padding: '10px 32px',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            fontSize: 12.5,
            color: '#B45309',
          }}
        >
          <svg width="13" height="13" viewBox="0 0 16 16" style={{ flexShrink: 0 }} aria-hidden>
            <path d="M8 2 L15 14 L1 14 Z M8 6 L8 10 M8 12 L8 12.3" stroke="currentColor" strokeWidth={1.4} fill="none" strokeLinejoin="round" />
          </svg>
          <span>
            <strong>A suggested update</strong> to this article is pending editorial review.
          </span>
          <button onClick={onOpenReview} style={{ marginLeft: 'auto', color: '#B45309', fontWeight: 600, textDecoration: 'underline' }}>
            Review diff →
          </button>
        </div>
      )}
      <div className="view-header" style={{ paddingBottom: 14 }}>
        <Breadcrumb
          items={[
            { label: 'Home', to: '/' },
            { label: 'Knowledge Base', to: '/kb' },
            { label: 'CON Wiki', to: '/wiki' },
            { label: article.group ?? 'Article' },
          ]}
        />
        <Link to="/wiki" className="text-link" style={{ fontSize: 12 }}>
          ← All articles
        </Link>
      </div>
      <div style={{ padding: '34px 32px 70px' }}>
        <div style={{ maxWidth: 1080, display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 260px', gap: 38, alignItems: 'start' }}>
          <article className="card" style={{ padding: '40px 46px 48px', minWidth: 0 }}>
            <div className="label-upper" style={{ color: 'var(--accent-text)', letterSpacing: 1.6, marginBottom: 12 }}>{article.group}</div>
            <h1 className="serif" style={{ fontSize: 30, fontWeight: 600, color: 'var(--text)', margin: '0 0 12px', lineHeight: 1.2, letterSpacing: '-0.5px' }}>
              {article.title}
            </h1>
            <div style={{ display: 'flex', gap: 14, fontSize: 12, color: 'var(--text3)', paddingBottom: 22, marginBottom: 26, borderBottom: '1px solid var(--surface2)', flexWrap: 'wrap' }}>
              {article.readTime && (
                <>
                  <span>{article.readTime} read</span>
                  <span>·</span>
                </>
              )}
              <span>Updated {article.updated}</span>
              <span>·</span>
              <span>PHRD Healthcare editorial</span>
              {article.justUpdated && (
                <span style={{ color: '#10B981', fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.5, fontSize: 10.5 }}>
                  ● Recently updated
                </span>
              )}
            </div>
            {article.lead && (
              <p className="serif" style={{ fontSize: 17, color: 'var(--text2)', lineHeight: 1.6, margin: '0 0 26px', fontStyle: 'italic' }}>{article.lead}</p>
            )}
            {(article.body ?? []).map((b, i) => {
              if (b.h) {
                return (
                  <h2 key={i} className="serif" style={{ fontSize: 19, fontWeight: 600, color: 'var(--text)', margin: '30px 0 10px', letterSpacing: '-0.2px' }}>
                    {b.h}
                  </h2>
                );
              }
              if (b.note) {
                return (
                  <div key={i} style={{ background: 'rgba(245,158,11,0.08)', borderLeft: '3px solid #F59E0B', padding: '14px 18px', margin: '0 0 20px', fontSize: 13.5, color: '#B45309', lineHeight: 1.6 }}>
                    {renderSegs(b.note)}
                  </div>
                );
              }
              if (b.list) {
                return (
                  <ul key={i} style={{ margin: '0 0 16px', paddingLeft: 22 }}>
                    {b.list.map((item, li) => (
                      <li key={li} style={{ fontSize: 15, color: 'var(--text2)', lineHeight: 1.7, marginBottom: 6 }}>
                        {renderSegs(item)}
                      </li>
                    ))}
                  </ul>
                );
              }
              return (
                <p key={i} style={{ fontSize: 15, color: 'var(--text2)', lineHeight: 1.72, margin: '0 0 16px' }}>
                  {renderSegs(b.p ?? [])}
                </p>
              );
            })}
          </article>

          <aside style={{ position: 'sticky', top: 20, display: 'flex', flexDirection: 'column', gap: 20, minWidth: 0 }}>
            {headings.length > 0 && (
              <div className="card" style={{ padding: '16px 18px' }}>
                <div className="label-upper" style={{ fontSize: 10, letterSpacing: 1.4, marginBottom: 10 }}>On this page</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  {headings.map((h) => (
                    <div key={h} style={{ fontSize: 12, color: 'var(--text2)', lineHeight: 1.4, padding: '6px 0 6px 10px', borderLeft: '2px solid var(--surface2)' }}>
                      {h}
                    </div>
                  ))}
                </div>
              </div>
            )}
            {(article.related?.length ?? 0) > 0 && (
              <div className="card" style={{ borderLeft: '3px solid var(--brand-red)', borderRadius: '0 2px 2px 0', padding: '16px 18px' }}>
                <div className="label-upper" style={{ fontSize: 10, letterSpacing: 1.4, color: 'var(--accent-text)', marginBottom: 11 }}>Related authorities</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
                  {article.related!.map((r, i) => (
                    <Link key={i} to={relatedTo(r)} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, fontSize: 12.5, color: 'var(--accent-text)', lineHeight: 1.4 }}>
                      <span
                        style={{
                          flexShrink: 0,
                          fontSize: 8,
                          textTransform: 'uppercase',
                          letterSpacing: 0.6,
                          fontWeight: 700,
                          color: 'var(--text3)',
                          background: 'var(--page-bg)',
                          border: '1px solid var(--surface2)',
                          padding: '2px 5px',
                          borderRadius: 1,
                          marginTop: 1,
                        }}
                      >
                        {r.kind}
                      </span>
                      <span style={{ flex: 1 }}>{r.label}</span>
                    </Link>
                  ))}
                </div>
              </div>
            )}
            {(article.revisions?.length ?? 0) > 0 && (
              <div className="card" style={{ padding: '16px 18px' }}>
                <div className="label-upper" style={{ fontSize: 10, letterSpacing: 1.4, marginBottom: 12 }}>Revision timeline</div>
                <div style={{ position: 'relative', paddingLeft: 14 }}>
                  <div style={{ position: 'absolute', left: 3, top: 2, bottom: 2, width: 1, background: 'var(--surface2)' }} />
                  {article.revisions!.map((rv, i) => (
                    <div key={i} style={{ position: 'relative', marginBottom: 13 }}>
                      <span style={{ position: 'absolute', left: -14, top: 3, width: 7, height: 7, borderRadius: '50%', background: rv.highlight ? 'var(--brand-red)' : 'var(--border2)' }} />
                      <div style={{ fontSize: 11.5, color: rv.highlight ? 'var(--text)' : 'var(--text2)', fontWeight: rv.highlight ? 600 : 400 }}>
                        {rv.date ?? ''}
                      </div>
                      <div style={{ fontSize: 10.5, color: 'var(--text3)', marginTop: 1 }}>{rv.text ?? rv.status ?? ''}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </aside>
        </div>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Route component
// ---------------------------------------------------------------------------

export default function Wiki() {
  const { articleId } = useParams();
  const navigate = useNavigate();
  const { showToast } = useToast();

  const [index, setIndex] = useState<WikiIndex | null>(null);
  const [article, setArticle] = useState<WikiArticleDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reviewOpen, setReviewOpen] = useState(false);
  const [pending, setPending] = useState<WikiPendingEdit | null>(null);
  const [pendingTitle, setPendingTitle] = useState('');

  const load = useCallback(() => {
    setError(null);
    if (articleId) {
      api
        .getWikiArticle(articleId)
        .then((a) => {
          setArticle(a);
          if (a.pending) {
            setPending(a.pending);
            setPendingTitle(a.title ?? '');
          }
        })
        .catch((e: Error) => setError(e.message));
    } else {
      api
        .listWiki()
        .then((idx) => {
          setIndex(idx);
          if (idx.pendingArticleId) {
            setPendingTitle(idx.pendingArticleTitle ?? '');
            // Pull the diff body for the review modal.
            api
              .getWikiArticle(idx.pendingArticleId)
              .then((a) => setPending(a.pending ?? null))
              .catch(() => setPending(null));
          } else {
            setPending(null);
          }
        })
        .catch((e: Error) => setError(e.message));
    }
  }, [articleId]);

  useEffect(() => {
    setArticle(null);
    setIndex(null);
    load();
  }, [load]);

  const onReviewed = async (action: 'approve' | 'reject') => {
    if (!pending) return;
    await api.reviewWikiRevision(pending.articleId, pending.revisionId, action);
    setReviewOpen(false);
    setPending(null);
    showToast(
      action === 'approve' ? 'Suggested update published to the article' : 'Suggested update discarded',
      action === 'approve' ? 'success' : 'info',
    );
    if (action === 'approve' && !articleId) navigate(`/wiki/${pending.articleId}`);
    else load();
  };

  if (error) {
    return (
      <section>
        <PageHeader crumbs={[{ label: 'Home', to: '/' }, { label: 'Knowledge Base', to: '/kb' }, { label: 'CON Wiki' }]} title="CON Wiki" titleSize={26} />
        <div style={{ padding: '60px 32px', color: 'var(--text3)', fontSize: 13 }}>Wiki unavailable — {error}</div>
      </section>
    );
  }

  return (
    <section>
      {articleId ? (
        article ? (
          <WikiArticleView article={article} onOpenReview={() => setReviewOpen(true)} />
        ) : (
          <div style={{ padding: '60px 32px', color: 'var(--text3)', fontSize: 13 }}>Loading article…</div>
        )
      ) : index ? (
        <WikiIndexView index={index} onOpenReview={() => setReviewOpen(true)} />
      ) : (
        <div style={{ padding: '60px 32px', color: 'var(--text3)', fontSize: 13 }}>Loading wiki…</div>
      )}
      {reviewOpen && pending && (
        <ReviewModal pending={pending} articleTitle={pendingTitle || 'CON Wiki article'} onClose={() => setReviewOpen(false)} onReviewed={(a) => void onReviewed(a)} />
      )}
    </section>
  );
}
