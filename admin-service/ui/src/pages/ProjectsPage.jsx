/**
 * Projects List Page
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Card,
  Table,
  Button,
  Space,
  Typography,
  Modal,
  Form,
  Input,
  message,
  Tag,
  Tooltip,
  Popconfirm,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { projectsApi } from '../services/api';

const { Title, Text } = Typography;

export default function ProjectsPage() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingProject, setEditingProject] = useState(null);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
  });

  const createMutation = useMutation({
    mutationFn: projectsApi.create,
    onSuccess: () => {
      message.success('Project created');
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      handleCloseModal();
    },
    onError: (error) => {
      message.error(error.response?.data?.detail || 'Failed to create project');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ slug, data }) => projectsApi.update(slug, data),
    onSuccess: () => {
      message.success('Project updated');
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      handleCloseModal();
    },
    onError: (error) => {
      message.error(error.response?.data?.detail || 'Failed to update project');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: projectsApi.delete,
    onSuccess: () => {
      message.success('Project deleted');
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
    onError: (error) => {
      message.error(error.response?.data?.detail || 'Failed to delete project');
    },
  });

  const handleOpenModal = (project = null) => {
    setEditingProject(project);
    if (project) {
      form.setFieldsValue({
        name: project.name,
        slug: project.slug,
        description: project.description,
      });
    } else {
      form.resetFields();
    }
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingProject(null);
    form.resetFields();
  };

  const handleSubmit = async (values) => {
    if (editingProject) {
      updateMutation.mutate({ slug: editingProject.slug, data: values });
    } else {
      createMutation.mutate(values);
    }
  };

  const handleDelete = (slug) => {
    deleteMutation.mutate(slug);
  };

  const projects = data?.items || [];

  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (name, record) => (
        <Link to={`/projects/${record.slug}`}>
          <Text strong>{name}</Text>
        </Link>
      ),
    },
    {
      title: 'Slug',
      dataIndex: 'slug',
      key: 'slug',
      render: (slug) => <Text code>{slug}</Text>,
    },
    {
      title: 'Versions',
      key: 'versions',
      render: (_, record) => {
        const versions = record.versions || [];
        const draft = versions.filter((v) => v.status === 'draft').length;
        const published = versions.filter((v) => v.status === 'published').length;
        return (
          <Space>
            {draft > 0 && <Tag color="blue">{draft} draft</Tag>}
            {published > 0 && <Tag color="green">{published} published</Tag>}
            {versions.length === 0 && <Text type="secondary">No versions</Text>}
          </Space>
        );
      },
    },
    {
      title: 'Current Release',
      dataIndex: 'current_release_id',
      key: 'release',
      render: (releaseId) =>
        releaseId ? (
          <Tag color="green">{releaseId.slice(0, 20)}...</Tag>
        ) : (
          <Text type="secondary">None</Text>
        ),
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => new Date(date).toLocaleDateString(),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 150,
      render: (_, record) => (
        <Space>
          <Tooltip title="View">
            <Link to={`/projects/${record.slug}`}>
              <Button type="text" icon={<EyeOutlined />} />
            </Link>
          </Tooltip>
          <Tooltip title="Edit">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleOpenModal(record)}
            />
          </Tooltip>
          <Tooltip title="Delete">
            <Popconfirm
              title="Delete project?"
              description="This action cannot be undone."
              onConfirm={() => handleDelete(record.slug)}
              okText="Delete"
              okButtonProps={{ danger: true }}
            >
              <Button type="text" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 24,
        }}
      >
        <div>
          <Title level={3} style={{ marginBottom: 8 }}>
            Projects
          </Title>
          <Text type="secondary">Manage your master plan projects</Text>
        </div>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => handleOpenModal()}
        >
          New Project
        </Button>
      </div>

      <Card>
        <Table
          columns={columns}
          dataSource={projects}
          rowKey="id"
          loading={isLoading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `${total} projects`,
          }}
        />
      </Card>

      <Modal
        title={editingProject ? 'Edit Project' : 'New Project'}
        open={isModalOpen}
        onCancel={handleCloseModal}
        footer={null}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          style={{ marginTop: 16 }}
        >
          <Form.Item
            name="name"
            label="Project Name"
            rules={[{ required: true, message: 'Please enter a name' }]}
          >
            <Input placeholder="My Project" />
          </Form.Item>

          <Form.Item
            name="slug"
            label="Slug"
            rules={[
              { required: true, message: 'Please enter a slug' },
              {
                pattern: /^[a-z0-9-]+$/,
                message: 'Slug must be lowercase letters, numbers, and hyphens only',
              },
            ]}
            extra="URL-friendly identifier (e.g., my-project)"
          >
            <Input placeholder="my-project" disabled={!!editingProject} />
          </Form.Item>

          <Form.Item name="description" label="Description">
            <Input.TextArea rows={3} placeholder="Project description..." />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={handleCloseModal}>Cancel</Button>
              <Button
                type="primary"
                htmlType="submit"
                loading={createMutation.isPending || updateMutation.isPending}
              >
                {editingProject ? 'Update' : 'Create'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
