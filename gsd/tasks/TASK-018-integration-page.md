# TASK-018: Integration Setup Page

**Phase**: 5 - Admin UI
**Status**: [x] Complete
**Priority**: P1 - High
**Depends On**: TASK-009, TASK-015

## Objective

Create the client API integration configuration UI.

## Files to Create

```
admin-service/ui/src/pages/
└── IntegrationPage.jsx
```

## Implementation

```jsx
// src/pages/IntegrationPage.jsx
import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Card, Form, Input, Select, Button, Switch, InputNumber,
  Typography, Space, Alert, Divider, Table, message, Tag
} from 'antd';
import { ApiOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import api from '../services/api';

const { Title, Text } = Typography;
const { Option } = Select;

const AUTH_TYPES = [
  { value: 'none', label: 'No Authentication' },
  { value: 'bearer', label: 'Bearer Token' },
  { value: 'api_key', label: 'API Key' },
  { value: 'basic', label: 'Basic Auth' },
];

const UPDATE_METHODS = [
  { value: 'polling', label: 'Polling' },
  { value: 'sse', label: 'Server-Sent Events (SSE)' },
  { value: 'webhook', label: 'Webhook' },
];

const DEFAULT_STATUS_MAPPING = {
  available: ['Available', 'AVAILABLE', 'available'],
  reserved: ['Reserved', 'RESERVED', 'reserved', 'Hold', 'HOLD'],
  sold: ['Sold', 'SOLD', 'sold'],
  hidden: ['Hidden', 'HIDDEN', 'hidden'],
  unreleased: ['Unreleased', 'UNRELEASED', 'unreleased'],
};

export default function IntegrationPage() {
  const { slug } = useParams();
  const queryClient = useQueryClient();
  const [form] = Form.useForm();
  const [testResult, setTestResult] = useState(null);
  const [testing, setTesting] = useState(false);

  // Fetch current config
  const { data: config, isLoading } = useQuery({
    queryKey: ['integration', slug],
    queryFn: () => api.get(`/projects/${slug}/integration`).then(res => res.data),
  });

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: (data) => api.put(`/projects/${slug}/integration`, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['integration', slug]);
      message.success('Integration settings saved');
    },
    onError: (error) => {
      message.error(error.response?.data?.detail || 'Failed to save');
    },
  });

  // Test connection
  const testConnection = async () => {
    setTesting(true);
    setTestResult(null);

    try {
      const response = await api.post(`/projects/${slug}/integration/test`);
      setTestResult(response.data);
    } catch (error) {
      setTestResult({
        success: false,
        error: error.response?.data?.detail || 'Test failed',
      });
    } finally {
      setTesting(false);
    }
  };

  const onFinish = (values) => {
    // Build auth credentials
    let auth_credentials = null;

    if (values.auth_type === 'bearer' && values.bearer_token) {
      auth_credentials = { token: values.bearer_token };
    } else if (values.auth_type === 'api_key' && values.api_key) {
      auth_credentials = {
        api_key: values.api_key,
        api_key_header: values.api_key_header || 'X-API-Key',
      };
    } else if (values.auth_type === 'basic' && values.basic_username) {
      auth_credentials = {
        username: values.basic_username,
        password: values.basic_password,
      };
    }

    saveMutation.mutate({
      api_base_url: values.api_base_url,
      auth_type: values.auth_type,
      auth_credentials,
      status_endpoint: values.status_endpoint,
      status_mapping: values.status_mapping,
      update_method: values.update_method,
      polling_interval_seconds: values.polling_interval_seconds,
      timeout_seconds: values.timeout_seconds,
      retry_count: values.retry_count,
    });
  };

  const authType = Form.useWatch('auth_type', form);

  return (
    <div style={{ maxWidth: 800 }}>
      <Card loading={isLoading}>
        <Title level={4}>
          <ApiOutlined /> Client API Integration
        </Title>

        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
          initialValues={{
            api_base_url: config?.api_base_url || '',
            auth_type: config?.auth_type || 'none',
            status_endpoint: config?.status_endpoint || '/api/units/status',
            status_mapping: config?.status_mapping || DEFAULT_STATUS_MAPPING,
            update_method: config?.update_method || 'polling',
            polling_interval_seconds: config?.polling_interval_seconds || 30,
            timeout_seconds: config?.timeout_seconds || 10,
            retry_count: config?.retry_count || 3,
          }}
        >
          <Form.Item
            name="api_base_url"
            label="API Base URL"
            rules={[{ required: true, message: 'Please enter API URL' }]}
          >
            <Input placeholder="https://client-api.example.com" />
          </Form.Item>

          <Form.Item
            name="auth_type"
            label="Authentication Type"
          >
            <Select options={AUTH_TYPES} />
          </Form.Item>

          {/* Bearer Token */}
          {authType === 'bearer' && (
            <Form.Item
              name="bearer_token"
              label="Bearer Token"
            >
              <Input.Password
                placeholder={config?.has_credentials ? '••••••••' : 'Enter token'}
              />
            </Form.Item>
          )}

          {/* API Key */}
          {authType === 'api_key' && (
            <>
              <Form.Item name="api_key" label="API Key">
                <Input.Password
                  placeholder={config?.has_credentials ? '••••••••' : 'Enter API key'}
                />
              </Form.Item>
              <Form.Item name="api_key_header" label="Header Name">
                <Input placeholder="X-API-Key" />
              </Form.Item>
            </>
          )}

          {/* Basic Auth */}
          {authType === 'basic' && (
            <>
              <Form.Item name="basic_username" label="Username">
                <Input />
              </Form.Item>
              <Form.Item name="basic_password" label="Password">
                <Input.Password />
              </Form.Item>
            </>
          )}

          <Divider>Status Endpoint</Divider>

          <Form.Item
            name="status_endpoint"
            label="Status Endpoint Path"
          >
            <Input placeholder="/api/units/status" />
          </Form.Item>

          <Form.Item
            name="update_method"
            label="Update Method"
          >
            <Select options={UPDATE_METHODS} />
          </Form.Item>

          <Space>
            <Form.Item
              name="polling_interval_seconds"
              label="Polling Interval (seconds)"
            >
              <InputNumber min={5} max={300} />
            </Form.Item>

            <Form.Item
              name="timeout_seconds"
              label="Timeout (seconds)"
            >
              <InputNumber min={1} max={60} />
            </Form.Item>

            <Form.Item
              name="retry_count"
              label="Retry Count"
            >
              <InputNumber min={0} max={10} />
            </Form.Item>
          </Space>

          <Divider>Status Mapping</Divider>

          <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
            Map client status values to standard statuses. Enter comma-separated values.
          </Text>

          {Object.keys(DEFAULT_STATUS_MAPPING).map((status) => (
            <Form.Item
              key={status}
              name={['status_mapping', status]}
              label={
                <Tag color={status === 'available' ? 'green' : status === 'sold' ? 'red' : 'default'}>
                  {status.toUpperCase()}
                </Tag>
              }
            >
              <Select
                mode="tags"
                placeholder={`Values that mean "${status}"`}
              />
            </Form.Item>
          ))}

          <Divider />

          <Space>
            <Button
              type="primary"
              htmlType="submit"
              loading={saveMutation.isPending}
            >
              Save Settings
            </Button>

            <Button
              onClick={testConnection}
              loading={testing}
              icon={<ApiOutlined />}
            >
              Test Connection
            </Button>
          </Space>
        </Form>

        {/* Test Result */}
        {testResult && (
          <Alert
            style={{ marginTop: 24 }}
            type={testResult.success ? 'success' : 'error'}
            icon={testResult.success ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
            message={testResult.success ? 'Connection Successful' : 'Connection Failed'}
            description={
              <div>
                {testResult.status_code && (
                  <p>Status Code: {testResult.status_code}</p>
                )}
                {testResult.response_time_ms && (
                  <p>Response Time: {testResult.response_time_ms}ms</p>
                )}
                {testResult.error && (
                  <p style={{ color: 'red' }}>{testResult.error}</p>
                )}
                {testResult.sample_data && (
                  <pre style={{ fontSize: 12, maxHeight: 200, overflow: 'auto' }}>
                    {JSON.stringify(testResult.sample_data, null, 2)}
                  </pre>
                )}
              </div>
            }
          />
        )}
      </Card>
    </div>
  );
}
```

## Acceptance Criteria

- [ ] Can configure API base URL
- [ ] Can select authentication type
- [ ] Credentials masked in UI
- [ ] Can test connection
- [ ] Test shows status code and sample data
- [ ] Can configure status mapping
- [ ] Settings saved to API
