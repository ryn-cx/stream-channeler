// TODO: Validate
import { Check, Copy } from "lucide-react"
import { useState } from "react"

import type { SortOptionOutput, SourcePublic } from "@/client"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import useCustomToast from "@/hooks/useCustomToast"

interface AIBuilderPanelProps {
  sortOptions: SortOptionOutput[]
  sortSourceKeys: string[]
  channelSources: SourcePublic[]
  currentSettings: Record<string, unknown>
}

// TODO: Validate
function describeSortOptions(sortOptions: SortOptionOutput[]): string {
  const fieldDescriptions: Record<string, string> = {
    "episode.air_date": "the date the episode aired.",
    "episode.duration": "the episode's length in seconds.",
    "episode.episode_number":
      "the episode's number within its season. Specials are numbered 0.",
    "episode.episode_number_zero_last":
      "the episode's number within its season, with episode 0 (specials) placed after every other episode instead of first.",
    "episode.name": "the episode's name, alphabetically.",
    "episode.sort_order":
      "the order the streaming website lists the episode in.",
    "episode.sequential":
      "the episode's position within its season (by episode number, then website order). Use this to play a season in order.",
    "episode.sequential_zero_last":
      "like episode.sequential, but specials (episode 0) are placed last.",
    "episode.random":
      "a random value per episode, seeded by randomSeed. Shuffles episodes.",
    "episode.recently_aired":
      'whether the episode aired recently: 1 if it aired on or after the cutoff, 0 otherwise. The cutoff is set with "days" (days ago, default 7) or "recentlyAiredDate" (an absolute YYYY-MM-DD date). Use direction "descending" to put recent episodes first.',
    "episode.saved_order":
      "the episode's position in the order the channel owner saved by hand. Episodes not in the saved order sort last.",
    "episode.last_watched_completed":
      "when the viewer last finished watching the episode. Never-finished episodes come first when ascending and last when descending. Needs the viewer to be logged in.",
    "episode.last_watched_incomplete":
      'when the viewer last started but did not finish the episode. Never-started episodes come first when ascending and last when descending. Use direction "descending" to resume in-progress episodes first. Needs the viewer to be logged in.',
    "season.name": "the season's name, alphabetically.",
    "season.season_number":
      "the season's number within its title. Specials are season 0.",
    "season.season_number_zero_last":
      "the season's number, with season 0 (specials) placed after every other season instead of first.",
    "season.sort_order": "the order the streaming website lists the season in.",
    "season.sequential":
      "the season's position within its title (by season number, then website order). Use this to play a title's seasons in order.",
    "season.sequential_zero_last":
      "like season.sequential, but the specials season (season 0) is placed last.",
    "season.random":
      "a random value per season, seeded by randomSeed. Shuffles seasons.",
    "title.name": "the title's (show's or movie's) name, alphabetically.",
    "title.media_type": "the title's media type, such as tv or movie.",
    "title.episode_count":
      "how many episodes the title has in this channel. Ascending puts short shows first.",
    "title.started":
      '1 if the viewer has watched any episode of the title, 0 otherwise. Use direction "descending" to put shows the viewer has started first. Needs the viewer to be logged in.',
    "title.random":
      "a random value per title, seeded by randomSeed. Shuffles the titles while keeping every episode of a title sharing one value.",
    "source.key":
      'the name of the streaming website the episode comes from, alphabetically. Set "sourceKeys" to an ordered list of website names to put those websites first, in that order, and every other website after them.',
    "source.id":
      "the streaming website's internal id. Only useful to group episodes by website.",
    "plugin.key": "the name of the plugin that imported the episode.",
    "plugin.id":
      "the plugin's internal id. Only useful to group episodes by plugin.",
    "channel.id":
      "the sub-channel the episode was added through, for a channel that combines other channels. Only useful to group or interleave episodes by sub-channel.",
  }

  return sortOptions
    .map((option) => {
      const description =
        fieldDescriptions[`${option.model}.${option.field}`] ?? option.label
      const comparable = option.value_type
        ? ` Comparable as a ${option.value_type}.`
        : ""
      return `- model "${option.model}", field "${option.field}" (${option.label}): ${description}${comparable}`
    })
    .join("\n")
}

// TODO: Validate
function describeChannelSources(channelSources: SourcePublic[]): string {
  if (channelSources.length === 0) {
    return "This channel has no sources listed, so sourceIds cannot be used."
  }
  return channelSources
    .map((source) => `- "${source.key}": id ${source.id}`)
    .join("\n")
}

// TODO: Validate
function buildAIBuilderPrompt({
  request,
  sortOptions,
  sortSourceKeys,
  channelSources,
  currentSettings,
  currentUrl,
  baseUrl,
}: AIBuilderPanelProps & {
  request: string
  currentUrl: string
  baseUrl: string
}): string {
  return `You are configuring the episode order of a channel in Stream Channeler, an app that plays episodes of TV shows, movies and videos from streaming websites like a TV channel. A channel's order and filters are set entirely by the query parameters of its URL. Build a new URL for the channel that applies what the user describes below, starting from the channel's current settings.

# What the user wants

${request.trim()}

# The channel right now

Current URL: ${currentUrl}
Base URL (the channel page without any query parameters): ${baseUrl}

Current settings, decoded from the URL:
${JSON.stringify(currentSettings, null, 2)}

Keep a current setting unless the user's request replaces or contradicts it. The settings above already include everything the channel currently applies, so never add an "orderPresetId" parameter: it would replace every other setting.

# URL format

The URL is the base URL followed by "?" and the query parameters, joined with "&". Every parameter value is written as JSON and then percent-encoded:
- Numbers and booleans are written plainly: randomSeed=42, hideWatched=true
- Arrays and objects are written as JSON and percent-encoded: sortBy=%5B%7B%22model%22%3A%22title%22%2C...%7D%5D
- Plain strings such as dates and ids are written without quotes: minimumAirDateAbsolute=2020-01-01
- Leave a parameter out entirely when it is not used. Never write a parameter with an empty value, false, or 0, since those are the defaults.

# Filter parameters

- hideWatched (boolean): hide episodes the viewer has finished watching.
- hideUnwatched (boolean): hide episodes the viewer has never started.
- hidePartiallyWatched (boolean): hide episodes the viewer started but never finished.
- maximumWatchDateAbsolute (YYYY-MM-DD) or maximumWatchDateRelative (integer days ago): only used together with hideWatched. A finished watch older than this no longer counts, so episodes watched long ago come back as if unwatched. Use one form, not both.
- minimumAirDateAbsolute (YYYY-MM-DD) or minimumAirDateRelative (integer days ago): only keep episodes that aired on or after this date.
- maximumAirDateAbsolute (YYYY-MM-DD) or maximumAirDateRelative (integer days ago): only keep episodes that aired on or before this date. Use the absolute or the relative form for both air date bounds, not a mix.
- minimumDuration / maximumDuration (integer seconds): only keep episodes at least / at most this long.
- limit (integer 1 to 1000, default 1000): the most episodes to list.
- totalTitlesCount (integer): narrow the channel down to this many titles (shows or movies), taking the titles in the order their first episode appears in the sorted result.
- startedTitlesCount (integer): how many of those titles are ones the viewer has already started.
- newTitlesCount (integer): how many of those titles are ones the viewer has not started yet.
- sourceIds (array of source ids): limit episodes to these streaming websites.
- sourceIdsIsBlacklist (boolean): when true, sourceIds lists the websites to hide instead of the only ones to keep.
- randomSeed (integer): the seed every random value is derived from. The same seed gives the same shuffle. Keep the current seed unless the user asks for a different shuffle.

Every parameter about watches or started titles (hideWatched, hideUnwatched, hidePartiallyWatched, the maximumWatchDate parameters, the title counts, and the last_watched and started sort fields) only applies when the viewer is logged in and is ignored otherwise.

The channel's sources:
${describeChannelSources(channelSources)}

# Sorting

"sortBy" is an array of up to 10 sort keys, applied in order: the first key sorts everything, the second breaks ties within the first, and so on. Episodes still tied after every key fall back to being grouped by title. Each key is an object:

- "model" (required): one of "episode", "season", "title", "source", "plugin", "channel".
- "field" (required): a field of that model, from the list below. "random" is valid for every model.
- "direction" (required): "ascending" or "descending". Episodes with no value for the field sort last, except for the last_watched fields described below.
- "order" (required): how the key arranges the episodes:
  - "sequential": sort plainly by the value. Every episode with the first value, then every episode with the next value, and so on.
  - "interleave": group the episodes by this key's value and take turns between the groups: the first episode of every group (groups in this key's direction), then the second episode of every group, and so on. The keys after this one decide which episode is first, second and so on within each group. When an earlier key is set, the interleaving happens separately inside each of its groups.
  - "randomize": like "interleave", but the groups take their turns in a random order (seeded by randomSeed) instead of in the key's direction.
- "aggregation" (optional): "max", "min" or "avg". Only for model "episode". Instead of each episode's own value, every episode gets the max/min/average of that field across all the episodes of its title in this channel, so the key orders whole titles, for example by their newest air date. Use it with air_date, duration, episode_number, sort_order, last_watched_completed, last_watched_incomplete or recently_aired; "avg" only with number fields.
- "days" (optional integer) or "recentlyAiredDate" (optional YYYY-MM-DD): only for episode.recently_aired. Sets the cutoff described below.
- "sourceKeys" (optional array of website names): only for source.key. Puts those websites first, in the listed order.
- "fuzziness" (optional integer, 0 or more): loosens the key so an episode can drift up to this many places from where the key's value puts it, chosen at random by randomSeed. Useful to keep a rough order without being strictly in order.
- "comparison" (optional): only for episode fields marked as comparable below. Turns the key into a yes/no test: the value becomes 1 when the test passes and 0 when it does not. One of "greater_than", "greater_than_or_equal", "equal", "not_equal", "less_than_or_equal", "less_than", or "undefined" (passes when the episode has no value for the field). Use direction "descending" to put the episodes that pass first.
- "comparisonValue": required with every comparison except "undefined". A number for number fields. For date fields, either a number of days ago or a YYYY-MM-DD date.

The available sort fields:
${describeSortOptions(sortOptions)}

Website names usable in sourceKeys: ${sortSourceKeys.length > 0 ? sortSourceKeys.join(", ") : "none listed"}

# Examples of sortBy

Play every show from start to finish, with the shows in a random order:
[{"model":"title","field":"random","direction":"ascending","order":"sequential"},{"model":"season","field":"sequential","direction":"ascending","order":"sequential"},{"model":"episode","field":"sequential","direction":"ascending","order":"sequential"}]

Play like a TV channel, rotating between shows in a random rotation while each show progresses in order:
[{"model":"title","field":"random","direction":"ascending","order":"randomize"},{"model":"season","field":"sequential","direction":"ascending","order":"sequential"},{"model":"episode","field":"sequential","direction":"ascending","order":"sequential"}]

Resume in-progress episodes first, then rotate randomly between shows with random episodes:
[{"model":"episode","field":"last_watched_incomplete","direction":"descending","order":"sequential"},{"model":"title","field":"random","direction":"ascending","order":"randomize"},{"model":"episode","field":"random","direction":"ascending","order":"sequential"}]

Newest episodes first:
[{"model":"episode","field":"air_date","direction":"descending","order":"sequential"}]

Shows with a new episode in the last 14 days first, each show in order:
[{"model":"episode","field":"recently_aired","direction":"descending","order":"sequential","aggregation":"max","days":14},{"model":"title","field":"random","direction":"ascending","order":"sequential"},{"model":"season","field":"sequential","direction":"ascending","order":"sequential"},{"model":"episode","field":"sequential","direction":"ascending","order":"sequential"}]

# What cannot be done

Only the parameters and sort fields above exist. Anything else cannot be expressed in the URL, for example picking or ranking specific shows by name, filtering by genre, rating, cast or year of a show, weighting how often a show plays, or scheduling by time of day. When part of the request cannot be expressed, get as close as the options above allow and report what was dropped or approximated.

# How to answer

Reply with exactly this and nothing else:

URL: <the complete new URL>

Summary: <either "Every requested feature was incorporated." or a short list of each requested feature that was dropped or only approximated, with one line on why>

Settings: <one short line per sort key and filter used, saying what it does in plain words>
`
}

// TODO: Validate
export function AIBuilderPanel({
  sortOptions,
  sortSourceKeys,
  channelSources,
  currentSettings,
}: AIBuilderPanelProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [request, setRequest] = useState("")
  const [copied, setCopied] = useState(false)

  // TODO: Validate
  const onCopyQuery = async () => {
    const prompt = buildAIBuilderPrompt({
      request,
      sortOptions,
      sortSourceKeys,
      channelSources,
      currentSettings,
      currentUrl: window.location.href,
      baseUrl: `${window.location.origin}${window.location.pathname}`,
    })
    try {
      await navigator.clipboard.writeText(prompt)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
      showSuccessToast("Query copied to clipboard")
    } catch (error) {
      showErrorToast(`Could not copy: ${error}`)
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Describe the channel order you want, then copy the query into an AI. It
        replies with a URL for this channel with that order applied.
      </p>
      <div className="space-y-2">
        <Label htmlFor="ai-builder-request">Channel order</Label>
        <Textarea
          id="ai-builder-request"
          value={request}
          onChange={(event) => setRequest(event.target.value)}
          placeholder="Rotate between my shows in a random order, each show playing in order, and hide anything I've already watched."
          className="min-h-32 max-h-60 overflow-y-auto"
        />
      </div>
      <Button
        type="button"
        onClick={onCopyQuery}
        disabled={request.trim() === ""}
      >
        {copied ? <Check /> : <Copy />}
        Copy Query
      </Button>
    </div>
  )
}
