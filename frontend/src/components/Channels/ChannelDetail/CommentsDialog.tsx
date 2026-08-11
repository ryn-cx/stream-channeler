// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { MessageSquare } from "lucide-react"
import { useState } from "react"

import { type CommentOutput, CommentsService } from "@/client"
import { ModalContent } from "@/components/Common/ModalContent"
import {
  type TriggerVariant,
  VariantTrigger,
} from "@/components/Common/VariantTrigger"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogBody,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

const PAGE_SIZE = 20

interface CommentFormProps {
  placeholder: string
  submitLabel: string
  pending: boolean
  onSubmit: (body: string) => void
  onCancel?: () => void
}

// TODO: Validate
function CommentForm({
  placeholder,
  submitLabel,
  pending,
  onSubmit,
  onCancel,
}: CommentFormProps) {
  const [body, setBody] = useState("")

  return (
    <div className="flex flex-col gap-2">
      <Textarea
        value={body}
        placeholder={placeholder}
        rows={3}
        onChange={(event) => setBody(event.target.value)}
      />
      <div className="flex gap-2">
        <Button
          size="sm"
          disabled={pending || body.trim().length === 0}
          onClick={() => {
            onSubmit(body.trim())
            setBody("")
          }}
        >
          {submitLabel}
        </Button>
        {onCancel && (
          <Button size="sm" variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
        )}
      </div>
    </div>
  )
}

interface CommentNodeProps {
  comment: CommentOutput
  currentUserId?: string
  pending: boolean
  onReply: (parentCommentId: string, body: string) => void
  onDelete: (commentId: string) => void
  /** True when the comment already carries its replies from a thread response. */
  preloaded?: boolean
}

// A top level comment shows on its own until its thread is asked for, and the thread
// request returns every descendant nested, so one click reveals the whole tree. Replies
// rendered from that response already carry their own children and never refetch.
// TODO: Validate
function CommentNode({
  comment,
  currentUserId,
  pending,
  onReply,
  onDelete,
  preloaded = false,
}: CommentNodeProps) {
  const [replying, setReplying] = useState(false)
  const [expanded, setExpanded] = useState(preloaded)

  const { data: threadData, isFetching } = useQuery({
    queryKey: ["commentReplies", comment.id],
    queryFn: () =>
      CommentsService.readCommentReplies({ commentId: comment.id }),
    enabled: expanded && !preloaded,
  })

  const replies = preloaded
    ? (comment.replies ?? [])
    : (threadData?.comments ?? [])
  const replyCount = comment.reply_count ?? 0

  return (
    <div className="flex flex-col gap-2">
      <div className="rounded-md border px-3 py-2">
        <div className="flex items-baseline justify-between gap-2">
          <Link
            to="/users/$userId/channels"
            params={{ userId: comment.user_id }}
            className="text-sm font-semibold hover:underline"
          >
            {comment.author}
          </Link>
          <span className="text-xs text-muted-foreground">
            {new Date(comment.created_at).toLocaleString()}
          </span>
        </div>
        <p className="mt-1 whitespace-pre-wrap text-sm">{comment.body}</p>
        <div className="mt-2 flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setReplying(!replying)}
          >
            Reply
          </Button>
          {replyCount > 0 && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setExpanded(!expanded)}
            >
              {expanded
                ? "Hide replies"
                : `Show ${replyCount} ${replyCount === 1 ? "reply" : "replies"}`}
            </Button>
          )}
          {currentUserId === comment.user_id && (
            <Button
              size="sm"
              variant="ghost"
              disabled={pending}
              onClick={() => onDelete(comment.id)}
            >
              Delete
            </Button>
          )}
        </div>
        {replying && (
          <div className="mt-2">
            <CommentForm
              placeholder={`Reply to ${comment.author}`}
              submitLabel="Reply"
              pending={pending}
              onCancel={() => setReplying(false)}
              onSubmit={(body) => {
                onReply(comment.id, body)
                setReplying(false)
                setExpanded(true)
              }}
            />
          </div>
        )}
      </div>
      {expanded && (
        <div className="ml-4 flex flex-col gap-2 border-l pl-3">
          {isFetching && replies.length === 0 && (
            <p className="text-sm text-muted-foreground">Loading replies…</p>
          )}
          {replies.map((reply) => (
            <CommentNode
              key={reply.id}
              comment={reply}
              currentUserId={currentUserId}
              pending={pending}
              onReply={onReply}
              onDelete={onDelete}
              preloaded
            />
          ))}
        </div>
      )}
    </div>
  )
}

interface CommentsDialogProps {
  channelId: string
  channelName?: string | null
  variant?: TriggerVariant
}

// TODO: Validate
export function CommentsDialog({
  channelId,
  channelName,
  variant = "button",
}: CommentsDialogProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [page, setPage] = useState(0)
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const { data, isLoading } = useQuery({
    queryKey: ["channelComments", channelId, page],
    queryFn: () =>
      CommentsService.readChannelComments({
        channelId,
        offset: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      }),
    enabled: isOpen,
  })

  // TODO: Validate
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["channelComments", channelId] })
    queryClient.invalidateQueries({ queryKey: ["commentReplies"] })
    queryClient.invalidateQueries({ queryKey: ["unreadCommentCount"] })
  }

  const createMutation = useMutation({
    mutationFn: ({
      body,
      parentCommentId,
    }: {
      body: string
      parentCommentId?: string
    }) =>
      CommentsService.createChannelComment({
        channelId,
        requestBody: { body, parent_comment_id: parentCommentId ?? null },
      }),
    onSuccess: () => {
      showSuccessToast("Comment posted")
      invalidate()
    },
    onError: handleError.bind(showErrorToast),
  })

  const deleteMutation = useMutation({
    mutationFn: (commentId: string) =>
      CommentsService.deleteChannelComment({ commentId }),
    onSuccess: () => {
      showSuccessToast("Comment deleted")
      invalidate()
    },
    onError: handleError.bind(showErrorToast),
  })

  const comments = data?.comments ?? []
  const totalCount = data?.total_count ?? 0
  const pageCount = Math.max(1, Math.ceil(totalCount / PAGE_SIZE))
  const pending = createMutation.isPending || deleteMutation.isPending

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <VariantTrigger
          variant={variant}
          icon={MessageSquare}
          label="Comments"
          iconTitle="Comments"
        />
      </DialogTrigger>
      <ModalContent size="3xl">
        <DialogHeader>
          <DialogTitle>Comments</DialogTitle>
          <DialogDescription>
            {channelName
              ? `Comments on ${channelName}`
              : "Comments on this channel"}
          </DialogDescription>
        </DialogHeader>
        <DialogBody className="flex flex-col gap-4">
          <CommentForm
            placeholder="Leave a comment"
            submitLabel="Post comment"
            pending={pending}
            onSubmit={(body) => createMutation.mutate({ body })}
          />
          {isLoading && (
            <p className="text-sm text-muted-foreground">Loading…</p>
          )}
          {!isLoading && comments.length === 0 && (
            <p className="text-sm text-muted-foreground">No comments yet.</p>
          )}
          {comments.map((comment) => (
            <CommentNode
              key={comment.id}
              comment={comment}
              currentUserId={user?.id}
              pending={pending}
              onReply={(parentCommentId, body) =>
                createMutation.mutate({ body, parentCommentId })
              }
              onDelete={(commentId) => deleteMutation.mutate(commentId)}
            />
          ))}
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
        </DialogBody>
      </ModalContent>
    </Dialog>
  )
}
