/**
 * LoadingSpinner Component
 *
 * Full-screen loading state with spinner.
 */

interface LoadingSpinnerProps {
  message?: string;
}

export default function LoadingSpinner({ message = 'Loading...' }: LoadingSpinnerProps) {
  return (
    <div className="loading-spinner" style={styles.container}>
      <div className="spinner" style={styles.spinner} />
      <p style={styles.message}>{message}</p>
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
  },
  spinner: {
    width: 48,
    height: 48,
    border: '4px solid rgba(255, 255, 255, 0.1)',
    borderTopColor: '#4B9C55',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },
  message: {
    fontSize: 14,
    color: '#9e9e9e',
    margin: 0,
  },
};

// Add keyframes to document
if (typeof document !== 'undefined') {
  const styleSheet = document.createElement('style');
  styleSheet.textContent = `
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  `;
  document.head.appendChild(styleSheet);
}
