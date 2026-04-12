// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import {
  ArrowLeft,
  Check,
  Cherry,
  ChevronRight,
  Dice5,
  Link2,
  ListOrdered,
  PartyPopper,
  Plus,
  Search,
  Trash2,
  Waves,
} from "lucide-react"
import { useState } from "react"
import Markdown from "react-markdown"
import { remarkAlert } from "remark-github-blockquote-alert"
import "remark-github-blockquote-alert/alert.css"
import type { ChannelQueueOutput, SortKeyInput } from "@/client"
import { ChannelsService } from "@/client"
import { OpenAPI } from "@/client/core/OpenAPI"
import { request as apiRequest } from "@/client/core/request"
import { ShowSearch } from "@/components/Channels/ChannelDetail/Search"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

type Step = "name" | "shows" | "sort" | "done"

const STEPS: Step[] = ["name", "shows", "sort", "done"]

interface SortPreset {
  label: string
  description: string
  icon: React.ReactNode
  sortBy: SortKeyInput[]
}

const SORT_PRESETS: SortPreset[] = [
  {
    label: "Roll The Dice",
    description: "The episode order is completely random",
    icon: <Dice5 className="h-10 w-10" />,
    sortBy: [
      {
        model: "episode",
        field: "random",
        direction: "ascending",
        mode: "normal",
      },
    ],
  },
  {
    label: "Channel Surfing",
    description:
      "Episodes play in order within each show, but shows are interleaved randomly",
    icon: <Waves className="h-10 w-10" />,
    sortBy: [
      {
        model: "episode",
        field: "episode_number",
        direction: "ascending",
        mode: "normal",
      },
      {
        model: "season",
        field: "season_number",
        direction: "ascending",
        mode: "normal",
      },
      {
        model: "show",
        field: "name",
        direction: "ascending",
        mode: "interleave_random",
      },
    ],
  },
  {
    label: "Fresh Picks",
    description: "Most recently aired episodes appear first",
    icon: <Cherry className="h-10 w-10" />,
    sortBy: [
      {
        model: "episode",
        field: "air_date",
        direction: "descending",
        mode: "normal",
      },
    ],
  },
  {
    label: "Marathon Mode",
    description:
      "All episodes of one show play in order before moving to the next show",
    icon: <ListOrdered className="h-10 w-10" />,
    sortBy: [
      {
        model: "episode",
        field: "episode_number",
        direction: "ascending",
        mode: "normal",
      },
      {
        model: "season",
        field: "season_number",
        direction: "ascending",
        mode: "normal",
      },
      {
        model: "show",
        field: "name",
        direction: "ascending",
        mode: "normal",
      },
    ],
  },
]

function AddShowsStep({
  channelId,
  onDone,
  onBack,
}: {
  channelId: string
  onDone: () => void
  onBack: () => void
}) {
  const [mode, setMode] = useState<"search" | "url">("search")
  const [urlInput, setUrlInput] = useState("")
  const [selectedPlugin, setSelectedPlugin] = useState<string | null>(null)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()

  const { data: urlImportPlugins } = useQuery({
    queryKey: ["url-import-plugins"],
    queryFn: () =>
      apiRequest<Array<{ name: string; instructions: string }>>(OpenAPI, {
        method: "GET",
        url: "/api/v1/plugins/import-url-information",
      }),
  })

  const { data: queueData } = useQuery({
    queryKey: ["channelQueue", channelId],
    queryFn: () => ChannelsService.getUserChannelQueue({ channelId }),
    refetchInterval: 5000,
  })

  const queueEntries = queueData ?? []

  const addUrlsMutation = useMutation({
    mutationFn: (urls: string[]) =>
      ChannelsService.createUserChannelQueueUrls({
        channelId,
        requestBody: urls,
      }),
    onSuccess: () => {
      showSuccessToast("URLs added to import queue")
      setUrlInput("")
      queryClient.invalidateQueries({
        queryKey: ["channelQueue", channelId],
      })
    },
    onError: handleError.bind(showErrorToast),
  })

  const deleteUrlMutation = useMutation({
    mutationFn: (urlId: string) =>
      ChannelsService.deleteUserChannelQueueUrl({ channelId, urlId }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["channelQueue", channelId],
      })
    },
    onError: handleError.bind(showErrorToast),
  })

  const handleAddUrls = () => {
    const urls = urlInput
      .split("\n")
      .map((url) => url.trim())
      .filter((url) => url.length > 0)
    if (urls.length === 0) return
    addUrlsMutation.mutate(urls)
  }

  return (
    <div className="space-y-6">
      <div className="text-center space-y-3">
        <h1 className="text-3xl font-bold">Add Shows</h1>
        <p className="text-muted-foreground">
          {mode === "search"
            ? "Search for shows and movies to add to your channel."
            : "Add URLs to your channel directly, one per line."}
        </p>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setMode(mode === "search" ? "url" : "search")}
        >
          {mode === "search" ? (
            <>
              <Link2 className="h-4 w-4 mr-1" /> Add Media By URL
            </>
          ) : (
            <>
              <Search className="h-4 w-4 mr-1" /> Add Media By Searching
            </>
          )}
        </Button>
      </div>

      {mode === "search" ? (
        <ShowSearch channelId={channelId} />
      ) : (
        <div className="space-y-4">
          <div className="border rounded-lg p-4 space-y-3">
            <p className="text-sm text-muted-foreground">
              Select a site to see supported URL formats:
            </p>
            <Select
              value={selectedPlugin ?? "__none__"}
              onValueChange={(value) =>
                setSelectedPlugin(value === "__none__" ? null : value)
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__none__">Choose a site...</SelectItem>
                {(urlImportPlugins ?? []).map((plugin) => (
                  <SelectItem key={plugin.name} value={plugin.name}>
                    {plugin.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {selectedPlugin && (
              <div className="text-sm text-muted-foreground [&_code]:bg-muted [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_code]:text-xs">
                <Markdown
                  remarkPlugins={[[remarkAlert, { legacyTitle: true }]]}
                >
                  {(urlImportPlugins ?? []).find(
                    (p) => p.name === selectedPlugin,
                  )?.instructions ?? ""}
                </Markdown>
              </div>
            )}
            <textarea
              value={urlInput}
              onChange={(event) => setUrlInput(event.target.value)}
              placeholder={
                "https://example.com/show-1\nhttps://example.com/show-2"
              }
              rows={4}
              className="w-full rounded-md border border-input px-3 py-2 text-sm outline-none"
            />
            <div className="flex justify-end">
              <Button
                onClick={handleAddUrls}
                disabled={addUrlsMutation.isPending || !urlInput.trim()}
                size="sm"
              >
                <Plus className="h-4 w-4 mr-1" />
                Add URLs
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Queue */}
      {queueEntries.length > 0 && (
        <div className="border rounded-lg p-4 space-y-3">
          <h3 className="font-medium">Import Queue ({queueEntries.length})</h3>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {queueEntries.map((entry: ChannelQueueOutput) => (
              <div
                key={entry.id}
                className="flex items-center gap-2 text-sm py-1"
              >
                <span className="flex-1 truncate">{entry.url}</span>
                <Badge
                  variant={
                    entry.status === "Imported"
                      ? "default"
                      : entry.status === "Failed"
                        ? "destructive"
                        : "secondary"
                  }
                >
                  {entry.status}
                </Badge>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={() => deleteUrlMutation.mutate(entry.id)}
                  disabled={deleteUrlMutation.isPending}
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex justify-between">
        <Button variant="outline" onClick={onBack} size="lg">
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back
        </Button>
        <Button onClick={onDone} size="lg">
          Continue
          <ChevronRight className="h-4 w-4 ml-1" />
        </Button>
      </div>
    </div>
  )
}

export function Onboarding() {
  const [step, setStep] = useState<Step>("name")
  const [channelName, setChannelName] = useState("")
  const [channelId, setChannelId] = useState<string | null>(null)
  const [selectedSort, setSelectedSort] = useState<number | null>(null)
  const { showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()

  const createChannelMutation = useMutation({
    mutationFn: () =>
      ChannelsService.createUserChannel({
        requestBody: {
          name: channelName.trim(),
          channel_number: 3,
          public: false,
        },
      }),
    onSuccess: (channel) => {
      setChannelId(channel.id)
      queryClient.invalidateQueries({ queryKey: ["channels"] })
      setStep("shows")
    },
    onError: handleError.bind(showErrorToast),
  })

  const updateChannelMutation = useMutation({
    mutationFn: () =>
      ChannelsService.updateUserChannel({
        channelId: channelId!,
        requestBody: { name: channelName.trim() },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["channels"] })
      setStep("shows")
    },
    onError: handleError.bind(showErrorToast),
  })

  const saveSortMutation = useMutation({
    mutationFn: (sortBy: SortKeyInput[]) =>
      ChannelsService.updateUserChannelDefaultOrder({
        channelId: channelId!,
        requestBody: { sortBy } as any,
      }),
    onSuccess: () => {
      setStep("done")
    },
    onError: handleError.bind(showErrorToast),
  })

  const handleNameSubmit = () => {
    if (!channelName.trim()) {
      showErrorToast("Please enter a channel name")
      return
    }
    if (channelId) {
      updateChannelMutation.mutate()
    } else {
      createChannelMutation.mutate()
    }
  }

  const handleSaveSort = () => {
    if (selectedSort === null) {
      showErrorToast("Please select a sort option")
      return
    }
    saveSortMutation.mutate(SORT_PRESETS[selectedSort].sortBy)
  }

  const isPending =
    createChannelMutation.isPending || updateChannelMutation.isPending

  return (
    <div className="flex flex-col items-center justify-center min-h-[80vh] px-4">
      <div className="w-full max-w-2xl">
        {/* Progress indicator */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {STEPS.map((stepName, index) => (
            <div key={stepName} className="flex items-center gap-2">
              <div
                className={`h-2 w-12 rounded-full transition-colors ${
                  STEPS.indexOf(step) >= index ? "bg-primary" : "bg-muted"
                }`}
              />
            </div>
          ))}
        </div>

        {/* Step 1: Name */}
        {step === "name" && (
          <div className="space-y-6 text-center">
            <h1 className="text-3xl font-bold">
              {channelId ? "Edit Channel Name" : "Create Your First Channel"}
            </h1>
            <p className="text-muted-foreground">
              A channel is an automatically updated curated playlist of shows
              and movies that you pick. Give it a name to get started.
            </p>
            <div className="max-w-sm mx-auto space-y-4">
              <Input
                value={channelName}
                onChange={(event) => setChannelName(event.target.value)}
                placeholder="My Channel"
                onKeyDown={(event) => {
                  if (event.key === "Enter") handleNameSubmit()
                }}
                autoFocus
              />
              <Button
                onClick={handleNameSubmit}
                disabled={isPending}
                className="w-full"
              >
                {isPending
                  ? channelId
                    ? "Updating..."
                    : "Creating..."
                  : channelId
                    ? "Update & Continue"
                    : "Create Channel"}
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </div>
        )}

        {/* Step 2: Add Shows */}
        {step === "shows" && channelId && (
          <AddShowsStep
            channelId={channelId}
            onDone={() => setStep("sort")}
            onBack={() => setStep("name")}
          />
        )}

        {/* Step 3: Sort */}
        {step === "sort" && (
          <div className="space-y-6">
            <div className="text-center">
              <h1 className="text-3xl font-bold">
                How Should Episodes Be Ordered?
              </h1>
              <p className="text-muted-foreground mt-2">
                Choose a default ordering for your channel.
              </p>
            </div>
            <div className="grid gap-3">
              {SORT_PRESETS.map((preset, index) => (
                <button
                  key={preset.label}
                  type="button"
                  className={`flex items-center gap-4 p-4 rounded-lg border text-left transition-colors ${
                    selectedSort === index
                      ? "border-primary bg-primary/5"
                      : "border-border hover:bg-accent/50"
                  }`}
                  onClick={() => setSelectedSort(index)}
                >
                  <div
                    className={`shrink-0 ${selectedSort === index ? "text-primary" : "text-muted-foreground"}`}
                  >
                    {preset.icon}
                  </div>
                  <div className="flex-1">
                    <p className="font-medium">{preset.label}</p>
                    <p className="text-sm text-muted-foreground">
                      {preset.description}
                    </p>
                  </div>
                  {selectedSort === index && (
                    <Check className="h-5 w-5 text-primary shrink-0" />
                  )}
                </button>
              ))}
            </div>
            <div className="flex justify-between">
              <Button
                variant="outline"
                onClick={() => setStep("shows")}
                size="lg"
              >
                <ArrowLeft className="h-4 w-4 mr-1" />
                Back
              </Button>
              <Button
                onClick={handleSaveSort}
                disabled={saveSortMutation.isPending || selectedSort === null}
                size="lg"
              >
                {saveSortMutation.isPending ? "Saving..." : "Save & Continue"}
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </div>
        )}

        {/* Step 4: Done */}
        {step === "done" && channelId && (
          <div className="space-y-8 text-center">
            <PartyPopper className="h-16 w-16 mx-auto text-primary" />
            <h1 className="text-3xl font-bold">Congratulations!</h1>
            <p className="text-muted-foreground text-lg">
              Your channel is set up and ready to go.
            </p>
            <p className="text-sm text-muted-foreground">
              It may take a couple of minutes for your shows to be imported.
            </p>
            <div className="flex justify-between">
              <Button
                variant="outline"
                onClick={() => setStep("sort")}
                size="lg"
              >
                <ArrowLeft className="h-4 w-4 mr-1" />
                Back
              </Button>
              <Button asChild size="lg">
                <Link to="/channels/$channelId" params={{ channelId }}>
                  View Your Channel
                  <ChevronRight className="h-4 w-4 ml-1" />
                </Link>
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
