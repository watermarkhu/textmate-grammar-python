function sealed<T extends { new (...args: any[]): object }>(target: T): T {
  Object.seal(target);
  Object.seal(target.prototype);
  return target;
}

@sealed
export class Cache<T> {
  #entries = new Map<string, T>();
  get(key: string): T | undefined {
    return this.#entries.get(key);
  }
}
