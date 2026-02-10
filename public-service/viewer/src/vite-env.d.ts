/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_PUBLIC_API_URL: string;
  readonly VITE_CDN_BASE_URL: string;
  readonly VITE_DEFAULT_LOCALE: string;
  readonly VITE_PROJECT_SLUG: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
