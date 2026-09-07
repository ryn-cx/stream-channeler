// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { Unlink } from "lucide-react"

import { TitlesService } from "@/client"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { Label } from "@/components/ui/label"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import EditTitle from "./Edit"

interface NonCanonicalTitleLinksProps {
  titleId: string
  enabled: boolean
}

// TODO: Validate
export function NonCanonicalTitleLinks({
  titleId,
  enabled,
}: NonCanonicalTitleLinksProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const { data: titles, isLoading } = useQuery({
    queryKey: ["titles", titleId, "non-canonical"],
    queryFn: () => TitlesService.getNonCanonicalTitles({ titleId }),
    enabled,
  })

  const unlinkMutation = useMutation({
    mutationFn: (droppedId: string) =>
      TitlesService.adminUnlinkTitleFromCanonical({
        titleId: droppedId,
        canonicalTitleId: titleId,
      }),
    onSuccess: () => {
      showSuccessToast("Title unlinked from this title")
      queryClient.invalidateQueries({ queryKey: ["titles"] })
      queryClient.invalidateQueries({
        queryKey: ["title-information", titleId],
      })
      queryClient.invalidateQueries({ queryKey: ["canonical-title"] })
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
  })

  if (isLoading) {
    return (
      <p className="text-sm text-muted-foreground">
        Reading the linked titles…
      </p>
    )
  }
  if (!titles || titles.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No title is linked to this title.
      </p>
    )
  }

  return (
    <div className="space-y-2">
      <Label>Linked Titles</Label>
      <div className="rounded-lg border">
        {titles.map((linked) => (
          <div
            key={linked.id}
            className="flex items-center gap-3 border-b px-3 py-2 text-sm last:border-b-0"
          >
            <span className="flex-1 whitespace-normal wrap-break-word">
              <Link
                to="/seasons"
                search={{ title_id: linked.id }}
                className="hover:underline"
              >
                {linked.name ?? "Unnamed"}
              </Link>
              <span className="block text-xs text-muted-foreground">
                {linked.source_key ?? linked.plugin_name ?? linked.key}
              </span>
            </span>
            <EditTitle title={linked} size="sm" />
            <TooltipIconButton
              label="Unlink Title"
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
