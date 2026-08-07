// TODO: Validate
import { z } from "zod"

/**
 * Shared Zod field schemas reused across the app's forms. Centralizing these
 * keeps validation — and the empty-string handling that react-hook-form text
 * inputs produce — consistent everywhere.
 */

/**
 * Optional free-text field that also accepts an empty string. Blank inputs are
 * normalized to `undefined` so forms can submit the parsed data straight to the
 * API instead of mapping empty strings by hand.
 */
export const optionalString = z
  .string()
  .optional()
  .or(z.literal(""))
  .transform((value) => value || undefined)

/** Optional integer whose form input may be left blank (empty string). */
export const optionalInt = z
  .union([z.literal(""), z.coerce.number().int()])
  .optional()
  .transform((value) => (value === "" ? undefined : value))

/** Optional non-negative integer whose form input may be left blank. */
export const optionalNonNegativeInt = z
  .union([z.literal(""), z.coerce.number().int().min(0)])
  .optional()
  .transform((value) => (value === "" ? undefined : value))

/** Required identifier ("key") field. */
export const requiredKey = z.string().min(1, "Key is required")

/** Required identifier shared by every copy of the same media. */
export const requiredIdentifier = z.string().min(1, "Identifier is required")

/** Visibility selector shared by plugin and channel forms. */
export const visibilityEnum = z.enum(["public", "unlisted", "private"])

export function nullifyBlanks<T extends object>(data: T): T {
  return Object.fromEntries(
    Object.entries(data).map(([key, value]) => [
      key,
      value === undefined ? null : value,
    ]),
  ) as T
}
