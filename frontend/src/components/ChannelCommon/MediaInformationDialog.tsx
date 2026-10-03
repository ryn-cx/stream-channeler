// TODO: Validate
import { useEpisodeInformation } from "@/components/ChannelCommon/EpisodeInformationHero"
import { SeasonInformationPanel } from "@/components/ChannelCommon/SeasonInformationDialog"
import { TitleInformationPanel } from "@/components/ChannelCommon/TitleInformationDialog"
import { ModalContent } from "@/components/Common/ModalContent"
import { EpisodeInformationContent } from "@/components/Episodes/Edit"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogBody,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import useAuth from "@/hooks/useAuth"
import { useEpisode } from "@/hooks/useEntities"
import {
  type MediaTarget,
  useCloseMedia,
  useMediaInformationState,
} from "@/hooks/useOpenMedia"

type EpisodeTarget = Extract<MediaTarget, { kind: "episode" }>

// TODO: Validate
function EpisodeHeading({ episodeId }: { episodeId: string }) {
  const { data } = useEpisodeInformation(episodeId, true)
  const side = data?.source
  const heading = [
    side?.label,
    side?.title.name,
    side?.season.name ??
      (side?.season.season_number != null
        ? `Season ${side.season.season_number}`
        : null),
    "Episode Information",
  ]
    .filter(Boolean)
    .join(" - ")
  return <DialogTitle>{heading}</DialogTitle>
}

// TODO: Validate
function EpisodeBody({ episode }: { episode: EpisodeTarget["episode"] }) {
  const { user } = useAuth()
  const isAdmin = Boolean(user?.is_superuser)
  const hasFields = episode.tmdb_episode_ids !== undefined
  const { data: fields } = useEpisode(
    isAdmin && !hasFields ? episode.id : undefined,
  )
  const resolved = hasFields || !isAdmin ? episode : fields

  if (!resolved) {
    return (
      <p className="text-sm text-muted-foreground">
        Loading episode information…
      </p>
    )
  }
  return (
    <div className="py-4">
      <EpisodeInformationContent episode={resolved} enabled />
    </div>
  )
}

// TODO: Validate
function MediaContent({ target }: { target: MediaTarget }) {
  if (target.kind === "title") {
    return (
      <>
        <DialogHeader>
          <DialogTitle>Title Information</DialogTitle>
        </DialogHeader>
        <DialogBody className="overflow-x-auto">
          <TitleInformationPanel
            titleId={target.titleId}
            extraLinks={target.extraLinks}
          />
        </DialogBody>
      </>
    )
  }
  if (target.kind === "season") {
    return (
      <>
        <DialogHeader>
          <DialogTitle>Season Information</DialogTitle>
          <DialogDescription>
            What the source and TMDB each say about this season. The season is
            shown as TMDB has it wherever TMDB has anything to say.
          </DialogDescription>
        </DialogHeader>
        <DialogBody className="overflow-x-auto">
          <SeasonInformationPanel seasonIds={target.seasonIds} />
        </DialogBody>
      </>
    )
  }
  return (
    <>
      <DialogHeader>
        <EpisodeHeading episodeId={target.episode.id} />
      </DialogHeader>
      <DialogBody>
        <EpisodeBody episode={target.episode} />
      </DialogBody>
    </>
  )
}

// TODO: Validate
export function MediaInformationDialog() {
  const state = useMediaInformationState()
  const closeMedia = useCloseMedia()

  return (
    <Dialog
      open={state !== undefined}
      onOpenChange={(open) => {
        if (!open) closeMedia()
      }}
    >
      {state ? (
        <ModalContent
          size={state.target.kind === "episode" ? "3xl" : "full"}
          aria-describedby={undefined}
        >
          <MediaContent
            key={`${state.depth}:${JSON.stringify(state.target)}`}
            target={state.target}
          />
          <DialogFooter>
            <Button variant="outline" onClick={closeMedia}>
              Close
            </Button>
          </DialogFooter>
        </ModalContent>
      ) : null}
    </Dialog>
  )
}
