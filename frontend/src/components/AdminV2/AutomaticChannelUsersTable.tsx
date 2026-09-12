// TODO: Validate
import { useMutation, useQuery } from "@tanstack/react-query"
import { Bot, Trash2 } from "lucide-react"
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
  const [pendingUser, setPendingUser] =
    useState<AutomaticChannelUserOutput | null>(null)

  const { data: users, isPending } = useQuery({
    queryKey: ["automatic-channel-users"],
    queryFn: () => ChannelsService.getAutomaticChannelUsers(),
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

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Manage Automatic Channels"
        description="The users a source writes channels as, and the channels each of them owns."
      />

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
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => setPendingUser(user)}
                      disabled={deleteChannels.isPending}
                    >
                      <Trash2 />
                      Delete channels
                    </Button>
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
        open={pendingUser !== null}
        onOpenChange={(open) => {
          if (!open) setPendingUser(null)
        }}
        title="Delete every channel this user owns?"
        description={
          pendingUser
            ? `${pendingUser.channel_count} channel${pendingUser.channel_count === 1 ? "" : "s"} owned by ${pendingUser.email} will be deleted, along with the titles and queued URLs they hold. A source writes its channels again the next time it runs.`
            : ""
        }
        confirmLabel="Delete channels"
        onConfirm={() => {
          if (pendingUser) deleteChannels.mutate(pendingUser.id)
        }}
      />
    </div>
  )
}
