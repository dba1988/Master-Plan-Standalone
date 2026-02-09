# TASK-015: Projects List + Dashboard

**Phase**: 5 - Admin UI
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-014

## Objective

Create project management pages - list and dashboard views.

## Files to Create

```
admin-ui/src/
├── pages/
│   ├── ProjectsPage.jsx
│   ├── NewProjectPage.jsx
│   └── ProjectDashboard.jsx
└── components/
    ├── Layout.jsx
    └── ProjectCard.jsx
```

## Implementation

### Layout Component
```jsx
// src/components/Layout.jsx
import React from 'react';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { Layout as AntLayout, Menu, Dropdown, Avatar, Typography } from 'antd';
import {
  ProjectOutlined, LogoutOutlined, UserOutlined
} from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';
import ProjectsPage from '../pages/ProjectsPage';
import NewProjectPage from '../pages/NewProjectPage';
import ProjectDashboard from '../pages/ProjectDashboard';

const { Header, Content } = AntLayout;
const { Text } = Typography;

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const userMenu = {
    items: [
      { key: 'logout', icon: <LogoutOutlined />, label: 'Logout' }
    ],
    onClick: async ({ key }) => {
      if (key === 'logout') {
        await logout();
        navigate('/login');
      }
    }
  };

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Header style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 24px',
        background: '#3F5277'
      }}>
        <div
          style={{ cursor: 'pointer', display: 'flex', alignItems: 'center' }}
          onClick={() => navigate('/')}
        >
          <ProjectOutlined style={{ fontSize: 24, color: '#fff', marginRight: 12 }} />
          <Text strong style={{ color: '#fff', fontSize: 18 }}>
            Master Plan Studio
          </Text>
        </div>

        <Dropdown menu={userMenu} trigger={['click']}>
          <div style={{ cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
            <Avatar icon={<UserOutlined />} />
            <Text style={{ color: '#fff', marginLeft: 8 }}>{user?.name}</Text>
          </div>
        </Dropdown>
      </Header>

      <Content style={{ padding: 24, background: '#f0f2f5' }}>
        <Routes>
          <Route path="/" element={<ProjectsPage />} />
          <Route path="/projects/new" element={<NewProjectPage />} />
          <Route path="/projects/:slug/*" element={<ProjectDashboard />} />
        </Routes>
      </Content>
    </AntLayout>
  );
}
```

### Projects Page
```jsx
// src/pages/ProjectsPage.jsx
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Row, Col, Card, Button, Typography, Spin, Empty, Tag } from 'antd';
import { PlusOutlined, RightOutlined } from '@ant-design/icons';
import { projectsApi } from '../services/api';

const { Title, Text } = Typography;

export default function ProjectsPage() {
  const navigate = useNavigate();

  const { data, isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list().then(res => res.data),
  });

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}>Projects</Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => navigate('/projects/new')}
        >
          New Project
        </Button>
      </div>

      {data?.projects?.length === 0 ? (
        <Empty description="No projects yet">
          <Button type="primary" onClick={() => navigate('/projects/new')}>
            Create your first project
          </Button>
        </Empty>
      ) : (
        <Row gutter={[16, 16]}>
          {data?.projects?.map((project) => (
            <Col xs={24} sm={12} lg={8} key={project.id}>
              <Card
                hoverable
                onClick={() => navigate(`/projects/${project.slug}`)}
                actions={[
                  <Button type="link" icon={<RightOutlined />}>
                    Open
                  </Button>
                ]}
              >
                <Card.Meta
                  title={project.name}
                  description={
                    <div>
                      <Text type="secondary">{project.slug}</Text>
                      <div style={{ marginTop: 8 }}>
                        <Tag color={project.is_active ? 'green' : 'default'}>
                          {project.is_active ? 'Active' : 'Inactive'}
                        </Tag>
                      </div>
                    </div>
                  }
                />
              </Card>
            </Col>
          ))}
        </Row>
      )}
    </div>
  );
}
```

### New Project Page
```jsx
// src/pages/NewProjectPage.jsx
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Form, Input, Button, Card, message, Typography } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { projectsApi } from '../services/api';

const { Title } = Typography;

export default function NewProjectPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [form] = Form.useForm();

  const createMutation = useMutation({
    mutationFn: (data) => projectsApi.create(data),
    onSuccess: (response) => {
      queryClient.invalidateQueries(['projects']);
      message.success('Project created successfully');
      navigate(`/projects/${response.data.slug}`);
    },
    onError: (error) => {
      message.error(error.response?.data?.detail || 'Failed to create project');
    },
  });

  const onFinish = (values) => {
    createMutation.mutate(values);
  };

  // Auto-generate slug from name
  const onNameChange = (e) => {
    const name = e.target.value;
    const slug = name.toLowerCase()
      .replace(/[^a-z0-9\s-]/g, '')
      .replace(/\s+/g, '-');
    form.setFieldsValue({ slug });
  };

  return (
    <div style={{ maxWidth: 600, margin: '0 auto' }}>
      <Button
        type="link"
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate('/')}
        style={{ marginBottom: 16, padding: 0 }}
      >
        Back to Projects
      </Button>

      <Card>
        <Title level={3}>Create New Project</Title>

        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
          requiredMark={false}
        >
          <Form.Item
            name="name"
            label="Project Name"
            rules={[{ required: true, message: 'Please enter project name' }]}
          >
            <Input
              placeholder="e.g., Malaysia Development"
              onChange={onNameChange}
            />
          </Form.Item>

          <Form.Item
            name="slug"
            label="URL Slug"
            rules={[
              { required: true, message: 'Please enter URL slug' },
              { pattern: /^[a-z][a-z0-9-]*$/, message: 'Lowercase letters, numbers, hyphens only' }
            ]}
            extra="Used in URLs. Cannot be changed later."
          >
            <Input placeholder="e.g., malaysia-development" />
          </Form.Item>

          <Form.Item
            name="name_ar"
            label="Arabic Name (Optional)"
          >
            <Input placeholder="e.g., التنمية الماليزية" dir="rtl" />
          </Form.Item>

          <Form.Item
            name="description"
            label="Description (Optional)"
          >
            <Input.TextArea rows={3} placeholder="Brief project description" />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={createMutation.isPending}
              block
            >
              Create Project
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
```

### Project Dashboard
```jsx
// src/pages/ProjectDashboard.jsx
import React from 'react';
import { useParams, useNavigate, Routes, Route, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Card, Tabs, Typography, Spin, Row, Col, Statistic, Button, Tag } from 'antd';
import {
  ArrowLeftOutlined, EditOutlined, FileImageOutlined,
  ApiOutlined, CloudUploadOutlined
} from '@ant-design/icons';
import { projectsApi } from '../services/api';

const { Title, Text } = Typography;

export default function ProjectDashboard() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  const { data: project, isLoading } = useQuery({
    queryKey: ['project', slug],
    queryFn: () => projectsApi.get(slug).then(res => res.data),
  });

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Spin size="large" />
      </div>
    );
  }

  // Determine active tab from URL
  const pathParts = location.pathname.split('/');
  const activeTab = pathParts[3] || 'dashboard';

  const tabs = [
    { key: 'dashboard', label: 'Dashboard' },
    { key: 'editor', label: 'Editor' },
    { key: 'assets', label: 'Assets' },
    { key: 'integration', label: 'Integration' },
    { key: 'publish', label: 'Publish' },
  ];

  const handleTabChange = (key) => {
    if (key === 'dashboard') {
      navigate(`/projects/${slug}`);
    } else {
      navigate(`/projects/${slug}/${key}`);
    }
  };

  return (
    <div>
      <Button
        type="link"
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate('/')}
        style={{ marginBottom: 16, padding: 0 }}
      >
        Back to Projects
      </Button>

      <div style={{ marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}>{project?.name}</Title>
        <Text type="secondary">{project?.slug}</Text>
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={handleTabChange}
        items={tabs}
      />

      {activeTab === 'dashboard' && (
        <DashboardView project={project} navigate={navigate} slug={slug} />
      )}

      {activeTab === 'editor' && <div>Editor Page (TASK-017)</div>}
      {activeTab === 'assets' && <div>Assets Page (TASK-016)</div>}
      {activeTab === 'integration' && <div>Integration Page (TASK-018)</div>}
      {activeTab === 'publish' && <div>Publish Page (TASK-019)</div>}
    </div>
  );
}

function DashboardView({ project, navigate, slug }) {
  const draftVersion = project?.versions?.find(v => v.status === 'draft');
  const publishedVersion = project?.versions?.find(v => v.status === 'published');

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Draft Version"
              value={draftVersion?.version_number || '-'}
              prefix={<Tag color="blue">Draft</Tag>}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Published Version"
              value={publishedVersion?.version_number || '-'}
              prefix={<Tag color="green">Live</Tag>}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Overlays"
              value={0}  // TODO: Fetch from API
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Assets"
              value={0}  // TODO: Fetch from API
            />
          </Card>
        </Col>
      </Row>

      <Card title="Quick Actions" style={{ marginTop: 24 }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={6}>
            <Button
              block
              icon={<EditOutlined />}
              onClick={() => navigate(`/projects/${slug}/editor`)}
            >
              Open Editor
            </Button>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Button
              block
              icon={<FileImageOutlined />}
              onClick={() => navigate(`/projects/${slug}/assets`)}
            >
              Upload Assets
            </Button>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Button
              block
              icon={<ApiOutlined />}
              onClick={() => navigate(`/projects/${slug}/integration`)}
            >
              Configure API
            </Button>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Button
              block
              type="primary"
              icon={<CloudUploadOutlined />}
              onClick={() => navigate(`/projects/${slug}/publish`)}
            >
              Publish
            </Button>
          </Col>
        </Row>
      </Card>
    </div>
  );
}
```

## Acceptance Criteria

- [ ] Projects list shows all projects
- [ ] Can create new project
- [ ] Slug auto-generated from name
- [ ] Can navigate to project dashboard
- [ ] Dashboard shows version info
- [ ] Quick actions navigate correctly
- [ ] Tabs switch between sections
