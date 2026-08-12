// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Link, useNavigate } from "@tanstack/react-router"
import { ArrowLeft, Check, ChevronRight, PartyPopper } from "lucide-react"
import { type ReactNode, useEffect, useState } from "react"
import "remark-github-blockquote-alert/alert.css"
import type { ChannelOutput, Visibility } from "@/client"
import { ChannelOrdersService, ChannelsService, UsersService } from "@/client"
import { ManageShowsTabs } from "@/components/Channels/ChannelDetail/ManageShowsTabs"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
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

// TODO: Validate
function OnboardingShell({
  currentStep,
  children,
}: {
  currentStep: number
  children: ReactNode
}) {
  return (
    <div className="flex flex-col items-center px-4 py-8">
      <div className="w-full max-w-2xl">
        <div className="flex items-center justify-center gap-2 mb-8">
          {Array.from({ length: TOTAL_STEPS }).map((_, index) => (
            <div
              key={index}
              className={`h-2 w-12 rounded-full transition-colors ${
                currentStep >= index ? "bg-primary" : "bg-foreground/30"
              }`}
            />
          ))}
        </div>
        {children}
      </div>
    </div>
  )
}

// TODO: Validate
function useChannelForm() {
  const [channelName, setChannelName] = useState("")
  const [channelNumber, setChannelNumber] = useState<string>("")
  const [visibility, setVisibility] = useState<Visibility>("private")
  const [description, setDescription] = useState("")
  const [anonymous, setAnonymous] = useState(false)
  const [score, setScore] = useState("0")
  const [ownerId, setOwnerId] = useState<string | null>(null)
  const { user } = useAuth()
  const isAdmin = user?.is_superuser === true

  const usersQuery = useQuery({
    queryKey: ["users"],
    queryFn: () => UsersService.readUsers(),
    enabled: isAdmin,
  })
  const users = usersQuery.data?.data ?? []

  // The channel belongs to whoever is making it until an admin says otherwise.
  useEffect(() => {
    if (user && ownerId === null) {
      setOwnerId(user.id)
    }
  }, [user, ownerId])

  const owner = users.find((candidate) => candidate.id === ownerId)

  return {
    channelName,
    setChannelName,
    channelNumber,
    setChannelNumber,
    visibility,
    setVisibility,
    description,
    setDescription,
    anonymous,
    setAnonymous,
    score,
    setScore,
    ownerId,
    setOwnerId,
    isAdmin,
    users,
    owner,
    ownerName: (isAdmin ? owner?.username : undefined) ?? user?.username,
    channelInput: {
      name: channelName.trim(),
      channel_number:
        channelNumber === "" ? null : Number.parseFloat(channelNumber),
      visibility,
      description: description.trim() === "" ? null : description.trim(),
      anonymous,
    },
    adminInput: {
      score: score === "" ? 0 : Number.parseInt(score, 10),
      user_id: ownerId,
    },
  }
}

type ChannelFormState = ReturnType<typeof useChannelForm>

// TODO: Validate
function isChannelFormValid(
  form: ChannelFormState,
  showErrorToast: (message: string) => void,
) {
  if (!form.channelName.trim()) {
    showErrorToast("Please enter a channel name")
    return false
  }
  if (form.isAdmin && !form.ownerId) {
    showErrorToast("Please pick the user the channel is for")
    return false
  }
  if (
    form.isAdmin &&
    form.score !== "" &&
    !Number.isInteger(Number(form.score))
  ) {
    showErrorToast("Score must be a whole number")
    return false
  }
  return true
}

// TODO: Validate
function ChannelFormFields({
  form,
  onSubmit,
  isPending,
  submitLabel,
  pendingLabel,
}: {
  form: ChannelFormState
  onSubmit: () => void
  isPending: boolean
  submitLabel: string
  pendingLabel: string
}) {
  const [ownerPickerOpen, setOwnerPickerOpen] = useState(false)

  return (
    <div className="max-w-sm mx-auto space-y-4 text-left">
      <div className="space-y-1.5">
        <Label htmlFor="channel-name">Name</Label>
        <Input
          id="channel-name"
          value={form.channelName}
          onChange={(event) => form.setChannelName(event.target.value)}
          placeholder="My Channel"
          onKeyDown={(event) => {
            if (event.key === "Enter") onSubmit()
          }}
          autoFocus
        />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="channel-number">Channel Number</Label>
        <Input
          id="channel-number"
          type="number"
          value={form.channelNumber}
          onChange={(event) => form.setChannelNumber(event.target.value)}
          placeholder="Optional"
        />
        <p className="text-sm text-muted-foreground">
          Used to determine the order channels are displayed in. Lower numbers
          appear first. Leave blank to let it sort by name.
        </p>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="channel-description">Description</Label>
        <Textarea
          id="channel-description"
          value={form.description}
          onChange={(event) => form.setDescription(event.target.value)}
          placeholder="Optional"
        />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="channel-visibility">Visibility</Label>
        <Select
          value={form.visibility}
          onValueChange={(value) => form.setVisibility(value as Visibility)}
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
          {visibilityDescription(form.visibility)}
        </p>
      </div>
      <div className="flex items-start gap-3">
        <Checkbox
          id="channel-anonymous"
          checked={form.anonymous}
          onCheckedChange={(checked) => form.setAnonymous(checked === true)}
        />
        <div className="space-y-1 leading-none">
          <Label htmlFor="channel-anonymous">Publish anonymously</Label>
          <p className="text-sm text-muted-foreground">
            The creator of the channel will be listed as{" "}
            {form.anonymous ? "anonymous" : form.ownerName}.
          </p>
        </div>
      </div>
      {form.isAdmin && (
        <Accordion
          type="single"
          collapsible
          className="rounded-md border border-dashed border-destructive/40 bg-destructive/10 px-4 dark:bg-destructive/25"
        >
          <AccordionItem value="admin-options" className="border-b-0">
            <AccordionTrigger className="text-sm font-medium text-destructive [&>svg]:text-destructive/70">
              Admin options
            </AccordionTrigger>
            <AccordionContent className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="channel-owner">Owner</Label>
                <Popover
                  open={ownerPickerOpen}
                  onOpenChange={setOwnerPickerOpen}
                >
                  <PopoverTrigger asChild>
                    <Button
                      id="channel-owner"
                      variant="outline"
                      role="combobox"
                      aria-expanded={ownerPickerOpen}
                      className="w-full justify-start font-normal"
                    >
                      {form.owner?.username ?? "Select a user..."}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent
                    className="w-[--radix-popover-trigger-width] p-0"
                    align="start"
                  >
                    <Command>
                      <CommandInput placeholder="Filter users..." />
                      <CommandList>
                        <CommandEmpty>No users found.</CommandEmpty>
                        <CommandGroup>
                          {form.users.map((candidate) => (
                            <CommandItem
                              key={candidate.id}
                              value={candidate.username}
                              keywords={[candidate.email, candidate.id]}
                              onSelect={() => {
                                form.setOwnerId(candidate.id)
                                setOwnerPickerOpen(false)
                              }}
                            >
                              <Check
                                className={`h-4 w-4 mr-2 ${
                                  candidate.id === form.ownerId
                                    ? "opacity-100"
                                    : "opacity-0"
                                }`}
                              />
                              <span>{candidate.username}</span>
                              <span className="ml-auto text-xs text-muted-foreground">
                                {candidate.email}
                              </span>
                            </CommandItem>
                          ))}
                        </CommandGroup>
                      </CommandList>
                    </Command>
                  </PopoverContent>
                </Popover>
                <p className="text-sm text-muted-foreground">
                  The user the channel belongs to.
                </p>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="channel-score">Score</Label>
                <Input
                  id="channel-score"
                  type="number"
                  value={form.score}
                  onChange={(event) => form.setScore(event.target.value)}
                  placeholder="0"
                />
                <p className="text-sm text-muted-foreground">
                  Higher scored channels are shown first on the public list.
                </p>
              </div>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      )}
      <Button onClick={onSubmit} disabled={isPending} className="w-full">
        {isPending ? pendingLabel : submitLabel}
        <ChevronRight className="h-4 w-4 ml-1" />
      </Button>
    </div>
  )
}

// TODO: Validate
export function OnboardingCreateName() {
  const form = useChannelForm()
  const { showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const createChannelMutation = useMutation({
    mutationFn: () =>
      form.isAdmin && form.ownerId
        ? ChannelsService.adminCreateChannel({
            requestBody: {
              ...form.channelInput,
              ...form.adminInput,
              user_id: form.ownerId,
            },
          })
        : ChannelsService.createChannel({ requestBody: form.channelInput }),
    onSuccess: (channel: ChannelOutput) => {
      queryClient.invalidateQueries({ queryKey: ["channels"] })
      navigate({
        to: "/onboarding/$channelId/shows",
        params: { channelId: channel.id },
      })
    },
    onError: handleError.bind(showErrorToast),
  })

  // TODO: Validate
  const handleSubmit = () => {
    if (!isChannelFormValid(form, showErrorToast)) {
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
        <ChannelFormFields
          form={form}
          onSubmit={handleSubmit}
          isPending={createChannelMutation.isPending}
          submitLabel="Create Channel"
          pendingLabel="Creating..."
        />
      </div>
    </OnboardingShell>
  )
}

// TODO: Validate
export function OnboardingEditName({ channelId }: { channelId: string }) {
  const form = useChannelForm()
  const [initialized, setInitialized] = useState(false)
  const { showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const channelQuery = useQuery({
    queryKey: ["channels", channelId],
    queryFn: () => ChannelsService.getChannel({ channelId }),
  })

  const channel = channelQuery.data
  const {
    setChannelName,
    setChannelNumber,
    setVisibility,
    setDescription,
    setAnonymous,
    setScore,
    setOwnerId,
  } = form

  useEffect(() => {
    if (channel && !initialized) {
      setChannelName(channel.name ?? "")
      setChannelNumber(
        channel.channel_number == null ? "" : String(channel.channel_number),
      )
      setVisibility(channel.visibility ?? "private")
      setDescription(channel.description ?? "")
      setAnonymous(channel.anonymous ?? false)
      setScore(String(channel.score ?? 0))
      // An anonymous channel redacts its owner from everyone but an admin, and
      // an admin is the only viewer the owner field is shown to anyway.
      if (channel.user_id) {
        setOwnerId(channel.user_id)
      }
      setInitialized(true)
    }
  }, [
    channel,
    initialized,
    setChannelName,
    setChannelNumber,
    setVisibility,
    setDescription,
    setAnonymous,
    setScore,
    setOwnerId,
  ])

  const updateChannelMutation = useMutation({
    mutationFn: () =>
      form.isAdmin
        ? ChannelsService.adminUpdateChannel({
            channelId,
            requestBody: { ...form.channelInput, ...form.adminInput },
          })
        : ChannelsService.updateChannel({
            channelId,
            requestBody: form.channelInput,
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

  // TODO: Validate
  const handleSubmit = () => {
    if (!isChannelFormValid(form, showErrorToast)) {
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
        <ChannelFormFields
          form={form}
          onSubmit={handleSubmit}
          isPending={updateChannelMutation.isPending}
          submitLabel="Update & Continue"
          pendingLabel="Updating..."
        />
      </div>
    </OnboardingShell>
  )
}

// TODO: Validate
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

        <div className="flex flex-wrap justify-between gap-3">
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

// TODO: Validate
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

  // TODO: Validate
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

// TODO: Validate
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
