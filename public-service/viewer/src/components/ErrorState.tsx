/**
 * ErrorState Component
 *
 * Shows error message with retry button.
 */

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export default function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="error-state" style={styles.container}>
      <div className="error-icon" style={styles.icon}>
        ⚠️
      </div>
      <h2 style={styles.title}>Something went wrong</h2>
      <p style={styles.message}>{message}</p>
      {onRetry && (
        <button onClick={onRetry} style={styles.button}>
          Try Again
        </button>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    width: '100%',
    backgroundColor: '#1a1a2e',
    color: '#ffffff',
    gap: 16,
    padding: 24,
    textAlign: 'center',
  },
  icon: {
    fontSize: 48,
  },
  title: {
    fontSize: 24,
    fontWeight: 600,
    margin: 0,
    color: '#ffffff',
  },
  message: {
    fontSize: 14,
    color: '#9e9e9e',
    margin: 0,
    maxWidth: 400,
  },
  button: {
    marginTop: 16,
    padding: '12px 24px',
    backgroundColor: '#4B9C55',
    color: '#ffffff',
    border: 'none',
    borderRadius: 8,
    fontSize: 14,
    fontWeight: 600,
    cursor: 'pointer',
  },
};
