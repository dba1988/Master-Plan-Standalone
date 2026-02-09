# TASK-017: Basic Editor

**Phase**: 5 - Admin UI
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-007, TASK-016

## Objective

Create a simplified map editor for viewing and editing overlays.

## Files to Create

```
admin-ui/src/
├── pages/
│   └── EditorPage.jsx
└── components/
    └── editor/
        ├── MapCanvas.jsx
        ├── ToolsPanel.jsx
        └── InspectorPanel.jsx
```

## Implementation

### Editor Page (Simplified)
```jsx
// src/pages/EditorPage.jsx
import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Layout, Button, message, Spin, Empty } from 'antd';
import { SaveOutlined } from '@ant-design/icons';
import api from '../services/api';
import MapCanvas from '../components/editor/MapCanvas';
import ToolsPanel from '../components/editor/ToolsPanel';
import InspectorPanel from '../components/editor/InspectorPanel';

const { Sider, Content } = Layout;

export default function EditorPage() {
  const { slug } = useParams();
  const queryClient = useQueryClient();
  const [selectedOverlay, setSelectedOverlay] = useState(null);
  const [overlays, setOverlays] = useState([]);
  const [hasChanges, setHasChanges] = useState(false);

  // Get project and draft version
  const { data: project } = useQuery({
    queryKey: ['project', slug],
    queryFn: () => api.get(`/projects/${slug}`).then(res => res.data),
  });

  const draftVersion = project?.versions?.find(v => v.status === 'draft')?.version_number;

  // Fetch overlays
  const { data: overlaysData, isLoading } = useQuery({
    queryKey: ['overlays', slug, draftVersion],
    queryFn: () =>
      api.get(`/projects/${slug}/versions/${draftVersion}/overlays`)
        .then(res => res.data),
    enabled: !!draftVersion,
  });

  // Fetch config for viewBox
  const { data: config } = useQuery({
    queryKey: ['config', slug, draftVersion],
    queryFn: () =>
      api.get(`/projects/${slug}/versions/${draftVersion}/config`)
        .then(res => res.data),
    enabled: !!draftVersion,
  });

  // Initialize overlays from API
  useEffect(() => {
    if (overlaysData?.overlays) {
      setOverlays(overlaysData.overlays);
    }
  }, [overlaysData]);

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: (updates) =>
      api.post(`/projects/${slug}/versions/${draftVersion}/overlays/bulk`, {
        overlays: updates.map(o => ({
          overlay_type: o.overlay_type,
          ref: o.ref,
          geometry: o.geometry,
          label: o.label,
          label_position: o.label_position,
          props: o.props,
          style_override: o.style_override,
        })),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries(['overlays', slug]);
      message.success('Changes saved');
      setHasChanges(false);
    },
    onError: () => {
      message.error('Failed to save changes');
    },
  });

  const handleOverlayUpdate = (id, updates) => {
    setOverlays(prev =>
      prev.map(o =>
        o.id === id ? { ...o, ...updates } : o
      )
    );
    setHasChanges(true);
  };

  const handleSave = () => {
    const changedOverlays = overlays.filter(o => {
      const original = overlaysData?.overlays?.find(orig => orig.id === o.id);
      return JSON.stringify(o) !== JSON.stringify(original);
    });

    if (changedOverlays.length > 0) {
      saveMutation.mutate(changedOverlays);
    }
  };

  if (!draftVersion) {
    return <Empty description="No draft version available" />;
  }

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <Layout style={{ height: 'calc(100vh - 180px)', background: '#fff' }}>
      {/* Left Panel - Tools */}
      <Sider width={250} theme="light" style={{ borderRight: '1px solid #f0f0f0' }}>
        <ToolsPanel
          overlays={overlays}
          selectedId={selectedOverlay?.id}
          onSelect={(overlay) => setSelectedOverlay(overlay)}
        />
      </Sider>

      {/* Center - Canvas */}
      <Content style={{ position: 'relative', overflow: 'hidden' }}>
        <MapCanvas
          overlays={overlays}
          viewBox={config?.default_view_box || '0 0 4096 4096'}
          selectedId={selectedOverlay?.id}
          onSelect={(overlay) => setSelectedOverlay(overlay)}
        />

        {/* Save Button */}
        <Button
          type="primary"
          icon={<SaveOutlined />}
          onClick={handleSave}
          loading={saveMutation.isPending}
          disabled={!hasChanges}
          style={{
            position: 'absolute',
            top: 16,
            right: 16,
            zIndex: 10,
          }}
        >
          Save Changes
        </Button>
      </Content>

      {/* Right Panel - Inspector */}
      <Sider width={300} theme="light" style={{ borderLeft: '1px solid #f0f0f0' }}>
        <InspectorPanel
          overlay={selectedOverlay}
          onUpdate={(updates) => {
            if (selectedOverlay) {
              handleOverlayUpdate(selectedOverlay.id, updates);
              setSelectedOverlay({ ...selectedOverlay, ...updates });
            }
          }}
        />
      </Sider>
    </Layout>
  );
}
```

### Map Canvas
```jsx
// src/components/editor/MapCanvas.jsx
import React, { useRef, useEffect, useState } from 'react';

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
        {overlays.map((overlay) => {
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
        })}
      </svg>
    </div>
  );
}
```

### Tools Panel
```jsx
// src/components/editor/ToolsPanel.jsx
import React from 'react';
import { Input, List, Tag, Typography, Collapse } from 'antd';

const { Search } = Input;
const { Text } = Typography;

export default function ToolsPanel({ overlays, selectedId, onSelect }) {
  const [search, setSearch] = React.useState('');

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

### Inspector Panel
```jsx
// src/components/editor/InspectorPanel.jsx
import React from 'react';
import { Form, Input, InputNumber, Typography, Divider, Empty, Tag } from 'antd';

const { Title, Text } = Typography;

export default function InspectorPanel({ overlay, onUpdate }) {
  if (!overlay) {
    return (
      <div style={{ padding: 24 }}>
        <Empty description="Select an overlay to edit" />
      </div>
    );
  }

  return (
    <div style={{ padding: 16 }}>
      <Title level={5}>Properties</Title>

      <div style={{ marginBottom: 16 }}>
        <Tag color="blue">{overlay.overlay_type}</Tag>
      </div>

      <Form layout="vertical" size="small">
        <Form.Item label="Reference ID">
          <Input value={overlay.ref} disabled />
        </Form.Item>

        <Form.Item label="Label (English)">
          <Input
            value={overlay.label?.en || ''}
            onChange={(e) =>
              onUpdate({
                label: { ...overlay.label, en: e.target.value },
              })
            }
          />
        </Form.Item>

        <Form.Item label="Label (Arabic)">
          <Input
            value={overlay.label?.ar || ''}
            dir="rtl"
            onChange={(e) =>
              onUpdate({
                label: { ...overlay.label, ar: e.target.value },
              })
            }
          />
        </Form.Item>

        <Divider>Label Position</Divider>

        <div style={{ display: 'flex', gap: 8 }}>
          <Form.Item label="X" style={{ flex: 1 }}>
            <InputNumber
              value={overlay.label_position?.[0]}
              style={{ width: '100%' }}
              onChange={(val) =>
                onUpdate({
                  label_position: [val, overlay.label_position?.[1] || 0],
                })
              }
            />
          </Form.Item>
          <Form.Item label="Y" style={{ flex: 1 }}>
            <InputNumber
              value={overlay.label_position?.[1]}
              style={{ width: '100%' }}
              onChange={(val) =>
                onUpdate({
                  label_position: [overlay.label_position?.[0] || 0, val],
                })
              }
            />
          </Form.Item>
        </div>
      </Form>
    </div>
  );
}
```

## Acceptance Criteria

- [ ] Canvas renders overlays correctly
- [ ] Can pan and zoom canvas
- [ ] Can select overlays
- [ ] Inspector shows selected overlay properties
- [ ] Can edit label text
- [ ] Can edit label position
- [ ] Save updates overlays via API
