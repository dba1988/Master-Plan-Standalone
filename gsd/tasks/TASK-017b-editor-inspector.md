# TASK-017b: Editor Inspector + Page Integration

**Phase**: 5 - Admin UI
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-017a (canvas + tools)
**Blocks**: TASK-019 (publish page)
**Estimated Time**: 2-3 hours

## Objective

Create the inspector panel for editing overlay properties and integrate all editor components into the EditorPage.

## Scope

This task covers the inspector panel and EditorPage. Canvas and tools are in TASK-017a.

## Files to Create

```
admin-service/ui/src/
├── pages/
│   └── EditorPage.jsx
└── components/
    └── editor/
        └── InspectorPanel.jsx
```

## Implementation

### Inspector Panel

```jsx
// src/components/editor/InspectorPanel.jsx
import React from 'react';
import { Form, Input, InputNumber, Typography, Divider, Empty, Tag } from 'antd';

const { Title } = Typography;

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

        {/* Props section for status integration */}
        {overlay.props?.status && (
          <>
            <Divider>Status</Divider>
            <Form.Item label="Current Status">
              <Tag color={getStatusColor(overlay.props.status)}>
                {overlay.props.status}
              </Tag>
            </Form.Item>
          </>
        )}
      </Form>
    </div>
  );
}

function getStatusColor(status) {
  // 5 canonical statuses per STATUS-TAXONOMY.md
  const colors = {
    available: 'green',
    reserved: 'orange',
    sold: 'red',
    hidden: 'default',
    unreleased: 'default',
  };
  return colors[status] || 'default';
}
```

### Editor Page

```jsx
// src/pages/EditorPage.jsx
import React, { useState, useEffect } from 'react';
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

## Acceptance Criteria

- [ ] Inspector shows selected overlay properties
- [ ] Can edit label text (English and Arabic)
- [ ] Can edit label position (X, Y)
- [ ] Reference ID is read-only
- [ ] Empty state shown when no overlay selected
- [ ] Status displayed if present in props
- [ ] EditorPage integrates all components
- [ ] Save button enabled when changes exist
- [ ] Save mutation updates overlays via API
- [ ] Success/error messages shown after save
