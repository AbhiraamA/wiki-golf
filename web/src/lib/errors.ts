/** Shared API error. Kept in its own module so the mock can throw it without importing api.ts,
 * which would create a runtime import cycle (api.ts dynamically imports the mock). */

export class ApiError extends Error {
  constructor(
    public code: string,
    public status: number,
  ) {
    super(code);
  }
}
