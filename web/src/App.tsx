/*
 * Route table — one route per handoff view (28 including Compare), all inside
 * the global Shell layout. Every screen is a real implementation (phase 1's
 * core five plus phase 2's remaining 22 — no placeholders remain). Deep-link
 * routes /document/:entryId and /docket/:docketId are load-bearing (the
 * Copilot agent links straight into them).
 */
import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';

import { Shell } from './components/Shell';

const Home = lazy(() => import('./views/Home'));
const Results = lazy(() => import('./views/Results'));
const DocumentView = lazy(() => import('./views/DocumentView'));
const Docket = lazy(() => import('./views/Docket'));
const Citator = lazy(() => import('./views/Citator'));
const Topics = lazy(() => import('./views/Topics'));
const StatutesIndex = lazy(() => import('./views/StatutesIndex'));
const Statute = lazy(() => import('./views/Statute'));
const History = lazy(() => import('./views/History'));
const Alerts = lazy(() => import('./views/Alerts'));
const Submit = lazy(() => import('./views/Submit'));
const Applications = lazy(() => import('./views/Applications'));
const Stats = lazy(() => import('./views/Stats'));
const Calculator = lazy(() => import('./views/Calculator'));
const Compare = lazy(() => import('./views/Compare'));
const MapView = lazy(() => import('./views/MapView'));
const Kb = lazy(() => import('./views/Kb'));
const Wiki = lazy(() => import('./views/Wiki'));
const Research = lazy(() => import('./views/Research'));
const NewSearch = lazy(() => import('./views/NewSearch'));
const NewProject = lazy(() => import('./views/NewProject'));
const Library = lazy(() => import('./views/Library'));
const ProjectDetail = lazy(() => import('./views/ProjectDetail'));
const Proceedings = lazy(() => import('./views/Proceedings'));
const MatterHistory = lazy(() => import('./views/MatterHistory'));
const Tools = lazy(() => import('./views/Tools'));
const Upload = lazy(() => import('./views/Upload'));
const Reports = lazy(() => import('./views/Reports'));

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
            ['/topics', <Topics />],
            ['/topics/:topicId', <Topics />],
            ['/statutes', <StatutesIndex />],
            ['/statute/:statuteId', <Statute />],
            ['/history', <History />],
            ['/history/:docketId', <History />],
            ['/alerts', <Alerts />],
            ['/submit', <Submit />],
            ['/applications', <Applications />],
            ['/stats', <Stats />],
            ['/calculator', <Calculator />],
            ['/compare', <Compare />],
            ['/map', <MapView />],
            ['/kb', <Kb />],
            ['/wiki', <Wiki />],
            ['/wiki/:articleId', <Wiki />],
            ['/research', <Research />],
            ['/search/new', <NewSearch />],
            ['/projects/new', <NewProject />],
            ['/library', <Library />],
            ['/projects/:projectId', <ProjectDetail />],
            ['/proceedings', <Proceedings />],
            ['/proceedings/history', <MatterHistory />],
            ['/tools', <Tools />],
            ['/upload', <Upload />],
            ['/reports', <Reports />],
          ] as [string, JSX.Element][]
        ).map(([path, element]) => (
          <Route key={path} path={path} element={<Suspense fallback={<Loading />}>{element}</Suspense>} />
        ))}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
