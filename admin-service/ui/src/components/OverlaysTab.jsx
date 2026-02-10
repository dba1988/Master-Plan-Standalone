/**
 * Overlays Tab
 *
 * View and manage overlays (zones, units, POIs).
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Table,
  Button,
  Space,
  Typography,
  Tag,
  message,
  Popconfirm,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  Statistic,
  Row,
  Col,
  Card,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import { overlaysApi } from '../services/api';

const { Text } = Typography;
const { TextArea } = Input;

const OVERLAY_TYPES = [
  { value: 'zone', label: 'Zone', color: 'orange' },
  { value: 'unit', label: 'Unit', color: 'blue' },
  { value: 'poi', label: 'POI', color: 'green' },
];

export default function OverlaysTab({ projectSlug, isDraft }) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingOverlay, setEditingOverlay] = useState(null);
  const [typeFilter, setTypeFilter] = useState(null);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['overlays', projectSlug, typeFilter],
    queryFn: () =>
      overlaysApi.list(projectSlug, {
        overlay_type: typeFilter,
      }),
  });

  const createMutation = useMutation({
    mutationFn: (data) => overlaysApi.create(projectSlug, data),
    onSuccess: () => {
      message.success('Overlay created');
      queryClient.invalidateQueries({
        queryKey: ['overlays', projectSlug],
      });
      handleCloseModal();
    },
    onError: (error) => {
      message.error(error.response?.data?.detail || 'Failed to create overlay');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }) =>
      overlaysApi.update(projectSlug, id, data),
    onSuccess: () => {
      message.success('Overlay updated');
      queryClient.invalidateQueries({
        queryKey: ['overlays', projectSlug],
      });
      handleCloseModal();
    },
    onError: (error) => {
      message.error(error.response?.data?.detail || 'Failed to update overlay');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => overlaysApi.delete(projectSlug, id),
    onSuccess: () => {
      message.success('Overlay deleted');
      queryClient.invalidateQueries({
        queryKey: ['overlays', projectSlug],
      });
    },
    onError: (error) => {
      message.error(error.response?.data?.detail || 'Failed to delete overlay');
    },
  });

  const handleOpenModal = (overlay = null) => {
    setEditingOverlay(overlay);
    if (overlay) {
      form.setFieldsValue({
        ref: overlay.ref,
        overlay_type: overlay.overlay_type,
        layer: overlay.layer,
        sort_order: overlay.sort_order,
        label_en: overlay.label?.en,
        label_ar: overlay.label?.ar,
        geometry: JSON.stringify(overlay.geometry, null, 2),
        props: JSON.stringify(overlay.props || {}, null, 2),
      });
    } else {
      form.resetFields();
    }
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingOverlay(null);
    form.resetFields();
  };

  const handleSubmit = async (values) => {
    const data = {
      ref: values.ref,
      overlay_type: values.overlay_type,
      layer: values.layer || null,
      sort_order: values.sort_order || 0,
      label: {
        en: values.label_en,
        ar: values.label_ar || null,
      },
      geometry: JSON.parse(values.geometry),
      props: values.props ? JSON.parse(values.props) : {},
    };

    if (editingOverlay) {
      updateMutation.mutate({ id: editingOverlay.id, data });
    } else {
      createMutation.mutate(data);
    }
  };

  const overlays = data?.overlays || [];
  const total = data?.total || 0;

  // Count by type
  const counts = {
    zone: overlays.filter((o) => o.overlay_type === 'zone').length,
    unit: overlays.filter((o) => o.overlay_type === 'unit').length,
    poi: overlays.filter((o) => o.overlay_type === 'poi').length,
  };

  const columns = [
    {
      title: 'Ref',
      dataIndex: 'ref',
      key: 'ref',
      render: (ref) => <Text code>{ref}</Text>,
    },
    {
      title: 'Type',
      dataIndex: 'overlay_type',
      key: 'overlay_type',
      render: (type) => {
        const overlayType = OVERLAY_TYPES.find((t) => t.value === type);
        return (
          <Tag color={overlayType?.color || 'default'}>
            {overlayType?.label || type}
          </Tag>
        );
      },
    },
    {
      title: 'Label',
      key: 'label',
      render: (_, record) => record.label?.en || '-',
    },
    {
      title: 'Layer',
      dataIndex: 'layer',
      key: 'layer',
      render: (layer) => layer || <Text type="secondary">-</Text>,
    },
    {
      title: 'Order',
      dataIndex: 'sort_order',
      key: 'sort_order',
      width: 80,
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 100,
      render: (_, record) =>
        isDraft ? (
          <Space>
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleOpenModal(record)}
            />
            <Popconfirm
              title="Delete overlay?"
              onConfirm={() => deleteMutation.mutate(record.id)}
              okText="Delete"
              okButtonProps={{ danger: true }}
            >
              <Button type="text" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          </Space>
        ) : (
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => handleOpenModal(record)}
            disabled
          />
        ),
    },
  ];

  return (
    <div>
      {/* Stats */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic title="Total" value={total} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="Zones" value={counts.zone} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="Units" value={counts.unit} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="POIs" value={counts.poi} />
          </Card>
        </Col>
      </Row>

      {/* Filters and Actions */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          marginBottom: 16,
        }}
      >
        <Select
          value={typeFilter}
          onChange={setTypeFilter}
          options={[
            { value: null, label: 'All Types' },
            ...OVERLAY_TYPES,
          ]}
          style={{ width: 150 }}
          allowClear
          placeholder="Filter by type"
        />
        {isDraft && (
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => handleOpenModal()}
          >
            Add Overlay
          </Button>
        )}
      </div>

      <Table
        columns={columns}
        dataSource={overlays}
        rowKey="id"
        loading={isLoading}
        pagination={{
          pageSize: 20,
          showSizeChanger: true,
          showTotal: (total) => `${total} overlays`,
        }}
      />

      <Modal
        title={editingOverlay ? 'Edit Overlay' : 'New Overlay'}
        open={isModalOpen}
        onCancel={handleCloseModal}
        footer={null}
        width={600}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          style={{ marginTop: 16 }}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="ref"
                label="Reference"
                rules={[{ required: true, message: 'Required' }]}
              >
                <Input placeholder="UNIT-001" disabled={!!editingOverlay} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="overlay_type"
                label="Type"
                rules={[{ required: true, message: 'Required' }]}
              >
                <Select
                  options={OVERLAY_TYPES}
                  placeholder="Select type"
                  disabled={!!editingOverlay}
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="label_en" label="Label (EN)">
                <Input placeholder="Unit 1" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="label_ar" label="Label (AR)">
                <Input placeholder="وحدة 1" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="layer" label="Layer">
                <Input placeholder="floor-1" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="sort_order" label="Sort Order">
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="geometry"
            label="Geometry (JSON)"
            rules={[
              { required: true, message: 'Required' },
              {
                validator: (_, value) => {
                  try {
                    JSON.parse(value);
                    return Promise.resolve();
                  } catch {
                    return Promise.reject('Invalid JSON');
                  }
                },
              },
            ]}
          >
            <TextArea
              rows={4}
              placeholder='{"type": "path", "d": "M100,100 L200,100..."}'
              style={{ fontFamily: 'monospace' }}
            />
          </Form.Item>

          <Form.Item
            name="props"
            label="Properties (JSON)"
            rules={[
              {
                validator: (_, value) => {
                  if (!value) return Promise.resolve();
                  try {
                    JSON.parse(value);
                    return Promise.resolve();
                  } catch {
                    return Promise.reject('Invalid JSON');
                  }
                },
              },
            ]}
          >
            <TextArea
              rows={3}
              placeholder='{"bedrooms": 2, "area": 120}'
              style={{ fontFamily: 'monospace' }}
            />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={handleCloseModal}>Cancel</Button>
              <Button
                type="primary"
                htmlType="submit"
                loading={createMutation.isPending || updateMutation.isPending}
              >
                {editingOverlay ? 'Update' : 'Create'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
