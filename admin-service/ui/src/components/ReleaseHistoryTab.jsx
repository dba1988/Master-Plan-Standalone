/**
 * Release History Tab
 *
 * Shows all published releases for a project with their manifests.
 */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Table,
  Button,
  Space,
  Typography,
  Tag,
  Card,
  Modal,
  Descriptions,
  Spin,
  Empty,
  Statistic,
  Row,
  Col,
  Tabs,
  message,
} from 'antd';
import {
  EyeOutlined,
  CheckCircleOutlined,
  LinkOutlined,
  HistoryOutlined,
  CopyOutlined,
  CodeOutlined,
} from '@ant-design/icons';
import { releasesApi } from '../services/api';

const { Text, Title } = Typography;

export default function ReleaseHistoryTab({ projectSlug }) {
  const [selectedRelease, setSelectedRelease] = useState(null);
  const [manifestModalOpen, setManifestModalOpen] = useState(false);
  const [manifestData, setManifestData] = useState(null);
  const [loadingManifest, setLoadingManifest] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['releases', projectSlug],
    queryFn: () => releasesApi.getHistory(projectSlug),
  });

  const handleViewManifest = async (release) => {
    setSelectedRelease(release);
    setManifestModalOpen(true);
    setLoadingManifest(true);

    try {
      const manifest = await releasesApi.getManifest(projectSlug, release.release_id);
      setManifestData(manifest);
    } catch (error) {
      console.error('Failed to load manifest:', error);
      setManifestData(null);
    } finally {
      setLoadingManifest(false);
    }
  };

  const handleCopyUrl = async (release) => {
    try {
      const { url } = await releasesApi.getUrl(projectSlug, release.release_id);
      await navigator.clipboard.writeText(url);
      message.success('URL copied to clipboard');
    } catch (error) {
      console.error('Failed to get URL:', error);
      message.error('Failed to copy URL');
    }
  };

  const handleCopyManifest = () => {
    if (manifestData) {
      navigator.clipboard.writeText(JSON.stringify(manifestData, null, 2));
      message.success('Manifest JSON copied to clipboard');
    }
  };

  const releases = data?.releases || [];
  const currentReleaseId = data?.current_release_id;

  const columns = [
    {
      title: 'Version',
      dataIndex: 'version_number',
      key: 'version_number',
      width: 100,
      render: (v) => <Text strong>v{v}</Text>,
    },
    {
      title: 'Release ID',
      dataIndex: 'release_id',
      key: 'release_id',
      render: (id, record) => (
        <Space>
          <Text code style={{ fontSize: 11 }}>{id}</Text>
          {record.is_current && (
            <Tag color="green" icon={<CheckCircleOutlined />}>
              Current
            </Tag>
          )}
        </Space>
      ),
    },
    {
      title: 'Published',
      dataIndex: 'published_at',
      key: 'published_at',
      width: 180,
      render: (date) => date ? new Date(date).toLocaleString() : '-',
    },
    {
      title: 'Published By',
      dataIndex: 'published_by',
      key: 'published_by',
      width: 180,
      render: (email) => email || <Text type="secondary">-</Text>,
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 150,
      render: (_, record) => (
        <Space>
          <Button
            type="text"
            icon={<EyeOutlined />}
            onClick={() => handleViewManifest(record)}
          >
            View
          </Button>
          <Button
            type="text"
            icon={<LinkOutlined />}
            onClick={() => handleCopyUrl(record)}
            title="Copy presigned URL"
          />
        </Space>
      ),
    },
  ];

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Spin />
      </div>
    );
  }

  if (releases.length === 0) {
    return (
      <Card>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="No releases yet"
        >
          <Text type="secondary">
            Publish a version to create your first release.
          </Text>
        </Empty>
      </Card>
    );
  }

  return (
    <div>
      <Card
        title={
          <Space>
            <HistoryOutlined />
            Release History
          </Space>
        }
        extra={
          currentReleaseId && (
            <Text type="secondary">
              Current: <Text code>{currentReleaseId}</Text>
            </Text>
          )
        }
      >
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={8}>
            <Statistic title="Total Releases" value={releases.length} />
          </Col>
          <Col span={8}>
            <Statistic
              title="Latest Version"
              value={releases[0]?.version_number || 0}
              prefix="v"
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="First Release"
              value={releases.length > 0 ? new Date(releases[releases.length - 1]?.published_at).toLocaleDateString() : '-'}
            />
          </Col>
        </Row>

        <Table
          columns={columns}
          dataSource={releases}
          rowKey="release_id"
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `${total} releases`,
          }}
        />
      </Card>

      {/* Manifest Modal */}
      <Modal
        title={
          <Space>
            <Text>Release Manifest</Text>
            {selectedRelease && (
              <Tag color="blue">v{selectedRelease.version_number}</Tag>
            )}
          </Space>
        }
        open={manifestModalOpen}
        onCancel={() => {
          setManifestModalOpen(false);
          setSelectedRelease(null);
          setManifestData(null);
        }}
        footer={null}
        width={800}
      >
        {loadingManifest ? (
          <div style={{ textAlign: 'center', padding: 48 }}>
            <Spin />
          </div>
        ) : manifestData ? (
          <Tabs
            items={[
              {
                key: 'summary',
                label: 'Summary',
                children: (
                  <div>
                    <Descriptions column={2} size="small" style={{ marginBottom: 16 }}>
                      <Descriptions.Item label="Release ID">
                        <Text code>{manifestData.release_id}</Text>
                      </Descriptions.Item>
                      <Descriptions.Item label="Published At">
                        {new Date(manifestData.published_at).toLocaleString()}
                      </Descriptions.Item>
                      <Descriptions.Item label="Published By">
                        {manifestData.published_by}
                      </Descriptions.Item>
                      <Descriptions.Item label="Checksum">
                        <Text code style={{ fontSize: 10 }}>
                          {manifestData.checksum?.substring(0, 30)}...
                        </Text>
                      </Descriptions.Item>
                    </Descriptions>

                    <Card size="small" title="Configuration" style={{ marginBottom: 16 }}>
                      <Descriptions column={2} size="small">
                        <Descriptions.Item label="View Box">
                          {manifestData.config?.default_view_box}
                        </Descriptions.Item>
                        <Descriptions.Item label="Default Locale">
                          {manifestData.config?.default_locale}
                        </Descriptions.Item>
                        <Descriptions.Item label="Zoom Range">
                          {manifestData.config?.default_zoom?.min} - {manifestData.config?.default_zoom?.max}
                        </Descriptions.Item>
                        <Descriptions.Item label="Supported Locales">
                          {manifestData.config?.supported_locales?.join(', ')}
                        </Descriptions.Item>
                      </Descriptions>
                    </Card>

                    {manifestData.tiles && (
                      <Card size="small" title="Tiles" style={{ marginBottom: 16 }}>
                        <Descriptions column={3} size="small">
                          <Descriptions.Item label="Dimensions">
                            {manifestData.tiles.width}x{manifestData.tiles.height}
                          </Descriptions.Item>
                          <Descriptions.Item label="Tile Size">
                            {manifestData.tiles.tile_size}px
                          </Descriptions.Item>
                          <Descriptions.Item label="Levels">
                            {manifestData.tiles.levels}
                          </Descriptions.Item>
                        </Descriptions>
                      </Card>
                    )}

                    <Card size="small" title="Overlays">
                      <Row gutter={16}>
                        <Col span={8}>
                          <Statistic
                            title="Total"
                            value={manifestData.overlays?.length || 0}
                          />
                        </Col>
                        <Col span={8}>
                          <Statistic
                            title="Zones"
                            value={manifestData.overlays?.filter(o => o.overlay_type === 'zone').length || 0}
                          />
                        </Col>
                        <Col span={8}>
                          <Statistic
                            title="Units"
                            value={manifestData.overlays?.filter(o => o.overlay_type === 'unit').length || 0}
                          />
                        </Col>
                      </Row>
                    </Card>
                  </div>
                ),
              },
              {
                key: 'json',
                label: (
                  <Space>
                    <CodeOutlined />
                    Raw JSON
                  </Space>
                ),
                children: (
                  <div>
                    <div style={{ marginBottom: 12, textAlign: 'right' }}>
                      <Button
                        icon={<CopyOutlined />}
                        onClick={handleCopyManifest}
                        size="small"
                      >
                        Copy JSON
                      </Button>
                    </div>
                    <pre
                      style={{
                        background: '#f5f5f5',
                        padding: 16,
                        borderRadius: 6,
                        maxHeight: 500,
                        overflow: 'auto',
                        fontSize: 12,
                        lineHeight: 1.5,
                      }}
                    >
                      {JSON.stringify(manifestData, null, 2)}
                    </pre>
                  </div>
                ),
              },
            ]}
          />
        ) : (
          <Empty description="Failed to load manifest" />
        )}
      </Modal>
    </div>
  );
}
