// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Link, useNavigate } from "@tanstack/react-router"
import { ArrowLeft, Check, ChevronRight, PartyPopper } from "lucide-react"
import { type ReactNode, useEffect, useState } from "react"
import "remark-github-blockquote-alert/alert.css"
import type { ChannelOutput, Visibility } from "@/client"
import { ChannelOrdersService, ChannelsService } from "@/client"
import { ManageShowsTabs } from "@/components/Channels/ChannelDetail/ManageShowsTabs"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import {
  VISIBILITY_OPTIONS,
  visibilityDescription,
  visibilityLabel,
} from "@/lib/visibility"
import { handleError } from "@/utils"

const TOTAL_STEPS = 4

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
  const [description, setDescription] = useState("")
  const [anonymous, setAnonymous] = useState(false)
  const { user } = useAuth()
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
          description: description.trim() === "" ? null : description.trim(),
          anonymous,
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
        <h1 className="text-3xl font-bold">Create A Channel</h1>
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
            <Label htmlFor="channel-description">Description</Label>
            <Textarea
              id="channel-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Optional"
            />
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
              {visibilityDescription(visibility)}
            </p>
          </div>
          <div className="flex items-start gap-3">
            <Checkbox
              id="channel-anonymous"
              checked={anonymous}
              onCheckedChange={(checked) => setAnonymous(checked === true)}
            />
            <div className="space-y-1 leading-none">
              <Label htmlFor="channel-anonymous">Publish anonymously</Label>
              <p className="text-sm text-muted-foreground">
                The creator of the channel will be listed as{" "}
                {anonymous ? "anonymous" : user?.username}.
              </p>
            </div>
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
  const [description, setDescription] = useState("")
  const [anonymous, setAnonymous] = useState(false)
  const [initialized, setInitialized] = useState(false)
  const { user } = useAuth()
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
      setDescription(channelQuery.data.description ?? "")
      setAnonymous(channelQuery.data.anonymous ?? false)
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
          description: description.trim() === "" ? null : description.trim(),
          anonymous,
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
            <Label htmlFor="channel-description">Description</Label>
            <Textarea
              id="channel-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Optional"
            />
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
              {visibilityDescription(visibility)}
            </p>
          </div>
          <div className="flex items-start gap-3">
            <Checkbox
              id="channel-anonymous"
              checked={anonymous}
              onCheckedChange={(checked) => setAnonymous(checked === true)}
            />
            <div className="space-y-1 leading-none">
              <Label htmlFor="channel-anonymous">Share Anonymously</Label>
              <p className="text-sm text-muted-foreground">
                The creator of the channel will be listed as{" "}
                {anonymous ? "Anonymous" : user?.username}.
              </p>
            </div>
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
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null)
  const { showErrorToast } = useCustomToast()
  const navigate = useNavigate()

  const { data: orders = [] } = useQuery({
    queryKey: ["channel-orders", "featured"],
    queryFn: () => ChannelOrdersService.getFeaturedChannelOrders(),
    refetchOnWindowFocus: false,
  })

  const saveSortMutation = useMutation({
    mutationFn: (orderPresetId: string) =>
      ChannelsService.updateChannelDefaultOrder({
        channelId,
        requestBody: { orderPresetId },
      }),
    onSuccess: (_data, orderPresetId) => {
      navigate({
        to: "/onboarding/$channelId/done",
        params: { channelId },
        search: { orderPresetId },
      })
    },
    onError: handleError.bind(showErrorToast),
  })

  const handleSave = () => {
    if (!selectedOrderId) {
      showErrorToast("Please select a sort option")
      return
    }
    saveSortMutation.mutate(selectedOrderId)
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
        {orders.length === 0 ? (
          <p className="text-center text-muted-foreground">
            No featured orders are available yet.
          </p>
        ) : (
          <div className="grid gap-3">
            {orders.map((order) => {
              const emoji = order.icon
              const label = order.name
              const isSelected = selectedOrderId === order.id
              return (
                <button
                  key={order.id}
                  type="button"
                  className={`flex items-center gap-4 p-4 rounded-lg border text-left transition-colors ${
                    isSelected
                      ? "border-primary bg-primary/5"
                      : "border-border hover:bg-accent/50"
                  }`}
                  onClick={() => setSelectedOrderId(order.id)}
                >
                  {emoji && (
                    <div className="shrink-0 text-4xl leading-none">
                      {emoji}
                    </div>
                  )}
                  <div className="flex-1">
                    <p className="font-medium">{label || "Untitled order"}</p>
                    {order.description && (
                      <p className="text-sm text-muted-foreground">
                        {order.description}
                      </p>
                    )}
                  </div>
                  {isSelected && (
                    <Check className="h-5 w-5 text-primary shrink-0" />
                  )}
                </button>
              )
            })}
          </div>
        )}
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
            disabled={saveSortMutation.isPending || selectedOrderId === null}
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
  orderPresetId,
}: {
  channelId: string
  orderPresetId?: string
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
              search={orderPresetId ? { orderPresetId } : undefined}
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
