// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { Pencil, X } from "lucide-react"
import { useState } from "react"

import { type ChannelAdminOutput, ChannelsService } from "@/client"
import { EditChannelDialog } from "@/components/Channels/EditChannelDialog"
import { PageHeader } from "@/components/Common/PageHeader"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { cn } from "@/lib/utils"
import { visibilityDotClass, visibilityLabel } from "@/lib/visibility"

function getAdminChannelsQueryOptions() {
  return {
    queryFn: () => ChannelsService.adminListChannels(),
    queryKey: ["admin-channels"],
    refetchOnWindowFocus: false,
    placeholderData: (previousData: any) => previousData,
  }
}

export function ChannelsAdminTable() {
  const { data: channels, isPlaceholderData } = useQuery(
    getAdminChannelsQueryOptions(),
  )
  // When set, the table only shows channels owned by this user. Set by clicking
  // a username in the table.
  const [filterUserId, setFilterUserId] = useState<string | null>(null)
  const [editingChannel, setEditingChannel] =
    useState<ChannelAdminOutput | null>(null)

  if (!channels) {
    return (
      <div>
        <PageHeader title="All Channels" />
        <p className="px-[4%] text-sm text-muted-foreground">Loading…</p>
      </div>
    )
  }

  const filterUsername =
    filterUserId != null
      ? channels.find((channel) => channel.user_id === filterUserId)?.username
      : null
  const visibleChannels =
    filterUserId == null
      ? channels
      : channels.filter((channel) => channel.user_id === filterUserId)

  return (
    <div
      className={
        isPlaceholderData
          ? "opacity-60 transition-opacity duration-200"
          : undefined
      }
    >
      <PageHeader title="All Channels">
        {filterUserId != null && (
          <Button variant="outline" onClick={() => setFilterUserId(null)}>
            <X />
            {filterUsername
              ? `Showing ${filterUsername}'s channels`
              : "Clear filter"}
          </Button>
        )}
      </PageHeader>

      <div className="px-[4%]">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Channel #</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Owner</TableHead>
              <TableHead>Visibility</TableHead>
              <TableHead>Score</TableHead>
              <TableHead>Anonymous</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {visibleChannels.map((channel) => (
              <TableRow key={channel.id}>
                <TableCell className="tabular-nums text-muted-foreground">
                  {channel.channel_number ?? "—"}
                </TableCell>
                <TableCell className="font-medium">
                  <Link
                    to="/channels/$channelId"
                    params={{ channelId: channel.id }}
                    className="hover:underline"
                  >
                    {channel.name ?? "Channel"}
                  </Link>
                </TableCell>
                <TableCell>
                  <button
                    type="button"
                    className="text-primary hover:underline"
                    onClick={() => setFilterUserId(channel.user_id)}
                  >
                    {channel.username ?? "Anonymous"}
                  </button>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        "size-2 rounded-full",
                        visibilityDotClass(channel.visibility),
                      )}
                    />
                    {visibilityLabel(channel.visibility)}
                  </div>
                </TableCell>
                <TableCell className="tabular-nums">{channel.score}</TableCell>
                <TableCell className="text-muted-foreground">
                  {channel.anonymous ? "Yes" : "No"}
                </TableCell>
                <TableCell>
                  <div className="flex justify-end gap-2">
                    <Button
                      variant="outline"
                      size="icon-sm"
                      onClick={() => setEditingChannel(channel)}
                    >
                      <Pencil />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {editingChannel && (
        <EditChannelDialog
          channel={editingChannel}
          open={editingChannel != null}
          onOpenChange={(open) => {
            if (!open) setEditingChannel(null)
          }}
        />
      )}
    </div>
  )
}
