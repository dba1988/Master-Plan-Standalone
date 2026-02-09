# TASK-017a: Editor Canvas + Tools Panel

**Phase**: 5 - Admin UI
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-007 (overlays CRUD), TASK-016 (assets page)
**Blocks**: TASK-017b (inspector panel)
**Estimated Time**: 2-3 hours

## Objective

Create the map canvas component with pan/zoom controls and the tools panel for overlay navigation.

## Scope

This task covers the canvas and tools panel ONLY. The inspector panel and page integration are in TASK-017b.

## Files to Create

```
admin-service/ui/src/components/editor/
├── MapCanvas.jsx
└── ToolsPanel.jsx
```

## Implementation

### Map Canvas

```jsx
// src/components/editor/MapCanvas.jsx
import React, { useRef, useState } from 'react';

export default function MapCanvas({ overlays, viewBox, selectedId, onSelect }) {
  const svgRef = useRef(null);
  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 1 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });

  // Parse viewBox
  const [vbX, vbY, vbW, vbH] = viewBox.split(' ').map(Number);

  // Pan handlers
  const handleMouseDown = (e) => {
    if (e.target === svgRef.current) {
      setIsPanning(true);
      setPanStart({ x: e.clientX - transform.x, y: e.clientY - transform.y });
    }
  };

  const handleMouseMove = (e) => {
    if (isPanning) {
      setTransform(prev => ({
        ...prev,
        x: e.clientX - panStart.x,
        y: e.clientY - panStart.y,
      }));
    }
  };

  const handleMouseUp = () => {
    setIsPanning(false);
  };

  // Zoom with wheel
  const handleWheel = (e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setTransform(prev => ({
      ...prev,
      scale: Math.min(Math.max(prev.scale * delta, 0.1), 10),
    }));
  };

  const renderOverlay = (overlay) => {
    const isSelected = overlay.id === selectedId;
    const geometry = overlay.geometry;

    if (geometry?.type === 'path') {
      return (
        <g key={overlay.id}>
          <path
            d={geometry.d}
            fill={isSelected ? '#DAA520' : 'rgba(75, 156, 85, 0.5)'}
            fillOpacity={isSelected ? 0.5 : 0.7}
            stroke={isSelected ? '#F1DA9E' : '#fff'}
            strokeWidth={isSelected ? 2 : 1}
            style={{ cursor: 'pointer' }}
            onClick={(e) => {
              e.stopPropagation();
              onSelect(overlay);
            }}
          />
          {/* Label */}
          {overlay.label_position && (
            <text
              x={overlay.label_position[0]}
              y={overlay.label_position[1]}
              textAnchor="middle"
              dominantBaseline="middle"
              fontSize="12"
              fill="#333"
              pointerEvents="none"
            >
              {overlay.label?.en || overlay.ref}
            </text>
          )}
        </g>
      );
    }

    if (geometry?.type === 'point') {
      return (
        <circle
          key={overlay.id}
          cx={geometry.x}
          cy={geometry.y}
          r={10}
          fill={isSelected ? '#DAA520' : '#1890ff'}
          stroke="#fff"
          strokeWidth={2}
          style={{ cursor: 'pointer' }}
          onClick={(e) => {
            e.stopPropagation();
            onSelect(overlay);
          }}
        />
      );
    }

    return null;
  };

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        background: '#e8e8e8',
        overflow: 'hidden',
        cursor: isPanning ? 'grabbing' : 'grab',
      }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onWheel={handleWheel}
    >
      <svg
        ref={svgRef}
        viewBox={viewBox}
        style={{
          width: '100%',
          height: '100%',
          transform: `translate(${transform.x}px, ${transform.y}px) scale(${transform.scale})`,
          transformOrigin: 'center',
        }}
      >
        {/* Background */}
        <rect
          x={vbX}
          y={vbY}
          width={vbW}
          height={vbH}
          fill="#f5f5f5"
        />

        {/* Overlays */}
        {overlays.map(renderOverlay)}
      </svg>
    </div>
  );
}
```

### Tools Panel

```jsx
// src/components/editor/ToolsPanel.jsx
import React, { useState } from 'react';
import { Input, List, Tag, Typography, Collapse } from 'antd';

const { Search } = Input;
const { Text } = Typography;

export default function ToolsPanel({ overlays, selectedId, onSelect }) {
  const [search, setSearch] = useState('');

  // Group overlays by type
  const grouped = overlays.reduce((acc, o) => {
    const type = o.overlay_type;
    if (!acc[type]) acc[type] = [];
    acc[type].push(o);
    return acc;
  }, {});

  const filterOverlays = (items) => {
    if (!search) return items;
    return items.filter(o =>
      o.ref.toLowerCase().includes(search.toLowerCase()) ||
      o.label?.en?.toLowerCase().includes(search.toLowerCase())
    );
  };

  return (
    <div style={{ padding: 16 }}>
      <Search
        placeholder="Search overlays..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        style={{ marginBottom: 16 }}
      />

      <Collapse defaultActiveKey={['zone', 'unit', 'poi']}>
        {Object.entries(grouped).map(([type, items]) => (
          <Collapse.Panel
            key={type}
            header={
              <span>
                {type.toUpperCase()}
                <Tag style={{ marginLeft: 8 }}>{items.length}</Tag>
              </span>
            }
          >
            <List
              size="small"
              dataSource={filterOverlays(items)}
              renderItem={(item) => (
                <List.Item
                  onClick={() => onSelect(item)}
                  style={{
                    cursor: 'pointer',
                    background: item.id === selectedId ? '#e6f7ff' : undefined,
                    padding: '8px 12px',
                    marginBottom: 4,
                    borderRadius: 4,
                  }}
                >
                  <Text ellipsis style={{ maxWidth: 180 }}>
                    {item.label?.en || item.ref}
                  </Text>
                </List.Item>
              )}
            />
          </Collapse.Panel>
        ))}
      </Collapse>
    </div>
  );
}
```

## Acceptance Criteria

- [ ] Canvas renders overlays (paths and points)
- [ ] Can pan canvas with mouse drag
- [ ] Can zoom canvas with mouse wheel
- [ ] Selected overlay has distinct styling
- [ ] Click on overlay triggers onSelect callback
- [ ] Tools panel shows overlays grouped by type
- [ ] Search filters overlays by ref or label
- [ ] Selected overlay highlighted in tools panel
