// TODO: Validate
import { useMutation, useQuery } from "@tanstack/react-query"
import { Bot, Eraser, Plus, Trash2 } from "lucide-react"
import { useState } from "react"
import type { AutomaticChannelUserOutput } from "@/client"
import { ChannelsService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { EmptyState } from "@/components/Common/EmptyState"
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

// TODO: Validate
export function AutomaticChannelUsersTable() {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [pendingClearUser, setPendingClearUser] =
    useState<AutomaticChannelUserOutput | null>(null)
  const [pendingDeleteUser, setPendingDeleteUser] =
    useState<AutomaticChannelUserOutput | null>(null)
  const [isClearAllPending, setIsClearAllPending] = useState(false)
  const [isDeleteAllPending, setIsDeleteAllPending] = useState(false)

  const { data: users, isPending } = useQuery({
    queryKey: ["automatic-channel-users"],
    queryFn: () => ChannelsService.getAutomaticChannelUsers(),
  })

  const createChannels = useMutation({
    mutationFn: (userId: string) =>
      ChannelsService.createAutomaticChannels({ userId }),
    onSuccess: (message, _userId, _onMutateResult, context) => {
      showSuccessToast(message.message)
      context.client.invalidateQueries({
        queryKey: ["automatic-channel-users"],
      })
      context.client.invalidateQueries({ queryKey: ["channels"] })
    },
    onError: handleError.bind(showErrorToast),
  })

  const clearChannels = useMutation({
    mutationFn: (userId: string) =>
      ChannelsService.clearAutomaticChannels({ userId }),
    onSuccess: (message, _userId, _onMutateResult, context) => {
      showSuccessToast(message.message)
      context.client.invalidateQueries({
        queryKey: ["automatic-channel-users"],
      })
      context.client.invalidateQueries({ queryKey: ["channels"] })
    },
    onError: handleError.bind(showErrorToast),
  })

  const deleteChannels = useMutation({
    mutationFn: (userId: string) =>
      ChannelsService.deleteAutomaticChannels({ userId }),
    onSuccess: (message, _userId, _onMutateResult, context) => {
      showSuccessToast(message.message)
      context.client.invalidateQueries({
        queryKey: ["automatic-channel-users"],
      })
      context.client.invalidateQueries({ queryKey: ["channels"] })
    },
    onError: handleError.bind(showErrorToast),
  })

  const createAllChannels = useMutation({
    mutationFn: () => ChannelsService.createAllAutomaticChannels(),
    onSuccess: (message, _variables, _onMutateResult, context) => {
      showSuccessToast(message.message)
      context.client.invalidateQueries({
        queryKey: ["automatic-channel-users"],
      })
      context.client.invalidateQueries({ queryKey: ["channels"] })
    },
    onError: handleError.bind(showErrorToast),
  })

  const clearAllChannels = useMutation({
    mutationFn: () => ChannelsService.clearAllAutomaticChannels(),
    onSuccess: (message, _variables, _onMutateResult, context) => {
      showSuccessToast(message.message)
      context.client.invalidateQueries({
        queryKey: ["automatic-channel-users"],
      })
      context.client.invalidateQueries({ queryKey: ["channels"] })
    },
    onError: handleError.bind(showErrorToast),
  })

  const deleteAllChannels = useMutation({
    mutationFn: () => ChannelsService.deleteAllAutomaticChannels(),
    onSuccess: (message, _variables, _onMutateResult, context) => {
      showSuccessToast(message.message)
      context.client.invalidateQueries({
        queryKey: ["automatic-channel-users"],
      })
      context.client.invalidateQueries({ queryKey: ["channels"] })
    },
    onError: handleError.bind(showErrorToast),
  })

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Manage Automatic Channels"
        description="The users a source writes channels as, and the channels each of them owns."
      >
        <Button
          size="sm"
          onClick={() => createAllChannels.mutate()}
          disabled={createAllChannels.isPending}
        >
          <Plus />
          Create all channels
        </Button>
        <Button
          variant="destructive"
          size="sm"
          onClick={() => setIsClearAllPending(true)}
          disabled={clearAllChannels.isPending}
        >
          <Eraser />
          Clear all channels
        </Button>
        <Button
          variant="destructive"
          size="sm"
          onClick={() => setIsDeleteAllPending(true)}
          disabled={deleteAllChannels.isPending}
        >
          <Trash2 />
          Delete all channels
        </Button>
      </PageHeader>

      {isPending ? null : users?.length ? (
        <div className="px-[4%]">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>User</TableHead>
                <TableHead>Key</TableHead>
                <TableHead className="text-right">Channels</TableHead>
                <TableHead className="w-0" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map((user) => (
                <TableRow key={user.id}>
                  <TableCell>{user.username ?? user.email}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {user.email}
                  </TableCell>
                  <TableCell className="text-right">
                    {user.channel_count}
                  </TableCell>
                  <TableCell>
                    <div className="flex justify-end gap-2">
                      {user.can_create_channels && (
                        <Button
                          size="sm"
                          onClick={() => createChannels.mutate(user.id)}
                          disabled={createChannels.isPending}
                        >
                          <Plus />
                          Create channels
                        </Button>
                      )}
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => setPendingClearUser(user)}
                        disabled={clearChannels.isPending}
                      >
                        <Eraser />
                        Clear channels
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => setPendingDeleteUser(user)}
                        disabled={deleteChannels.isPending}
                      >
                        <Trash2 />
                        Delete channels
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : (
        <EmptyState
          icon={Bot}
          title="No automatic channels"
          description="No source has written any channels yet."
        />
      )}

      <ConfirmDialog
        open={pendingClearUser !== null}
        onOpenChange={(open) => {
          if (!open) setPendingClearUser(null)
        }}
        title="Clear every channel this user owns?"
        description={
          pendingClearUser
            ? `The titles and queued URLs in ${pendingClearUser.channel_count} channel${pendingClearUser.channel_count === 1 ? "" : "s"} owned by ${pendingClearUser.email} will be removed. The channels themselves are kept, and a source fills them in again the next time it runs.`
            : ""
        }
        confirmLabel="Clear channels"
        onConfirm={() => {
          if (pendingClearUser) clearChannels.mutate(pendingClearUser.id)
        }}
      />

      <ConfirmDialog
        open={pendingDeleteUser !== null}
        onOpenChange={(open) => {
          if (!open) setPendingDeleteUser(null)
        }}
        title="Delete every channel this user owns?"
        description={
          pendingDeleteUser
            ? `${pendingDeleteUser.channel_count} channel${pendingDeleteUser.channel_count === 1 ? "" : "s"} owned by ${pendingDeleteUser.email} will be deleted along with their titles, queued URLs, favorites, comments and any place they are combined into another channel.`
            : ""
        }
        confirmLabel="Delete channels"
        onConfirm={() => {
          if (pendingDeleteUser) deleteChannels.mutate(pendingDeleteUser.id)
        }}
      />

      <ConfirmDialog
        open={isClearAllPending}
        onOpenChange={setIsClearAllPending}
        title="Clear every automatic channel?"
        description="The titles and queued URLs in every channel owned by an automatic channel user are removed. The channels themselves are kept, and each source fills them in again the next time it runs."
        confirmLabel="Clear all channels"
        onConfirm={() => clearAllChannels.mutate()}
      />

      <ConfirmDialog
        open={isDeleteAllPending}
        onOpenChange={setIsDeleteAllPending}
        title="Delete every automatic channel?"
        description="Every channel owned by an automatic channel user is deleted along with its titles, queued URLs, favorites, comments and any place it is combined into another channel. Create all channels or a reimport makes them again."
        confirmLabel="Delete all channels"
        onConfirm={() => deleteAllChannels.mutate()}
      />
    </div>
  )
}
