// TODO: Validate
import { ClampedContent } from "@/components/ChannelCommon/ClampedContent"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

export type InformationRows = Record<string, React.ReactNode>

// TODO: Validate
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

// TODO: Validate
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

// TODO: Validate
/**
 * What the website and TMDB each say about one record, side by side, so the two
 * accounts can be compared rather than one standing in for the other.
 *
 * A record TMDB has nothing to say about is only the website's account, so it is
 * laid out on its own rather than beside a column of blanks.
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
          {tmdbRows && <TableHead>{tmdbLabel}</TableHead>}
        </TableRow>
      </TableHeader>
      <TableBody>
        {rowLabels.map((label) => (
          <TableRow key={label}>
            <TableCell className="font-medium align-top">{label}</TableCell>
            <TableCell className="align-top whitespace-pre-wrap">
              <ClampedContent>{sourceRows[label] ?? "—"}</ClampedContent>
            </TableCell>
            {tmdbRows && (
              <TableCell className="align-top whitespace-pre-wrap">
                <ClampedContent>{tmdbRows[label] ?? "—"}</ClampedContent>
              </TableCell>
            )}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
