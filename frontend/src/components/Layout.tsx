import { Box } from '@mui/material';
import { Outlet } from 'react-router-dom';

import type { ThemeMode } from '../theme';
import AppHeader from './AppHeader';

export default function Layout({
  mode,
  onToggleMode,
}: {
  mode: ThemeMode;
  onToggleMode: () => void;
}) {
  return (
    <Box sx={{ minHeight: '100vh', background: 'var(--s-page)' }}>
      <AppHeader mode={mode} onToggleMode={onToggleMode} />
      <Box
        component="main"
        sx={{ maxWidth: 1600, mx: 'auto', p: 3 }}
      >
        <Outlet />
      </Box>
    </Box>
  );
}
