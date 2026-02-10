/**
 * Integration Tab
 *
 * Configure client API integration for status updates.
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Form,
  Input,
  Select,
  Button,
  Space,
  Card,
  Typography,
  message,
  Row,
  Col,
  Spin,
  Alert,
  Descriptions,
  Tag,
  InputNumber,
} from 'antd';
import {
  SaveOutlined,
  ApiOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import { integrationApi } from '../services/api';

const { Text, Paragraph } = Typography;

const AUTH_TYPES = [
  { value: 'none', label: 'None' },
  { value: 'bearer', label: 'Bearer Token' },
  { value: 'api_key', label: 'API Key' },
  { value: 'basic', label: 'Basic Auth' },
];

const UPDATE_METHODS = [
  { value: 'polling', label: 'Polling' },
  { value: 'sse', label: 'Server-Sent Events' },
  { value: 'webhook', label: 'Webhook' },
];

export default function IntegrationTab({ projectSlug }) {
  const [testResult, setTestResult] = useState(null);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  const { data: config, isLoading } = useQuery({
    queryKey: ['integration', projectSlug],
    queryFn: () => integrationApi.get(projectSlug),
  });

  const updateMutation = useMutation({
    mutationFn: (data) => integrationApi.update(projectSlug, data),
    onSuccess: () => {
      message.success('Integration settings saved');
      queryClient.invalidateQueries({
        queryKey: ['integration', projectSlug],
      });
    },
    onError: (error) => {
      message.error(error.response?.data?.detail || 'Failed to save settings');
    },
  });

  const testMutation = useMutation({
    mutationFn: () => integrationApi.test(projectSlug),
    onSuccess: (data) => {
      setTestResult(data);
      if (data.success) {
        message.success('Connection successful');
      } else {
        message.error(`Connection failed: ${data.error}`);
      }
    },
    onError: (error) => {
      setTestResult({ success: false, error: error.message });
      message.error('Connection test failed');
    },
  });

  const deleteCredentialsMutation = useMutation({
    mutationFn: () => integrationApi.deleteCredentials(projectSlug),
    onSuccess: () => {
      message.success('Credentials deleted');
      queryClient.invalidateQueries({
        queryKey: ['integration', projectSlug],
      });
    },
    onError: (error) => {
      message.error(error.response?.data?.detail || 'Failed to delete credentials');
    },
  });

  const handleSubmit = (values) => {
    const data = {
      api_base_url: values.api_base_url,
      auth_type: values.auth_type,
      status_endpoint: values.status_endpoint,
      update_method: values.update_method,
      polling_interval_seconds: values.polling_interval_seconds,
      timeout_seconds: values.timeout_seconds,
      retry_count: values.retry_count,
    };

    // Add credentials if provided
    if (values.auth_type === 'bearer' && values.token) {
      data.auth_credentials = { token: values.token };
    } else if (values.auth_type === 'api_key' && values.api_key) {
      data.auth_credentials = {
        api_key: values.api_key,
        api_key_header: values.api_key_header || 'X-API-Key',
      };
    } else if (values.auth_type === 'basic' && values.username) {
      data.auth_credentials = {
        username: values.username,
        password: values.password,
      };
    }

    updateMutation.mutate(data);
  };

  const authType = Form.useWatch('auth_type', form);

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
          api_base_url: config?.api_base_url || '',
          auth_type: config?.auth_type || 'none',
          status_endpoint: config?.status_endpoint || '',
          update_method: config?.update_method || 'polling',
          polling_interval_seconds: config?.polling_interval_seconds || 30,
          timeout_seconds: config?.timeout_seconds || 10,
          retry_count: config?.retry_count || 3,
        }}
      >
        <Card title="API Connection" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={16}>
              <Form.Item
                name="api_base_url"
                label="API Base URL"
                extra="Base URL of the client's API"
              >
                <Input placeholder="https://api.client.com" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="status_endpoint"
                label="Status Endpoint"
                extra="Path to fetch unit statuses"
              >
                <Input placeholder="/api/units/status" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="update_method" label="Update Method">
                <Select options={UPDATE_METHODS} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="polling_interval_seconds" label="Polling Interval (sec)">
                <InputNumber min={5} max={300} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="timeout_seconds" label="Timeout (sec)">
                <InputNumber min={1} max={60} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        <Card
          title="Authentication"
          style={{ marginBottom: 16 }}
          extra={
            config?.has_credentials && (
              <Button
                type="text"
                danger
                icon={<DeleteOutlined />}
                onClick={() => deleteCredentialsMutation.mutate()}
                loading={deleteCredentialsMutation.isPending}
              >
                Clear Credentials
              </Button>
            )
          }
        >
          <Form.Item name="auth_type" label="Authentication Type">
            <Select options={AUTH_TYPES} style={{ width: 200 }} />
          </Form.Item>

          {authType === 'bearer' && (
            <Form.Item
              name="token"
              label="Bearer Token"
              extra={config?.has_credentials ? 'Leave empty to keep existing token' : ''}
            >
              <Input.Password placeholder="Enter token" />
            </Form.Item>
          )}

          {authType === 'api_key' && (
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="api_key"
                  label="API Key"
                  extra={config?.has_credentials ? 'Leave empty to keep existing key' : ''}
                >
                  <Input.Password placeholder="Enter API key" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="api_key_header"
                  label="Header Name"
                  extra="Custom header for API key"
                >
                  <Input placeholder="X-API-Key" />
                </Form.Item>
              </Col>
            </Row>
          )}

          {authType === 'basic' && (
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="username" label="Username">
                  <Input placeholder="Username" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="password"
                  label="Password"
                  extra={config?.has_credentials ? 'Leave empty to keep existing' : ''}
                >
                  <Input.Password placeholder="Password" />
                </Form.Item>
              </Col>
            </Row>
          )}

          {config?.has_credentials && (
            <Alert
              message="Credentials stored"
              description="Encrypted credentials are saved. They are never exposed in API responses."
              type="success"
              showIcon
              style={{ marginTop: 16 }}
            />
          )}
        </Card>

        {/* Test Connection */}
        <Card title="Test Connection" style={{ marginBottom: 16 }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Button
              icon={<ApiOutlined />}
              onClick={() => testMutation.mutate()}
              loading={testMutation.isPending}
            >
              Test Connection
            </Button>

            {testResult && (
              <Alert
                type={testResult.success ? 'success' : 'error'}
                showIcon
                icon={testResult.success ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
                message={testResult.success ? 'Connection Successful' : 'Connection Failed'}
                description={
                  testResult.success ? (
                    <Descriptions size="small" column={2}>
                      <Descriptions.Item label="Status">{testResult.status_code}</Descriptions.Item>
                      <Descriptions.Item label="Response Time">
                        {testResult.response_time_ms}ms
                      </Descriptions.Item>
                    </Descriptions>
                  ) : (
                    <Text type="danger">{testResult.error}</Text>
                  )
                }
              />
            )}
          </Space>
        </Card>

        {/* Status Mapping Info */}
        <Card title="Status Mapping" style={{ marginBottom: 16 }}>
          <Paragraph type="secondary">
            Client API status values are mapped to the 5-status taxonomy:
          </Paragraph>
          <Space wrap>
            <Tag color="green">available</Tag>
            <Tag color="orange">reserved</Tag>
            <Tag color="red">sold</Tag>
            <Tag color="default">hidden</Tag>
            <Tag color="purple">unreleased</Tag>
          </Space>
          <Paragraph type="secondary" style={{ marginTop: 16 }}>
            Configure custom mappings in the status_mapping field of the integration config.
          </Paragraph>
        </Card>

        <div style={{ textAlign: 'right' }}>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            htmlType="submit"
            loading={updateMutation.isPending}
          >
            Save Integration Settings
          </Button>
        </div>
      </Form>
    </div>
  );
}
