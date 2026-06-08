import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import DomainList from './pages/DomainList';
import DomainDetail from './pages/DomainDetail';
import Sessions from './pages/Sessions';
import SessionDetail from './pages/SessionDetail';
import ExtractProgress from './pages/ExtractProgress';
import Review from './pages/Review';
import Outputs from './pages/Outputs';
import NotFound from './pages/NotFound';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="domains" element={<DomainList />} />
          <Route path="domains/:name" element={<DomainDetail />} />
          <Route path="sessions" element={<Sessions />} />
          <Route path="sessions/:id" element={<SessionDetail />} />
          <Route path="sessions/:id/extract" element={<ExtractProgress />} />
          <Route path="sessions/:id/review" element={<Review />} />
          <Route path="outputs" element={<Outputs />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
