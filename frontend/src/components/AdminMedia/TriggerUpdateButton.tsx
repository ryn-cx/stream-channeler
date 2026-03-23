import { useMutation, useQueryClient } from "@tanstack/react-query"
import { RefreshCw } from "lucide-react"

import { OpenAPI } from "@/client"
import { request } from "@/client/core/request"
import { Button } from "@/components/ui/button"

interface TriggerUpdateButtonProps {
  entityType: "plugins" | "sources" | "shows" | "seasons" | "episodes"
  entityId: string
  queryKey: string[]
}

export default function TriggerUpdateButton({
  entityType,
  entityId,
  queryKey,
}: TriggerUpdateButtonProps) {
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: () =>
      request(OpenAPI, {
        method: "POST",
        url: `/api/v1/admin-media/${entityType}/{entity_id}/trigger-update`,
        path: { entity_id: entityId },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey })
    },
  })

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => mutation.mutate()}
      disabled={mutation.isPending}
      title="Trigger update"
    >
      <RefreshCw className={mutation.isPending ? "animate-spin" : ""} />
    </Button>
  )
}
