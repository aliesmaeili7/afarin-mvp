import { ApiError } from "@/lib/api/types";

/**
 * Browser-side stand-in for object storage.
 *
 * Uploaded photos are validated, downscaled and kept in IndexedDB (localStorage
 * is far too small for photos) behind opaque `local://` paths. Nothing outside
 * the mock API layer touches this module; Phase 2 swaps it for Supabase Storage
 * with signed URLs and the `storage_path` contract stays identical.
 */

const DB_NAME = "afarin-mock-storage";
const DB_VERSION = 1;
const STORE_NAME = "images";

export const ACCEPTED_MIME_TYPES = ["image/jpeg", "image/png", "image/webp"];
export const MAX_UPLOAD_BYTES = 12 * 1024 * 1024;
const MAX_DIMENSION = 1600;

const objectUrlCache = new Map<string, string>();

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      if (!request.result.objectStoreNames.contains(STORE_NAME)) {
        request.result.createObjectStore(STORE_NAME);
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () =>
      reject(new ApiError("upload_failed", "ذخیره عکس روی این مرورگر ممکن نشد."));
  });
}

async function withStore<T>(
  mode: IDBTransactionMode,
  run: (store: IDBObjectStore) => IDBRequest<T>,
): Promise<T> {
  const db = await openDatabase();
  try {
    return await new Promise<T>((resolve, reject) => {
      const transaction = db.transaction(STORE_NAME, mode);
      const request = run(transaction.objectStore(STORE_NAME));
      request.onsuccess = () => resolve(request.result);
      request.onerror = () =>
        reject(new ApiError("upload_failed", "ذخیره عکس ناموفق بود."));
    });
  } finally {
    db.close();
  }
}

export function validateImageFile(file: File): void {
  if (!ACCEPTED_MIME_TYPES.includes(file.type)) {
    throw new ApiError(
      "validation_error",
      "فقط عکس با فرمت JPG، PNG یا WEBP قابل قبوله.",
    );
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    throw new ApiError(
      "validation_error",
      "حجم عکس بیشتر از ۱۲ مگابایته. یه عکس سبک‌تر انتخاب کن.",
    );
  }
}

function loadBitmap(file: File): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      URL.revokeObjectURL(url);
      resolve(image);
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new ApiError("validation_error", "این فایل یک عکس معتبر نیست."));
    };
    image.src = url;
  });
}

/** Downscales to MAX_DIMENSION on the long edge to keep IndexedDB small. */
async function normalizeImage(file: File): Promise<Blob> {
  const image = await loadBitmap(file);
  const scale = Math.min(1, MAX_DIMENSION / Math.max(image.width, image.height));

  if (scale === 1 && file.size < 1_500_000) return file;

  const canvas = document.createElement("canvas");
  canvas.width = Math.round(image.width * scale);
  canvas.height = Math.round(image.height * scale);

  const context = canvas.getContext("2d");
  if (!context) return file;
  context.drawImage(image, 0, 0, canvas.width, canvas.height);

  const blob = await new Promise<Blob | null>((resolve) =>
    canvas.toBlob(resolve, "image/webp", 0.9),
  );
  return blob ?? file;
}

export async function putImage(file: File): Promise<string> {
  validateImageFile(file);
  const blob = await normalizeImage(file);
  const key = `local://img_${crypto.randomUUID().slice(0, 12)}`;
  await withStore("readwrite", (store) => store.put(blob, key));
  return key;
}

export async function getImageUrl(storagePath: string): Promise<string | null> {
  const cached = objectUrlCache.get(storagePath);
  if (cached) return cached;

  const blob = await withStore<Blob | undefined>("readonly", (store) =>
    store.get(storagePath),
  );
  if (!blob) return null;

  const url = URL.createObjectURL(blob);
  objectUrlCache.set(storagePath, url);
  return url;
}

export async function deleteImage(storagePath: string): Promise<void> {
  const cached = objectUrlCache.get(storagePath);
  if (cached) {
    URL.revokeObjectURL(cached);
    objectUrlCache.delete(storagePath);
  }
  await withStore("readwrite", (store) => store.delete(storagePath));
}
