// TODO: Validate
import { Link } from "@tanstack/react-router"
import {
  Filter,
  Layers,
  ListOrdered,
  MonitorPlay,
  Pencil,
  Plus,
  Radio,
  Rocket,
  Search,
  Shuffle,
  Tv,
} from "lucide-react"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"

function ChannelFieldDescriptions() {
  return (
    <ul className="list-disc list-inside ml-2 space-y-1 text-muted-foreground">
      <li>
        <strong className="text-foreground">Name</strong>: the display name for
        your channel
      </li>
      <li>
        <strong className="text-foreground">Channel Number</strong>: controls
        the order channels appear in on the channels page. You can even use
        negative numbers or decimals.
      </li>
      <li>
        <strong className="text-foreground">Public</strong>: when enabled,
        anyone with the link can view your channel. When disabled, only you can
        see it.
      </li>
      <li>
        <strong className="text-foreground">Default Order</strong>: a JSON
        string that sets the default sort and filter configuration. There is a
        special menu for editing the episode order, but you can also copy and
        paste a JSON string if you want to duplicate an existing sort order from
        one channel to another channel.
      </li>
    </ul>
  )
}

export function Dashboard() {
  return (
    <div className="max-w-4xl mx-auto space-y-10 px-4 py-8">
      {/* Hero */}
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground text-lg">
          Your home base for managing channels and discovering content
        </p>
      </div>

      {/* Main action cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Link
          to="/onboarding"
          className="group flex flex-col items-center gap-4 p-8 border rounded-xl hover:border-primary hover:bg-accent/30 transition-all"
        >
          <div className="h-14 w-14 rounded-full bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
            <Rocket className="h-7 w-7 text-primary" />
          </div>
          <div className="text-center">
            <h2 className="text-xl font-semibold">Create channel</h2>
            <p className="text-sm text-muted-foreground mt-1">
              Create a channel, add shows, and pick a sort order in a few quick
              steps
            </p>
          </div>
        </Link>

        <Link
          to="/channels"
          search={{ view: "public" }}
          className="group flex flex-col items-center gap-4 p-8 border rounded-xl hover:border-primary hover:bg-accent/30 transition-all"
        >
          <div className="h-14 w-14 rounded-full bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
            <Tv className="h-7 w-7 text-primary" />
          </div>
          <div className="text-center">
            <h2 className="text-xl font-semibold">Public Channels</h2>
            <p className="text-sm text-muted-foreground mt-1">
              Browse channels shared by other users for inspiration and ideas
            </p>
          </div>
        </Link>

        <Link
          to="/remote"
          className="group flex flex-col items-center gap-4 p-8 border rounded-xl hover:border-primary hover:bg-accent/30 transition-all"
        >
          <div className="h-14 w-14 rounded-full bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
            <Radio className="h-7 w-7 text-primary" />
          </div>
          <div className="text-center">
            <h2 className="text-xl font-semibold">Stream Channeler Remote</h2>
            <p className="text-sm text-muted-foreground mt-1">
              Play episodes back to back and queue shows for bulk import with a
              companion userscript
            </p>
          </div>
        </Link>
      </div>

      {/* User Manual */}
      <div id="user-manual" className="space-y-4 scroll-mt-8">
        <h2 className="text-2xl font-bold tracking-tight">User Manual</h2>

        <Accordion
          type="multiple"
          className="w-full"
          defaultValue={["create-channel"]}
        >
          {/* 1. Creating Channels */}
          <AccordionItem value="create-channel">
            <AccordionTrigger>
              <span className="flex items-center gap-2">
                <Plus className="h-4 w-4" />
                Creating Channels
              </span>
            </AccordionTrigger>
            <AccordionContent>
              <div className="space-y-3 text-sm">
                <p>
                  A channel is an automatically updated curated playlist of
                  shows and movies. You choose exactly what appears on it and
                  how it's sorted.
                </p>
                <ol className="list-decimal list-inside space-y-1.5 ml-2">
                  <li>
                    Go to the{" "}
                    <Link
                      to="/channels"
                      className="text-primary hover:underline"
                    >
                      Channels page
                    </Link>
                  </li>
                  <li>
                    Click <strong>Add Channel</strong>
                  </li>
                  <li>
                    Fill in the channel details:
                    <div className="ml-4 mt-1">
                      <ChannelFieldDescriptions />
                    </div>
                  </li>
                </ol>
              </div>
            </AccordionContent>
          </AccordionItem>

          {/* 2. Editing Channels */}
          <AccordionItem value="edit-channel">
            <AccordionTrigger>
              <span className="flex items-center gap-2">
                <Pencil className="h-4 w-4" />
                Editing Channels
              </span>
            </AccordionTrigger>
            <AccordionContent>
              <div className="space-y-3 text-sm">
                <p>
                  To edit an existing channel, click the pencil icon next to the
                  channel name on the{" "}
                  <Link to="/channels" className="text-primary hover:underline">
                    Channels page
                  </Link>
                  . You can change any of the following:
                </p>
                <ChannelFieldDescriptions />
              </div>
            </AccordionContent>
          </AccordionItem>

          {/* 3. Adding Shows */}
          <AccordionItem value="add-shows">
            <AccordionTrigger>
              <span className="flex items-center gap-2">
                <Search className="h-4 w-4" />
                Adding Shows
              </span>
            </AccordionTrigger>
            <AccordionContent>
              <div className="space-y-4 text-sm">
                <p>
                  There are two ways to add shows: <strong>Search</strong> and{" "}
                  <strong>Manual URLs</strong>.
                </p>

                <div className="border rounded-lg p-4 space-y-2">
                  <h4 className="font-semibold">Search (Recommended)</h4>
                  <p>
                    From the channel page, click <strong>Add Shows</strong> and
                    use the <strong>Search</strong> tab. Type a show name and
                    results will appear from JustWatch, covering 900+ streaming
                    services.
                  </p>
                  <p>
                    When you expand a result, you can{" "}
                    <strong>choose a specific source</strong> (like Netflix or
                    Hulu) or click <strong>Add All Sources</strong> to import
                    from every available provider. You can also type a custom
                    source name if the one you want isn't listed.
                  </p>
                  <p className="text-muted-foreground">
                    Selecting a specific source means episodes will link
                    directly to that streaming service's player.
                  </p>
                </div>

                <div className="border rounded-lg p-4 space-y-2">
                  <h4 className="font-semibold">Manual URLs</h4>
                  <p>
                    Switch to the <strong>Manual URLs</strong> tab to paste URLs
                    directly, one per line. This supports:
                  </p>
                  <ul className="list-disc list-inside ml-2 space-y-1">
                    <li>
                      <strong>JustWatch URLs</strong>: prepend the source name
                      before the URL (e.g.,{" "}
                      <code className="bg-muted px-1 rounded text-xs">
                        Hulu justwatch.com/us/tv-show/breaking-bad
                      </code>
                      )
                    </li>
                    <li>
                      <strong>YouTube</strong>: channel or playlist URLs
                      directly
                    </li>
                    <li>
                      <strong>Crunchyroll</strong>: series URLs directly
                    </li>
                  </ul>
                </div>
              </div>
            </AccordionContent>
          </AccordionItem>

          {/* 3. Sorting & Ordering */}
          <AccordionItem value="sorting">
            <AccordionTrigger>
              <span className="flex items-center gap-2">
                <ListOrdered className="h-4 w-4" />
                Sorting & Ordering
              </span>
            </AccordionTrigger>
            <AccordionContent>
              <div className="space-y-4 text-sm">
                <p>
                  Sorting controls the order episodes appear on your channel.
                  You can sort by any field (air date, episode number, show
                  name, duration, etc.) and stack multiple sort rules. The last
                  rule is the primary sort.
                </p>

                <h4 className="font-semibold">Sort Modes</h4>
                <p>
                  Each sort rule has a <strong>mode</strong> that changes how it
                  behaves:
                </p>

                <div className="space-y-3">
                  <div className="border rounded-lg p-3 space-y-1">
                    <div className="flex items-center gap-2 font-medium">
                      <ListOrdered className="h-4 w-4 text-primary" />
                      Normal
                    </div>
                    <p className="text-muted-foreground">
                      Standard sorting. Episodes are ordered by the chosen
                      field. All episodes from the same show will appear
                      together. Use this when you want a straightforward sort
                      like "newest first" or "alphabetical by show name."
                    </p>
                  </div>

                  <div className="border rounded-lg p-3 space-y-1">
                    <div className="flex items-center gap-2 font-medium">
                      <Shuffle className="h-4 w-4 text-primary" />
                      Interleave (Sequential / Random)
                    </div>
                    <p className="text-muted-foreground">
                      Spreads episodes from different shows across the list
                      instead of grouping them. Think of it like shuffling a
                      deck of cards: one episode from Show A, then one from Show
                      B, then Show C, and so on. <strong>Sequential</strong>{" "}
                      interleaves in a fixed order, while{" "}
                      <strong>Random</strong> shuffles the show order each time.
                      Great for a "TV channel" feel where you see variety
                      instead of marathoning one show.
                    </p>
                  </div>

                  <div className="border rounded-lg p-3 space-y-1">
                    <div className="flex items-center gap-2 font-medium">
                      <Layers className="h-4 w-4 text-primary" />
                      Show Group
                    </div>
                    <p className="text-muted-foreground">
                      Groups all episodes by show, then sorts the{" "}
                      <em>shows themselves</em> using an aggregate function
                      (sum, max, min, avg, count) on the chosen field. For
                      example, "recently aired + show group + max" puts shows
                      that have any recently aired episode first. Use this to
                      prioritize certain shows over others based on their
                      episodes' properties.
                    </p>
                  </div>
                </div>

                <div className="bg-muted/50 border rounded-lg p-3 text-muted-foreground">
                  <strong>Tip:</strong> Combine modes for powerful setups. For
                  example, use Show Group to put recently-aired shows first,
                  then Interleave to mix episodes between those shows, and
                  Normal to sort by episode number within each show.
                </div>
              </div>
            </AccordionContent>
          </AccordionItem>

          {/* 4. Filtering */}
          <AccordionItem value="filtering">
            <AccordionTrigger>
              <span className="flex items-center gap-2">
                <Filter className="h-4 w-4" />
                Filtering
              </span>
            </AccordionTrigger>
            <AccordionContent>
              <div className="space-y-3 text-sm">
                <p>
                  Filters let you narrow down which episodes appear on your
                  channel. Open <strong>Channel Options</strong> on any channel
                  to access filters.
                </p>
                <ul className="list-disc list-inside ml-2 space-y-1.5">
                  <li>
                    <strong>Hide Watched</strong>: only show episodes you
                    haven't seen yet
                  </li>
                  <li>
                    <strong>Hide Unwatched</strong>: only show episodes you've
                    already watched
                  </li>
                  <li>
                    <strong>Only Started Shows</strong>: only include shows
                    where you've watched at least one episode
                  </li>
                  <li>
                    <strong>Only New Shows</strong>: only include shows you
                    haven't started yet
                  </li>
                  <li>
                    <strong>Air Date Range</strong>: filter by when episodes
                    originally aired
                  </li>
                  <li>
                    <strong>Release Date Range</strong>: filter by streaming
                    release date
                  </li>
                  <li>
                    <strong>Duration Range</strong>: filter by episode length
                  </li>
                </ul>
                <p className="text-muted-foreground">
                  Click <strong>Save as Default</strong> to make your current
                  filter + sort configuration the default when opening the
                  channel. You can also bookmark the URL to save any
                  configuration.
                </p>
              </div>
            </AccordionContent>
          </AccordionItem>

          {/* 5. Watch History */}
          <AccordionItem value="watches">
            <AccordionTrigger>
              <span className="flex items-center gap-2">
                <MonitorPlay className="h-4 w-4" />
                Watch History
              </span>
            </AccordionTrigger>
            <AccordionContent>
              <div className="space-y-3 text-sm">
                <p>
                  When you click an episode to watch it, it's automatically
                  marked as watched. However, watches need to be{" "}
                  <strong>verified</strong> before watch-based filters apply
                  (like "Hide Watched").
                </p>
                <p>
                  You can verify watches from the episode card menu or from the{" "}
                  <Link to="/watches" className="text-primary hover:underline">
                    Watch History
                  </Link>{" "}
                  page. You can also import watch history from supported
                  services like YouTube and Crunchyroll.
                </p>
                <p className="text-muted-foreground">
                  Watch data powers sorting options like "Last Watched" and
                  filters like "Only Started Shows," making your channels
                  smarter over time.
                </p>
              </div>
            </AccordionContent>
          </AccordionItem>

          {/* 6. Additional Channels */}
          <AccordionItem value="additional-channels">
            <AccordionTrigger>
              <span className="flex items-center gap-2">
                <Layers className="h-4 w-4" />
                Combining Channels
              </span>
            </AccordionTrigger>
            <AccordionContent>
              <div className="space-y-3 text-sm">
                <p>
                  You can combine episodes from multiple channels into one view
                  using <strong>Additional Channels</strong>. This lets you
                  create a "super channel" that pulls from several smaller
                  channels without duplicating shows.
                </p>
                <p>
                  Each channel keeps its own whitelist/blacklist settings, so
                  episodes are filtered according to the channel they belong to.
                </p>
                <p className="text-muted-foreground">
                  Access this from <strong>Manage Additional Channels</strong>{" "}
                  on any channel page.
                </p>
              </div>
            </AccordionContent>
          </AccordionItem>

          {/* 7. Whitelist/Blacklist */}
          <AccordionItem value="whitelist">
            <AccordionTrigger>
              <span className="flex items-center gap-2">
                <Filter className="h-4 w-4" />
                Whitelist & Blacklist
              </span>
            </AccordionTrigger>
            <AccordionContent>
              <div className="space-y-3 text-sm">
                <p>
                  Each show in a channel can be in{" "}
                  <strong>Blacklist Mode</strong> (default) or{" "}
                  <strong>Whitelist Mode</strong>:
                </p>
                <ul className="list-disc list-inside ml-2 space-y-1.5">
                  <li>
                    <strong>Blacklist Mode</strong>: all episodes are included
                    by default. New episodes are automatically added. Mark
                    individual seasons or episodes to exclude them.
                  </li>
                  <li>
                    <strong>Whitelist Mode</strong>: no episodes are included by
                    default. New episodes are not automatically added. Mark
                    individual seasons or episodes to include them.
                  </li>
                </ul>
                <p className="text-muted-foreground">
                  Within a whitelisted season, you can exclude specific
                  episodes. Within a blacklisted season, you can include
                  specific episodes. This gives you fine-grained control over
                  exactly what appears on your channel.
                </p>
              </div>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </div>
    </div>
  )
}
