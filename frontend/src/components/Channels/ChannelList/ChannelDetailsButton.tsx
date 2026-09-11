// TODO: Validate
import { Link } from "@tanstack/react-router"
import { Info, Maximize2, Minimize2 } from "lucide-react"
import { useState } from "react"
import { ChannelDescriptionMarkdown } from "@/components/Channels/ChannelDetail/ChannelDescription"
import { TitleCardsWithInformation } from "@/components/Channels/TitleCardsWithInformation"
import {
  useAllChannelTitles,
  useChannelTitleStats,
} from "@/components/Channels/useChannelTitles"
import { ModalContent } from "@/components/Common/ModalContent"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import {
  type TriggerVariant,
  VariantTrigger,
} from "@/components/Common/VariantTrigger"
import {
  Dialog,
  DialogBody,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"

interface ChannelDetailsButtonProps {
  channel: { id: string; name?: string | null; description?: string | null }
  variant?: TriggerVariant
  showLabel?: boolean
}

// TODO: Validate
export function ChannelDetailsButton({
  channel,
  variant = "icon",
  showLabel,
}: ChannelDetailsButtonProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [isFullScreen, setIsFullScreen] = useState(false)

  const { data, isLoading } = useAllChannelTitles(channel.id, {
    enabled: isOpen,
  })

  const tmdbTitles = data?.tmdb_titles ?? {}
  const groups = (data?.groups ?? [])
    .map((group) => ({
      ...group,
      titles: (group.titles ?? []).filter((title) =>
        title.tmdb_title_id
          ? !!tmdbTitles[title.tmdb_title_id]?.name
          : !!title.name,
      ),
    }))
    .filter((group) => group.titles.length > 0)

  const listedTmdbTitleIds = [
    ...new Set(
      groups.flatMap((group) =>
        group.titles.map((title) => title.tmdb_title_id ?? title.id),
      ),
    ),
  ]
  const { data: stats } = useChannelTitleStats(channel.id, listedTmdbTitleIds)

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        {variant === "icon" ? (
          <TooltipIconButton
            label="Details"
            icon={<Info className="size-4" />}
            showLabel={showLabel}
          />
        ) : (
          <VariantTrigger
            variant={variant}
            icon={Info}
            label="Details"
            iconTitle="Details"
          />
        )}
      </DialogTrigger>
      <ModalContent
        size={isFullScreen ? "full" : "6xl"}
        className={
          isFullScreen
            ? "max-h-none h-[calc(100dvh-2rem)] flex flex-col overflow-hidden"
            : "max-h-[85vh] flex flex-col overflow-hidden"
        }
      >
        <DialogHeader className="pl-8">
          <DialogTitle>{channel.name ?? "Channel"}</DialogTitle>
          <DialogDescription>
            The channel's description and every title it includes.
          </DialogDescription>
        </DialogHeader>
        <DialogBody
          className={
            isFullScreen ? "flex-1 max-h-none space-y-4 py-2" : "space-y-4 py-2"
          }
        >
          {channel.description && (
            <ChannelDescriptionMarkdown description={channel.description} />
          )}

          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading titles...</p>
          ) : groups.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No titles in this channel yet.
            </p>
          ) : (
            groups.map((group) => (
              <div key={group.channel_id} className="space-y-1">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  <Link
                    to="/channels/$channelId"
                    params={{ channelId: group.channel_id }}
                    className="hover:text-foreground hover:underline"
                  >
                    {group.channel_name || "Unnamed Channel"}
                  </Link>
                </h3>
                <TitleCardsWithInformation
                  channelId={group.channel_id}
                  titles={group.titles}
                  sources={data?.sources ?? {}}
                  tmdbTitles={data?.tmdb_titles ?? {}}
                  tmdbSources={data?.tmdb_sources ?? {}}
                  stats={stats ?? {}}
                />
              </div>
            ))
          )}
        </DialogBody>

        <TooltipIconButton
          label={isFullScreen ? "Shrink to a window" : "Fill the screen"}
          icon={isFullScreen ? <Minimize2 /> : <Maximize2 />}
          size="icon-sm"
          className="absolute left-4 top-4 z-10"
          onClick={() => setIsFullScreen(!isFullScreen)}
        />
      </ModalContent>
    </Dialog>
  )
}
