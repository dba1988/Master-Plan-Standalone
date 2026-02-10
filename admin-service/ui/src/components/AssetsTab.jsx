/**
 * Assets Tab
 *
 * Upload and manage assets (base maps, SVG overlays, icons).
 * Assets belong to projects (not versions) - versions are just release tags.
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Table,
  Button,
  Space,
  Upload,
  Typography,
  Tag,
  message,
  Popconfirm,
  Modal,
  Select,
  Progress,
} from 'antd';
import {
  UploadOutlined,
  DeleteOutlined,
  DownloadOutlined,
  ImportOutlined,
  PictureOutlined,
  FileOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { assetsApi, overlaysApi } from '../services/api';

const { Text } = Typography;

const ASSET_TYPES = [
  { value: 'base_map', label: 'Base Map', color: 'blue' },
  { value: 'overlay_svg', label: 'Overlay SVG', color: 'green' },
  { value: 'icon', label: 'Icon', color: 'purple' },
  { value: 'other', label: 'Other', color: 'default' },
];

// Default levels - will be replaced by dynamic fetch
const DEFAULT_LEVELS = [
  { value: 'project', label: 'Project' },
];

export default function AssetsTab({ projectSlug, isDraft }) {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [selectedLevel, setSelectedLevel] = useState('project');
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [importAsset, setImportAsset] = useState(null);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['assets', projectSlug],
    queryFn: () => assetsApi.list(projectSlug),
  });

  // Fetch available levels (project + zones from imported overlays)
  const { data: levelsData } = useQuery({
    queryKey: ['levels', projectSlug],
    queryFn: () => overlaysApi.getLevels(projectSlug),
  });

  // Fetch overlays to check import status
  const { data: overlaysData } = useQuery({
    queryKey: ['overlays', projectSlug],
    queryFn: () => overlaysApi.list(projectSlug, { limit: 1000 }),
  });

  const levels = levelsData?.levels || DEFAULT_LEVELS;

  // Helper to check if an SVG asset has been imported
  const getImportStatus = (asset) => {
    if (asset.asset_type !== 'overlay_svg') return null;
    const overlays = overlaysData?.overlays || [];

    if (asset.level === 'project') {
      // Check for zone overlays
      const zones = overlays.filter(o => o.overlay_type === 'zone');
      return zones.length > 0 ? { imported: true, count: zones.length, type: 'zones' } : { imported: false };
    } else {
      // Check for unit overlays in this source_level
      const units = overlays.filter(o => o.overlay_type === 'unit' && o.source_level === asset.level);
      return units.length > 0 ? { imported: true, count: units.length, type: 'units' } : { imported: false };
    }
  };

  const deleteMutation = useMutation({
    mutationFn: (assetId) => assetsApi.delete(projectSlug, assetId),
    onSuccess: () => {
      message.success('Asset deleted');
      queryClient.invalidateQueries({ queryKey: ['assets', projectSlug] });
      queryClient.invalidateQueries({ queryKey: ['overlays', projectSlug] });
      queryClient.invalidateQueries({ queryKey: ['levels', projectSlug] });
    },
    onError: (error) => {
      message.error(error.response?.data?.detail || 'Failed to delete asset');
    },
  });

  const importSvgMutation = useMutation({
    mutationFn: ({ assetId, params }) =>
      assetsApi.importSvg(projectSlug, assetId, params),
    onSuccess: (data) => {
      message.success(`Imported ${data.created} overlays, updated ${data.updated}`);
      setImportModalOpen(false);
      setImportAsset(null);
      queryClient.invalidateQueries({ queryKey: ['overlays', projectSlug] });
      queryClient.invalidateQueries({ queryKey: ['levels', projectSlug] });
    },
    onError: (error) => {
      message.error(error.response?.data?.detail || 'Failed to import SVG');
    },
  });

  const handleUpload = async (file, assetType) => {
    setUploading(true);
    setUploadProgress(0);

    try {
      // Get upload URL
      const { upload_url, storage_path } = await assetsApi.getUploadUrl(
        projectSlug,
        {
          filename: file.name,
          asset_type: assetType,
          content_type: file.type,
        }
      );

      setUploadProgress(30);

      // Upload to storage
      await fetch(upload_url, {
        method: 'PUT',
        body: file,
        headers: {
          'Content-Type': file.type,
        },
      });

      setUploadProgress(70);

      // Confirm upload
      await assetsApi.confirmUpload(projectSlug, {
        storage_path,
        filename: file.name,
        asset_type: assetType,
        file_size: file.size,
        level: selectedLevel,
      });

      setUploadProgress(100);
      message.success(`${assetType === 'base_map' ? 'Base map' : 'Overlay SVG'} uploaded successfully`);
      setUploadModalOpen(false);
      queryClient.invalidateQueries({ queryKey: ['assets', projectSlug] });
      // Refresh levels in case new zones were imported
      queryClient.invalidateQueries({ queryKey: ['levels', projectSlug] });
    } catch (error) {
      message.error(error.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }

    return false; // Prevent default upload
  };

  const handleImportSvg = (asset) => {
    setImportAsset(asset);
    setImportModalOpen(true);
  };

  const confirmImport = () => {
    // Determine overlay type based on asset level
    // project level → zone, zone-* level → unit
    const overlayType = importAsset?.level === 'project' ? 'zone' : 'unit';
    const layer = importAsset?.level || 'project';

    importSvgMutation.mutate({
      assetId: importAsset.id,
      params: { overlay_type: overlayType, layer },
    });
  };

  const assets = (data?.assets || []).sort((a, b) => {
    // Sort by level, then by filename
    const levelA = a.level || 'zzz';
    const levelB = b.level || 'zzz';
    if (levelA !== levelB) return levelA.localeCompare(levelB);
    return a.filename.localeCompare(b.filename);
  });

  const columns = [
    {
      title: 'Level',
      dataIndex: 'level',
      key: 'level',
      width: 120,
      render: (level) => {
        if (!level) return <Text type="secondary">-</Text>;
        const levelConfig = levels.find((l) => l.value === level);
        const color = level === 'project' ? 'gold' : 'cyan';
        return <Tag color={color}>{levelConfig?.label || level}</Tag>;
      },
      sorter: (a, b) => (a.level || '').localeCompare(b.level || ''),
    },
    {
      title: 'Filename',
      dataIndex: 'filename',
      key: 'filename',
      render: (filename) => <Text strong>{filename}</Text>,
    },
    {
      title: 'Type',
      dataIndex: 'asset_type',
      key: 'asset_type',
      render: (type) => {
        const assetType = ASSET_TYPES.find((t) => t.value === type);
        return <Tag color={assetType?.color || 'default'}>{assetType?.label || type}</Tag>;
      },
    },
    {
      title: 'Size',
      dataIndex: 'file_size',
      key: 'file_size',
      render: (size) => {
        if (size < 1024) return `${size} B`;
        if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
        return `${(size / 1024 / 1024).toFixed(1)} MB`;
      },
    },
    {
      title: 'Uploaded',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => new Date(date).toLocaleDateString(),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 200,
      render: (_, record) => {
        const importStatus = getImportStatus(record);

        return (
          <Space>
            <Button
              type="text"
              icon={<DownloadOutlined />}
              onClick={() => window.open(`/api/projects/${projectSlug}/assets/${record.id}/download`)}
            />
            {record.asset_type === 'overlay_svg' && isDraft && (
              <>
                {importStatus?.imported && (
                  <Tag color="success" icon={<CheckCircleOutlined />}>
                    {importStatus.count} {importStatus.type}
                  </Tag>
                )}
                <Button
                  type="text"
                  icon={<ImportOutlined />}
                  onClick={() => handleImportSvg(record)}
                >
                  {importStatus?.imported ? 'Re-import' : 'Import'}
                </Button>
              </>
            )}
            {isDraft && (
              <Popconfirm
                title="Delete asset?"
                description={importStatus?.imported ? `This will also delete ${importStatus.count} ${importStatus.type}` : undefined}
                onConfirm={() => deleteMutation.mutate(record.id)}
                okText="Delete"
                okButtonProps={{ danger: true }}
              >
                <Button type="text" danger icon={<DeleteOutlined />} />
              </Popconfirm>
            )}
          </Space>
        );
      },
    },
  ];

  return (
    <div>
      {isDraft && (
        <div style={{ marginBottom: 16 }}>
          <Button
            type="primary"
            icon={<UploadOutlined />}
            onClick={() => setUploadModalOpen(true)}
          >
            Upload Asset
          </Button>
        </div>
      )}

      <Table
        columns={columns}
        dataSource={assets}
        rowKey="id"
        loading={isLoading}
        pagination={false}
      />

      {/* Upload Asset Modal */}
      <Modal
        title="Upload Asset"
        open={uploadModalOpen}
        onCancel={() => setUploadModalOpen(false)}
        footer={null}
        width={500}
      >
        <div style={{ marginBottom: 20 }}>
          <Text>Select the hierarchy level for this asset:</Text>
          <Select
            value={selectedLevel}
            onChange={setSelectedLevel}
            options={levels}
            style={{ width: '100%', marginTop: 8 }}
            placeholder="Select level"
          />
          {levels.length === 1 && (
            <Text type="secondary" style={{ display: 'block', marginTop: 8, fontSize: 12 }}>
              Tip: Upload and import a project-level SVG first to discover zones
            </Text>
          )}
        </div>

        {uploading ? (
          <div style={{ textAlign: 'center', padding: 20 }}>
            <Progress percent={uploadProgress} />
            <Text type="secondary">Uploading...</Text>
          </div>
        ) : (
          <div style={{ display: 'flex', gap: 16 }}>
            {/* Base Map Upload */}
            <div
              style={{
                flex: 1,
                border: '1px dashed #d9d9d9',
                borderRadius: 8,
                padding: 20,
                textAlign: 'center',
                cursor: 'pointer',
                transition: 'border-color 0.3s',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = '#1890ff')}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = '#d9d9d9')}
            >
              <Upload
                beforeUpload={(file) => handleUpload(file, 'base_map')}
                showUploadList={false}
                accept=".png,.jpg,.jpeg,.webp"
              >
                <div>
                  <PictureOutlined style={{ fontSize: 32, color: '#1890ff', marginBottom: 8 }} />
                  <div style={{ fontWeight: 500, marginBottom: 4 }}>Base Map</div>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    .webp, .jpg, .png
                  </Text>
                </div>
              </Upload>
            </div>

            {/* Overlay SVG Upload */}
            <div
              style={{
                flex: 1,
                border: '1px dashed #d9d9d9',
                borderRadius: 8,
                padding: 20,
                textAlign: 'center',
                cursor: 'pointer',
                transition: 'border-color 0.3s',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = '#52c41a')}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = '#d9d9d9')}
            >
              <Upload
                beforeUpload={(file) => handleUpload(file, 'overlay_svg')}
                showUploadList={false}
                accept=".svg"
              >
                <div>
                  <FileOutlined style={{ fontSize: 32, color: '#52c41a', marginBottom: 8 }} />
                  <div style={{ fontWeight: 500, marginBottom: 4 }}>Overlay SVG</div>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    .svg only
                  </Text>
                </div>
              </Upload>
            </div>
          </div>
        )}
      </Modal>

      {/* Import SVG Modal */}
      <Modal
        title="Import SVG Overlays"
        open={importModalOpen}
        onOk={confirmImport}
        onCancel={() => {
          setImportModalOpen(false);
          setImportAsset(null);
        }}
        confirmLoading={importSvgMutation.isPending}
      >
        <p>
          Import overlays from <strong>{importAsset?.filename}</strong>?
        </p>
        <p>
          Level: <Tag color={importAsset?.level === 'project' ? 'gold' : 'cyan'}>
            {importAsset?.level === 'project' ? 'Project' : importAsset?.level?.replace('zone-', 'Zone ').toUpperCase()}
          </Tag>
        </p>
        <p>
          Overlay type: <Tag color={importAsset?.level === 'project' ? 'orange' : 'blue'}>
            {importAsset?.level === 'project' ? 'Zone' : 'Unit'}
          </Tag>
        </p>
        <p style={{ marginTop: 16 }}>
          <Text type="secondary">
            Each path element in the SVG will be converted to an overlay with its
            geometry and calculated label position.
          </Text>
        </p>
      </Modal>
    </div>
  );
}
