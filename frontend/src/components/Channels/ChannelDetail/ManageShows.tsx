// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { List, Settings, Trash2 } from "lucide-react"
import { useState } from "react"

import { ChannelsService } from "@/client"
import { OpenAPI } from "@/client/core/OpenAPI"
import { request as apiRequest } from "@/client/core/request"
import { VariantTrigger } from "@/components/Common/VariantTrigger"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
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

import { WhitelistManager } from "./WhitelistManager"

interface Show {
  id: string
  name: string | null
  source_id: string
  url?: string | null
}

interface Source {
  favicon_url?: string | null
  name: string | null
}

interface ManageShowsProps {
  channelId: string
  variant?: "button" | "menu"
}

export function ManageShows({
  channelId,
  variant = "button",
}: ManageShowsProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [selectedShowId, setSelectedShowId] = useState<string | null>(null)

  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()

  const { data: showsData } = useQuery({
    queryKey: ["channel-shows", channelId],
    queryFn: () =>
      apiRequest<{
        shows: Show[]
        sources: Record<string, Source>
      }>(OpenAPI, {
        method: "GET",
        url: `/api/v1/channels/${channelId}/shows`,
      }),
    enabled: isOpen,
  })

  const shows: Record<string, Show> = showsData?.shows
    ? Object.fromEntries(showsData.shows.map((show) => [show.id, show]))
    : {}
  const sources: Record<string, Source> = showsData?.sources || {}

  const removeShowMutation = useMutation({
    mutationFn: (showId: string) =>
      ChannelsService.deleteChannelShow({ channelId, showId }),
    // When mutate is called:
    onMutate: async (showId) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await queryClient.cancelQueries({
        queryKey: ["channel-shows", channelId],
      })

      // Snapshot the previous values
      const previousEpisodesEntries = queryClient.getQueriesData({
        queryKey: ["episodes", channelId],
      })
      const previousShowsData = queryClient.getQueryData([
        "channel-shows",
        channelId,
      ])

      // Optimistically update to the new value
      queryClient.setQueryData(
        ["channel-shows", channelId],
        (oldData: any) => ({
          ...oldData,
          shows: oldData.shows.filter((show: Show) => show.id !== showId),
        }),
      )

      showSuccessToast("Show removed successfully")

      // Return a result with the snapshotted values
      return { previousEpisodesEntries, previousShowsData }
    },
    // If the mutation fails,
    // use the result returned from onMutate to roll back
    onError: (error, _showId, context) => {
      for (const [queryKey, data] of context?.previousEpisodesEntries ?? []) {
        queryClient.setQueryData(queryKey as any, data)
      }
      if (context?.previousShowsData) {
        queryClient.setQueryData(
          ["channel-shows", channelId],
          context.previousShowsData,
        )
      }
      handleError.call(showErrorToast, error as any)
    },
    // Always refetch after error or success:
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: ["channel-shows", channelId],
      })
      queryClient.invalidateQueries({
        queryKey: ["episodes", channelId],
      })
    },
  })

  const handleRemoveShow = (showId: string) => {
    if (
      confirm(
        "Are you sure you want to remove this show from the channel? This will remove all episodes from this show.",
      )
    ) {
      removeShowMutation.mutate(showId)
    }
  }

  const handleOpenWhitelistManager = (showId: string) => {
    setSelectedShowId(showId)
  }

  const handleCloseWhitelistManager = () => {
    setSelectedShowId(null)
  }

  const showsList = Object.values(shows).sort((a, b) =>
    (a.name ?? "").localeCompare(b.name ?? ""),
  )

  return (
    <>
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogTrigger asChild>
          <VariantTrigger variant={variant} icon={List} label="Manage Shows" />
        </DialogTrigger>

        <DialogContent className="sm:max-w-4xl max-h-[85vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>Manage Shows</DialogTitle>
            <DialogDescription>
              Remove shows from the channel or manage their whitelist settings
            </DialogDescription>
          </DialogHeader>

          <div className="overflow-y-auto py-4">
            {showsList.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">
                No shows in this channel
              </p>
            ) : (
              <div className="border rounded-lg">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Show</TableHead>
                      <TableHead className="w-[150px] text-center">
                        Actions
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {showsList.map((show) => {
                      const source = sources[show.source_id]
                      return (
                        <TableRow key={show.id}>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              {source?.favicon_url && (
                                <img
                                  src={source.favicon_url}
                                  alt={`${source.name} favicon`}
                                  className="size-4"
                                />
                              )}
                              <span>{show.name ?? ""}</span>
                            </div>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center justify-center gap-1">
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                onClick={() =>
                                  handleOpenWhitelistManager(show.id)
                                }
                                title="Manage whitelist"
                              >
                                <Settings className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                onClick={() => handleRemoveShow(show.id)}
                                disabled={removeShowMutation.isPending}
                                title="Remove show"
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {selectedShowId && (
        <WhitelistManager
          channelId={channelId}
          showId={selectedShowId}
          showName={shows[selectedShowId]?.name || "Unknown Show"}
          isOpen={!!selectedShowId}
          onClose={handleCloseWhitelistManager}
        />
      )}
    </>
  )
}
