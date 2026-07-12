/*
 * Route table — one route per handoff view (28 including Compare), all inside
 * the global Shell layout. Core phase-1 screens are full implementations;
 * the rest render a clean "coming in phase 2" placeholder so navigation is
 * complete. Deep-link routes /document/:entryId and /docket/:docketId are
 * load-bearing (the Copilot agent links straight into them).
 */
import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';

import { Shell } from './components/Shell';

const Home = lazy(() => import('./views/Home'));
const Results = lazy(() => import('./views/Results'));
const DocumentView = lazy(() => import('./views/DocumentView'));
const Docket = lazy(() => import('./views/Docket'));
const Citator = lazy(() => import('./views/Citator'));
const P = {
  Topics: lazy(() => import('./views/Placeholders').then((m) => ({ default: m.TopicsView }))),
  Statute: lazy(() => import('./views/Placeholders').then((m) => ({ default: m.StatuteView }))),
  Statutes: lazy(() => import('./views/Placeholders').then((m) => ({ default: m.StatutesIndexView }))),
  History: lazy(() => import('./views/Placeholders').then((m) => ({ default: m.HistoryView }))),
  Alerts: lazy(() => import('./views/Placeholders').then((m) => ({ default: m.AlertsView }))),
  Submit: lazy(() => import('./views/Placeholders').then((m) => ({ default: m.SubmitView }))),
  Applications: lazy(() => import('./views/Placeholders').then((m) => ({ default: m.ApplicationsView }))),
  Stats: lazy(() => import('./views/Placeholders').then((m) => ({ default: m.StatsView }))),
  Calculator: lazy(() => import('./views/Placeholders').then((m) => ({ default: m.CalculatorView }))),
  Compare: lazy(() => import('./views/Placeholders').then((m) => ({ default: m.CompareView }))),
  Map: lazy(() => import('./views/Placeholders').then((m) => ({ default: m.MapView }))),
  Kb: lazy(() => import('./views/Placeholders').then((m) => ({ default: m.KbView }))),
  Wiki: lazy(() => import('./views/Placeholders').then((m) => ({ default: m.WikiView }))),
  Research: lazy(() => import('./views/Placeholders').then((m) => ({ default: m.ResearchView }))),
  NewSearch: lazy(() => import('./views/Placeholders').then((m) => ({ default: m.NewSearchView }))),
  NewProject: lazy(() => import('./views/Placeholders').then((m) => ({ default: m.NewProjectView }))),
  Library: lazy(() => import('./views/Placeholders').then((m) => ({ default: m.LibraryView }))),
  ProjectDetail: lazy(() => import('./views/Placeholders').then((m) => ({ default: m.ProjectDetailView }))),
  Proceedings: lazy(() => import('./views/Placeholders').then((m) => ({ default: m.ProceedingsView }))),
  MatterHistory: lazy(() => import('./views/Placeholders').then((m) => ({ default: m.MatterHistoryView }))),
  Tools: lazy(() => import('./views/Placeholders').then((m) => ({ default: m.ToolsView }))),
  Upload: lazy(() => import('./views/Placeholders').then((m) => ({ default: m.UploadView }))),
  Reports: lazy(() => import('./views/Placeholders').then((m) => ({ default: m.ReportsView }))),
};

function Loading() {
  return (
    <div style={{ padding: '60px 32px', color: 'var(--text3)', fontSize: 13 }}>Loading…</div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route
          index
          element={
            <Suspense fallback={<Loading />}>
              <Home />
            </Suspense>
          }
        />
        {(
          [
            ['/results', <Results />],
            ['/document/:entryId', <DocumentView />],
            ['/docket/:docketId', <Docket />],
            ['/citator/:entryId', <Citator />],
            ['/topics', <P.Topics />],
            ['/topics/:topicId', <P.Topics />],
            ['/statutes', <P.Statutes />],
            ['/statute/:statuteId', <P.Statute />],
            ['/history', <P.History />],
            ['/alerts', <P.Alerts />],
            ['/submit', <P.Submit />],
            ['/applications', <P.Applications />],
            ['/stats', <P.Stats />],
            ['/calculator', <P.Calculator />],
            ['/compare', <P.Compare />],
            ['/map', <P.Map />],
            ['/kb', <P.Kb />],
            ['/wiki', <P.Wiki />],
            ['/wiki/:articleId', <P.Wiki />],
            ['/research', <P.Research />],
            ['/search/new', <P.NewSearch />],
            ['/projects/new', <P.NewProject />],
            ['/library', <P.Library />],
            ['/projects/:projectId', <P.ProjectDetail />],
            ['/proceedings', <P.Proceedings />],
            ['/proceedings/history', <P.MatterHistory />],
            ['/tools', <P.Tools />],
            ['/upload', <P.Upload />],
            ['/reports', <P.Reports />],
          ] as [string, JSX.Element][]
        ).map(([path, element]) => (
          <Route key={path} path={path} element={<Suspense fallback={<Loading />}>{element}</Suspense>} />
        ))}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
