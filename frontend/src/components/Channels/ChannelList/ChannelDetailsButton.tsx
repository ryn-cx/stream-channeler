// TODO: Validate
import { Link } from "@tanstack/react-router"
import { Info } from "lucide-react"
import { useEffect, useState } from "react"
import { ChannelDescriptionMarkdown } from "@/components/Channels/ChannelDetail/ChannelDescription"
import { TitleCardsWithInformation } from "@/components/Channels/TitleCardsWithInformation"
import {
  CHANNEL_TITLE_PAGE,
  useChannelTitlesPage,
} from "@/components/Channels/useChannelTitles"
import { PageControls } from "@/components/Common/PageControls"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import {
  type TriggerVariant,
  VariantTrigger,
} from "@/components/Common/VariantTrigger"
import { WinBoxModal } from "@/components/Common/WinBoxModal"

interface ChannelDetailsChannel {
  id: string
  name?: string | null
  description?: string | null
}

interface ChannelDetailsWinBoxProps {
  channel: ChannelDetailsChannel
  open: boolean
  onClose: () => void
}

// TODO: Validate
export function ChannelDetailsWinBox({
  channel,
  open,
  onClose,
}: ChannelDetailsWinBoxProps) {
  const [pageIndex, setPageIndex] = useState(0)
  const { data, isLoading } = useChannelTitlesPage(channel.id, pageIndex, "", {
    enabled: open,
  })

  const titleCount = data?.total ?? 0
  const pageCount = Math.max(1, Math.ceil(titleCount / CHANNEL_TITLE_PAGE))

  useEffect(() => {
    if (!open) setPageIndex(0)
  }, [open])

  useEffect(() => {
    if (data && pageIndex >= pageCount) setPageIndex(pageCount - 1)
  }, [data, pageIndex, pageCount])

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

  const stats = data?.stats ?? {}

  return (
    <WinBoxModal
      open={open}
      title={channel.name ?? "Channel"}
      onClose={onClose}
    >
      <div className="space-y-4">
        <p className="text-sm text-muted-foreground">
          The channel's description and every title it includes.
        </p>
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
                details={data?.details ?? {}}
              />
            </div>
          ))
        )}

        <PageControls
          pageIndex={pageIndex}
          pageCount={pageCount}
          onPageChange={setPageIndex}
        />
      </div>
    </WinBoxModal>
  )
}

interface ChannelDetailsButtonProps {
  channel: ChannelDetailsChannel
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

  return (
    <>
      {variant === "icon" ? (
        <TooltipIconButton
          label="Details"
          icon={<Info className="size-4" />}
          showLabel={showLabel}
          onClick={() => setIsOpen(true)}
        />
      ) : (
        <VariantTrigger
          variant={variant}
          icon={Info}
          label="Details"
          iconTitle="Details"
          onClick={() => setIsOpen(true)}
        />
      )}

      <ChannelDetailsWinBox
        channel={channel}
        open={isOpen}
        onClose={() => setIsOpen(false)}
      />
    </>
  )
}
