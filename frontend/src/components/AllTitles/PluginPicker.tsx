// TODO: Validate
import type { PluginBrowseInformation } from "@/client"
import { SourceOptionLabel } from "@/components/Common/SourceOptionLabel"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

// TODO: Validate
export function PluginPicker({
  plugins,
  value,
  onValueChange,
}: {
  plugins: PluginBrowseInformation[]
  value: string | null
  onValueChange: (pluginKey: string) => void
}) {
  const selected = plugins.find((plugin) => plugin.name === value)

  return (
    <Select value={value ?? undefined} onValueChange={onValueChange}>
      <SelectTrigger className="w-[220px]" aria-label="Website">
        <SelectValue placeholder="Choose a website">
          {selected ? (
            <SourceOptionLabel
              name={selected.name}
              faviconUrl={selected.favicon_url}
            />
          ) : null}
        </SelectValue>
      </SelectTrigger>
      <SelectContent>
        {plugins.map((plugin) => (
          <SelectItem key={plugin.name} value={plugin.name}>
            <SourceOptionLabel
              name={plugin.name}
              faviconUrl={plugin.favicon_url}
            />
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
