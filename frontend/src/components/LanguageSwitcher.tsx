
import React from 'react';
import { useTranslation } from 'react-i18next';
import { ButtonGroup, Button } from '@mui/material';

const languages = [
  { code: 'uk', label: 'УКР' },
  { code: 'de', label: 'DE' },
  { code: 'en', label: 'EN' },
];

const LanguageSwitcher: React.FC = () => {
  const { i18n } = useTranslation();

  const changeLanguage = (lang: string) => {
    i18n.changeLanguage(lang);
    localStorage.setItem('lang', lang);
  };

  return (
    <ButtonGroup
      variant="outlined"
      size="small"
      aria-label="Мова інтерфейсу"
      sx={{
        borderRadius: '8px',
        overflow: 'hidden',
        '& .MuiButtonGroup-grouped': {
          borderColor: 'divider',
        },
      }}
    >
      {languages.map((lang) => {
        const active = i18n.language === lang.code;
        return (
          <Button
            key={lang.code}
            onClick={() => changeLanguage(lang.code)}
            aria-pressed={active}
            sx={{
              px: 1.75,
              py: 0.5,
              fontFamily: '"IBM Plex Mono", monospace',
              fontSize: '0.75rem',
              fontWeight: 600,
              letterSpacing: '0.04em',
              color: active ? 'primary.contrastText' : 'text.secondary',
              bgcolor: active ? 'primary.main' : 'transparent',
              '&:hover': {
                bgcolor: active ? 'primary.dark' : 'rgba(47, 111, 94, 0.08)',
              },
            }}
          >
            {lang.label}
          </Button>
        );
      })}
    </ButtonGroup>
  );
};

export default LanguageSwitcher;