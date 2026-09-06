// TODO: Validate
import { Link } from "@tanstack/react-router"
import { Info } from "lucide-react"
import { useState } from "react"
import { ChannelDescriptionMarkdown } from "@/components/Channels/ChannelDetail/ChannelDescription"
import { TitleCardsWithInformation } from "@/components/Channels/TitleCardsWithInformation"
import {
  useAllChannelTitles,
  useChannelTitleStats,
} from "@/components/Channels/useChannelTitles"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import {
  type TriggerVariant,
  VariantTrigger,
} from "@/components/Common/VariantTrigger"
import {
  Dialog,
  DialogBody,
  DialogContent,
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

  const { data, isLoading } = useAllChannelTitles(channel.id, {
    enabled: isOpen,
  })

  const canonicalTitles = data?.canonical_titles ?? {}
  const groups = (data?.groups ?? [])
    .map((group) => ({
      ...group,
      titles: (group.titles ?? []).filter((title) =>
        title.canonical_title_id
          ? !!canonicalTitles[title.canonical_title_id]?.name
          : !!title.name,
      ),
    }))
    .filter((group) => group.titles.length > 0)

  const listedCanonicalTitleIds = [
    ...new Set(
      groups.flatMap((group) =>
        group.titles.map((title) => title.canonical_title_id ?? title.id),
      ),
    ),
  ]
  const { data: stats } = useChannelTitleStats(
    channel.id,
    listedCanonicalTitleIds,
  )

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
      <DialogContent className="sm:max-w-[calc(100%-2rem)] max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>{channel.name ?? "Channel"}</DialogTitle>
          <DialogDescription>
            The channel's description and every title it includes.
          </DialogDescription>
        </DialogHeader>
        <DialogBody className="space-y-4 py-2">
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
                  canonicalTitles={data?.canonical_titles ?? {}}
                  canonicalSources={data?.canonical_sources ?? {}}
                  stats={stats ?? {}}
                />
              </div>
            ))
          )}
        </DialogBody>
      </DialogContent>
    </Dialog>
  )
}
