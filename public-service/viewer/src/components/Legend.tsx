/**
 * Legend Component
 *
 * Shows status color legend on the map.
 */
import { Locale } from '../types/release';
import { STATUS_COLORS, STATUS_LABELS, UnitStatus } from '../styles/status-colors';

interface LegendProps {
  locale: Locale;
}

// Only show these statuses in the legend
const VISIBLE_STATUSES: UnitStatus[] = ['available', 'reserved', 'sold'];

export default function Legend({ locale }: LegendProps) {
  return (
    <div className="legend" style={styles.container}>
      {VISIBLE_STATUSES.map((status) => (
        <div key={status} className="legend-item" style={styles.item}>
          <span
            className="legend-color"
            style={{
              ...styles.colorBox,
              backgroundColor: STATUS_COLORS[status].solid,
            }}
          />
          <span className="legend-label" style={styles.label}>
            {STATUS_LABELS[status][locale]}
          </span>
        </div>
      ))}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    position: 'absolute',
    bottom: 20,
    left: 20,
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
    padding: '12px 16px',
    backgroundColor: 'rgba(26, 26, 46, 0.9)',
    borderRadius: 8,
    zIndex: 900,
    backdropFilter: 'blur(10px)',
  },
  item: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  colorBox: {
    width: 16,
    height: 16,
    borderRadius: 4,
    border: '1px solid rgba(255, 255, 255, 0.3)',
  },
  label: {
    fontSize: 12,
    color: '#ffffff',
    fontWeight: 500,
  },
};
