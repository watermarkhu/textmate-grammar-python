export function firstMatch<T>(values: Iterable<T>, predicate: (item: T) => boolean): T | undefined {
  for (const value of values) {
    if (predicate(value)) return value;
  }
  return undefined;
}

export const asRecord = <T extends object>(value: T) => ({ ...value });
