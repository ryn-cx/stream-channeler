// TODO: Validate
import type { Row } from "@tanstack/react-table"

// Convert a naive date string ("YYYY-MM-DD" or "YYYY-MM-DDTHH:mm") into an ISO string. A
// bare date is expanded to the start of the day for a minimum bound and the end of the
// day for a maximum bound so the whole day is covered.
export function datetimeStringToIsoString(
  datetimeString: string,
  kind: "minimum" | "maximum",
): string {
  if (!datetimeString) return ""
  const withTime = datetimeString.includes("T")
    ? datetimeString
    : `${datetimeString}T${kind === "minimum" ? "00:00:00.000" : "23:59:59.999"}`
  const date = new Date(withTime)
  return Number.isNaN(date.getTime()) ? "" : date.toISOString()
}

export function dateRangeFilter<TData>(
  row: Row<TData>,
  columnId: string,
  filterValue: unknown,
): boolean {
  const [rawMinimum, rawMaximum] =
    (filterValue as [string?, string?] | undefined) ?? []
  const minimum = datetimeStringToIsoString(rawMinimum ?? "", "minimum")
  const maximum = datetimeStringToIsoString(rawMaximum ?? "", "maximum")
  if (!minimum && !maximum) return true

  const rawDate = row.getValue<string | null | undefined>(columnId)
  if (!rawDate) return false
  const parsedDate = new Date(rawDate).getTime()

  if (minimum && parsedDate < new Date(minimum).getTime()) return false
  if (maximum && parsedDate > new Date(maximum).getTime()) return false
  return true
}

export function numberRangeFilter<TData>(
  row: Row<TData>,
  columnId: string,
  filterValue: unknown,
): boolean {
  const [rawMinimum, rawMaximum] =
    (filterValue as [string?, string?] | undefined) ?? []
  const minimum = rawMinimum ?? ""
  const maximum = rawMaximum ?? ""
  if (!minimum && !maximum) return true

  const rawValue = row.getValue<number | null | undefined>(columnId)
  if (rawValue === null || rawValue === undefined) return false

  if (minimum !== "" && rawValue < Number(minimum)) return false
  if (maximum !== "" && rawValue > Number(maximum)) return false
  return true
}
