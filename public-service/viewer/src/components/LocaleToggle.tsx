/**
 * LocaleToggle Component
 *
 * Switches between English and Arabic locales.
 */
import { Locale } from '../types/release';

interface LocaleToggleProps {
  locale: Locale;
  onChange: (locale: Locale) => void;
}

export default function LocaleToggle({ locale, onChange }: LocaleToggleProps) {
  const toggleLocale = () => {
    onChange(locale === 'en' ? 'ar' : 'en');
  };

  return (
    <button
      className="locale-toggle"
      onClick={toggleLocale}
      style={styles.button}
      aria-label={`Switch to ${locale === 'en' ? 'Arabic' : 'English'}`}
    >
      <span style={locale === 'en' ? styles.active : styles.inactive}>EN</span>
      <span style={styles.separator}>/</span>
      <span style={locale === 'ar' ? styles.active : styles.inactive}>عربي</span>
    </button>
  );
}

const styles: Record<string, React.CSSProperties> = {
  button: {
    position: 'absolute',
    top: 16,
    right: 16,
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    padding: '8px 16px',
    backgroundColor: 'rgba(26, 26, 46, 0.9)',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    borderRadius: 20,
    cursor: 'pointer',
    zIndex: 1000,
    backdropFilter: 'blur(10px)',
    fontSize: 14,
  },
  active: {
    color: '#ffffff',
    fontWeight: 600,
  },
  inactive: {
    color: '#757575',
    fontWeight: 400,
  },
  separator: {
    color: '#757575',
  },
};
