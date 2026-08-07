// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import type { ShowInformationSide } from "@/client"
import { ShowsService } from "@/client"
import {
  ExternalAnchor,
  type InformationRows,
  InformationTable,
} from "@/components/ChannelCommon/InformationTable"
import { IssueReportsSection } from "@/components/ChannelCommon/IssueReportsSection"
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

interface ShowInformationDialogProps {
  showId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

function sideRows(side: ShowInformationSide): InformationRows {
  return {
    Name: side.name,
    "Media type": side.media_type,
    Description: side.description,
    Link: side.url ? <ExternalAnchor href={side.url} label={side.url} /> : null,
    Image: side.image_url ? (
      <ExternalAnchor href={side.image_url} label={side.image_url} />
    ) : null,
    Key: side.key,
  }
}

const ROW_LABELS = ["Name", "Media type", "Description", "Link", "Image", "Key"]

export function ShowInformationDialog({
  showId,
  open,
  onOpenChange,
}: ShowInformationDialogProps) {
  const queryKey = ["show-information", showId]
  const { data, isLoading, error } = useQuery({
    queryKey,
    queryFn: () => ShowsService.getShowInformation({ showId }),
    enabled: open,
    staleTime: 5 * 60 * 1000,
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <ModalContent size="4xl">
        <DialogHeader>
          <DialogTitle>Show Information</DialogTitle>
          <DialogDescription>
            What the source and TMDB each say about this title. The title is
            shown as TMDB has it wherever TMDB has anything to say.
          </DialogDescription>
        </DialogHeader>

        <DialogBody className="overflow-x-auto">
          {isLoading ? (
            <p className="text-sm text-muted-foreground">
              Loading show information…
            </p>
          ) : error || !data ? (
            <p className="text-sm text-muted-foreground">
              Couldn't load the show information.
            </p>
          ) : (
            <>
              <InformationTable
                sourceLabel={data.source.label}
                tmdbLabel={data.tmdb ? data.tmdb.label : "TMDB (not linked)"}
                rowLabels={ROW_LABELS}
                sourceRows={sideRows(data.source)}
                tmdbRows={data.tmdb ? sideRows(data.tmdb) : null}
              />

              <dl className="mt-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
                <dt className="text-muted-foreground">Show identifier</dt>
                <dd className="break-all">{data.show_identifier}</dd>
                <dt className="text-muted-foreground">Identifier locked</dt>
                <dd>{data.show_identifier_locked ? "Yes" : "No"}</dd>
              </dl>

              <IssueReportsSection
                target="show"
                mediaId={showId}
                reports={data.issue_reports}
                informationQueryKey={queryKey}
              />
            </>
          )}
        </DialogBody>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </ModalContent>
    </Dialog>
  )
}
