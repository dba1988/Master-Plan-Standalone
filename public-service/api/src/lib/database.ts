import pg from 'pg';
import { config } from './config.js';

const { Pool } = pg;

// Create read-only connection pool
const pool = new Pool({
  connectionString: config.databaseUrl,
  max: 10,
});

/**
 * Execute a raw SQL query.
 * Use this for all database access in public-service.
 */
export async function query<T>(sql: string, params: unknown[] = []): Promise<T[]> {
  const result = await pool.query(sql, params);
  return result.rows as T[];
}

/**
 * Check if database is connected.
 */
export async function checkConnection(): Promise<boolean> {
  try {
    await pool.query('SELECT 1');
    return true;
  } catch {
    return false;
  }
}

export { pool };
