/**
 * Dashboard Page
 *
 * Shows overview stats and recent activity.
 */
import { useQuery } from '@tanstack/react-query';
import { Card, Row, Col, Statistic, Typography, List, Spin, Empty, Button } from 'antd';
import {
  ProjectOutlined,
  FileImageOutlined,
  AppstoreOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import { Link } from 'react-router-dom';
import { projectsApi, jobsApi } from '../services/api';

const { Title, Text } = Typography;

export default function DashboardPage() {
  const { data: projectsData, isLoading: projectsLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
  });

  const { data: jobsData, isLoading: jobsLoading } = useQuery({
    queryKey: ['jobs'],
    queryFn: () => jobsApi.list({ limit: 5 }),
  });

  const projects = projectsData?.items || [];
  const recentJobs = jobsData || [];

  // Calculate stats
  const stats = {
    totalProjects: projects.length,
    draftVersions: projects.reduce((acc, p) => {
      const drafts = p.versions?.filter((v) => v.status === 'draft') || [];
      return acc + drafts.length;
    }, 0),
    publishedVersions: projects.reduce((acc, p) => {
      const published = p.versions?.filter((v) => v.status === 'published') || [];
      return acc + published.length;
    }, 0),
  };

  if (projectsLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ marginBottom: 8 }}>
          Dashboard
        </Title>
        <Text type="secondary">
          Welcome to Master Plan Studio
        </Text>
      </div>

      {/* Stats */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Projects"
              value={stats.totalProjects}
              prefix={<ProjectOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Draft Versions"
              value={stats.draftVersions}
              prefix={<FileImageOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Published"
              value={stats.publishedVersions}
              prefix={<RocketOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Overlays"
              value={"-"}
              prefix={<AppstoreOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        {/* Recent Projects */}
        <Col xs={24} lg={12}>
          <Card
            title="Recent Projects"
            extra={<Link to="/projects">View All</Link>}
          >
            {projects.length === 0 ? (
              <Empty
                description="No projects yet"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              >
                <Link to="/projects">
                  <Button type="primary">Create Project</Button>
                </Link>
              </Empty>
            ) : (
              <List
                dataSource={projects.slice(0, 5)}
                renderItem={(project) => (
                  <List.Item>
                    <List.Item.Meta
                      avatar={<ProjectOutlined style={{ fontSize: 24 }} />}
                      title={
                        <Link to={`/projects/${project.slug}`}>
                          {project.name}
                        </Link>
                      }
                      description={`${project.versions?.length || 0} versions`}
                    />
                  </List.Item>
                )}
              />
            )}
          </Card>
        </Col>

        {/* Recent Jobs */}
        <Col xs={24} lg={12}>
          <Card title="Recent Jobs">
            {jobsLoading ? (
              <Spin />
            ) : recentJobs.length === 0 ? (
              <Empty
                description="No recent jobs"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            ) : (
              <List
                dataSource={recentJobs}
                renderItem={(job) => (
                  <List.Item>
                    <List.Item.Meta
                      title={
                        <Text>
                          {job.job_type.replace('_', ' ')}
                          <Text
                            type={
                              job.status === 'completed'
                                ? 'success'
                                : job.status === 'failed'
                                ? 'danger'
                                : 'secondary'
                            }
                            style={{ marginLeft: 8 }}
                          >
                            ({job.status})
                          </Text>
                        </Text>
                      }
                      description={new Date(job.created_at).toLocaleString()}
                    />
                  </List.Item>
                )}
              />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}
