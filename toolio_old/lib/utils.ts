/**
 * cn — the shadcn class-name helper.
 *
 * The canonical shadcn implementation is:
 *
 *   import { type ClassValue } from "clsx"
 *   import { twMerge } from "tailwind-merge"
 *   export function cn(...inputs: ClassValue[]) {
 *     return twMerge(clsx(inputs))
 *   }
 *
 * This copy is dependency-free so the static site can build the React islands
 * without adding two npm packages. On a real shadcn project, replace it with
 * the version above (see schoolio/SETUP.md).
 */

export type ClassValue =
  | string
  | number
  | null
  | undefined
  | false
  | ClassValue[];

export function cn(...inputs: ClassValue[]): string {
  const out: string[] = [];
  const walk = (v: ClassValue): void => {
    if (!v && v !== 0) return;
    if (typeof v === "string" || typeof v === "number") {
      out.push(String(v));
      return;
    }
    if (Array.isArray(v)) {
      for (const item of v) walk(item);
    }
  };
  for (const input of inputs) walk(input);
  return out.join(" ");
}

export default cn;
