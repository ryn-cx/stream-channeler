// TODO: Validate
import type { Visibility } from "@/client"

export const VISIBILITY_OPTIONS: readonly Visibility[] = [
  "public",
  "unlisted",
  "private",
]

// TODO: Validate
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

// TODO: Validate
export function visibilityDescription(
  visibility: Visibility | null | undefined,
): string {
  switch (visibility) {
    case "public":
      return "Public channels are accessible by anyone with the link and may appear in the public channels list."
    case "unlisted":
      return "Unlisted channels are accessible by anyone with the link."
    default:
      return "Private channels are only accessible by the owner."
  }
}

// TODO: Validate
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
