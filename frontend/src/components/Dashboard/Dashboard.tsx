// TODO: Validate
import { Link } from "@tanstack/react-router"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"

const JUSTWATCH_SUPPORTED_SERVICES = [
  "A&E",
  "A&E Crime Central Apple TV Channel",
  "Acaciatv Amazon Channel",
  "Acorn TV",
  "Acorn TV Apple TV",
  "AcornTV Amazon Channel",
  "AD tv",
  "Adult Swim",
  "Adultswim Amazon Channel",
  "AeroCinema Amazon Channel",
  "aha",
  "Alchemiya Amazon Channel",
  "All warrior network Amazon Channel",
  "ALLBLK",
  "ALLBLK Amazon channel",
  "ALLBLK Apple TV channel",
  "Amazon Prime Video",
  "Amazon Prime Video Free with Ads",
  "Amazon Prime Video with Ads",
  "Amazon Video",
  "AMC",
  "AMC Plus Apple TV Channel",
  "AMC Theatres",
  "AMC+",
  "AMC+ Amazon Channel",
  "AMC+ Roku Premium Channel",
  "Amebatv Amazon Channel",
  "Angel Studios",
  "Animal Planet",
  "Apple TV",
  "Apple TV Amazon Channel",
  "ARROW",
  "Artflix",
  "AsianCrush",
  "Aspire TV Amazon Channel",
  "Atom Tickets",
  "B&B Theatres",
  "Baeble Amazon Channel",
  "BBC America",
  "BBC Select Apple Tv channel",
  "BeFit Amazon Channel",
  "Best of British Tv Amazon Channel",
  "Best tv ever Amazon Channel",
  "Best Westerns Ever Amazon Channel",
  "BET+ Apple TV channel",
  "Bet+ Amazon Channel",
  "BFI Player Amazon Channel",
  "Bloodstream",
  "BongFlix Amazon Channel",
  "Bravo TV",
  "BritBox",
  "BritBox Amazon Channel",
  "Britbox Apple TV Channel",
  "Broadway HD Amazon Channel",
  "BroadwayHD",
  "Brown Sugar Amazon Channel",
  "BYUtv",
  "CaixaForum+",
  "Carnegie Hall+ Amazon Channel",
  "Carnegie Hall+ Apple TV Channel",
  "Cartoon Network Amazon Channel",
  "Chai Flicks",
  "Cinemark",
  "Cinemax Amazon Channel",
  "Cinemax Apple TV Channel",
  "Cinepolis Cinemas",
  "Cineverse",
  "Cineverse LiveTV",
  "Cocina ON Amazon Channel",
  "Cohen Media Amazon Channel",
  "Criterion Channel",
  "Crunchyroll Amazon Channel",
  "Cultpix",
  "Curiosity Stream",
  "CuriosityStream Apple TV Channel",
  "Daily Burn Amazon Channel",
  "dAnime Amazon Channel",
  "Daring Docs Amazon Channel",
  "Darkroom",
  "Dekkoo",
  "Dekkoo Amazon Channel",
  "Demand Africa Amazon Channel",
  "Destiny Image TV Amazon Channel",
  "Discovery",
  "Discovery +",
  "Discovery+ Amazon Channel",
  "Disney Plus",
  "DisneyNOW",
  "DistroTV",
  "DocAlliance Films",
  "DocCom Amazon Channel",
  "DOCSVILLE",
  "DocuramaFilms Amazon Channel",
  "Doki Amazon Channel",
  "Dove Amazon Channel",
  "Dox Amazon Channel",
  "Dreamscape Kids Amazon Channel",
  "DreamWorksTV Amazon Channel",
  "Echoboom Amazon Channel",
  "Eros Now Select Apple TV Channel",
  "Eternal Family",
  "Eventive",
  "Fandango",
  "Fandango At Home",
  "Fandango at Home Free",
  "Fandor",
  "Fandor Amazon Channel",
  "Fawesome",
  "Fear Factory Amazon Channel",
  "FidoTV Channel Amazon Channel",
  "Film Movement Plus",
  "Film Movement Plus Amazon Channel",
  "FilmBox Live Amazon Channel",
  "FilmBox+",
  "Filmzie",
  "Fitfusion Amazon Channel",
  "Flix Premiere",
  "FlixFling",
  "FlixHouse",
  "FlixLatino Amazon Channel",
  "Food Matters Amazon Channel",
  "Food Network",
  "FOUND TV",
  "Fox",
  "FOX One",
  "FOX One Amazon Channel",
  "France Channel Amazon Channel",
  "Free Movies Plus",
  "Freeform",
  "fuboTV",
  "FUEL TV+ Amazon Channel",
  "Full Moon Amazon Channel",
  "Fuse+ Amazon Channel",
  "FXNow",
  "FYI Network",
  "Gaia Amazon Channel",
  "Gaiam TV Yoga & Fit",
  "GlewedTV",
  "Google Play Movies",
  "Great American Pure Flix Amazon Channel",
  "Green Planet Stream Amazon Channel",
  "Grokker Yoga & Fitness Amazon Channel",
  "GuideDoc",
  "Hallmark TV Amazon Channel",
  "Hallmark+ Amazon Channel",
  "Hallmark+ Apple TV Channel",
  "Harkins Theatres",
  "HBO Max",
  "HBO Max Amazon Channel",
  "HBO Max CNN Amazon Channel",
  "Here TV",
  "Here TV Amazon Channel",
  "HGTV",
  "Hidive Amazon Channel",
  "History",
  "History Vault",
  "HISTORY Vault Amazon Channel",
  "HISTORY Vault Apple TV Channel",
  "Hi-YAH",
  "Hi-YAH Amazon Channel",
  "Hoichoi",
  "Hoopla",
  "Hopster Amazon Channel",
  "Hulu",
  "IFC Films Unlimited Apple TV Channel",
  "Indie Club Amazon Channel",
  "IndieFlix",
  "IndieFlix Shorts Amazon Channel",
  "IndiePix Unlimited Amazon Channel",
  "Investigation Discovery",
  "iQIYI",
  "ITV Amazon Channel",
  "Jolt Film",
  "JustWatchTV",
  "KableOne",
  "Kanopy",
  "Kartoon Channel Amazon Channel",
  "Kids and Family Max amazon channel",
  "Kidstream Amazon Channel",
  "Kino Film Collection",
  "Kino Film Collection Amazon Channel",
  "Klassiki",
  "Kocowa",
  "Kocowa Amazon Channel",
  "KQED",
  "Kundalini Yoga TV Amazon Channel",
  "Learn How to Run Amzon Channel",
  "Lifetime",
  "Lifetime Movie Club",
  "Lifetime Movie Club Amazon Channel",
  "Lifetime Movie Club Apple TV Channel",
  "Magellan TV",
  "Magnolia Network Amazon Channel",
  "Magnolia Selects Amazon Channel",
  "Marcus Theatres",
  "Marquee TV Amazon Channel",
  "Martha Stewart TV",
  "Metrograph",
  "MGM Plus",
  "MGM Plus Roku Premium Channel",
  "MGM+ Amazon Channel",
  "Mhz Choice",
  "MHz Choice Amazon Channel",
  "Midnight Pulp",
  "Midnight Pulp Amazon Channel",
  "Mometu",
  "Monsters and Nightmares Amazon Channel",
  "Motorvision TV Amazon Channel",
  "MovieMe",
  "MovieSaints",
  "MovieSphere+ Amazon Channel",
  "MTV Hits Amazon Channel",
  "MTV Plus Amazon Channel",
  "MUBI",
  "MUBI Amazon Channel",
  "myfilmfriend",
  "MyOutdoor TV Amazon Channel",
  "MyOutdoorTV",
  "MZ Choice Amazon Channel",
  "National Geographic",
  "NBC",
  "Netflix",
  "Netflix Kids",
  "Netflix Standard with Ads",
  "Night Flight Plus",
  "Noggin Amazon Channel",
  "On Air",
  "OnDemandKorea",
  "Outside TV Features Amzon Channel",
  "Outside Watch",
  "OUTtv Apple TV Channel",
  "Ovation TV",
  "OVID",
  "OXYGEN",
  "Panna Cooking Amazon Channel",
  "Pantaya appletv channel",
  "Paramount Plus Apple TV Channel",
  "Paramount Plus Essential",
  "Paramount Plus Premium",
  "Paramount+ Amazon Channel",
  "Paramount+ MTV Amazon Channel",
  "Paramount+ Originals Amazon Channel",
  "Paramount+ Roku Premium Channel",
  "Passionflix Amazon Channel",
  "PBS",
  "PBS America Amazon Channel",
  "PBS Documentaries Amazon Channel",
  "PBS Kids Amazon Channel",
  "PBS Living Amazon Channel",
  "PBS Masterpiece Amazon Channel",
  "Peacock Premium",
  "Peacock Premium Plus",
  "Peacock Premium Plus Amazon Channel",
  "Philo",
  "Pinoy Box Office Amazon Channel",
  "PixL Amazon Channel",
  "Planet Earth Amazon Channel",
  "Plex",
  "Plex Live TV",
  "Plex Player",
  "Pluto TV",
  "Pluto TV Live",
  "Pongalo Amazon Channel",
  "Popflick",
  "Public Domain Movies",
  "Pure Flix",
  "Qello Concerts by Stingray Amazon Channel",
  "Rakuten Viki",
  "REELZ+ Amazon Channel",
  "Regal Cinemas",
  "Retrocrush",
  "RetroCrush Amazon Channel",
  "Reveel",
  "Revry",
  "Revry Amazon Channel",
  "Runtime",
  "Ryan and Friends Plus Amazon Channel",
  "Science Channel",
  "Screambox Amazon Channel",
  "ScreenPix Amazon Channel",
  "ScreenPix Apple TV Channel",
  "Sensical Amazon Channel",
  "Shahid VIP",
  "ShortsTV Amazon Channel",
  "Shout! Factory Amazon Channel",
  "Shout! Factory TV",
  "Shudder",
  "Shudder Amazon Channel",
  "Shudder Apple TV Channel",
  "Sleep Sounds & Meditation Amazon Channel",
  "Spectrum On Demand",
  "Starz",
  "Starz Amazon Channel",
  "Starz Apple TV Channel",
  "Starz Roku Premium Channel",
  "Stingray Classica Amazon Channel",
  "Stingray Djazz Amazon Channel",
  "Stingray Karaoke Amazon Channel",
  "Strand Releasing Amazon Channel",
  "Stupid Co",
  "Sun Nxt",
  "Sundance Now",
  "Sundance Now Amazon Channel",
  "Sundance Now Apple TV Channel",
  "Sweatflix Amazon Channel",
  "Takflix",
  "Tastemade Amazon Channel",
  "Tastemade Apple TV Channel",
  "TBS",
  "TCM",
  "Telemundo",
  "Tentkotta",
  "The Coda Collection Amazon Channel",
  "The CW",
  "The Great Courses Amazon Channel",
  "The Oprah Winfrey Network",
  "The Roku Channel",
  "The Surf Network Amazon Channel",
  "The Titanic Channel Amazon Channel",
  "Thirteen",
  "TLC",
  "TNT",
  "Toku Amazon Channel",
  "Toon Goggles",
  "Travel Channel",
  "Troma NOW",
  "tru TV",
  "True Royalty Amazon Channel",
  "True Story",
  "Tubi TV",
  "TVCortos Amazon Channel",
  "Univer Video",
  "UP Faith & Family Amazon Channel",
  "UP Faith & Family Apple TV Channel",
  "USA Network",
  "Vemox Cine Amazon Channel",
  "VH1",
  "Viaplay Amazon Channel",
  "Vice TV",
  "Vimeo",
  "VIX",
  "Vix Gratis Amazon Channel",
  "ViX Premium Amazon Channel",
  "Warriors and Gangsters Amazon Channel",
  "Watchit.Kid Amazon Channel",
  "Wellness Plus by Psychetruth Amazon Channel",
  "WETA+",
  "WeTV",
  "WOW Presents Plus",
  "WWE Network",
  "Xive TV Documentaries Amazon Channel",
  "XLTV Amazon Channel",
  "Xumo Play",
  "Yipee Kids TV Amazon Channel",
  "Yoga and Fitness TV Amazon channel",
  "Yoga Anytime Amazon Channel",
  "Yoga Download Amazon Channel",
  "Yoga International Amazon Channel",
  "Young Hollywood Amazon Channel",
  "YouTube Free",
  "YouTube Premium",
  "YouTube TV",
  "ZenLIFE by Stingray Amazon Channel",
]

export function Dashboard() {
  return (
    <div className="max-w-3xl mx-auto space-y-6 px-4">
      <div className="text-center">
        <h2 className="text-2xl font-bold tracking-tight">Getting Started</h2>
        <p className="text-muted-foreground mt-1">
          Learn how to set up and use Stream Channeler
        </p>
      </div>
      <div>
        <Accordion type="single" collapsible className="w-full">
          <AccordionItem value="create-channel">
            <AccordionTrigger>1. Create a Channel</AccordionTrigger>
            <AccordionContent>
              <div className="space-y-2">
                <p>
                  Start by creating a channel to organize your media. A channel
                  is like a personalized collection that you can customize to
                  your liking.
                </p>
                <ol className="list-decimal list-inside space-y-1 ml-2">
                  <li>
                    Navigate to the{" "}
                    <Link
                      to="/channels"
                      className="text-primary hover:underline"
                    >
                      Channels page
                    </Link>{" "}
                    from the sidebar
                  </li>
                  <li>Click the "New Channel" button</li>
                  <li>
                    Give your channel a name and choose if it should be public
                    or private.
                  </li>
                  <li>Save your channel</li>
                  <li>
                    Click on the channel to add shows to it and set the episode
                    order parameters
                  </li>
                </ol>
                <p className="text-sm text-muted-foreground mt-3">
                  <strong>Note:</strong> Public channels can be accessed by
                  anyone with a link to the channel. Private channels can only
                  be accessed by you.
                </p>
              </div>
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="add-shows">
            <AccordionTrigger>2. Add Shows to Your Channel</AccordionTrigger>
            <AccordionContent>
              <ol className="list-decimal list-inside space-y-1 ml-2 text-sm mb-4">
                <li>From the channel page, click the "Add Shows" button</li>
                <li>Add the show URLs to the textbox</li>
                <li>Click "Add URLs" to add the URLs to the channel</li>
              </ol>
              <div className="text-sm mb-4">
                <p>
                  There are two main types of sources you can add to your
                  channels:
                </p>
                <p>
                  <strong>JustWatch supported websites</strong> that use URLs
                  from JustWatch.
                </p>
                <p>
                  <strong>Natively supported websites</strong> that support URLs
                  directly from the source website.
                </p>
              </div>
              <Accordion type="single" collapsible className="w-full">
                <AccordionItem value="justwatch-services">
                  <AccordionTrigger>
                    JustWatch Supported Services
                  </AccordionTrigger>
                  <AccordionContent>
                    <p className="text-sm mb-3">
                      These services support URLs through JustWatch:
                    </p>

                    <details className="mt-3">
                      <summary className="cursor-pointer font-medium text-sm">
                        View all supported services (
                        {JUSTWATCH_SUPPORTED_SERVICES.length})
                      </summary>
                      <div className="mt-2 max-h-48 overflow-y-auto border rounded p-3">
                        <ul className="grid grid-cols-1 sm:grid-cols-2 gap-1 text-sm">
                          {JUSTWATCH_SUPPORTED_SERVICES.map((service) => (
                            <li key={service} className="text-muted-foreground">
                              {service}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </details>
                    <p className="text-sm mb-3 mt-4">
                      For JustWatch URLs, the name of the source should be
                      included before the URL on the same line as the URL.
                    </p>
                    <p className="text-xs text-muted-foreground mb-1">
                      Example:
                    </p>
                    <code className="block bg-muted p-2 rounded text-sm mb-3">
                      Hulu https://www.justwatch.com/us/tv-show/breaking-bad
                    </code>
                  </AccordionContent>
                </AccordionItem>
                <AccordionItem value="native-websites">
                  <AccordionTrigger>
                    Natively supported websites
                  </AccordionTrigger>
                  <AccordionContent>
                    <p className="text-sm mb-3">
                      These services support URLs directly from the source
                      website:
                    </p>
                    <div className="space-y-4">
                      <div>
                        <p className="text-sm font-medium mb-1">
                          YouTube (Playlists and Channels)
                        </p>
                        <p className="text-xs text-muted-foreground mb-1">
                          Channel Example:
                        </p>
                        <code className="block bg-muted p-2 rounded text-xs break-all mb-2">
                          https://www.youtube.com/@jawed
                        </code>
                        <p className="text-xs text-muted-foreground mb-1">
                          Playlist Example:
                        </p>
                        <code className="block bg-muted p-2 rounded text-xs break-all">
                          https://www.youtube.com/watch?v=lVI_J1cbFb4&list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh
                        </code>
                      </div>
                      <div>
                        <p className="text-sm font-medium mb-1">Crunchyroll</p>
                        <p className="text-xs text-muted-foreground mb-1">
                          Example:
                        </p>
                        <code className="block bg-muted p-2 rounded text-xs break-all">
                          https://www.crunchyroll.com/series/G4PH0WXVJ/spy-x-family
                        </code>
                      </div>
                    </div>
                  </AccordionContent>
                </AccordionItem>
              </Accordion>
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="configure-channel">
            <AccordionTrigger>3. Configure the Channel</AccordionTrigger>
            <AccordionContent>
              <div className="space-y-4 text-sm">
                <div>
                  <h4 className="font-semibold mb-2">Channel Options</h4>
                  <p>
                    Use Channel options to set the order that the episodes will
                    be displayed.
                  </p>
                </div>

                <div>
                  <h4 className="font-semibold mb-2">
                    Manage Additional Channels
                  </h4>
                  <p>
                    Use manage additional channels to combine multiple channels
                    into one (non-recursively).
                  </p>
                </div>

                <div>
                  <h4 className="font-semibold mb-2">Saving Configurations</h4>
                  <p className="mb-2">
                    Hitting "Save as default" will make the channel open with
                    this setting when opening from the channel list.
                  </p>
                  <p>
                    You can also bookmark the current URL at any time to save
                    additional configurations.
                  </p>
                </div>

                <div>
                  <p className="text-xs text-muted-foreground bg-muted p-2 rounded">
                    <strong>Note:</strong> Episodes can be toggled between card
                    mode and table mode with a button in the top right.
                  </p>
                </div>
              </div>
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="managing-watches">
            <AccordionTrigger>4. Managing Watches</AccordionTrigger>
            <AccordionContent>
              <div className="space-y-4 text-sm">
                <p>
                  Whenever you click on the link for a media, it will be marked
                  as watched and the watch needs to be validated in the{" "}
                  <Link to="/watches" className="text-primary hover:underline">
                    watches page
                  </Link>{" "}
                  before any watch based filters will be applied to it.
                </p>

                <p>
                  This information can be used to determine channel order and
                  sorting, allowing you to create more useful channels. For
                  example, you can make a channel that only shows you content
                  you have never seen before.
                </p>
              </div>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </div>
    </div>
  )
}
