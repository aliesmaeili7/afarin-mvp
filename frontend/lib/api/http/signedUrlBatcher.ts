/**
 * Coalesces signed-URL lookups issued in the same tick into one request.
 *
 * The results page mounts five ad canvases at once, each resolving its own
 * `storage_path`. Left alone that is five round trips and a visibly staggered
 * reveal. Batching here rather than in the components means nothing above the
 * API boundary had to change.
 */
type Resolver = (paths: string[]) => Promise<Record<string, string | null>>;

interface Pending {
  resolve: (url: string | null) => void;
  reject: (error: unknown) => void;
}

export function createSignedUrlBatcher(fetchBatch: Resolver) {
  let queue = new Map<string, Pending[]>();
  let scheduled = false;

  async function flush() {
    const batch = queue;
    queue = new Map();
    scheduled = false;

    const paths = [...batch.keys()];
    try {
      const resolved = await fetchBatch(paths);
      batch.forEach((waiters, path) => {
        waiters.forEach((waiter) => waiter.resolve(resolved[path] ?? null));
      });
    } catch (error) {
      batch.forEach((waiters) => {
        waiters.forEach((waiter) => waiter.reject(error));
      });
    }
  }

  return function resolveOne(path: string): Promise<string | null> {
    return new Promise((resolve, reject) => {
      // The same path requested twice resolves from one lookup.
      const waiters = queue.get(path) ?? [];
      waiters.push({ resolve, reject });
      queue.set(path, waiters);

      if (!scheduled) {
        scheduled = true;
        queueMicrotask(() => void flush());
      }
    });
  };
}
