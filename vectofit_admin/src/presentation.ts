type ClassValue =
  | string
  | false
  | null
  | undefined
  | Record<string, unknown>
  | ClassValue[];
export function bindStyles(styles: Record<string, string>) {
  const resolve = (value: ClassValue): string[] =>
    typeof value === "string"
      ? value
          .split(/\s+/)
          .filter(Boolean)
          .flatMap((name) => (styles[name] ? [name, styles[name]] : [name]))
      : Array.isArray(value)
        ? value.flatMap(resolve)
        : value && typeof value === "object"
          ? Object.entries(value).flatMap(([name, enabled]) =>
              enabled ? resolve(name) : [],
            )
          : [];
  return (...values: ClassValue[]) =>
    [...new Set(values.flatMap(resolve))].join(" ");
}
export function each<T>(source: readonly T[]): [number, T][];
export function each(source: number): [number, number][];
export function each<T>(source: Record<string, T>): [string, T][];
export function each<T>(
  source: readonly T[] | Record<string, T> | number,
): ([number, T] | [string, T] | [number, number])[] {
  if (typeof source === "number")
    return Array.from({ length: source }, (_, index) => [index, index + 1]);
  if (Array.isArray(source))
    return source.map((value, index) => [index, value]);
  return Object.entries(source);
}
export const display = (value: unknown): string =>
  value == null
    ? ""
    : typeof value === "object"
      ? JSON.stringify(value, null, 2)
      : String(value);
export function scopeAttributes(props: object): Record<string, string> {
  return Object.fromEntries(
    Object.entries(props).filter(
      ([key, value]) => key.startsWith("data-v-") && typeof value === "string",
    ),
  );
}
