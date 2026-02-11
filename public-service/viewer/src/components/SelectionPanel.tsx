/**
 * SelectionPanel Component
 *
 * Shows details of the selected overlay at the bottom of the screen.
 */
import { ReleaseOverlay, Locale } from '../types/release';
import { UnitStatus, STATUS_LABELS, STATUS_COLORS } from '../styles/status-colors';

interface SelectionPanelProps {
  overlay: ReleaseOverlay;
  status: UnitStatus;
  locale: Locale;
  onClose: () => void;
  onNavigateToZone?: (zoneRef: string) => void;
}

export default function SelectionPanel({
  overlay,
  status,
  locale,
  onClose,
  onNavigateToZone,
}: SelectionPanelProps) {
  const { ref, label, overlay_type, layer, props } = overlay;
  const isZone = overlay_type === 'zone';
  const hasZoneLevel = isZone && layer;

  const displayLabel = label[locale] || label.en || ref;
  const statusLabel = STATUS_LABELS[status][locale];
  const statusColor = STATUS_COLORS[status].solid;

  return (
    <div className="selection-panel" style={styles.panel}>
      <button
        className="close-button"
        onClick={onClose}
        style={styles.closeButton}
        aria-label="Close"
      >
        &times;
      </button>

      <div className="panel-content" style={styles.content}>
        <div className="panel-header" style={styles.header}>
          <span className="overlay-type" style={styles.overlayType}>
            {overlay_type.toUpperCase()}
          </span>
          <h3 className="overlay-label" style={styles.label}>
            {displayLabel}
          </h3>
          <span className="overlay-ref" style={styles.ref}>
            {ref}
          </span>
        </div>

        <div className="panel-status" style={styles.statusRow}>
          <span
            className="status-badge"
            style={{
              ...styles.statusBadge,
              backgroundColor: statusColor,
            }}
          >
            {statusLabel}
          </span>

          {hasZoneLevel && onNavigateToZone && (
            <button
              className="view-zone-button"
              onClick={() => onNavigateToZone(layer!)}
              style={styles.viewZoneButton}
            >
              View Zone →
            </button>
          )}
        </div>

        {props && Object.keys(props).length > 0 && (
          <div className="panel-props" style={styles.props}>
            {Object.entries(props).map(([key, value]) => (
              <div key={key} style={styles.propRow}>
                <span style={styles.propKey}>{key}:</span>
                <span style={styles.propValue}>{String(value)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  panel: {
    position: 'absolute',
    bottom: 20,
    left: '50%',
    transform: 'translateX(-50%)',
    backgroundColor: 'rgba(26, 26, 46, 0.95)',
    borderRadius: 12,
    padding: '16px 24px',
    minWidth: 280,
    maxWidth: 400,
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
    zIndex: 1000,
    color: '#ffffff',
    backdropFilter: 'blur(10px)',
  },
  closeButton: {
    position: 'absolute',
    top: 8,
    right: 12,
    background: 'transparent',
    border: 'none',
    color: '#9e9e9e',
    fontSize: 24,
    cursor: 'pointer',
    padding: 4,
    lineHeight: 1,
  },
  content: {
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  header: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  overlayType: {
    fontSize: 10,
    fontWeight: 600,
    letterSpacing: 1,
    color: '#9e9e9e',
  },
  label: {
    margin: 0,
    fontSize: 20,
    fontWeight: 600,
    color: '#ffffff',
  },
  ref: {
    fontSize: 12,
    color: '#757575',
    fontFamily: 'monospace',
  },
  statusRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  statusBadge: {
    padding: '4px 12px',
    borderRadius: 16,
    fontSize: 12,
    fontWeight: 600,
    color: '#ffffff',
  },
  viewZoneButton: {
    marginLeft: 'auto',
    padding: '6px 16px',
    borderRadius: 8,
    fontSize: 13,
    fontWeight: 600,
    color: '#ffffff',
    backgroundColor: '#1976d2',
    border: 'none',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  },
  props: {
    borderTop: '1px solid rgba(255, 255, 255, 0.1)',
    paddingTop: 12,
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  propRow: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: 12,
  },
  propKey: {
    color: '#9e9e9e',
  },
  propValue: {
    color: '#ffffff',
    fontWeight: 500,
  },
};
