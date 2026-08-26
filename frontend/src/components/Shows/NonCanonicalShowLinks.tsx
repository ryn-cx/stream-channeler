// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { Unlink } from "lucide-react"

import { ShowsService } from "@/client"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { Label } from "@/components/ui/label"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import EditShow from "./Edit"

interface NonCanonicalShowLinksProps {
  showId: string
  enabled: boolean
}

// TODO: Validate
export function NonCanonicalShowLinks({
  showId,
  enabled,
}: NonCanonicalShowLinksProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const { data: shows, isLoading } = useQuery({
    queryKey: ["shows", showId, "non-canonical"],
    queryFn: () => ShowsService.getNonCanonicalShows({ showId }),
    enabled,
  })

  const unlinkMutation = useMutation({
    mutationFn: (droppedId: string) =>
      ShowsService.adminUnlinkShowFromCanonical({
        showId: droppedId,
        canonicalShowId: showId,
      }),
    onSuccess: () => {
      showSuccessToast("Show unlinked from this title")
      queryClient.invalidateQueries({ queryKey: ["shows"] })
      queryClient.invalidateQueries({ queryKey: ["show-information", showId] })
      queryClient.invalidateQueries({ queryKey: ["canonical-show"] })
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
  })

  if (isLoading) {
    return (
      <p className="text-sm text-muted-foreground">Reading the linked shows…</p>
    )
  }
  if (!shows || shows.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No show is linked to this title.
      </p>
    )
  }

  return (
    <div className="space-y-2">
      <Label>Linked Shows</Label>
      <div className="rounded-lg border">
        {shows.map((linked) => (
          <div
            key={linked.id}
            className="flex items-center gap-3 border-b px-3 py-2 text-sm last:border-b-0"
          >
            <span className="flex-1 whitespace-normal wrap-break-word">
              <Link
                to="/show/$showKey"
                params={{ showKey: linked.id }}
                className="hover:underline"
              >
                {linked.name ?? "Unnamed"}
              </Link>
              <span className="block text-xs text-muted-foreground">
                {linked.source_name ?? linked.plugin_name ?? linked.key}
              </span>
            </span>
            <EditShow show={linked} size="sm" />
            <TooltipIconButton
              label="Unlink Show"
              icon={<Unlink />}
              size="sm"
              disabled={unlinkMutation.isPending}
              onClick={() => unlinkMutation.mutate(linked.id)}
            />
          </div>
        ))}
      </div>
    </div>
  )
}
