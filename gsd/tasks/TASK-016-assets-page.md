# TASK-016: Asset Management Page

**Phase**: 5 - Admin UI
**Status**: [ ] Not Started
**Priority**: P1 - High
**Depends On**: TASK-006, TASK-015

## Objective

Create the asset upload and management interface.

## Files to Create

```
admin-service/ui/src/pages/
└── AssetsPage.jsx
```

## Implementation

```jsx
// src/pages/AssetsPage.jsx
import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Card, Upload, Button, List, Typography, Tag, Space,
  message, Popconfirm, Progress, Empty, Select
} from 'antd';
import {
  InboxOutlined, DeleteOutlined, EyeOutlined,
  FileImageOutlined, FileOutlined
} from '@ant-design/icons';
import api from '../services/api';

const { Dragger } = Upload;
const { Title, Text } = Typography;

const ASSET_TYPES = [
  { value: 'base_map', label: 'Base Map', accept: '.png,.webp,.jpg,.jpeg' },
  { value: 'overlay_svg', label: 'SVG Overlay', accept: '.svg' },
  { value: 'icon', label: 'Icon', accept: '.svg,.png' },
  { value: 'other', label: 'Other', accept: '*' },
];

export default function AssetsPage() {
  const { slug } = useParams();
  const queryClient = useQueryClient();
  const [selectedType, setSelectedType] = useState('base_map');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  // Get current draft version
  const { data: project } = useQuery({
    queryKey: ['project', slug],
    queryFn: () => api.get(`/projects/${slug}`).then(res => res.data),
  });

  const draftVersion = project?.versions?.find(v => v.status === 'draft')?.version_number;

  // Fetch assets
  const { data: assetsData, isLoading } = useQuery({
    queryKey: ['assets', slug, draftVersion],
    queryFn: () =>
      api.get(`/projects/${slug}/versions/${draftVersion}/assets`)
        .then(res => res.data),
    enabled: !!draftVersion,
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (assetId) =>
      api.delete(`/projects/${slug}/versions/${draftVersion}/assets/${assetId}`),
    onSuccess: () => {
      queryClient.invalidateQueries(['assets', slug]);
      message.success('Asset deleted');
    },
    onError: () => {
      message.error('Failed to delete asset');
    },
  });

  // Custom upload handler
  const customUpload = async ({ file, onSuccess, onError }) => {
    setUploading(true);
    setUploadProgress(0);

    try {
      // Step 1: Get signed URL
      const urlResponse = await api.post(
        `/projects/${slug}/versions/${draftVersion}/assets/upload-url`,
        {
          filename: file.name,
          asset_type: selectedType,
          content_type: file.type,
        }
      );

      const { upload_url, storage_path } = urlResponse.data;
      setUploadProgress(25);

      // Step 2: Upload to storage
      await fetch(upload_url, {
        method: 'PUT',
        body: file,
        headers: {
          'Content-Type': file.type,
        },
      });
      setUploadProgress(75);

      // Step 3: Confirm upload
      await api.post(
        `/projects/${slug}/versions/${draftVersion}/assets/confirm`,
        {
          storage_path,
          asset_type: selectedType,
          filename: file.name,
          file_size: file.size,
          metadata: {
            originalName: file.name,
            type: file.type,
          },
        }
      );
      setUploadProgress(100);

      queryClient.invalidateQueries(['assets', slug]);
      message.success(`${file.name} uploaded successfully`);
      onSuccess();

    } catch (error) {
      console.error('Upload error:', error);
      message.error(`Failed to upload ${file.name}`);
      onError(error);
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const getAssetIcon = (type) => {
    switch (type) {
      case 'base_map':
        return <FileImageOutlined style={{ fontSize: 24, color: '#1890ff' }} />;
      case 'overlay_svg':
        return <FileOutlined style={{ fontSize: 24, color: '#52c41a' }} />;
      default:
        return <FileOutlined style={{ fontSize: 24 }} />;
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '-';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (!draftVersion) {
    return (
      <Empty description="No draft version available" />
    );
  }

  return (
    <div>
      <Card title="Upload Assets" style={{ marginBottom: 24 }}>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <div>
            <Text strong>Asset Type:</Text>
            <Select
              value={selectedType}
              onChange={setSelectedType}
              style={{ width: 200, marginLeft: 16 }}
              options={ASSET_TYPES}
            />
          </div>

          <Dragger
            customRequest={customUpload}
            showUploadList={false}
            accept={ASSET_TYPES.find(t => t.value === selectedType)?.accept}
            disabled={uploading}
          >
            <p className="ant-upload-drag-icon">
              <InboxOutlined />
            </p>
            <p className="ant-upload-text">
              Click or drag file to upload
            </p>
            <p className="ant-upload-hint">
              {ASSET_TYPES.find(t => t.value === selectedType)?.label} -
              Accepted: {ASSET_TYPES.find(t => t.value === selectedType)?.accept}
            </p>
          </Dragger>

          {uploading && (
            <Progress percent={uploadProgress} status="active" />
          )}
        </Space>
      </Card>

      <Card title="Uploaded Assets">
        {isLoading ? (
          <div style={{ textAlign: 'center', padding: 24 }}>Loading...</div>
        ) : assetsData?.assets?.length === 0 ? (
          <Empty description="No assets uploaded yet" />
        ) : (
          <List
            itemLayout="horizontal"
            dataSource={assetsData?.assets || []}
            renderItem={(asset) => (
              <List.Item
                actions={[
                  <Button
                    type="text"
                    icon={<EyeOutlined />}
                    onClick={() => window.open(asset.storage_path, '_blank')}
                  >
                    View
                  </Button>,
                  <Popconfirm
                    title="Delete this asset?"
                    onConfirm={() => deleteMutation.mutate(asset.id)}
                    okText="Yes"
                    cancelText="No"
                  >
                    <Button
                      type="text"
                      danger
                      icon={<DeleteOutlined />}
                    >
                      Delete
                    </Button>
                  </Popconfirm>,
                ]}
              >
                <List.Item.Meta
                  avatar={getAssetIcon(asset.asset_type)}
                  title={asset.filename}
                  description={
                    <Space>
                      <Tag>{asset.asset_type}</Tag>
                      <Text type="secondary">
                        {formatFileSize(asset.file_size)}
                      </Text>
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Card>
    </div>
  );
}
```

## Acceptance Criteria

- [ ] Can select asset type before upload
- [ ] Drag and drop upload works
- [ ] Progress shown during upload
- [ ] Assets list displays correctly
- [ ] Can delete assets
- [ ] File type validation works
