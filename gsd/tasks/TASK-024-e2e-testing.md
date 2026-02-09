# TASK-024: End-to-End Testing

**Phase**: 7 - Integration & Polish
**Status**: [ ] Not Started
**Priority**: P1 - High
**Depends On**: All previous tasks

## Objective

Create comprehensive end-to-end tests covering the full workflow from admin UI to map viewer.

## Files to Create

```
e2e/
├── package.json
├── playwright.config.ts
├── tests/
│   ├── auth.spec.ts
│   ├── projects.spec.ts
│   ├── editor.spec.ts
│   ├── publish.spec.ts
│   └── viewer.spec.ts
├── fixtures/
│   ├── test-user.ts
│   └── test-project.ts
└── utils/
    └── helpers.ts
```

## Implementation

### Package.json
```json
{
  "name": "master-plan-e2e",
  "private": true,
  "scripts": {
    "test": "playwright test",
    "test:ui": "playwright test --ui",
    "test:headed": "playwright test --headed",
    "test:debug": "playwright test --debug",
    "report": "playwright show-report"
  },
  "devDependencies": {
    "@playwright/test": "^1.40.0",
    "@types/node": "^20.10.0"
  }
}
```

### Playwright Config
```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [
    ['html'],
    ['list'],
  ],

  use: {
    baseURL: process.env.ADMIN_URL || 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  webServer: [
    {
      command: 'cd ../admin-api && uvicorn app.main:app --port 8000',
      url: 'http://localhost:8000/health',
      reuseExistingServer: !process.env.CI,
    },
    {
      command: 'cd ../admin-ui && npm run dev',
      url: 'http://localhost:5173',
      reuseExistingServer: !process.env.CI,
    },
  ],
});
```

### Test Fixtures
```typescript
// fixtures/test-user.ts
import { test as base } from '@playwright/test';

export interface TestUser {
  email: string;
  password: string;
  name: string;
}

export const testUser: TestUser = {
  email: 'test@example.com',
  password: 'testpassword123',
  name: 'Test User',
};

export const test = base.extend<{ authenticatedPage: any }>({
  authenticatedPage: async ({ page }, use) => {
    // Login before test
    await page.goto('/login');
    await page.fill('input[name="email"]', testUser.email);
    await page.fill('input[name="password"]', testUser.password);
    await page.click('button[type="submit"]');

    // Wait for redirect to dashboard
    await page.waitForURL('**/projects**');

    await use(page);
  },
});
```

```typescript
// fixtures/test-project.ts
export interface TestProject {
  name: string;
  slug: string;
  nameAr?: string;
}

export const testProject: TestProject = {
  name: 'E2E Test Project',
  slug: 'e2e-test-project',
  nameAr: 'مشروع اختبار',
};
```

### Helper Utilities
```typescript
// utils/helpers.ts
import { Page, expect } from '@playwright/test';

export async function waitForToast(page: Page, message: string) {
  const toast = page.locator('.ant-message-notice').filter({ hasText: message });
  await expect(toast).toBeVisible({ timeout: 10000 });
}

export async function clearTestData(page: Page, projectSlug: string) {
  // Delete test project via API
  const response = await page.request.delete(`/api/projects/${projectSlug}`, {
    headers: {
      'Authorization': `Bearer ${await getAuthToken(page)}`,
    },
  });
  return response.ok();
}

export async function getAuthToken(page: Page): Promise<string> {
  const storage = await page.evaluate(() => localStorage.getItem('auth'));
  if (storage) {
    const auth = JSON.parse(storage);
    return auth.token;
  }
  return '';
}

export async function uploadFile(page: Page, selector: string, filePath: string) {
  const fileInput = page.locator(selector);
  await fileInput.setInputFiles(filePath);
}
```

### Auth Tests
```typescript
// tests/auth.spec.ts
import { test, expect } from '@playwright/test';
import { testUser } from '../fixtures/test-user';

test.describe('Authentication', () => {
  test('should show login page', async ({ page }) => {
    await page.goto('/login');

    await expect(page.locator('h1, h2, h3').filter({ hasText: /login|sign in/i })).toBeVisible();
    await expect(page.locator('input[name="email"]')).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
  });

  test('should reject invalid credentials', async ({ page }) => {
    await page.goto('/login');

    await page.fill('input[name="email"]', 'wrong@example.com');
    await page.fill('input[name="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');

    await expect(page.locator('.ant-message-error, .ant-alert-error')).toBeVisible();
  });

  test('should login successfully', async ({ page }) => {
    await page.goto('/login');

    await page.fill('input[name="email"]', testUser.email);
    await page.fill('input[name="password"]', testUser.password);
    await page.click('button[type="submit"]');

    await page.waitForURL('**/');
    await expect(page.locator('text=Projects')).toBeVisible();
  });

  test('should logout', async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.fill('input[name="email"]', testUser.email);
    await page.fill('input[name="password"]', testUser.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/');

    // Find and click logout
    await page.click('[data-testid="user-menu"], .ant-dropdown-trigger');
    await page.click('text=Logout');

    await page.waitForURL('**/login');
  });

  test('should redirect unauthenticated users to login', async ({ page }) => {
    await page.goto('/projects/test');
    await page.waitForURL('**/login');
  });
});
```

### Projects Tests
```typescript
// tests/projects.spec.ts
import { expect } from '@playwright/test';
import { test } from '../fixtures/test-user';
import { testProject } from '../fixtures/test-project';
import { waitForToast } from '../utils/helpers';

test.describe('Projects', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
  });

  test('should display projects list', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('text=Projects')).toBeVisible();
  });

  test('should create new project', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    // Click new project button
    await page.click('button:has-text("New Project")');
    await page.waitForURL('**/projects/new');

    // Fill form
    await page.fill('input[name="name"]', testProject.name);

    // Slug should auto-generate
    const slugInput = page.locator('input[name="slug"]');
    await expect(slugInput).toHaveValue(testProject.slug);

    // Add Arabic name
    await page.fill('input[name="name_ar"]', testProject.nameAr || '');

    // Submit
    await page.click('button[type="submit"]');

    // Should redirect to project dashboard
    await page.waitForURL(`**/projects/${testProject.slug}**`);
    await expect(page.locator(`text=${testProject.name}`)).toBeVisible();
  });

  test('should navigate to project dashboard', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    // Click on project card
    await page.click(`text=${testProject.name}`);

    await page.waitForURL(`**/projects/${testProject.slug}**`);

    // Verify dashboard elements
    await expect(page.locator('text=Dashboard')).toBeVisible();
    await expect(page.locator('text=Draft Version')).toBeVisible();
  });

  test('should show quick actions', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    await page.goto(`/projects/${testProject.slug}`);

    await expect(page.locator('button:has-text("Open Editor")')).toBeVisible();
    await expect(page.locator('button:has-text("Upload Assets")')).toBeVisible();
    await expect(page.locator('button:has-text("Configure API")')).toBeVisible();
    await expect(page.locator('button:has-text("Publish")')).toBeVisible();
  });
});
```

### Editor Tests
```typescript
// tests/editor.spec.ts
import { expect } from '@playwright/test';
import { test } from '../fixtures/test-user';
import { testProject } from '../fixtures/test-project';

test.describe('Editor', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto(`/projects/${testProject.slug}/editor`);
  });

  test('should load editor page', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    // Check for main editor components
    await expect(page.locator('[class*="tools-panel"], [data-testid="tools-panel"]')).toBeVisible();
    await expect(page.locator('[class*="canvas"], svg')).toBeVisible();
    await expect(page.locator('[class*="inspector"], [data-testid="inspector"]')).toBeVisible();
  });

  test('should display overlay list', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    // Look for overlay categories
    await expect(page.locator('text=/zone|unit|poi/i')).toBeVisible();
  });

  test('should select overlay and show inspector', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    // Click on an overlay in the list
    const overlayItem = page.locator('[class*="list-item"], .ant-list-item').first();

    if (await overlayItem.isVisible()) {
      await overlayItem.click();

      // Inspector should show properties
      await expect(page.locator('text=Properties')).toBeVisible();
      await expect(page.locator('input[value], [class*="reference"]')).toBeVisible();
    }
  });

  test('should enable save button on edit', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    // Select an overlay
    const overlayItem = page.locator('[class*="list-item"], .ant-list-item').first();

    if (await overlayItem.isVisible()) {
      await overlayItem.click();

      // Edit label
      const labelInput = page.locator('input[placeholder*="English"], input[name*="label"]').first();
      if (await labelInput.isVisible()) {
        await labelInput.fill('Updated Label');

        // Save button should be enabled
        const saveButton = page.locator('button:has-text("Save")');
        await expect(saveButton).toBeEnabled();
      }
    }
  });
});
```

### Publish Tests
```typescript
// tests/publish.spec.ts
import { expect } from '@playwright/test';
import { test } from '../fixtures/test-user';
import { testProject } from '../fixtures/test-project';
import { waitForToast } from '../utils/helpers';

test.describe('Publish', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto(`/projects/${testProject.slug}/publish`);
  });

  test('should display version status', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    await expect(page.locator('text=Version Status')).toBeVisible();
    await expect(page.locator('text=/Draft Version|Published Version/i')).toBeVisible();
  });

  test('should show environment selector', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    // Find environment dropdown
    const envSelect = page.locator('.ant-select, select').filter({ hasText: /production|staging/i });

    if (await envSelect.isVisible()) {
      await envSelect.click();
      await expect(page.locator('text=Development')).toBeVisible();
      await expect(page.locator('text=Staging')).toBeVisible();
      await expect(page.locator('text=Production')).toBeVisible();
    }
  });

  test('should show publish button', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    const publishButton = page.locator('button:has-text("Publish")');
    await expect(publishButton).toBeVisible();
  });

  test('should show version history', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    await expect(page.locator('text=Version History')).toBeVisible();
  });
});
```

### Viewer Tests
```typescript
// tests/viewer.spec.ts
import { test, expect } from '@playwright/test';
import { testProject } from '../fixtures/test-project';

const VIEWER_URL = process.env.VIEWER_URL || 'http://localhost:3000';

test.describe('Map Viewer', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${VIEWER_URL}/projects/${testProject.slug}`);
  });

  test('should load viewer', async ({ page }) => {
    // Wait for OpenSeadragon to initialize
    await page.waitForSelector('.openseadragon-container, [class*="viewer"]', { timeout: 30000 });
  });

  test('should show locale toggle', async ({ page }) => {
    await page.waitForSelector('.openseadragon-container');

    const localeButton = page.locator('button:has-text("العربية"), button:has-text("English")');
    await expect(localeButton).toBeVisible();
  });

  test('should toggle locale', async ({ page }) => {
    await page.waitForSelector('.openseadragon-container');

    const localeButton = page.locator('button:has-text("العربية"), button:has-text("English")');
    const initialText = await localeButton.textContent();

    await localeButton.click();

    // Button text should change
    await expect(localeButton).not.toHaveText(initialText || '');
  });

  test('should display overlays', async ({ page }) => {
    await page.waitForSelector('.openseadragon-container');

    // Wait for SVG overlays
    await page.waitForSelector('svg path, svg polygon, svg circle', { timeout: 10000 });

    const overlays = page.locator('svg path, svg polygon');
    const count = await overlays.count();

    expect(count).toBeGreaterThan(0);
  });

  test('should show status indicator', async ({ page }) => {
    await page.waitForSelector('.openseadragon-container');

    // Look for status indicator
    const statusIndicator = page.locator('text=/available|sold|reserved/i');

    if (await statusIndicator.isVisible()) {
      await expect(statusIndicator).toBeVisible();
    }
  });

  test('should select overlay on click', async ({ page }) => {
    await page.waitForSelector('.openseadragon-container');
    await page.waitForSelector('svg path, svg polygon');

    // Click on first overlay
    const overlay = page.locator('svg path, svg polygon').first();
    await overlay.click();

    // Panel should appear
    const panel = page.locator('[class*="panel"], [class*="details"]');
    await expect(panel).toBeVisible({ timeout: 5000 });
  });

  test('should support zoom controls', async ({ page }) => {
    await page.waitForSelector('.openseadragon-container');

    // Find zoom buttons
    const zoomIn = page.locator('[title*="Zoom in"], button:has-text("+")');
    const zoomOut = page.locator('[title*="Zoom out"], button:has-text("-")');

    if (await zoomIn.isVisible()) {
      await zoomIn.click();
      await page.waitForTimeout(500);
      await zoomOut.click();
    }
  });
});
```

## Acceptance Criteria

- [ ] All auth tests pass
- [ ] Project CRUD tests pass
- [ ] Editor interaction tests pass
- [ ] Publish workflow tests pass
- [ ] Viewer tests pass
- [ ] Tests run in CI pipeline
- [ ] HTML report generated
- [ ] Screenshots on failure
