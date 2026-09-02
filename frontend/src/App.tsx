import { CssBaseline, ThemeProvider } from '@mui/material';
import { useCallback, useMemo, useState } from 'react';
import { Route, Routes } from 'react-router-dom';

import Layout from './components/Layout';
import AnalyzerPage from './pages/Analyzer/AnalyzerPage';
import Dashboard from './pages/Dashboard';
import OnlinePage from './pages/OnlinePage';
import { buildTheme, type ThemeMode } from './theme';

const STORAGE_KEY = 'ltc-theme';

function initialMode(): ThemeMode {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'light' || stored === 'dark') return stored;
    if (window.matchMedia?.('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
  } catch {
    // storage unavailable (private mode) — fall through to light
  }
  return 'light';
}

export default function App() {
  const [mode, setMode] = useState<ThemeMode>(initialMode);
  const theme = useMemo(() => buildTheme(mode), [mode]);

  const toggleMode = useCallback(() => {
    setMode((current) => {
      const next = current === 'dark' ? 'light' : 'dark';
      try {
        localStorage.setItem(STORAGE_KEY, next);
      } catch {
        // ignore — theme just won't persist for this viewer
      }
      return next;
    });
  }, []);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Routes>
        <Route element={<Layout mode={mode} onToggleMode={toggleMode} />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/analyzer" element={<AnalyzerPage />} />
          <Route path="/online" element={<OnlinePage />} />
        </Route>
      </Routes>
    </ThemeProvider>
  );
}
