// TODO: Validate
import { useMutation, useQueries, useQueryClient } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { Pencil, Trash2, X } from "lucide-react"
import { useState } from "react"

import { type ChannelQueueAdminOutput, ChannelsService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
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
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { EditChannelQueueDialog } from "./EditChannelQueueDialog"

const ownerScopes = [undefined, "official", "others"] as const

export function ChannelQueuesAdminTable() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const results = useQueries({
    queries: ownerScopes.map((owner) => ({
      queryFn: () =>
        ChannelsService.getAllChannelQueues(owner ? { owner } : {}),
      queryKey: ["admin-channel-queues", owner ?? "mine"],
      refetchOnWindowFocus: false,
    })),
  })
  const isPlaceholderData = results.some((result) => result.isFetching)
  const entries = results.every((result) => result.data)
    ? results.flatMap((result) => result.data ?? [])
    : undefined

  // When set, the table only shows queue entries owned by this user. Set by
  // clicking a username in the table.
  const [filterUserId, setFilterUserId] = useState<string | null>(null)
  const [editingEntry, setEditingEntry] =
    useState<ChannelQueueAdminOutput | null>(null)
  const [deletingEntry, setDeletingEntry] =
    useState<ChannelQueueAdminOutput | null>(null)

  const deleteMutation = useMutation({
    mutationFn: (queueId: string) =>
      ChannelsService.adminDeleteChannelQueue({ queueId }),
    onSuccess: () => {
      showSuccessToast("Queue entry removed successfully")
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () =>
      queryClient.invalidateQueries({ queryKey: ["admin-channel-queues"] }),
  })

  if (!entries) {
    return (
      <div>
        <PageHeader title="All Channel Queues" />
        <p className="px-[4%] text-sm text-muted-foreground">Loading…</p>
      </div>
    )
  }

  const filterUsername =
    filterUserId != null
      ? entries.find((entry) => entry.user_id === filterUserId)?.username
      : null
  const visibleEntries =
    filterUserId == null
      ? entries
      : entries.filter((entry) => entry.user_id === filterUserId)

  return (
    <div
      className={
        isPlaceholderData
          ? "opacity-60 transition-opacity duration-200"
          : undefined
      }
    >
      <PageHeader title="All Channel Queues">
        {filterUserId != null && (
          <Button variant="outline" onClick={() => setFilterUserId(null)}>
            <X />
            {filterUsername
              ? `Showing ${filterUsername}'s queues`
              : "Clear filter"}
          </Button>
        )}
      </PageHeader>

      <div className="px-[4%]">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Channel #</TableHead>
              <TableHead>Channel</TableHead>
              <TableHead>Owner</TableHead>
              <TableHead>URL</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Note</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {visibleEntries.map((entry) => (
              <TableRow key={entry.id}>
                <TableCell className="tabular-nums text-muted-foreground">
                  {entry.channel_number ?? "—"}
                </TableCell>
                <TableCell className="font-medium">
                  <Link
                    to="/channels/$channelId"
                    params={{ channelId: entry.channel_id }}
                    className="hover:underline"
                  >
                    {entry.channel_name ?? "Channel"}
                  </Link>
                </TableCell>
                <TableCell>
                  <button
                    type="button"
                    className="text-primary hover:underline"
                    onClick={() => setFilterUserId(entry.user_id)}
                  >
                    {entry.username ?? "Anonymous"}
                  </button>
                </TableCell>
                <TableCell className="max-w-xs truncate">
                  <a
                    href={entry.url}
                    target="_blank"
                    rel="noreferrer"
                    className="hover:underline"
                    title={entry.url}
                  >
                    {entry.url}
                  </a>
                </TableCell>
                <TableCell>{entry.status}</TableCell>
                <TableCell className="max-w-xs truncate text-muted-foreground">
                  {entry.note ?? "—"}
                </TableCell>
                <TableCell>
                  <div className="flex justify-end gap-2">
                    <Button
                      variant="outline"
                      size="icon-sm"
                      onClick={() => setEditingEntry(entry)}
                    >
                      <Pencil />
                    </Button>
                    <Button
                      variant="outline"
                      size="icon-sm"
                      className="text-destructive hover:text-destructive"
                      onClick={() => setDeletingEntry(entry)}
                    >
                      <Trash2 />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {editingEntry && (
        <EditChannelQueueDialog
          queueEntry={editingEntry}
          open={editingEntry != null}
          onOpenChange={(open) => {
            if (!open) setEditingEntry(null)
          }}
        />
      )}

      {deletingEntry && (
        <ConfirmDialog
          open={deletingEntry != null}
          onOpenChange={(open) => {
            if (!open) setDeletingEntry(null)
          }}
          title="Delete Queue Entry"
          description={`Remove "${deletingEntry.url}" from the import queue? This cannot be undone.`}
          confirmLabel="Delete"
          onConfirm={() => deleteMutation.mutate(deletingEntry.id)}
        />
      )}
    </div>
  )
}
