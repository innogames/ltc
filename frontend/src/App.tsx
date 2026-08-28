import { Route, Routes } from 'react-router-dom';

import Layout from './components/Layout';
import AnalyzerPage from './pages/Analyzer/AnalyzerPage';
import Dashboard from './pages/Dashboard';
import OnlinePage from './pages/OnlinePage';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/analyzer" element={<AnalyzerPage />} />
        <Route path="/online" element={<OnlinePage />} />
      </Route>
    </Routes>
  );
}
