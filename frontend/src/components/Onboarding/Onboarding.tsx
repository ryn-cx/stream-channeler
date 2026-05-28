// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Link, useNavigate } from "@tanstack/react-router"
import {
  ArrowLeft,
  Check,
  Cherry,
  ChevronRight,
  Dice5,
  ListOrdered,
  PartyPopper,
  Waves,
} from "lucide-react"
import { type ReactNode, useEffect, useState } from "react"
import "remark-github-blockquote-alert/alert.css"
import type { ChannelOutput, SortKeyInput, Visibility } from "@/client"
import { ChannelsService } from "@/client"
import { ManageShowsTabs } from "@/components/Channels/ChannelDetail/ManageShowsTabs"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import useCustomToast from "@/hooks/useCustomToast"
import { VISIBILITY_OPTIONS, visibilityLabel } from "@/lib/visibility"
import { handleError } from "@/utils"

const TOTAL_STEPS = 4

interface SortPreset {
  label: string
  description: string
  icon: ReactNode
  sortBy: SortKeyInput[]
}

function sortKey(
  modelField: `${SortKeyInput["model"]}.${string}`,
  direction: SortKeyInput["direction"],
  order: NonNullable<SortKeyInput["order"]> = "sequential",
): SortKeyInput {
  const [model, field] = modelField.split(".") as [
    SortKeyInput["model"],
    string,
  ]
  return { model, field, direction, order }
}

const SORT_PRESETS: SortPreset[] = [
  {
    label: "Roll The Dice",
    description: "The episode order is completely random",
    icon: <Dice5 className="h-10 w-10" />,
    sortBy: [sortKey("episode.random", "ascending")],
  },
  {
    label: "Channel Surfing",
    description:
      "Episodes play in order within each show, but show order is random",
    icon: <Waves className="h-10 w-10" />,
    sortBy: [
      sortKey("season.sequential", "ascending"),
      sortKey("episode.sequential", "ascending"),
      sortKey("episode.id", "ascending", "randomize"),
    ],
  },
  {
    label: "Fresh Picks",
    description: "Most recently aired episodes appear first",
    icon: <Cherry className="h-10 w-10" />,
    sortBy: [sortKey("episode.air_date", "descending")],
  },
  {
    label: "Marathon Mode",
    description:
      "All episodes of one show play in order before moving to the next show",
    icon: <ListOrdered className="h-10 w-10" />,
    sortBy: [
      sortKey("show.name", "ascending"),
      sortKey("season.season_number", "ascending"),
      sortKey("episode.episode_number", "ascending"),
    ],
  },
]

function OnboardingShell({
  currentStep,
  children,
}: {
  currentStep: number
  children: ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[80vh] px-4">
      <div className="w-full max-w-2xl">
        <div className="flex items-center justify-center gap-2 mb-8">
          {Array.from({ length: TOTAL_STEPS }).map((_, index) => (
            <div
              key={index}
              className={`h-2 w-12 rounded-full transition-colors ${
                currentStep >= index ? "bg-primary" : "bg-muted"
              }`}
            />
          ))}
        </div>
        {children}
      </div>
    </div>
  )
}

export function OnboardingCreateName() {
  const [channelName, setChannelName] = useState("")
  const [channelNumber, setChannelNumber] = useState<string>("")
  const [visibility, setVisibility] = useState<Visibility>("private")
  const { showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const createChannelMutation = useMutation({
    mutationFn: () =>
      ChannelsService.createChannel({
        requestBody: {
          name: channelName.trim(),
          channel_number:
            channelNumber === "" ? null : Number.parseFloat(channelNumber),
          visibility,
        },
      }),
    onSuccess: (channel: ChannelOutput) => {
      queryClient.invalidateQueries({ queryKey: ["channels"] })
      navigate({
        to: "/onboarding/$channelId/shows",
        params: { channelId: channel.id },
      })
    },
    onError: handleError.bind(showErrorToast),
  })

  const handleSubmit = () => {
    if (!channelName.trim()) {
      showErrorToast("Please enter a channel name")
      return
    }
    createChannelMutation.mutate()
  }

  return (
    <OnboardingShell currentStep={0}>
      <div className="space-y-6 text-center">
        <h1 className="text-3xl font-bold">Create Your First Channel</h1>
        <p className="text-muted-foreground">
          A channel is an automatically updated curated playlist of shows and
          movies that you pick. Give it a name to get started.
        </p>
        <div className="max-w-sm mx-auto space-y-4 text-left">
          <div className="space-y-1.5">
            <Label htmlFor="channel-name">Name</Label>
            <Input
              id="channel-name"
              value={channelName}
              onChange={(event) => setChannelName(event.target.value)}
              placeholder="My Channel"
              onKeyDown={(event) => {
                if (event.key === "Enter") handleSubmit()
              }}
              autoFocus
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="channel-number">Channel Number</Label>
            <Input
              id="channel-number"
              type="number"
              value={channelNumber}
              onChange={(event) => setChannelNumber(event.target.value)}
              placeholder="Optional"
            />
            <p className="text-sm text-muted-foreground">
              Used to determine the order channels are displayed in. Lower
              numbers appear first. Leave blank to let it sort by name.
            </p>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="channel-visibility">Visibility</Label>
            <Select
              value={visibility}
              onValueChange={(value) => setVisibility(value as Visibility)}
            >
              <SelectTrigger id="channel-visibility">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {VISIBILITY_OPTIONS.map((option) => (
                  <SelectItem key={option} value={option}>
                    {visibilityLabel(option)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-sm text-muted-foreground">
              Public channels are listed for anyone. Unlisted channels are only
              accessible via direct link. Private channels are only visible to
              you.
            </p>
          </div>
          <Button
            onClick={handleSubmit}
            disabled={createChannelMutation.isPending}
            className="w-full"
          >
            {createChannelMutation.isPending ? "Creating..." : "Create Channel"}
            <ChevronRight className="h-4 w-4 ml-1" />
          </Button>
        </div>
      </div>
    </OnboardingShell>
  )
}

export function OnboardingEditName({ channelId }: { channelId: string }) {
  const [channelName, setChannelName] = useState("")
  const [channelNumber, setChannelNumber] = useState<string>("")
  const [visibility, setVisibility] = useState<Visibility>("private")
  const [initialized, setInitialized] = useState(false)
  const { showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const channelQuery = useQuery({
    queryKey: ["channels", channelId],
    queryFn: () => ChannelsService.getChannel({ channelId }),
  })

  useEffect(() => {
    if (channelQuery.data && !initialized) {
      setChannelName(channelQuery.data.name ?? "")
      setChannelNumber(
        channelQuery.data.channel_number == null
          ? ""
          : String(channelQuery.data.channel_number),
      )
      setVisibility(channelQuery.data.visibility ?? "private")
      setInitialized(true)
    }
  }, [channelQuery.data, initialized])

  const updateChannelMutation = useMutation({
    mutationFn: () =>
      ChannelsService.updateChannel({
        channelId,
        requestBody: {
          name: channelName.trim(),
          channel_number:
            channelNumber === "" ? null : Number.parseFloat(channelNumber),
          visibility,
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["channels"] })
      navigate({
        to: "/onboarding/$channelId/shows",
        params: { channelId },
      })
    },
    onError: handleError.bind(showErrorToast),
  })

  const handleSubmit = () => {
    if (!channelName.trim()) {
      showErrorToast("Please enter a channel name")
      return
    }
    updateChannelMutation.mutate()
  }

  return (
    <OnboardingShell currentStep={0}>
      <div className="space-y-6 text-center">
        <h1 className="text-3xl font-bold">Edit Channel</h1>
        <p className="text-muted-foreground">
          Adjust your channel settings before continuing.
        </p>
        <div className="max-w-sm mx-auto space-y-4 text-left">
          <div className="space-y-1.5">
            <Label htmlFor="channel-name">Name</Label>
            <Input
              id="channel-name"
              value={channelName}
              onChange={(event) => setChannelName(event.target.value)}
              placeholder="My Channel"
              onKeyDown={(event) => {
                if (event.key === "Enter") handleSubmit()
              }}
              autoFocus
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="channel-number">Channel Number</Label>
            <Input
              id="channel-number"
              type="number"
              value={channelNumber}
              onChange={(event) => setChannelNumber(event.target.value)}
              placeholder="Optional"
            />
            <p className="text-sm text-muted-foreground">
              Used to determine the order channels are displayed in. Lower
              numbers appear first. Leave blank to let it sort by name.
            </p>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="channel-visibility">Visibility</Label>
            <Select
              value={visibility}
              onValueChange={(value) => setVisibility(value as Visibility)}
            >
              <SelectTrigger id="channel-visibility">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {VISIBILITY_OPTIONS.map((option) => (
                  <SelectItem key={option} value={option}>
                    {visibilityLabel(option)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-sm text-muted-foreground">
              Public channels are listed for anyone. Unlisted channels are only
              accessible via direct link. Private channels are only visible to
              you.
            </p>
          </div>
          <Button
            onClick={handleSubmit}
            disabled={updateChannelMutation.isPending}
            className="w-full"
          >
            {updateChannelMutation.isPending
              ? "Updating..."
              : "Update & Continue"}
            <ChevronRight className="h-4 w-4 ml-1" />
          </Button>
        </div>
      </div>
    </OnboardingShell>
  )
}

export function OnboardingShows({ channelId }: { channelId: string }) {
  const navigate = useNavigate()

  return (
    <OnboardingShell currentStep={1}>
      <div className="space-y-6">
        <div className="text-center space-y-3">
          <h1 className="text-3xl font-bold">Add Shows</h1>
          <p className="text-muted-foreground">
            Search, import, and manage shows in your channel.
          </p>
        </div>

        <ManageShowsTabs channelId={channelId} queueRefetchInterval={5000} />

        <div className="flex justify-between">
          <Button
            variant="outline"
            size="lg"
            onClick={() =>
              navigate({
                to: "/onboarding/$channelId/name",
                params: { channelId },
              })
            }
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back
          </Button>
          <Button
            size="lg"
            onClick={() =>
              navigate({
                to: "/onboarding/$channelId/sort",
                params: { channelId },
              })
            }
          >
            Continue
            <ChevronRight className="h-4 w-4 ml-1" />
          </Button>
        </div>
      </div>
    </OnboardingShell>
  )
}

export function OnboardingSort({ channelId }: { channelId: string }) {
  const [selectedSort, setSelectedSort] = useState<number | null>(null)
  const { showErrorToast } = useCustomToast()
  const navigate = useNavigate()

  const saveSortMutation = useMutation({
    mutationFn: (sortBy: SortKeyInput[]) =>
      ChannelsService.updateChannelDefaultOrder({
        channelId,
        requestBody: { sortBy } as any,
      }),
    onSuccess: (_data, sortBy) => {
      navigate({
        to: "/onboarding/$channelId/done",
        params: { channelId },
        search: { sortBy },
      })
    },
    onError: handleError.bind(showErrorToast),
  })

  const handleSave = () => {
    if (selectedSort === null) {
      showErrorToast("Please select a sort option")
      return
    }
    saveSortMutation.mutate(SORT_PRESETS[selectedSort].sortBy)
  }

  return (
    <OnboardingShell currentStep={2}>
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
            size="lg"
            onClick={() =>
              navigate({
                to: "/onboarding/$channelId/shows",
                params: { channelId },
              })
            }
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back
          </Button>
          <Button
            size="lg"
            onClick={handleSave}
            disabled={saveSortMutation.isPending || selectedSort === null}
          >
            {saveSortMutation.isPending ? "Saving..." : "Save & Continue"}
            <ChevronRight className="h-4 w-4 ml-1" />
          </Button>
        </div>
      </div>
    </OnboardingShell>
  )
}

export function OnboardingDone({
  channelId,
  sortBy,
}: {
  channelId: string
  sortBy?: SortKeyInput[]
}) {
  const navigate = useNavigate()

  return (
    <OnboardingShell currentStep={3}>
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
            size="lg"
            onClick={() =>
              navigate({
                to: "/onboarding/$channelId/sort",
                params: { channelId },
              })
            }
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back
          </Button>
          <Button asChild size="lg">
            <Link
              to="/channels/$channelId"
              params={{ channelId }}
              search={sortBy ? { sortBy } : undefined}
            >
              View Your Channel
              <ChevronRight className="h-4 w-4 ml-1" />
            </Link>
          </Button>
        </div>
      </div>
    </OnboardingShell>
  )
}
