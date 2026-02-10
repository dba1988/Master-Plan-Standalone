/**
 * Config Tab
 *
 * Manage version configuration (view settings, status styles, etc.).
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Form,
  Input,
  InputNumber,
  Select,
  Button,
  Space,
  Card,
  Typography,
  message,
  Divider,
  Row,
  Col,
  Spin,
  ColorPicker,
} from 'antd';
import { SaveOutlined, ReloadOutlined } from '@ant-design/icons';
import { configApi } from '../services/api';

const { Title, Text } = Typography;

const LOCALES = [
  { value: 'en', label: 'English' },
  { value: 'ar', label: 'Arabic' },
];

const STATUS_KEYS = ['available', 'reserved', 'sold', 'hidden', 'unreleased'];

export default function ConfigTab({ projectSlug, isDraft }) {
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  const { data: config, isLoading } = useQuery({
    queryKey: ['config', projectSlug],
    queryFn: () => configApi.get(projectSlug),
  });

  const updateMutation = useMutation({
    mutationFn: (data) => configApi.update(projectSlug, data),
    onSuccess: () => {
      message.success('Configuration saved');
      queryClient.invalidateQueries({
        queryKey: ['config', projectSlug],
      });
    },
    onError: (error) => {
      message.error(error.response?.data?.detail || 'Failed to save configuration');
    },
  });

  const handleSubmit = (values) => {
    const data = {
      default_view_box: values.default_view_box,
      default_zoom: values.default_zoom,
      min_zoom: values.min_zoom,
      max_zoom: values.max_zoom,
      default_locale: values.default_locale,
      supported_locales: values.supported_locales,
    };

    updateMutation.mutate(data);
  };

  const handleReset = () => {
    if (config) {
      form.setFieldsValue({
        default_view_box: config.default_view_box,
        default_zoom: config.default_zoom,
        min_zoom: config.min_zoom,
        max_zoom: config.max_zoom,
        default_locale: config.default_locale,
        supported_locales: config.supported_locales,
      });
    }
  };

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Spin />
      </div>
    );
  }

  return (
    <div>
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{
          default_view_box: config?.default_view_box || '0 0 4096 4096',
          default_zoom: config?.default_zoom || 1.0,
          min_zoom: config?.min_zoom || 0.5,
          max_zoom: config?.max_zoom || 3.0,
          default_locale: config?.default_locale || 'en',
          supported_locales: config?.supported_locales || ['en'],
        }}
      >
        <Card title="View Settings" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="default_view_box"
                label="Default ViewBox"
                extra="SVG viewBox (e.g., 0 0 4096 4096)"
              >
                <Input placeholder="0 0 4096 4096" disabled={!isDraft} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="default_zoom" label="Default Zoom">
                <InputNumber
                  min={0.1}
                  max={10}
                  step={0.1}
                  style={{ width: '100%' }}
                  disabled={!isDraft}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="min_zoom" label="Min Zoom">
                <InputNumber
                  min={0.1}
                  max={10}
                  step={0.1}
                  style={{ width: '100%' }}
                  disabled={!isDraft}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="max_zoom" label="Max Zoom">
                <InputNumber
                  min={0.1}
                  max={10}
                  step={0.1}
                  style={{ width: '100%' }}
                  disabled={!isDraft}
                />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        <Card title="Localization" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="default_locale" label="Default Locale">
                <Select options={LOCALES} disabled={!isDraft} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="supported_locales" label="Supported Locales">
                <Select
                  mode="multiple"
                  options={LOCALES}
                  disabled={!isDraft}
                />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        <Card title="Status Colors" style={{ marginBottom: 16 }}>
          <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
            Configure how each status is displayed in the viewer.
          </Text>

          <Row gutter={[16, 16]}>
            {STATUS_KEYS.map((status) => {
              const colors = config?.status_colors?.[status] || {};
              return (
                <Col span={12} key={status}>
                  <Card size="small" title={status.charAt(0).toUpperCase() + status.slice(1)}>
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Text>Fill:</Text>
                        <Text code>{colors.fill || 'default'}</Text>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Text>Stroke:</Text>
                        <Text code>{colors.stroke || 'default'}</Text>
                      </div>
                    </Space>
                  </Card>
                </Col>
              );
            })}
          </Row>
        </Card>

        {isDraft && (
          <div style={{ textAlign: 'right' }}>
            <Space>
              <Button icon={<ReloadOutlined />} onClick={handleReset}>
                Reset
              </Button>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                htmlType="submit"
                loading={updateMutation.isPending}
              >
                Save Configuration
              </Button>
            </Space>
          </div>
        )}
      </Form>
    </div>
  );
}
