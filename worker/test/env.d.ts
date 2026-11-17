import type * as Main from '../src/index';
import type { Env as WorkerEnv } from '../src/env';

declare global {
  namespace Cloudflare {
    interface GlobalProps {
      mainModule: typeof Main;
    }
    // eslint-disable-next-line @typescript-eslint/no-empty-object-type
    interface Env extends WorkerEnv {}
  }
}
