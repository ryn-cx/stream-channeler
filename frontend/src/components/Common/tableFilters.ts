import type { ColumnFiltersState, Row } from "@tanstack/react-table"


/**
 * Convert a naive date string ("YYYY-MM-DD" or "YYYY-MM-DDTHH:mm"), into an ISO string.
 * A date without a time will be set to the start of the end of the day based on the
 * value of kind.
 */
function datetimeStringToIsoString(
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
  const [rawMinimum, rawMaximum] = (filterValue as [string?, string?] | undefined) ?? []
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

export function serializeFilterOptions(filterOptions: ColumnFiltersState): string {
  const converted = filterOptions.map((option) =>
    Array.isArray(option.value)
      ? {
        ...option,
        value: [
          datetimeStringToIsoString(String(option.value[0] ?? ""), "minimum"),
          datetimeStringToIsoString(String(option.value[1] ?? ""), "maximum"),
        ],
      }
      : option,
  )
  return JSON.stringify(converted)
}
