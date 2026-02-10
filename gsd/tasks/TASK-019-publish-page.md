# TASK-019: Publish Page

**Phase**: 5 - Admin UI
**Status**: [x] Complete
**Priority**: P0 - Critical
**Depends On**: TASK-013b (publish workflow), TASK-015

## Objective

Create the build and publish workflow UI.

## Files to Create

```
admin-service/ui/src/pages/
└── PublishPage.jsx
```

## Implementation

```jsx
// src/pages/PublishPage.jsx
import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Card, Button, Progress, Steps, Typography, Alert, Space,
  Select, Tag, Descriptions, Timeline, message
} from 'antd';
import {
  CloudUploadOutlined, CheckCircleOutlined, CloseCircleOutlined,
  LoadingOutlined, ClockCircleOutlined
} from '@ant-design/icons';
import api from '../services/api';

const { Title, Text, Paragraph } = Typography;
const { Step } = Steps;

export default function PublishPage() {
  const { slug } = useParams();
  const queryClient = useQueryClient();
  const [targetEnv, setTargetEnv] = useState('production');
  const [activeJobId, setActiveJobId] = useState(null);

  // Fetch project
  const { data: project } = useQuery({
    queryKey: ['project', slug],
    queryFn: () => api.get(`/projects/${slug}`).then(res => res.data),
  });

  const draftVersion = project?.versions?.find(v => v.status === 'draft');
  const publishedVersion = project?.versions?.find(v => v.status === 'published');

  // Fetch job status (polling)
  const { data: job, isLoading: jobLoading } = useQuery({
    queryKey: ['job', activeJobId],
    queryFn: () => api.get(`/jobs/${activeJobId}`).then(res => res.data),
    enabled: !!activeJobId,
    refetchInterval: (data) => {
      if (data?.status === 'running' || data?.status === 'queued') {
        return 1000; // Poll every second while running
      }
      return false;
    },
  });

  // Publish mutation
  const publishMutation = useMutation({
    mutationFn: () =>
      api.post(`/projects/${slug}/versions/${draftVersion?.version_number}/publish`, {
        target_environment: targetEnv,
      }),
    onSuccess: (response) => {
      setActiveJobId(response.data.id);
      message.info('Publish job started');
    },
    onError: (error) => {
      message.error(error.response?.data?.detail || 'Failed to start publish');
    },
  });

  // Clear job when completed
  useEffect(() => {
    if (job?.status === 'completed') {
      queryClient.invalidateQueries(['project', slug]);
      message.success('Published successfully!');
    } else if (job?.status === 'failed') {
      message.error('Publish failed');
    }
  }, [job?.status]);

  const getStepStatus = (progress) => {
    if (!job) return 'wait';
    if (job.status === 'failed') return 'error';
    if (job.progress >= progress) return 'finish';
    if (job.progress > progress - 25) return 'process';
    return 'wait';
  };

  const isPublishing = activeJobId && (job?.status === 'running' || job?.status === 'queued');

  return (
    <div style={{ maxWidth: 800 }}>
      {/* Current Status */}
      <Card style={{ marginBottom: 24 }}>
        <Title level={4}>Version Status</Title>

        <Descriptions column={2}>
          <Descriptions.Item label="Draft Version">
            {draftVersion ? (
              <Space>
                <Tag color="blue">v{draftVersion.version_number}</Tag>
                <Text type="secondary">Ready to publish</Text>
              </Space>
            ) : (
              <Text type="secondary">No draft</Text>
            )}
          </Descriptions.Item>

          <Descriptions.Item label="Published Version">
            {publishedVersion ? (
              <Space>
                <Tag color="green">v{publishedVersion.version_number}</Tag>
                <Text type="secondary">
                  {new Date(publishedVersion.published_at).toLocaleDateString()}
                </Text>
              </Space>
            ) : (
              <Text type="secondary">Not published</Text>
            )}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* Publish Action */}
      {draftVersion && (
        <Card style={{ marginBottom: 24 }}>
          <Title level={4}>
            <CloudUploadOutlined /> Publish Version {draftVersion.version_number}
          </Title>

          <Paragraph type="secondary">
            Publishing will generate the release.json and upload all assets to the CDN.
            The map viewer will start serving this version immediately.
          </Paragraph>

          <Space style={{ marginBottom: 24 }}>
            <Text>Target Environment:</Text>
            <Select
              value={targetEnv}
              onChange={setTargetEnv}
              style={{ width: 200 }}
              disabled={isPublishing}
              options={[
                { value: 'development', label: 'Development' },
                { value: 'staging', label: 'Staging' },
                { value: 'production', label: 'Production' },
              ]}
            />
          </Space>

          {!isPublishing && (
            <Button
              type="primary"
              size="large"
              icon={<CloudUploadOutlined />}
              onClick={() => publishMutation.mutate()}
              loading={publishMutation.isPending}
            >
              Publish to {targetEnv}
            </Button>
          )}

          {/* Progress */}
          {isPublishing && (
            <div style={{ marginTop: 24 }}>
              <Progress
                percent={job?.progress || 0}
                status={job?.status === 'failed' ? 'exception' : 'active'}
              />

              <Steps current={Math.floor((job?.progress || 0) / 25)} style={{ marginTop: 24 }}>
                <Step
                  title="Validate"
                  status={getStepStatus(25)}
                  icon={getStepStatus(25) === 'process' ? <LoadingOutlined /> : null}
                />
                <Step
                  title="Generate"
                  status={getStepStatus(50)}
                  icon={getStepStatus(50) === 'process' ? <LoadingOutlined /> : null}
                />
                <Step
                  title="Upload"
                  status={getStepStatus(75)}
                  icon={getStepStatus(75) === 'process' ? <LoadingOutlined /> : null}
                />
                <Step
                  title="Complete"
                  status={getStepStatus(100)}
                  icon={getStepStatus(100) === 'process' ? <LoadingOutlined /> : null}
                />
              </Steps>
            </div>
          )}

          {/* Job Result */}
          {job?.status === 'completed' && (
            <Alert
              type="success"
              style={{ marginTop: 24 }}
              message="Published Successfully"
              description={
                <div>
                  <p>Release URL: {job.result?.release_url}</p>
                  <p>Overlays: {job.result?.overlay_count}</p>
                  <p>Published: {job.result?.published_at}</p>
                </div>
              }
            />
          )}

          {job?.status === 'failed' && (
            <Alert
              type="error"
              style={{ marginTop: 24 }}
              message="Publish Failed"
              description={job.error}
            />
          )}

          {/* Logs */}
          {job?.logs?.length > 0 && (
            <Card size="small" style={{ marginTop: 24 }} title="Logs">
              <Timeline>
                {job.logs.map((log, i) => (
                  <Timeline.Item
                    key={i}
                    color={log.level === 'error' ? 'red' : 'blue'}
                  >
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </Text>
                    <br />
                    {log.message}
                  </Timeline.Item>
                ))}
              </Timeline>
            </Card>
          )}
        </Card>
      )}

      {/* Version History */}
      <Card title="Version History">
        <Timeline>
          {project?.versions?.sort((a, b) => b.version_number - a.version_number)
            .map((version) => (
              <Timeline.Item
                key={version.version_number}
                color={version.status === 'published' ? 'green' : 'blue'}
                dot={
                  version.status === 'published' ? (
                    <CheckCircleOutlined />
                  ) : (
                    <ClockCircleOutlined />
                  )
                }
              >
                <Space>
                  <Text strong>Version {version.version_number}</Text>
                  <Tag color={version.status === 'published' ? 'green' : 'blue'}>
                    {version.status}
                  </Tag>
                </Space>
                <br />
                <Text type="secondary">
                  {version.status === 'published'
                    ? `Published ${new Date(version.published_at).toLocaleDateString()}`
                    : `Created ${new Date(version.created_at).toLocaleDateString()}`
                  }
                </Text>
              </Timeline.Item>
            ))}
        </Timeline>
      </Card>
    </div>
  );
}
```

## Acceptance Criteria

- [ ] Shows current draft and published versions
- [ ] Can select target environment
- [ ] Publish button starts job
- [ ] Progress bar updates in real-time
- [ ] Steps show current phase
- [ ] Logs display as timeline
- [ ] Success/error messages shown
- [ ] Version history displayed
