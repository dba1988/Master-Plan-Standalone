import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout, Typography } from 'antd'

const { Header, Content } = Layout
const { Title } = Typography

function HomePage() {
  return (
    <div style={{ textAlign: 'center', padding: '48px' }}>
      <Title level={2}>Master Plan Studio</Title>
      <p>Admin dashboard for managing master plans.</p>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <Layout style={{ minHeight: '100vh' }}>
        <Header style={{ display: 'flex', alignItems: 'center' }}>
          <Title level={4} style={{ color: 'white', margin: 0 }}>
            Master Plan Studio
          </Title>
        </Header>
        <Content style={{ padding: '24px' }}>
          <Routes>
            <Route path="/" element={<HomePage />} />
          </Routes>
        </Content>
      </Layout>
    </BrowserRouter>
  )
}

export default App
