export const API_URL_CONFIG = (
  process.env.NEXT_PUBLIC_API_URL?.trim() ?? "http://localhost:8000"
).replace(/\/+$/, "");