// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"
import { useState } from "react"

import {
  type ChannelCommentOutput,
  type CommentScope,
  CommentsService,
} from "@/client"
import { DataTable } from "@/components/Common/DataTable"
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

const PAGE_SIZE = 20

export const Route = createFileRoute("/_layout/channel-comments")({
  component: ChannelComments,
  head: () => ({
    meta: [
      {
        title: "Comments - Stream Channeler",
      },
    ],
  }),
})

function ChannelComments() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(0)
  const [scope, setScope] = useState<CommentScope>("owned")
  const { user: currentUser } = useAuth()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const { data, isLoading } = useQuery({
    queryKey: ["myChannelComments", scope, page],
    queryFn: () =>
      CommentsService.readMyChannelComments({
        scope,
        offset: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      }),
  })

  const readMutation = useMutation({
    mutationFn: (commentId?: string) =>
      CommentsService.markCommentsRead({ commentId: commentId ?? null }),
    onSuccess: () => {
      showSuccessToast("Marked as read")
      queryClient.invalidateQueries({ queryKey: ["myChannelComments"] })
      queryClient.invalidateQueries({ queryKey: ["unreadCommentCount"] })
    },
    onError: handleError.bind(showErrorToast),
  })

  const columns: ColumnDef<ChannelCommentOutput, unknown>[] = [
    {
      accessorKey: "channel_name",
      header: "Channel",
      cell: ({ row }) => (
        <Link
          to="/channels/$channelId"
          params={{ channelId: row.original.channel_id }}
          className="underline"
        >
          {row.original.channel_name ?? "Channel"}
        </Link>
      ),
    },
    {
      accessorKey: "author",
      header: "Author",
      cell: ({ row }) => (
        <Link
          to="/users/$userId/channels"
          params={{ userId: row.original.user_id }}
          className="underline"
        >
          {row.original.author}
        </Link>
      ),
    },
    {
      accessorKey: "body",
      header: "Comment",
      cell: ({ row }) => (
        <span className="whitespace-pre-wrap">{row.original.body}</span>
      ),
    },
    {
      accessorKey: "parent_comment_id",
      header: "Type",
      cell: ({ row }) => (row.original.parent_comment_id ? "Reply" : "Comment"),
    },
    {
      accessorKey: "created_at",
      header: "Left",
      cell: ({ row }) => new Date(row.original.created_at).toLocaleString(),
    },
    {
      accessorKey: "is_read",
      header: "Status",
      cell: ({ row }) =>
        row.original.is_read ? (
          <span className="text-muted-foreground">Read</span>
        ) : (
          <Button
            size="sm"
            variant="ghost"
            disabled={readMutation.isPending}
            onClick={() => readMutation.mutate(row.original.id)}
          >
            Mark read
          </Button>
        ),
    },
  ]

  const comments = data?.comments ?? []
  const totalCount = data?.total_count ?? 0
  const pageCount = Math.max(1, Math.ceil(totalCount / PAGE_SIZE))

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-2 px-[4%] pt-4 pb-2">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight">Comments</h1>
          {currentUser?.is_superuser && (
            <Tabs
              value={scope}
              onValueChange={(value) => {
                setScope(value as CommentScope)
                setPage(0)
              }}
            >
              <TabsList>
                <TabsTrigger value="owned">My channels</TabsTrigger>
                <TabsTrigger value="all">All channels</TabsTrigger>
              </TabsList>
            </Tabs>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {(data?.unread_count ?? 0) > 0 && (
            <Button
              variant="outline"
              size="sm"
              disabled={readMutation.isPending}
              onClick={() => readMutation.mutate(undefined)}
            >
              Mark all read ({data?.unread_count})
            </Button>
          )}
        </div>
      </div>
      <div className="flex flex-col gap-4 px-[4%]">
        {isLoading && <p className="text-sm text-muted-foreground">Loading…</p>}
        {!isLoading && comments.length === 0 && (
          <p className="text-sm text-muted-foreground">
            {scope === "all"
              ? "Nobody has commented on any channel yet."
              : "Nobody has commented on your channels yet."}
          </p>
        )}
        {comments.length > 0 && (
          <DataTable
            columns={columns}
            data={comments}
            storageKey="channelComments"
            rowClassName={(row) => (row.is_read ? undefined : "font-medium")}
          />
        )}
        {totalCount > PAGE_SIZE && (
          <div className="flex items-center justify-between gap-2">
            <Button
              size="sm"
              variant="outline"
              disabled={page === 0}
              onClick={() => setPage(page - 1)}
            >
              Previous
            </Button>
            <span className="text-xs text-muted-foreground">
              Page {page + 1} of {pageCount} ({totalCount} comments)
            </span>
            <Button
              size="sm"
              variant="outline"
              disabled={page + 1 >= pageCount}
              onClick={() => setPage(page + 1)}
            >
              Next
            </Button>
          </div>
        )}
      </div>
    </>
  )
}
