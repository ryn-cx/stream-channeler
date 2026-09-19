// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { useState } from "react"

import { type EpisodeDatabaseRow, EpisodesService } from "@/client"
import { SeasonInformationDialog } from "@/components/ChannelCommon/SeasonInformationDialog"
import { TitleInformationDialog } from "@/components/ChannelCommon/TitleInformationDialog"
import { Label } from "@/components/ui/label"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

// TODO: Validate
const columnNames = (rows: EpisodeDatabaseRow[]) => {
  const names: string[] = []
  for (const row of rows) {
    for (const column of row.columns) {
      if (!names.includes(column.name)) names.push(column.name)
    }
  }
  return names
}

// TODO: Validate
const columnValue = (row: EpisodeDatabaseRow, name: string) =>
  row.columns.find((column) => column.name === name)?.value ?? null

// TODO: Validate
const DatabaseValue = ({
  name,
  value,
  onOpenRecord,
}: {
  name: string
  value: string | null
  onOpenRecord: (() => void) | null
}) => {
  if (value === null) return <span className="text-muted-foreground">—</span>
  if (onOpenRecord) {
    return (
      <button
        type="button"
        className="text-left text-primary underline break-all"
        onClick={onOpenRecord}
      >
        {value}
      </button>
    )
  }
  if (name === "image_url" || name === "thumbnail_url") {
    return (
      <div className="space-y-1">
        <img
          src={value}
          alt={name}
          className="max-h-32 rounded border object-contain"
        />
        <a
          href={value}
          target="_blank"
          rel="noopener noreferrer"
          className="block text-xs text-primary underline break-all"
        >
          {value}
        </a>
      </div>
    )
  }
  if (value.startsWith("http://") || value.startsWith("https://")) {
    return (
      <a
        href={value}
        target="_blank"
        rel="noopener noreferrer"
        className="text-primary underline break-all"
      >
        {value}
      </a>
    )
  }
  return <span className="break-all whitespace-pre-wrap">{value}</span>
}

// TODO: Validate
export function EpisodeDatabaseDetails({
  episodeId,
  enabled,
}: {
  episodeId: string
  enabled: boolean
}) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["episode-database", episodeId],
    queryFn: () => EpisodesService.getEpisodeDatabaseRows({ episodeId }),
    enabled,
  })
  const [openSeasonId, setOpenSeasonId] = useState<string | null>(null)
  const [openTitleId, setOpenTitleId] = useState<string | null>(null)

  const rows = data ? [data.episode, ...data.tmdb_episodes] : []

  const recordOpener = (row: EpisodeDatabaseRow, name: string) => {
    if (name === "season_name") {
      const seasonId = columnValue(row, "season_id")
      return seasonId ? () => setOpenSeasonId(seasonId) : null
    }
    if (name === "title_name") {
      const titleId = columnValue(row, "title_id")
      return titleId ? () => setOpenTitleId(titleId) : null
    }
    return null
  }

  return (
    <div className="space-y-2">
      <Label>Database</Label>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Reading the database…</p>
      ) : null}
      {error ? (
        <p className="text-sm text-muted-foreground">
          Couldn't read the database rows.
        </p>
      ) : null}

      {data ? (
        <div className="overflow-x-auto rounded-md border bg-background">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[200px]">Column</TableHead>
                {rows.map((row, index) => (
                  <TableHead key={row.episode_id} className="min-w-[240px]">
                    {index === 0 ? "This episode" : "Canonical link"}
                    <span className="block text-xs font-normal text-muted-foreground">
                      {row.label}
                    </span>
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {columnNames(rows).map((name) => (
                <TableRow key={name}>
                  <TableCell className="font-medium align-top">
                    {name}
                  </TableCell>
                  {rows.map((row) => (
                    <TableCell
                      key={row.episode_id}
                      className="align-top text-xs"
                    >
                      <DatabaseValue
                        name={name}
                        value={columnValue(row, name)}
                        onOpenRecord={recordOpener(row, name)}
                      />
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : null}

      {openSeasonId ? (
        <SeasonInformationDialog
          seasonIds={[openSeasonId]}
          open
          onOpenChange={(isOpen) => {
            if (!isOpen) setOpenSeasonId(null)
          }}
        />
      ) : null}
      {openTitleId ? (
        <TitleInformationDialog
          titleId={openTitleId}
          open
          onOpenChange={(isOpen) => {
            if (!isOpen) setOpenTitleId(null)
          }}
        />
      ) : null}
    </div>
  )
}
