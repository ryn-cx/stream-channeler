// TODO: Validate
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

export type InformationRows = Record<string, React.ReactNode>

export function ExternalAnchor({
  href,
  label,
}: {
  href: string
  label: string
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-primary underline break-all"
    >
      {label}
    </a>
  )
}

export function formatInformationDate(value: string | null) {
  if (!value) return null
  return new Date(value).toLocaleString()
}

interface InformationTableProps {
  sourceLabel: string
  tmdbLabel: string
  rowLabels: string[]
  sourceRows: InformationRows
  tmdbRows: InformationRows | null
}

/**
 * What the website and TMDB each say about one record, side by side, so the two
 * accounts can be compared rather than one standing in for the other.
 */
export function InformationTable({
  sourceLabel,
  tmdbLabel,
  rowLabels,
  sourceRows,
  tmdbRows,
}: InformationTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-[140px]">Field</TableHead>
          <TableHead>{sourceLabel}</TableHead>
          <TableHead>{tmdbLabel}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rowLabels.map((label) => (
          <TableRow key={label}>
            <TableCell className="font-medium align-top">{label}</TableCell>
            <TableCell className="align-top whitespace-pre-wrap">
              {sourceRows[label] ?? "—"}
            </TableCell>
            <TableCell className="align-top whitespace-pre-wrap">
              {tmdbRows ? (tmdbRows[label] ?? "—") : "—"}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
