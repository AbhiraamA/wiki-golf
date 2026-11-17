// wrangler needs the static assets folder to exist. In dev the Vite server serves the
// front end, so an empty folder is enough when web/dist has not been built yet.
import { mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

mkdirSync(fileURLToPath(new URL('../../web/dist', import.meta.url)), { recursive: true });
