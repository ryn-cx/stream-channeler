// TODO: Validate
import { Link } from "@tanstack/react-router"
import { Info } from "lucide-react"
import { useState } from "react"
import { ChannelDescriptionMarkdown } from "@/components/Channels/ChannelDetail/ChannelDescription"
import { TitleCardsWithInformation } from "@/components/Channels/TitleCardsWithInformation"
import { useAllChannelTitles } from "@/components/Channels/useChannelTitles"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import {
  type TriggerVariant,
  VariantTrigger,
} from "@/components/Common/VariantTrigger"
import { WinBoxModal } from "@/components/Common/WinBoxModal"

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

  const stats = data?.stats ?? {}

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

      <WinBoxModal
        open={isOpen}
        title={channel.name ?? "Channel"}
        onClose={() => setIsOpen(false)}
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
                />
              </div>
            ))
          )}
        </div>
      </WinBoxModal>
    </>
  )
}
