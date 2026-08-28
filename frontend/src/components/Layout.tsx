import LogoutIcon from '@mui/icons-material/Logout';
import {
  AppBar,
  Box,
  Button,
  Container,
  IconButton,
  Toolbar,
  Tooltip,
  Typography,
} from '@mui/material';
import { Link, Outlet, useLocation } from 'react-router-dom';

import { useMe } from '../api/hooks';

const NAV = [
  { label: 'DASHBOARD', to: '/' },
  { label: 'ANALYZER', to: '/analyzer' },
  { label: 'ONLINE', to: '/online' },
];

export default function Layout() {
  const location = useLocation();
  const { data: me } = useMe();

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'grey.100' }}>
      <AppBar position="sticky">
        <Toolbar variant="dense">
          <Typography variant="h6" sx={{ mr: 4 }}>
            LTC
          </Typography>
          {NAV.map(({ label, to }) => (
            <Button
              key={to}
              component={Link}
              to={to}
              color="inherit"
              sx={{
                fontWeight: location.pathname === to ? 700 : 400,
                opacity: location.pathname === to ? 1 : 0.8,
              }}
            >
              {label}
            </Button>
          ))}
          {me?.is_staff && (
            <Button color="inherit" href="/admin/" sx={{ opacity: 0.8 }}>
              ADMIN
            </Button>
          )}
          <Box sx={{ flexGrow: 1 }} />
          {me && (
            <Typography variant="body2" sx={{ mr: 1, opacity: 0.8 }}>
              {me.username}
            </Typography>
          )}
          <Tooltip title="Log out">
            <IconButton color="inherit" href="/logout/" size="small">
              <LogoutIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>
      <Container maxWidth={false} sx={{ py: 3 }}>
        <Outlet />
      </Container>
    </Box>
  );
}
