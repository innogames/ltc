import DarkModeIcon from '@mui/icons-material/DarkMode';
import LightModeIcon from '@mui/icons-material/LightMode';
import LogoutIcon from '@mui/icons-material/Logout';
import SearchIcon from '@mui/icons-material/Search';
import {
  Autocomplete,
  Avatar,
  Box,
  Button,
  IconButton,
  InputAdornment,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import { Link, useLocation, useNavigate } from 'react-router-dom';

import { useMe, useTests } from '../api/hooks';
import { testLabel } from '../lib/format';
import { BRAND, FONT_DISPLAY, type ThemeMode } from '../theme';

const NAV = [
  { label: 'Dashboard', to: '/' },
  { label: 'Analyzer', to: '/analyzer' },
  { label: 'Online', to: '/online', live: true },
];

function LtcLogo() {
  return (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M12 2 20.66 7v10L12 22 3.34 17V7z"
        stroke={BRAND.headerAccent}
        strokeWidth={2}
      />
      <path
        d="M12 7.5 15.9 9.75v4.5L12 16.5 8.1 14.25v-4.5z"
        fill={BRAND.headerAccent}
      />
    </svg>
  );
}

export default function AppHeader({
  mode,
  onToggleMode,
}: {
  mode: ThemeMode;
  onToggleMode: () => void;
}) {
  const location = useLocation();
  const navigate = useNavigate();
  const { data: me } = useMe();
  // Search source: recent tests (ids/names) — enough to jump anywhere.
  const { data: tests } = useTests({ pageSize: 200, started: true });

  const initials = me
    ? `${me.first_name?.[0] ?? me.username[0] ?? ''}${
        me.last_name?.[0] ?? ''
      }`.toUpperCase()
    : '';

  const navButton = (item: (typeof NAV)[number]) => {
    const active = location.pathname === item.to;
    return (
      <Button
        key={item.to}
        component={Link}
        to={item.to}
        disableRipple
        sx={{
          height: '100%',
          borderRadius: 0,
          px: 1.75,
          color: BRAND.headerText,
          opacity: active ? 1 : 0.7,
          borderBottom: `3px solid ${
            active ? BRAND.headerAccent : 'transparent'
          }`,
          mb: '-3px',
          fontFamily: FONT_DISPLAY,
          fontSize: 12,
          letterSpacing: '.1em',
          '&:hover': { background: 'rgba(255,255,255,.06)', opacity: 1 },
        }}
      >
        {item.label}
        {item.live && (
          <Box
            component="span"
            sx={{
              ml: 1,
              width: 8,
              height: 8,
              borderRadius: 99,
              background: BRAND.headerAccent,
              animation: 'ltc-pulse 1.6s ease-in-out infinite',
            }}
          />
        )}
      </Button>
    );
  };

  return (
    <Box
      component="header"
      sx={{
        position: 'sticky',
        top: 0,
        zIndex: 20,
        height: 56,
        background: BRAND.headerBg,
        color: BRAND.headerText,
        display: 'flex',
        alignItems: 'center',
        px: 3,
        gap: 4,
        borderBottom: `3px solid ${BRAND.headerAccent}`,
      }}
    >
      <Box
        component={Link}
        to="/"
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1.25,
          textDecoration: 'none',
        }}
      >
        <LtcLogo />
        <Box sx={{ display: 'flex', flexDirection: 'column', lineHeight: 1 }}>
          <Box
            component="span"
            sx={{
              fontFamily: FONT_DISPLAY,
              fontWeight: 700,
              fontSize: 20,
              letterSpacing: '.04em',
              color: BRAND.headerText,
            }}
          >
            LTC
          </Box>
          <Box
            component="span"
            sx={{
              fontFamily: FONT_DISPLAY,
              fontSize: 10,
              letterSpacing: '.14em',
              textTransform: 'uppercase',
              color: BRAND.headerText2,
            }}
          >
            Load Testing Center
          </Box>
        </Box>
      </Box>

      <Box
        component="nav"
        sx={{ display: 'flex', gap: 0.5, height: '100%' }}
      >
        {NAV.map(navButton)}
        <Button
          href="/admin/"
          disableRipple
          sx={{
            height: '100%',
            borderRadius: 0,
            px: 1.75,
            color: BRAND.headerText,
            opacity: 0.6,
            fontFamily: FONT_DISPLAY,
            fontSize: 12,
            letterSpacing: '.1em',
          }}
        >
          Admin
        </Button>
      </Box>

      <Box sx={{ flex: 1 }} />

      <Autocomplete
        size="small"
        options={tests?.results ?? []}
        getOptionLabel={(t) => `${t.id} · ${testLabel(t)}`}
        filterOptions={(options, state) => {
          const q = state.inputValue.trim().toLowerCase();
          if (!q) return [];
          return options
            .filter(
              (t) =>
                String(t.id).includes(q) ||
                testLabel(t).toLowerCase().includes(q) ||
                (t.project?.name ?? '').toLowerCase().includes(q),
            )
            .slice(0, 8);
        }}
        onChange={(_, value) => {
          if (value) navigate(`/analyzer?test=${value.id}`);
        }}
        sx={{ width: 260 }}
        renderInput={(params) => (
          <TextField
            {...params}
            placeholder="Jump to test id or project…"
            InputProps={{
              ...params.InputProps,
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon
                    sx={{ fontSize: 16, color: BRAND.headerText2 }}
                  />
                </InputAdornment>
              ),
              sx: {
                height: 34,
                background: '#2E5E1F',
                color: BRAND.headerText,
                fontSize: 13,
                '& fieldset': { borderColor: '#386823' },
                '&:hover fieldset': { borderColor: BRAND.headerAccent },
                '& input::placeholder': {
                  color: BRAND.headerText2,
                  opacity: 0.8,
                },
              },
            }}
          />
        )}
      />

      <Tooltip title={mode === 'dark' ? 'Light theme' : 'Dark theme'}>
        <IconButton
          onClick={onToggleMode}
          size="small"
          sx={{
            border: `2px solid ${BRAND.headerAccent}`,
            color: BRAND.headerText,
          }}
        >
          {mode === 'dark' ? (
            <LightModeIcon sx={{ fontSize: 16 }} />
          ) : (
            <DarkModeIcon sx={{ fontSize: 16 }} />
          )}
        </IconButton>
      </Tooltip>

      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1.25,
          color: BRAND.headerText2,
        }}
      >
        {me && (
          <>
            <Avatar
              sx={{
                width: 28,
                height: 28,
                fontSize: 12,
                fontWeight: 700,
                background: BRAND.headerAccent,
                color: BRAND.headerBg,
              }}
            >
              {initials}
            </Avatar>
            <Typography variant="body2" sx={{ whiteSpace: 'nowrap' }}>
              {me.username}
            </Typography>
          </>
        )}
        <Tooltip title="Log out">
          <IconButton
            href="/logout/"
            size="small"
            sx={{ color: BRAND.headerText2 }}
          >
            <LogoutIcon sx={{ fontSize: 18 }} />
          </IconButton>
        </Tooltip>
      </Box>
    </Box>
  );
}
