// TODO: Validate
import { useMutation, useQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import { Upload } from "lucide-react"
import { useRef, useState } from "react"
import Markdown from "react-markdown"
import {
  PluginsService,
  WatchesService,
  type WatchImportResult,
  type WatchImportResults,
} from "@/client"

interface PluginImportWatchHistoryInfo {
  plugin_key: string
  file_extension: string | null
  instructions: string
}

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { isLoggedIn } from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

export const Route = createFileRoute("/_layout/watches_/import")({
  component: ImportWatchHistory,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Import Watch History - Stream Channeler" }],
  }),
})

// TODO: Validate
function groupByShow(entries: Array<WatchImportResult>) {
  const groups = new Map<
    string,
    { show_url: string; episodes: Array<WatchImportResult> }
  >()
  for (const entry of entries) {
    const existing = groups.get(entry.show)
    if (existing) {
      existing.episodes.push(entry)
    } else {
      groups.set(entry.show, { show_url: entry.show_url, episodes: [entry] })
    }
  }
  return groups
}

// TODO: Validate
function EntryList({ entries }: { entries: Array<WatchImportResult> }) {
  if (entries.length === 0) return null

  const groups = [...groupByShow(entries).entries()].sort(
    (a, b) => b[1].episodes.length - a[1].episodes.length,
  )

  return (
    <Accordion type="multiple">
      {groups.map(([show, { show_url, episodes }]) => (
        <AccordionItem key={show} value={show}>
          <AccordionTrigger className="py-2 text-sm justify-start gap-1 flex-initial">
            {show_url ? (
              <a
                href={show_url}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:underline text-primary"
                onClick={(e) => e.stopPropagation()}
              >
                {show}
              </a>
            ) : (
              show
            )}
            <span className="text-muted-foreground">({episodes.length})</span>
          </AccordionTrigger>
          <AccordionContent>
            <ul className="space-y-1 pl-4">
              {episodes.map((ep, i) => (
                <li key={i} className="text-sm text-muted-foreground">
                  {ep.episode_url ? (
                    <a
                      href={ep.episode_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:underline text-primary"
                    >
                      {ep.episode}
                    </a>
                  ) : (
                    ep.episode
                  )}
                </li>
              ))}
            </ul>
          </AccordionContent>
        </AccordionItem>
      ))}
    </Accordion>
  )
}

// TODO: Validate
function ImportResults({ result }: { result: WatchImportResults }) {
  const categories = [
    { title: "Added", entries: result.added },
    { title: "Existing", entries: result.existing },
    {
      title: "Skipped (Add the show to a channel first)",
      entries: result.skipped,
    },
  ].filter((c) => c.entries.length > 0)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Import Results</CardTitle>
        <CardDescription>
          {result.added.length} added, {result.existing.length} existing,{" "}
          {result.skipped.length} skipped
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Accordion
          type="multiple"
          defaultValue={categories.map((c) => c.title)}
        >
          {categories.map(({ title, entries }) => (
            <AccordionItem key={title} value={title}>
              <AccordionTrigger>
                {title} ({entries.length})
              </AccordionTrigger>
              <AccordionContent>
                <EntryList entries={entries} />
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </CardContent>
    </Card>
  )
}

// TODO: Validate
function ImportWatchHistory() {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [selectedPlugin, setSelectedPlugin] = useState<string>("")
  const [newOnly, setNewOnly] = useState(true)
  const [verified, setVerified] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [importResult, setImportResult] = useState<WatchImportResults | null>(
    null,
  )
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { data: pluginsData, isLoading: pluginsLoading } = useQuery({
    queryFn: () =>
      PluginsService.importWatchHistoryInformation() as unknown as Promise<
        PluginImportWatchHistoryInfo[]
      >,
    queryKey: ["watch-import-plugins"],
  })

  const mutation = useMutation({
    mutationFn: async () => {
      if (!selectedPlugin || !selectedFile) return
      return WatchesService.importWatchHistory({
        pluginKey: selectedPlugin,
        newOnly: newOnly,
        verified: verified,
        formData: { file: selectedFile },
      })
    },
    onSuccess: (data) => {
      if (!data) return
      setImportResult(data)
      showSuccessToast(
        `Import complete: ${data.added.length} added, ${data.existing.length} already watched, ${data.skipped.length} not found`,
      )
      setSelectedFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ""
    },
    onError: handleError.bind(showErrorToast),
  })

  const selectedPluginInfo: PluginImportWatchHistoryInfo | undefined =
    pluginsData?.find(
      (p: PluginImportWatchHistoryInfo) => p.plugin_key === selectedPlugin,
    )

  return (
    <div className="flex flex-col gap-6 px-[4%] pt-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          Import Watch History
        </h1>
        <p className="text-muted-foreground">
          Upload a watch history file to import your viewing history
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Select Plugin</CardTitle>
          <CardDescription>
            Choose which service to import watch history from
          </CardDescription>
        </CardHeader>
        <CardContent>
          {pluginsLoading ? (
            <p className="text-muted-foreground">
              Loading available plugins...
            </p>
          ) : (
            <Select value={selectedPlugin} onValueChange={setSelectedPlugin}>
              <SelectTrigger className="w-[280px]">
                <SelectValue placeholder="Select a plugin" />
              </SelectTrigger>
              <SelectContent>
                {pluginsData?.map((plugin: PluginImportWatchHistoryInfo) => (
                  <SelectItem key={plugin.plugin_key} value={plugin.plugin_key}>
                    {plugin.plugin_key}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </CardContent>
      </Card>

      {selectedPluginInfo && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Instructions</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              <Markdown
                components={{
                  ol: ({ children }) => (
                    <ol className="list-decimal list-inside space-y-1">
                      {children}
                    </ol>
                  ),
                }}
              >
                {selectedPluginInfo.instructions}
              </Markdown>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Import Options</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="flex items-center gap-2">
                <Checkbox
                  id="new-only"
                  checked={newOnly}
                  onCheckedChange={(checked) => setNewOnly(checked === true)}
                />
                <label htmlFor="new-only" className="text-sm font-medium">
                  Skip already watched episodes
                </label>
              </div>

              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <Checkbox
                    id="verified"
                    checked={verified}
                    onCheckedChange={(checked) => setVerified(checked === true)}
                  />
                  <label htmlFor="verified" className="text-sm font-medium">
                    Mark as verified
                  </label>
                </div>
                <p className="text-xs text-muted-foreground">
                  Only applies to watches the file does not record a verified
                  status for.
                </p>
              </div>

              <div>
                <label
                  htmlFor="file-upload"
                  className="text-sm font-medium mb-2 block"
                >
                  Upload File ({selectedPluginInfo.file_extension})
                </label>
                <input
                  id="file-upload"
                  ref={fileInputRef}
                  type="file"
                  accept={selectedPluginInfo.file_extension ?? undefined}
                  onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
                  className="block w-full text-sm text-muted-foreground file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-primary file:text-primary-foreground hover:file:bg-primary/90"
                />
              </div>

              <LoadingButton
                onClick={() => mutation.mutate()}
                loading={mutation.isPending}
                disabled={!selectedFile}
                className="w-fit"
              >
                <Upload className="mr-2 h-4 w-4" />
                Import Watch History
              </LoadingButton>
            </CardContent>
          </Card>

          {importResult && <ImportResults result={importResult} />}
        </>
      )}
    </div>
  )
}
