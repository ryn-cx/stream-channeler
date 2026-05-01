// TODO: Validate
import type { Visibility } from "@/client"

export const VISIBILITY_OPTIONS: readonly Visibility[] = [
  "public",
  "unlisted",
  "private",
]

export function visibilityLabel(
  visibility: Visibility | null | undefined,
): string {
  switch (visibility) {
    case "public":
      return "Public"
    case "unlisted":
      return "Unlisted"
    case "private":
      return "Private"
    default:
      return "Private"
  }
}

export function visibilityDotClass(
  visibility: Visibility | null | undefined,
): string {
  switch (visibility) {
    case "public":
      return "bg-green-500"
    case "unlisted":
      return "bg-yellow-500"
    default:
      return "bg-gray-400"
  }
}
