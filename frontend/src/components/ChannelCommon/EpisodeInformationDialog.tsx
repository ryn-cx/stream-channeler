// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { Flag } from "lucide-react"
import { useState } from "react"
import type { EpisodeInformationSide } from "@/client"
import { EpisodesService } from "@/client"
import { ReportEpisodeIssueDialog } from "@/components/ChannelCommon/ReportEpisodeIssueDialog"
import { ModalContent } from "@/components/Common/ModalContent"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogBody,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

interface EpisodeInformationDialogProps {
  episodeId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

type SideValue = React.ReactNode

function formatDate(value: string | null) {
  if (!value) return null
  return new Date(value).toLocaleString()
}

function formatDuration(value: number | null) {
  if (value == null) return null
  const minutes = Math.floor(value / 60)
  const seconds = value % 60
  return `${value}s (${minutes}m ${seconds}s)`
}

function ExternalAnchor({ href, label }: { href: string; label: string }) {
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

function sideRows(side: EpisodeInformationSide): Record<string, SideValue> {
  return {
    Name: side.name,
    "Episode number": side.episode_number,
    "Season number": side.season_number,
    "Season name": side.season_name,
    Show: side.show_name,
    Duration: formatDuration(side.duration),
    "Release date": formatDate(side.release_date),
    "Air date": formatDate(side.air_date),
    Description: side.description,
    Link: side.url ? <ExternalAnchor href={side.url} label={side.url} /> : null,
    Image: side.image_url ? (
      <ExternalAnchor href={side.image_url} label={side.image_url} />
    ) : null,
    Key: side.key,
  }
}

const ROW_LABELS = [
  "Name",
  "Episode number",
  "Season number",
  "Season name",
  "Show",
  "Duration",
  "Release date",
  "Air date",
  "Description",
  "Link",
  "Image",
  "Key",
]

export function EpisodeInformationDialog({
  episodeId,
  open,
  onOpenChange,
}: EpisodeInformationDialogProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["episode-information", episodeId],
    queryFn: () => EpisodesService.getEpisodeInformation({ episodeId }),
    enabled: open,
    staleTime: 5 * 60 * 1000,
  })
  const [reportIssue, setReportIssue] = useState(false)

  const sourceRows = data ? sideRows(data.source) : null
  const tmdbRows = data?.tmdb ? sideRows(data.tmdb) : null

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <ModalContent size="4xl">
          <DialogHeader>
            <DialogTitle>Episode Information</DialogTitle>
            <DialogDescription>
              What the source and TMDB each say about this episode. The episode
              is shown as TMDB has it wherever TMDB has anything to say.
            </DialogDescription>
          </DialogHeader>

          <DialogBody className="overflow-x-auto">
            {isLoading ? (
              <p className="text-sm text-muted-foreground">
                Loading episode information…
              </p>
            ) : error || !data || !sourceRows ? (
              <p className="text-sm text-muted-foreground">
                Couldn't load the episode information.
              </p>
            ) : (
              <>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[140px]">Field</TableHead>
                      <TableHead>{data.source.label}</TableHead>
                      <TableHead>
                        {data.tmdb ? data.tmdb.label : "TMDB (not linked)"}
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {ROW_LABELS.map((label) => (
                      <TableRow key={label}>
                        <TableCell className="font-medium align-top">
                          {label}
                        </TableCell>
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

                <dl className="mt-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
                  <dt className="text-muted-foreground">Episode identifier</dt>
                  <dd className="break-all">{data.episode_identifier}</dd>
                  <dt className="text-muted-foreground">Identifier locked</dt>
                  <dd>{data.episode_identifier_locked ? "Yes" : "No"}</dd>
                  <dt className="text-muted-foreground">Reported issue</dt>
                  <dd className="whitespace-pre-wrap">
                    {data.issue_report ?? "None"}
                  </dd>
                </dl>
              </>
            )}
          </DialogBody>

          <DialogFooter>
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Close
            </Button>
            <Button
              variant="outline"
              disabled={!data}
              onClick={() => setReportIssue(true)}
            >
              <Flag />
              {data?.issue_report ? "Edit Issue Report" : "Report Issue"}
            </Button>
          </DialogFooter>
        </ModalContent>
      </Dialog>

      {reportIssue && data && (
        <ReportEpisodeIssueDialog
          episodeId={episodeId}
          episodeName={data.source.name}
          currentReport={data.issue_report ?? null}
          open={reportIssue}
          onOpenChange={setReportIssue}
        />
      )}
    </>
  )
}
