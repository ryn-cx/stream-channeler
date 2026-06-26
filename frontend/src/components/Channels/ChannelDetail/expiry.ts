// TODO: Validate
// Helpers to convert between an ISO timestamp (what the API stores/returns) and the
// value format used by `<input type="datetime-local">` ("YYYY-MM-DDTHH:mm" in local
// time).

export function isoToLocalInput(iso: string | null | undefined): string {
  if (!iso) return ""
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ""
  // Shift by the timezone offset so the local wall-clock time is preserved, then trim
  // to minute precision.
  const offsetMs = date.getTimezoneOffset() * 60 * 1000
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16)
}

export function localInputToIso(localValue: string): string | null {
  if (!localValue) return null
  const date = new Date(localValue)
  if (Number.isNaN(date.getTime())) return null
  return date.toISOString()
}
