/**
 * Project Detail Page
 *
 * Main workspace for managing a project's versions, assets, overlays, config, and publishing.
 */
import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Card,
  Tabs,
  Typography,
  Button,
  Space,
  Tag,
  Descriptions,
  Spin,
  Empty,
  Select,
  message,
  Breadcrumb,
  Popconfirm,
} from 'antd';
import {
  PlusOutlined,
  HomeOutlined,
  ProjectOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import { projectsApi, versionsApi } from '../services/api';
import AssetsTab from '../components/AssetsTab';
import OverlaysTab from '../components/OverlaysTab';
import ConfigTab from '../components/ConfigTab';
import IntegrationTab from '../components/IntegrationTab';
import PublishTab from '../components/PublishTab';
import ReleaseHistoryTab from '../components/ReleaseHistoryTab';

const { Title, Text } = Typography;

export default function ProjectDetailPage() {
  const { slug } = useParams();
  const [selectedVersion, setSelectedVersion] = useState(null);
  const queryClient = useQueryClient();

  const { data: project, isLoading } = useQuery({
    queryKey: ['project', slug],
    queryFn: () => projectsApi.get(slug),
  });

  const createVersionMutation = useMutation({
    mutationFn: () => versionsApi.create(slug),
    onSuccess: (data) => {
      message.success('Version created');
      queryClient.invalidateQueries({ queryKey: ['project', slug] });
      setSelectedVersion(data.version_number);
    },
    onError: (error) => {
      message.error(error.response?.data?.detail || 'Failed to create version');
    },
  });

  const deleteVersionMutation = useMutation({
    mutationFn: (versionNumber) => versionsApi.delete(slug, versionNumber),
    onSuccess: () => {
      message.success('Draft version deleted');
      queryClient.invalidateQueries({ queryKey: ['project', slug] });
      setSelectedVersion(null);
    },
    onError: (error) => {
      message.error(error.response?.data?.detail || 'Failed to delete version');
    },
  });

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!project) {
    return (
      <Empty description="Project not found">
        <Link to="/projects">
          <Button type="primary">Back to Projects</Button>
        </Link>
      </Empty>
    );
  }

  const versions = project.versions || [];
  const currentVersion =
    versions.find((v) => v.version_number === selectedVersion) ||
    versions.find((v) => v.status === 'draft') ||
    versions[0];

  const versionOptions = versions.map((v) => ({
    value: v.version_number,
    label: (
      <Space>
        <span>Version {v.version_number}</span>
        <Tag color={v.status === 'published' ? 'green' : 'blue'} style={{ marginLeft: 4 }}>
          {v.status}
        </Tag>
      </Space>
    ),
  }));

  const tabItems = currentVersion
    ? [
        {
          key: 'assets',
          label: 'Assets',
          children: (
            <AssetsTab
              projectSlug={slug}
              isDraft={currentVersion.status === 'draft'}
            />
          ),
        },
        {
          key: 'overlays',
          label: 'Overlays',
          children: (
            <OverlaysTab
              projectSlug={slug}
              isDraft={currentVersion.status === 'draft'}
            />
          ),
        },
        {
          key: 'config',
          label: 'Config',
          children: (
            <ConfigTab
              projectSlug={slug}
              isDraft={currentVersion.status === 'draft'}
            />
          ),
        },
        {
          key: 'integration',
          label: 'Integration',
          children: <IntegrationTab projectSlug={slug} />,
        },
        {
          key: 'publish',
          label: 'Publish',
          children: (
            <PublishTab
              projectSlug={slug}
              versionNumber={currentVersion.version_number}
              version={currentVersion}
            />
          ),
        },
        {
          key: 'releases',
          label: 'Releases',
          children: <ReleaseHistoryTab projectSlug={slug} />,
        },
      ]
    : [];

  return (
    <div>
      <Breadcrumb
        style={{ marginBottom: 16 }}
        items={[
          { href: '/', title: <HomeOutlined /> },
          { href: '/projects', title: 'Projects' },
          { title: project.name },
        ]}
      />

      <Card style={{ marginBottom: 24 }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
          }}
        >
          <div>
            <Space align="center" style={{ marginBottom: 8 }}>
              <ProjectOutlined style={{ fontSize: 24 }} />
              <Title level={3} style={{ margin: 0 }}>
                {project.name}
              </Title>
            </Space>
            <Text type="secondary">{project.description || 'No description'}</Text>
          </div>

          <Space>
            <Select
              value={currentVersion?.version_number}
              onChange={setSelectedVersion}
              options={versionOptions}
              style={{ width: 180 }}
              placeholder="Select version"
            />
            {currentVersion?.status === 'draft' && (
              <Popconfirm
                title="Delete draft version?"
                description={`This will permanently delete Version ${currentVersion.version_number}. This cannot be undone.`}
                onConfirm={() => deleteVersionMutation.mutate(currentVersion.version_number)}
                okText="Delete"
                okButtonProps={{ danger: true }}
                cancelText="Cancel"
              >
                <Button
                  icon={<DeleteOutlined />}
                  danger
                  loading={deleteVersionMutation.isPending}
                >
                  Delete Draft
                </Button>
              </Popconfirm>
            )}
            <Button
              icon={<PlusOutlined />}
              onClick={() => createVersionMutation.mutate()}
              loading={createVersionMutation.isPending}
            >
              New Version
            </Button>
          </Space>
        </div>

        {currentVersion && (
          <Descriptions size="small" style={{ marginTop: 16 }} column={4}>
            <Descriptions.Item label="Slug">
              <Text code>{project.slug}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="Version">
              {currentVersion.version_number}
            </Descriptions.Item>
            <Descriptions.Item label="Status">
              <Tag color={currentVersion.status === 'published' ? 'green' : 'blue'}>
                {currentVersion.status}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Current Release">
              {project.current_release_id ? (
                <Text code style={{ fontSize: 11 }}>
                  {project.current_release_id}
                </Text>
              ) : (
                <Text type="secondary">None</Text>
              )}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Card>

      {currentVersion ? (
        <Card>
          <Tabs items={tabItems} />
        </Card>
      ) : (
        <Card>
          <Empty description="No versions yet">
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => createVersionMutation.mutate()}
              loading={createVersionMutation.isPending}
            >
              Create First Version
            </Button>
          </Empty>
        </Card>
      )}
    </div>
  );
}
