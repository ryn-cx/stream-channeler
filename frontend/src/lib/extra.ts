// TODO: Validate

// TODO: Validate
/**
 * What a row keeps in `extra`, as text and back.
 *
 * `extra` is an object rather than a string, so that a plugin keeping two things
 * there does not have to decide what the one it stored first now means. Nothing
 * on screen can show an object as it is, so the admin tables and the forms that
 * edit it by hand read it as the JSON it is.
 */

// TODO: Validate
/** Read `extra` as the text an admin table shows and a form edits. */
export function extraText(extra: Record<string, unknown> | null | undefined) {
  if (!extra || Object.keys(extra).length === 0) return ""
  return JSON.stringify(extra)
}

// TODO: Validate
/** Read text typed into a form back into what `extra` holds. */
export function parseExtraText(value: string): Record<string, unknown> {
  const trimmed = value.trim()
  if (!trimmed) return {}
  const parsed: unknown = JSON.parse(trimmed)
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    throw new Error("Extra must be a JSON object.")
  }
  return parsed as Record<string, unknown>
}
