export interface Page<T> {
  items: readonly T[];
  next?: string;
}

export async function fetchPage<T>(url: string): Promise<Page<T>> {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return (await response.json()) as Page<T>;
}
