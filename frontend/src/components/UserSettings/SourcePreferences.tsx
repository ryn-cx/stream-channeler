// TODO: Validate
// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  ChevronDown,
  ChevronsDown,
  ChevronsUp,
  ChevronUp,
  Globe,
} from "lucide-react"
import { useEffect, useState } from "react"

import { type SourcePreferenceOutput, UsersService } from "@/client"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

const OTHER_SOURCE_KEY = "Other"

// TODO: Validate
function sourceLabel(preference: SourcePreferenceOutput): string {
  if (preference.source_key === OTHER_SOURCE_KEY) {
    return "Other (custom media)"
  }
  return preference.name ?? preference.source_key
}

// TODO: Validate
const SourcePreferences = () => {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [preferences, setPreferences] = useState<SourcePreferenceOutput[]>([])

  const { data } = useQuery({
    queryKey: ["source-preferences"],
    queryFn: () => UsersService.readSourcePreferences(),
    refetchOnWindowFocus: false,
  })

  useEffect(() => {
    if (data) {
      setPreferences(data)
    }
  }, [data])

  const mutation = useMutation({
    mutationFn: (body: SourcePreferenceOutput[]) =>
      UsersService.updateSourcePreferences({
        requestBody: body.map(({ source_key, enabled }) => ({
          source_key,
          enabled,
        })),
      }),
    onSuccess: (updated) => {
      setPreferences(updated)
      showSuccessToast("Source preferences updated")
      queryClient.invalidateQueries({ queryKey: ["source-preferences"] })
    },
    onError: handleError.bind(showErrorToast),
  })

  const visible = preferences.filter(
    (preference) => preference.episode_count > 0,
  )

  // TODO: Validate
  const moveTo = (sourceKey: string, targetIndex: number) => {
    const next = [...preferences]
    const from = next.findIndex(
      (preference) => preference.source_key === sourceKey,
    )
    const [moved] = next.splice(from, 1)
    next.splice(targetIndex, 0, moved)
    setPreferences(next)
  }

  // TODO: Validate
  const move = (visibleIndex: number, direction: -1 | 1) => {
    const neighbor = visible[visibleIndex + direction]
    if (!neighbor) {
      return
    }
    const neighborIndex = preferences.findIndex(
      (preference) => preference.source_key === neighbor.source_key,
    )
    moveTo(visible[visibleIndex].source_key, neighborIndex)
  }

  // TODO: Validate
  const toggle = (sourceKey: string) => {
    setPreferences(
      preferences.map((preference) =>
        preference.source_key === sourceKey
          ? { ...preference, enabled: !(preference.enabled ?? true) }
          : preference,
      ),
    )
  }

  return (
    <div>
      <h3 className="text-lg font-semibold py-4">Sources</h3>
      <p className="text-sm text-muted-foreground mb-4">
        When the same episode is available from more than one source, the source
        highest in this list is shown and the duplicates are hidden. Use the
        checkbox to enable or disable a source everywhere &mdash; a disabled
        source's episodes are hidden from all of your channels. Reorder with the
        arrows, or send a source straight to the top or bottom with the double
        arrows. Only sources with at least one episode are listed. This applies
        on top of each channel's own source filtering.
      </p>
      <ul className="divide-y rounded-md border">
        {visible.map((preference, index) => (
          <li
            key={preference.source_key}
            className="flex items-center gap-2 px-3 py-1.5"
          >
            <Checkbox
              checked={preference.enabled ?? true}
              onCheckedChange={() => toggle(preference.source_key)}
              aria-label={`Enable ${sourceLabel(preference)}`}
            />
            <Button
              variant="ghost"
              size="icon-sm"
              disabled={index === 0}
              onClick={() => moveTo(preference.source_key, 0)}
              aria-label={`Move ${sourceLabel(preference)} to the top`}
            >
              <ChevronsUp className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              disabled={index === 0}
              onClick={() => move(index, -1)}
              aria-label={`Move ${sourceLabel(preference)} up`}
            >
              <ChevronUp className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              disabled={index === visible.length - 1}
              onClick={() => move(index, 1)}
              aria-label={`Move ${sourceLabel(preference)} down`}
            >
              <ChevronDown className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              disabled={index === visible.length - 1}
              onClick={() =>
                moveTo(preference.source_key, preferences.length - 1)
              }
              aria-label={`Move ${sourceLabel(preference)} to the bottom`}
            >
              <ChevronsDown className="h-4 w-4" />
            </Button>
            {preference.favicon_url ? (
              <img
                src={preference.favicon_url}
                alt=""
                className="size-4 shrink-0 rounded-sm"
              />
            ) : (
              <Globe className="size-4 shrink-0 text-muted-foreground" />
            )}
            <span className="flex-1 truncate">{sourceLabel(preference)}</span>
          </li>
        ))}
      </ul>
      <LoadingButton
        className="mt-4"
        loading={mutation.isPending}
        onClick={() => mutation.mutate(preferences)}
      >
        Save
      </LoadingButton>
    </div>
  )
}

export default SourcePreferences
