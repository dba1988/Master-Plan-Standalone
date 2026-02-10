/**
 * Publish Tab
 *
 * Build and publish workflow:
 * 1. Build - Generate tiles and preview manifest
 * 2. Preview - View the build before publishing
 * 3. Publish - Create an immutable release
 */
import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Space,
  Card,
  Typography,
  message,
  Alert,
  Steps,
  Progress,
  Result,
  Tag,
  Descriptions,
  Spin,
  Divider,
  Row,
  Col,
  Statistic,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  RocketOutlined,
  LoadingOutlined,
  BuildOutlined,
  EyeOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { publishApi, buildApi, jobsApi } from '../services/api';

const { Title, Text, Paragraph } = Typography;

export default function PublishTab({ projectSlug, versionNumber, version }) {
  const [activeJobId, setActiveJobId] = useState(null);
  const [activeJobType, setActiveJobType] = useState(null); // 'build' or 'publish'
  const [jobStatus, setJobStatus] = useState(null);
  const queryClient = useQueryClient();

  // Build validation query
  const {
    data: buildValidation,
    isLoading: validatingBuild,
    refetch: revalidateBuild,
  } = useQuery({
    queryKey: ['build-validation', projectSlug, versionNumber],
    queryFn: () => buildApi.validate(projectSlug, versionNumber),
    enabled: version?.status === 'draft',
  });

  // Build status query
  const {
    data: buildStatus,
    isLoading: loadingBuildStatus,
    refetch: refetchBuildStatus,
  } = useQuery({
    queryKey: ['build-status', projectSlug, versionNumber],
    queryFn: () => buildApi.getStatus(projectSlug, versionNumber),
    enabled: version?.status === 'draft',
  });

  // Publish validation query
  const {
    data: publishValidation,
    isLoading: validatingPublish,
    refetch: revalidatePublish,
  } = useQuery({
    queryKey: ['publish-validation', projectSlug, versionNumber],
    queryFn: () => publishApi.validate(projectSlug, versionNumber),
    enabled: version?.status === 'draft' && buildStatus?.has_build,
  });

  // Poll job status when building or publishing
  useEffect(() => {
    if (!activeJobId) return;

    const pollInterval = setInterval(async () => {
      try {
        const job = await jobsApi.get(activeJobId);
        setJobStatus(job);

        if (job.status === 'completed' || job.status === 'failed') {
          clearInterval(pollInterval);
          if (job.status === 'completed') {
            if (activeJobType === 'build') {
              message.success('Build completed successfully');
              refetchBuildStatus();
              revalidatePublish();
            } else {
              message.success('Version published successfully');
              queryClient.invalidateQueries({ queryKey: ['project', projectSlug] });
            }
          }
        }
      } catch (error) {
        console.error('Failed to poll job status:', error);
      }
    }, 2000);

    return () => clearInterval(pollInterval);
  }, [activeJobId, activeJobType, projectSlug, queryClient, refetchBuildStatus, revalidatePublish]);

  const buildMutation = useMutation({
    mutationFn: () => buildApi.start(projectSlug, versionNumber),
    onSuccess: (data) => {
      setActiveJobId(data.job_id);
      setActiveJobType('build');
      setJobStatus({ status: 'queued', progress: 0 });
      message.info('Build job started');
    },
    onError: (error) => {
      message.error(error.response?.data?.detail || 'Failed to start build');
    },
  });

  const publishMutation = useMutation({
    mutationFn: () => publishApi.publish(projectSlug, versionNumber),
    onSuccess: (data) => {
      setActiveJobId(data.job_id);
      setActiveJobType('publish');
      setJobStatus({ status: 'queued', progress: 0 });
      message.info('Publish job started');
    },
    onError: (error) => {
      message.error(error.response?.data?.detail || 'Failed to start publish');
    },
  });

  const handleBuild = () => {
    buildMutation.mutate();
  };

  const handlePublish = () => {
    publishMutation.mutate();
  };

  const resetJobState = () => {
    setActiveJobId(null);
    setActiveJobType(null);
    setJobStatus(null);
  };

  // Already published
  if (version?.status === 'published') {
    return (
      <Result
        status="success"
        icon={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
        title="Version Published"
        subTitle={
          <Space direction="vertical">
            <Text>
              Release ID: <Text code>{version.release_id || 'N/A'}</Text>
            </Text>
            <Text>
              Published: {version.published_at ? new Date(version.published_at).toLocaleString() : 'N/A'}
            </Text>
          </Space>
        }
      />
    );
  }

  // Job in progress (build or publish)
  if (activeJobId && jobStatus && jobStatus.status !== 'completed' && jobStatus.status !== 'failed') {
    const isBuild = activeJobType === 'build';
    return (
      <Card>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <div style={{ textAlign: 'center' }}>
            <LoadingOutlined style={{ fontSize: 48, color: isBuild ? '#722ed1' : '#1890ff' }} />
            <Title level={4} style={{ marginTop: 16 }}>
              {isBuild ? 'Building' : 'Publishing'} Version {versionNumber}
            </Title>
          </div>

          <Progress
            percent={jobStatus.progress || 0}
            status="active"
            strokeColor={isBuild ? '#722ed1' : '#1890ff'}
          />

          <Text type="secondary" style={{ textAlign: 'center', display: 'block' }}>
            {jobStatus.message || 'Processing...'}
          </Text>

          <Steps
            current={isBuild ? getBuildStepFromProgress(jobStatus.progress) : getPublishStepFromProgress(jobStatus.progress)}
            items={isBuild ? [
              { title: 'Validating' },
              { title: 'Generating Tiles' },
              { title: 'Uploading' },
              { title: 'Creating Manifest' },
              { title: 'Complete' },
            ] : [
              { title: 'Validating' },
              { title: 'Copying Tiles' },
              { title: 'Generating Manifest' },
              { title: 'Uploading' },
              { title: 'Complete' },
            ]}
          />
        </Space>
      </Card>
    );
  }

  // Job failed
  if (jobStatus?.status === 'failed') {
    const isBuild = activeJobType === 'build';
    return (
      <Result
        status="error"
        title={`${isBuild ? 'Build' : 'Publish'} Failed`}
        subTitle={jobStatus.error || 'An error occurred'}
        extra={[
          <Button key="retry" type="primary" onClick={isBuild ? handleBuild : handlePublish}>
            Retry {isBuild ? 'Build' : 'Publish'}
          </Button>,
          <Button key="reset" onClick={resetJobState}>
            Start Over
          </Button>,
        ]}
      />
    );
  }

  // Job completed (transient state, should refresh)
  if (jobStatus?.status === 'completed') {
    const isBuild = activeJobType === 'build';
    if (isBuild) {
      // After build completes, reset and show the main view
      setTimeout(() => resetJobState(), 1000);
    }
    return (
      <Result
        status="success"
        title={`${isBuild ? 'Build' : 'Version'} ${isBuild ? 'Completed' : 'Published'}`}
        subTitle={
          isBuild ? (
            <Text>Build ID: <Text code>{jobStatus.result?.build_id}</Text></Text>
          ) : (
            <Text>Release ID: <Text code>{jobStatus.result?.release_id}</Text></Text>
          )
        }
        extra={
          isBuild ? (
            <Button type="primary" onClick={resetJobState}>
              Continue to Publish
            </Button>
          ) : (
            <Button type="primary" onClick={() => window.location.reload()}>
              Refresh Page
            </Button>
          )
        }
      />
    );
  }

  // Main view - Build & Publish workflow
  return (
    <div>
      {/* Step 1: Build */}
      <Card
        title={
          <Space>
            <BuildOutlined />
            Step 1: Build
          </Space>
        }
        style={{ marginBottom: 16 }}
        extra={
          buildStatus?.has_build && (
            <Tag color="success" icon={<CheckCircleOutlined />}>
              Build Ready
            </Tag>
          )
        }
      >
        {validatingBuild || loadingBuildStatus ? (
          <div style={{ textAlign: 'center', padding: 24 }}>
            <Spin />
          </div>
        ) : (
          <>
            <Paragraph>
              Build generates tiles from your base map assets and creates a preview manifest.
              This step must be completed before publishing.
            </Paragraph>

            {/* Build Validation */}
            {buildValidation && (
              <Space direction="vertical" style={{ width: '100%', marginBottom: 16 }}>
                {buildValidation.errors?.length > 0 && (
                  <Alert
                    type="error"
                    showIcon
                    message="Cannot Build"
                    description={
                      <ul style={{ margin: '8px 0 0', paddingLeft: 20 }}>
                        {buildValidation.errors.map((error, i) => (
                          <li key={i}>{error}</li>
                        ))}
                      </ul>
                    }
                  />
                )}

                {buildValidation.warnings?.length > 0 && (
                  <Alert
                    type="warning"
                    showIcon
                    message="Warnings"
                    description={
                      <ul style={{ margin: '8px 0 0', paddingLeft: 20 }}>
                        {buildValidation.warnings.map((warning, i) => (
                          <li key={i}>{warning}</li>
                        ))}
                      </ul>
                    }
                  />
                )}
              </Space>
            )}

            {/* Build Stats */}
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={8}>
                <Statistic
                  title="Base Maps"
                  value={buildValidation?.base_map_count || 0}
                  valueStyle={{ color: buildValidation?.base_map_count > 0 ? '#3f8600' : '#999' }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="Overlays"
                  value={buildValidation?.overlay_count || 0}
                  valueStyle={{ color: buildValidation?.overlay_count > 0 ? '#3f8600' : '#999' }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="Build Status"
                  value={buildStatus?.has_build ? 'Ready' : 'Not Built'}
                  valueStyle={{ color: buildStatus?.has_build ? '#3f8600' : '#cf1322' }}
                />
              </Col>
            </Row>

            {/* Current Build Info */}
            {buildStatus?.has_build && (
              <Card size="small" style={{ marginBottom: 16, background: '#f6ffed' }}>
                <Descriptions column={2} size="small">
                  <Descriptions.Item label="Build ID">
                    <Text code style={{ fontSize: 11 }}>{buildStatus.build_id}</Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="Built At">
                    {buildStatus.built_at ? new Date(buildStatus.built_at).toLocaleString() : 'N/A'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Overlays">
                    {buildStatus.overlay_count}
                  </Descriptions.Item>
                  <Descriptions.Item label="Tile Levels">
                    {buildStatus.tiles?.levels?.join(', ') || 'None'}
                  </Descriptions.Item>
                </Descriptions>
                <Button
                  type="link"
                  icon={<EyeOutlined />}
                  href={buildStatus.preview_url}
                  target="_blank"
                  style={{ padding: 0, marginTop: 8 }}
                >
                  View Preview Manifest
                </Button>
              </Card>
            )}

            <Space>
              <Button
                type={buildStatus?.has_build ? 'default' : 'primary'}
                icon={<ThunderboltOutlined />}
                onClick={handleBuild}
                loading={buildMutation.isPending}
                disabled={!buildValidation?.valid}
              >
                {buildStatus?.has_build ? 'Rebuild' : 'Start Build'}
              </Button>
              <Button type="link" onClick={() => revalidateBuild()}>
                Re-validate
              </Button>
            </Space>
          </>
        )}
      </Card>

      {/* Step 2: Publish */}
      <Card
        title={
          <Space>
            <RocketOutlined />
            Step 2: Publish
          </Space>
        }
      >
        {!buildStatus?.has_build ? (
          <Alert
            type="info"
            showIcon
            message="Build Required"
            description="Complete the build step above before publishing."
          />
        ) : validatingPublish ? (
          <div style={{ textAlign: 'center', padding: 24 }}>
            <Spin />
          </div>
        ) : (
          <>
            <Paragraph>
              Publishing creates an <strong>immutable release</strong> from your build.
              Once published, the version cannot be modified.
            </Paragraph>

            {/* Publish Validation */}
            {publishValidation && (
              <Space direction="vertical" style={{ width: '100%', marginBottom: 16 }}>
                {publishValidation.valid ? (
                  <Alert
                    type="success"
                    showIcon
                    icon={<CheckCircleOutlined />}
                    message="Ready to Publish"
                    description="All checks passed. You can publish this version."
                  />
                ) : (
                  <Alert
                    type="error"
                    showIcon
                    message="Cannot Publish"
                    description={
                      <ul style={{ margin: '8px 0 0', paddingLeft: 20 }}>
                        {publishValidation.errors?.map((error, i) => (
                          <li key={i}>{error}</li>
                        ))}
                      </ul>
                    }
                  />
                )}

                {publishValidation.warnings?.length > 0 && (
                  <Alert
                    type="warning"
                    showIcon
                    message="Warnings"
                    description={
                      <ul style={{ margin: '8px 0 0', paddingLeft: 20 }}>
                        {publishValidation.warnings.map((warning, i) => (
                          <li key={i}>{warning}</li>
                        ))}
                      </ul>
                    }
                  />
                )}
              </Space>
            )}

            <Alert
              type="info"
              showIcon
              message="What happens when you publish"
              description={
                <ul style={{ margin: '8px 0 0', paddingLeft: 20 }}>
                  <li>Tiles are copied from the build to an immutable release folder</li>
                  <li>A release.json manifest is generated with all overlays and config</li>
                  <li>The version status changes to "published"</li>
                  <li>The project's current release pointer is updated</li>
                </ul>
              }
              style={{ marginBottom: 16 }}
            />

            <Space>
              <Button
                type="primary"
                size="large"
                icon={<RocketOutlined />}
                onClick={handlePublish}
                loading={publishMutation.isPending}
                disabled={!publishValidation?.valid}
              >
                Publish Version {versionNumber}
              </Button>
              <Button type="link" onClick={() => revalidatePublish()}>
                Re-validate
              </Button>
            </Space>
          </>
        )}
      </Card>
    </div>
  );
}

function getBuildStepFromProgress(progress) {
  if (progress < 8) return 0;
  if (progress < 75) return 1;
  if (progress < 85) return 2;
  if (progress < 95) return 3;
  return 4;
}

function getPublishStepFromProgress(progress) {
  if (progress < 10) return 0;
  if (progress < 60) return 1;
  if (progress < 80) return 2;
  if (progress < 95) return 3;
  return 4;
}
