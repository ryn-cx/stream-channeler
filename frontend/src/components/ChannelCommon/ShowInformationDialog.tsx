// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import type { ShowInformationOutput, ShowInformationSide } from "@/client"
import { ShowsService } from "@/client"
import { CollapsibleSection } from "@/components/ChannelCommon/CollapsibleSection"
import { InformationHero } from "@/components/ChannelCommon/InformationHero"
import {
  ExternalAnchor,
  type InformationRows,
  InformationTable,
} from "@/components/ChannelCommon/InformationTable"
import { IssueReportsSection } from "@/components/ChannelCommon/IssueReportsSection"
import { ModalContent } from "@/components/Common/ModalContent"
import { TmdbIdentifierField } from "@/components/Common/TmdbIdentifierField"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogBody,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface ShowInformationDialogProps {
  showId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

// TODO: Validate
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

// TODO: Validate
function heroFacts(data: ShowInformationOutput) {
  const facts = [data.tmdb?.media_type ?? data.source.media_type]
  facts.push(data.tmdb ? "Linked to TMDB" : "Not linked to TMDB")
  facts.push(data.source.label)
  return facts.filter((fact): fact is string => !!fact)
}

// TODO: Validate
function heroLinks(data: ShowInformationOutput) {
  const links = []
  if (data.source.url) {
    links.push({ label: data.source.label, href: data.source.url })
  }
  if (data.tmdb?.url) {
    links.push({ label: data.tmdb.label, href: data.tmdb.url })
  }
  return links
}

interface ShowIdentifierEditorProps {
  showId: string
  showIdentifier: string
  showIdentifierLocked: boolean
  informationQueryKey: string[]
}

// TODO: Validate
function ShowIdentifierEditor({
  showId,
  showIdentifier,
  showIdentifierLocked,
  informationQueryKey,
}: ShowIdentifierEditorProps) {
  const [identifier, setIdentifier] = useState(showIdentifier)
  const [locked, setLocked] = useState(showIdentifierLocked)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: () =>
      ShowsService.updateShow({
        showId,
        requestBody: {
          show_identifier: identifier,
          show_identifier_locked: locked,
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: informationQueryKey })
      queryClient.invalidateQueries({ queryKey: ["shows"] })
      showSuccessToast("Show identifier updated successfully")
    },
    onError: handleError.bind(showErrorToast),
  })

  return (
    <div className="mt-4 grid gap-3 rounded-lg border p-4">
      <TmdbIdentifierField
        identifier={identifier}
        onChange={(nextIdentifier) => {
          setIdentifier(nextIdentifier)
          setLocked(true)
        }}
      />
      <div className="grid gap-2">
        <Label htmlFor="show-identifier">Show identifier</Label>
        <Input
          id="show-identifier"
          value={identifier}
          onChange={(event) => {
            setIdentifier(event.target.value)
            setLocked(true)
          }}
        />
      </div>
      <div className="flex items-center gap-3">
        <Checkbox
          id="show-identifier-locked"
          checked={locked}
          onCheckedChange={(checked) => setLocked(checked === true)}
        />
        <Label htmlFor="show-identifier-locked" className="font-normal">
          Lock show identifier?
        </Label>
      </div>
      <div className="flex justify-end">
        <LoadingButton
          onClick={() => mutation.mutate()}
          loading={mutation.isPending}
          disabled={!identifier}
        >
          Save Identifier
        </LoadingButton>
      </div>
    </div>
  )
}

interface ShowInformationPanelProps {
  showId: string
  /** Whether the information is wanted yet, so a collapsed panel fetches nothing. */
  enabled?: boolean
}

// TODO: Validate
/**
 * The title's own account of itself beside TMDB's, without a dialog around it,
 * so it can be read inside whatever is already open.
 */
export function ShowInformationPanel({
  showId,
  enabled = true,
}: ShowInformationPanelProps) {
  const queryKey = ["show-information", showId]
  const { data, isLoading, error } = useQuery({
    queryKey,
    queryFn: () => ShowsService.getShowInformation({ showId }),
    enabled,
    staleTime: 5 * 60 * 1000,
  })

  if (isLoading) {
    return (
      <p className="text-sm text-muted-foreground">Loading show information…</p>
    )
  }
  if (error || !data) {
    return (
      <p className="text-sm text-muted-foreground">
        Couldn't load the show information.
      </p>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <InformationHero
        title={data.tmdb?.name ?? data.source.name ?? "Unnamed show"}
        subtitle={
          data.tmdb && data.source.name !== data.tmdb.name
            ? data.source.name
            : null
        }
        description={data.tmdb?.description ?? data.source.description}
        imageUrl={data.tmdb?.image_url ?? data.source.image_url}
        facts={heroFacts(data)}
        links={heroLinks(data)}
      />

      <CollapsibleSection title="Field comparison">
        <div className="overflow-x-auto">
          <InformationTable
            sourceLabel={data.source.label}
            tmdbLabel={data.tmdb ? data.tmdb.label : "TMDB (not linked)"}
            rowLabels={ROW_LABELS}
            sourceRows={sideRows(data.source)}
            tmdbRows={data.tmdb ? sideRows(data.tmdb) : null}
          />
        </div>
      </CollapsibleSection>

      <div className="grid items-start gap-4 sm:grid-cols-2">
        {data.editable ? (
          <ShowIdentifierEditor
            showId={showId}
            showIdentifier={data.show_identifier}
            showIdentifierLocked={data.show_identifier_locked}
            informationQueryKey={queryKey}
          />
        ) : (
          <dl className="mt-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
            <dt className="text-muted-foreground">Show identifier</dt>
            <dd className="break-all">{data.show_identifier}</dd>
            <dt className="text-muted-foreground">Identifier locked</dt>
            <dd>{data.show_identifier_locked ? "Yes" : "No"}</dd>
          </dl>
        )}

        <IssueReportsSection
          target="show"
          mediaId={showId}
          reports={data.issue_reports}
          informationQueryKey={queryKey}
        />
      </div>
    </div>
  )
}

// TODO: Validate
export function ShowInformationDialog({
  showId,
  open,
  onOpenChange,
}: ShowInformationDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <ModalContent size="full">
        <DialogHeader>
          <DialogTitle>Show Information</DialogTitle>
          <DialogDescription>
            What the source and TMDB each say about this title. The title is
            shown as TMDB has it wherever TMDB has anything to say.
          </DialogDescription>
        </DialogHeader>

        <DialogBody className="overflow-x-auto">
          <ShowInformationPanel showId={showId} enabled={open} />
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
