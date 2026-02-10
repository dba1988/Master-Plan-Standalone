import { useState, useEffect } from 'react';

function App() {
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const apiUrl = import.meta.env.VITE_PUBLIC_API_URL || 'http://localhost:8001';

    fetch(`${apiUrl}/health`)
      .then(res => res.json())
      .then(() => setReady(true))
      .catch(err => {
        console.error('API health check failed:', err);
        setError('Failed to connect to API');
      });
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Master Plan Viewer</h1>
      </header>

      <main className="app-main">
        {error ? (
          <div className="status-error">
            <p>{error}</p>
          </div>
        ) : (
          <div className="status-container">
            <p>API Status: {ready ? 'Connected' : 'Connecting...'}</p>
            <p className="hint">Map viewer will be implemented in TASK-020</p>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
