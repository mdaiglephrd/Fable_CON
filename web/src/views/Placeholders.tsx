/*
 * Phase-2 views — every non-core handoff view gets a routed page with title +
 * breadcrumb and a "coming in phase 2" card, so the left rail and cross-links
 * never dead-end.
 */
import { useParams } from 'react-router-dom';

import { Placeholder } from '../components/Placeholder';

const HOME = { label: 'Home', to: '/' };

export function TopicsView() {
  const { topicId } = useParams();
  return (
    <Placeholder
      title="Topics & Key Numbers"
      crumbs={[HOME, { label: 'Knowledge Base', to: '/kb' }, { label: topicId ? `Topics · ${topicId}` : 'Topics & Key Numbers' }]}
      blurb="The CON key-number taxonomy (roots I–VII) with expandable key numbers and headnoted cases arrives in phase 2. Cross-links from headnotes and citator keys already route here."
    />
  );
}

export function StatuteView() {
  const { statuteId } = useParams();
  return (
    <Placeholder
      title={statuteId ? `Statute · ${statuteId}` : 'Statute'}
      crumbs={[HOME, { label: 'Statutes & Rules', to: '/statutes' }, { label: statuteId ?? 'Statute' }]}
      blurb="The annotated O.C.G.A. / DCH rule reader (full text, cross-references, citing cases) arrives in phase 2. Statute cross-links in opinions already route here."
    />
  );
}

export function StatutesIndexView() {
  return (
    <Placeholder
      title="Statutes & Rules Index"
      crumbs={[HOME, { label: 'Knowledge Base', to: '/kb' }, { label: 'Statutes & Rules' }]}
    />
  );
}

export function HistoryView() {
  return <Placeholder title="Research History" crumbs={[HOME, { label: 'Research', to: '/research' }, { label: 'History' }]} />;
}

export function AlertsView() {
  return (
    <Placeholder
      title="Alerts"
      crumbs={[HOME, { label: 'My Proceedings', to: '/proceedings' }, { label: 'Alerts' }]}
      blurb="Saved-search and docket-watch management (Docket Watch, Search Alert, Statute/Rule Watch, Citation Alert) arrives in phase 2."
    />
  );
}

export function SubmitView() {
  return (
    <Placeholder
      title="Submit Document"
      crumbs={[HOME, { label: 'Upload', to: '/upload' }, { label: 'Submit Document' }]}
      blurb="The 3-step submission wizard (details → metadata → review & save) arrives in phase 2."
    />
  );
}

export function ApplicationsView() {
  return (
    <Placeholder
      title="Active Proceedings"
      crumbs={[HOME, { label: 'Knowledge Base', to: '/kb' }, { label: 'Active Proceedings' }]}
      blurb="The live docket tracker with status summary cards and per-row mini progress bars arrives in phase 2."
    />
  );
}

export function StatsView() {
  return (
    <Placeholder
      title="Outcome Statistics"
      crumbs={[HOME, { label: 'Analytics & Tools', to: '/tools' }, { label: 'Outcome Statistics' }]}
      blurb="Grant/denial analytics by service category, docket type, forum, and year (GET /stats) arrive in phase 2."
    />
  );
}

export function CalculatorView() {
  return (
    <Placeholder
      title="Deadline Calculator"
      crumbs={[HOME, { label: 'Analytics & Tools', to: '/tools' }, { label: 'Deadline Calculator' }]}
      blurb="Event + date inputs computing regulatory deadlines (POST /deadlines/calculate) arrive in phase 2."
    />
  );
}

export function CompareView() {
  return (
    <Placeholder
      title="Compare"
      crumbs={[HOME, { label: 'Analytics & Tools', to: '/tools' }, { label: 'Compare' }]}
      blurb="Side-by-side comparison of two cases/dockets arrives in phase 2."
    />
  );
}

export function MapView() {
  return (
    <Placeholder
      title="Service-Area Map"
      crumbs={[HOME, { label: 'Analytics & Tools', to: '/tools' }, { label: 'Service-Area Map' }]}
    />
  );
}

export function KbView() {
  return (
    <Placeholder
      title="Knowledge Base"
      crumbs={[HOME, { label: 'Knowledge Base' }]}
      blurb="Hub linking into the CON Wiki and the Statutes & Rules index — full landing arrives in phase 2. Use the left rail to reach Topics, Statutes, and the Wiki."
    />
  );
}

export function WikiView() {
  const { articleId } = useParams();
  return (
    <Placeholder
      title={articleId ? `CON Wiki · ${articleId}` : 'CON Wiki'}
      crumbs={[HOME, { label: 'Knowledge Base', to: '/kb' }, { label: 'CON Wiki' }]}
      blurb="Wiki articles with table of contents, cross-links, revision history, and the pending-edit review flow arrive in phase 2."
    />
  );
}

export function ResearchView() {
  return (
    <Placeholder
      title="Research"
      crumbs={[HOME, { label: 'Research' }]}
      blurb="Entry point for Quick Search, New Research Project, and the Research Library — full landing arrives in phase 2."
    />
  );
}

export function NewSearchView() {
  return (
    <Placeholder
      title="Advanced Search"
      crumbs={[HOME, { label: 'Research', to: '/research' }, { label: 'Advanced Search' }]}
      blurb="The structured query builder (all words, phrase, doc type, forum, outcome) arrives in phase 2; the top-bar scoped search already covers quick queries."
    />
  );
}

export function NewProjectView() {
  return (
    <Placeholder
      title="New Research Project"
      crumbs={[HOME, { label: 'Research', to: '/research' }, { label: 'New Project' }]}
    />
  );
}

export function LibraryView() {
  return (
    <Placeholder
      title="Research Library"
      crumbs={[HOME, { label: 'Research', to: '/research' }, { label: 'Library' }]}
    />
  );
}

export function ProjectDetailView() {
  const { projectId } = useParams();
  return (
    <Placeholder
      title={`Research Project · ${projectId ?? ''}`}
      crumbs={[HOME, { label: 'Research', to: '/research' }, { label: 'Project' }]}
    />
  );
}

export function ProceedingsView() {
  return (
    <Placeholder
      title="My Proceedings"
      crumbs={[HOME, { label: 'My Proceedings' }]}
      blurb="Your tracked matters land here in phase 2. The Docket View console is live — open it from the left rail or any result card."
    />
  );
}

export function MatterHistoryView() {
  return (
    <Placeholder
      title="Proceedings History"
      crumbs={[HOME, { label: 'My Proceedings', to: '/proceedings' }, { label: 'History' }]}
    />
  );
}

export function ToolsView() {
  return (
    <Placeholder
      title="Analytics & Tools"
      crumbs={[HOME, { label: 'Analytics & Tools' }]}
      blurb="Hub linking Outcome Statistics, the Deadline Calculator, Compare, and the Service-Area Map — full landing arrives in phase 2."
    />
  );
}

export function UploadView() {
  return <Placeholder title="Upload" crumbs={[HOME, { label: 'Upload' }]} />;
}

export function ReportsView() {
  return (
    <Placeholder
      title="Weekly Reports"
      crumbs={[HOME, { label: 'Analytics & Tools', to: '/tools' }, { label: 'Weekly Reports' }]}
    />
  );
}
