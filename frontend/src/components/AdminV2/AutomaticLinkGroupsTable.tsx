// TODO: Validate
import { useMutation, useQuery } from "@tanstack/react-query"
import { Link2Off, RotateCcw } from "lucide-react"
import { useState } from "react"
import type { AutomaticLinkGroupOutput } from "@/client"
import { TitlesService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { EmptyState } from "@/components/Common/EmptyState"
import { PageHeader } from "@/components/Common/PageHeader"
import { Button } from "@/components/ui/button"
import { ButtonGroup } from "@/components/ui/button-group"
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
export function AutomaticLinkGroupsTable() {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [bySource, setBySource] = useState(false)
  const [pendingGroup, setPendingGroup] =
    useState<AutomaticLinkGroupOutput | null>(null)

  const { data: groups, isPending } = useQuery({
    queryKey: ["automatic-link-groups", bySource],
    queryFn: () => TitlesService.adminGetAutomaticLinkGroups({ bySource }),
  })

  const resetGroup = useMutation({
    mutationFn: (groupId: string) =>
      TitlesService.adminResetAutomaticLinkGroup({ groupId, bySource }),
    onSuccess: (message, _groupId, _onMutateResult, context) => {
      showSuccessToast(message.message)
      context.client.invalidateQueries({ queryKey: ["automatic-link-groups"] })
      context.client.invalidateQueries({ queryKey: ["titles"] })
    },
    onError: handleError.bind(showErrorToast),
  })

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Reset Automatic Links"
        description="Titles whose every TMDB link was made automatically and has not been verified. Resetting drops those links so the linker matches them again."
      />

      <div className="flex px-[4%]">
        <ButtonGroup>
          <Button
            variant={bySource ? "outline" : "default"}
            size="sm"
            onClick={() => setBySource(false)}
          >
            By plugin
          </Button>
          <Button
            variant={bySource ? "default" : "outline"}
            size="sm"
            onClick={() => setBySource(true)}
          >
            By source
          </Button>
        </ButtonGroup>
      </div>

      {isPending ? null : groups?.length ? (
        <div className="px-[4%]">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{bySource ? "Source" : "Plugin"}</TableHead>
                {bySource && <TableHead>Plugin</TableHead>}
                <TableHead className="text-right">Titles</TableHead>
                <TableHead className="w-0" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {groups.map((group) => (
                <TableRow key={group.id}>
                  <TableCell>{group.key}</TableCell>
                  {bySource && (
                    <TableCell className="text-muted-foreground">
                      {group.plugin_key}
                    </TableCell>
                  )}
                  <TableCell className="text-right">
                    {group.title_count.toLocaleString()}
                  </TableCell>
                  <TableCell>
                    <div className="flex justify-end">
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => setPendingGroup(group)}
                        disabled={resetGroup.isPending}
                      >
                        <RotateCcw />
                        Reset links
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
          icon={Link2Off}
          title="Nothing to reset"
          description="Every title here either has a link someone settled by hand or has already been verified."
        />
      )}

      <ConfirmDialog
        open={pendingGroup !== null}
        onOpenChange={(open) => {
          if (!open) setPendingGroup(null)
        }}
        title="Drop every automatic link?"
        description={
          pendingGroup
            ? `The TMDB links of ${pendingGroup.title_count.toLocaleString()} title${pendingGroup.title_count === 1 ? "" : "s"} in ${pendingGroup.key} will be deleted and their link status cleared, so the linker matches them again. Links settled by hand and verified titles are left alone.`
            : ""
        }
        confirmLabel="Reset links"
        onConfirm={() => {
          if (pendingGroup) resetGroup.mutate(pendingGroup.id)
        }}
      />
    </div>
  )
}
