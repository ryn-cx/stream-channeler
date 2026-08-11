// TODO: Validate
import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

// TODO: Validate
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
