type User = { id: number; name: string };

export function greeting(user: User, unread: number): string {
  const suffix = unread === 1 ? "message" : "messages";
  return `Hello, ${user.name}! You have ${unread} ${suffix}.`;
}

const tagged = String.raw`line one\nline two`;
