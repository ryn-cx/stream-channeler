// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ChevronDown, ChevronUp, Globe } from "lucide-react"
import { useEffect, useState } from "react"

import { type SourcePreferenceOutput, UsersService } from "@/client"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

const OTHER_SOURCE_KEY = "Other"

function sourceLabel(key: string): string {
  return key === OTHER_SOURCE_KEY ? "Other (custom media)" : key
}

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

  const move = (index: number, direction: -1 | 1) => {
    const target = index + direction
    if (target < 0 || target >= preferences.length) {
      return
    }
    const next = [...preferences]
    ;[next[index], next[target]] = [next[target], next[index]]
    setPreferences(next)
  }

  const toggle = (index: number) => {
    const next = [...preferences]
    next[index] = { ...next[index], enabled: !(next[index].enabled ?? true) }
    setPreferences(next)
  }

  return (
    <div>
      <h3 className="text-lg font-semibold py-4">Sources</h3>
      <p className="text-sm text-muted-foreground mb-4">
        When the same episode is available from more than one source, the source
        highest in this list is shown and the duplicates are hidden. Use the
        checkbox to enable or disable a source everywhere &mdash; a disabled
        source's episodes are hidden from all of your channels. Reorder with the
        arrows. This applies on top of each channel's own source filtering.
      </p>
      <ul className="divide-y rounded-md border">
        {preferences.map((preference, index) => (
          <li
            key={preference.source_key}
            className="flex items-center gap-2 px-3 py-1.5"
          >
            <Checkbox
              checked={preference.enabled ?? true}
              onCheckedChange={() => toggle(index)}
              aria-label={`Enable ${sourceLabel(preference.source_key)}`}
            />
            <Button
              variant="ghost"
              size="icon-sm"
              disabled={index === 0}
              onClick={() => move(index, -1)}
              aria-label={`Move ${sourceLabel(preference.source_key)} up`}
            >
              <ChevronUp className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              disabled={index === preferences.length - 1}
              onClick={() => move(index, 1)}
              aria-label={`Move ${sourceLabel(preference.source_key)} down`}
            >
              <ChevronDown className="h-4 w-4" />
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
            <span className="flex-1 truncate">
              {sourceLabel(preference.source_key)}
            </span>
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
