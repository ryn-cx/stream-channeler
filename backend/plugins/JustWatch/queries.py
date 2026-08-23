# TODO: Validate

BUY_BOX_OFFERS = """query GetBuyBoxOffers($nodeId: ID!, $country: Country!, $language: Language!, $platform: Platform! = WEB, $fallbackToForeignOffers: Boolean = true, $excludePackages: [String!] = []) {
  node(id: $nodeId) {
    id
    ...BuyBoxOffers
    __typename
  }
}

fragment BuyBoxOffers on MovieOrShowOrSeasonOrEpisode {
  __typename
  offerCount(country: $country, platform: $platform)
  maxOfferUpdatedAt(country: $country, platform: $platform)
  offersHistory(
    country: $country
    platform: $platform
    filterV2: {monetizationTypes: [FLATRATE, FLATRATE_AND_BUY, RENT, FREE, ADS, BUY, FAST], bestOnly: true, preAffiliate: true, fallbackToForeignOffers: $fallbackToForeignOffers, excludePackages: $excludePackages}
  ) {
    ...OffersHistory
    __typename
  }
  flatrate: offers(
    country: $country
    platform: $platform
    filter: {monetizationTypes: [FLATRATE, FLATRATE_AND_BUY, CINEMA], bestOnly: true, preAffiliate: true, fallbackToForeignOffers: $fallbackToForeignOffers, excludePackages: $excludePackages}
  ) {
    ...TitleOffer
    __typename
  }
  buy: offers(
    country: $country
    platform: $platform
    filter: {monetizationTypes: [BUY], bestOnly: true, preAffiliate: true, fallbackToForeignOffers: $fallbackToForeignOffers, excludePackages: $excludePackages}
  ) {
    ...TitleOffer
    offerSeasons
    minRetailPrice(country: $country, platform: $platform, language: $language)
    __typename
  }
  rent: offers(
    country: $country
    platform: $platform
    filter: {monetizationTypes: [RENT], bestOnly: true, preAffiliate: true, fallbackToForeignOffers: $fallbackToForeignOffers, excludePackages: $excludePackages}
  ) {
    ...TitleOffer
    offerSeasons
    minRetailPrice(country: $country, platform: $platform, language: $language)
    __typename
  }
  free: offers(
    country: $country
    platform: $platform
    filter: {monetizationTypes: [FREE, ADS], bestOnly: true, preAffiliate: true, fallbackToForeignOffers: $fallbackToForeignOffers, excludePackages: $excludePackages}
  ) {
    ...TitleOffer
    __typename
  }
  fast: offers(
    country: $country
    platform: $platform
    filter: {monetizationTypes: [FAST], bestOnly: true, preAffiliate: true, fallbackToForeignOffers: $fallbackToForeignOffers, excludePackages: $excludePackages}
  ) {
    ...FastOffer
    __typename
  }
  bundles(country: $country, platform: WEB) {
    node {
      id
      clearName
      icon(profile: S100)
      technicalName
      bundleId
      packages(country: $country, platform: $platform) {
        icon
        id
        iconWide(profile: S160)
        clearName
        packageId
        __typename
      }
      __typename
    }
    promotionUrl
    offer {
      ...TitleOffer
      __typename
    }
    __typename
  }
  ... on MovieOrShowOrSeason {
    promotedBundles(country: $country, platform: WEB) {
      node {
        id
        clearName
        icon(profile: S100)
        technicalName
        bundleId
        packages(country: $country, platform: $platform) {
          icon
          id
          clearName
          packageId
          iconWide(profile: S160)
          __typename
        }
        __typename
      }
      promotionUrl
      offer {
        ...TitleOffer
        __typename
      }
      __typename
    }
    promotedOffers(
      country: $country
      platform: WEB
      filter: {bestOnly: true, preAffiliate: true}
    ) {
      ...TitleOffer
      minRetailPrice(country: $country, platform: $platform, language: $language)
      __typename
    }
    __typename
  }
}

fragment OffersHistory on OfferHistory {
  __typename
  id
  country
  dateRanges {
    end
    start
    __typename
  }
  package {
    icon
    id
    iconWide(profile: S160)
    clearName
    packageId
    monetizationTypes
    __typename
  }
}

fragment TitleOffer on Offer {
  id
  presentationType
  monetizationType
  newElementCount
  retailPrice(language: $language)
  retailPriceValue
  currency
  lastChangeRetailPriceValue
  type
  country
  package {
    id
    packageId
    clearName
    shortName
    technicalName
    icon(profile: S100)
    iconWide(profile: S160)
    planOffers(country: $country, platform: WEB) {
      title
      retailPrice(language: $language)
      isTrial
      durationDays
      retailPriceValue
      children {
        title
        retailPrice(language: $language)
        isTrial
        durationDays
        retailPriceValue
        __typename
      }
      __typename
    }
    __typename
  }
  plans(platform: WEB) {
    title
    retailPrice(language: $language)
    isTrial
    durationDays
    retailPriceValue
    children {
      title
      retailPrice(language: $language)
      isTrial
      durationDays
      retailPriceValue
      __typename
    }
    __typename
  }
  standardWebURL
  preAffiliatedStandardWebURL
  streamUrl
  streamUrlExternalPlayer
  elementCount
  availableTo
  subtitleLanguages
  videoTechnology
  audioTechnology
  audioLanguages(language: $language)
  __typename
}

fragment FastOffer on Offer {
  ...TitleOffer
  availableTo
  availableFromTime
  availableToTime
  __typename
}
"""

NEW_TITLE_BUCKETS = """query GetNewTitleBuckets($country: Country!, $newTitlesFilter: TitleFilter, $newAfterCursor: String, $first: Int! = 2, $priceDrops: Boolean!, $bucketSize: Int! = 8, $groupBy: NewTitleAggregation! = DATE_PACKAGE, $pageType: NewPageType! = NEW) {
  newTitleBuckets(
    country: $country
    filter: $newTitlesFilter
    after: $newAfterCursor
    first: $first
    bucketSize: $bucketSize
    priceDrops: $priceDrops
    pageType: $pageType
    groupBy: $groupBy
  ) {
    pageInfo {
      startCursor
      endCursor
      hasPreviousPage
      hasNextPage
      __typename
    }
    edges {
      key {
        __typename
        ...NewBucketByDate
        ...NewBucketByPackage
      }
      node {
        totalCount
        pageInfo {
          startCursor
          endCursor
          hasNextPage
          hasPreviousPage
          __typename
        }
        __typename
      }
      __typename
    }
    __typename
  }
}

fragment NewBucketByDate on DatePackageAggregationKey {
  __typename
  date
  package {
    id
    packageId
    shortName
    icon
    __typename
  }
}

fragment NewBucketByPackage on BucketPackageAggregationKey {
  __typename
  bucketType
  package {
    id
    packageId
    shortName
    icon
    __typename
  }
}
"""

NEW_TITLES = """query GetNewTitles($country: Country!, $date: Date!, $language: Language!, $filter: TitleFilter, $after: String, $first: Int! = 10, $profile: PosterProfile, $format: ImageFormat, $priceDrops: Boolean!, $platform: Platform!, $bucketType: NewDateRangeBucket, $pageType: NewPageType! = NEW, $showDateBadge: Boolean!, $availableToPackages: [String!]) {
  newTitles(
    country: $country
    date: $date
    filter: $filter
    after: $after
    first: $first
    priceDrops: $priceDrops
    bucketType: $bucketType
    pageType: $pageType
  ) {
    totalCount
    edges {
      ...NewTitleGraphql
      __typename
    }
    pageInfo {
      endCursor
      hasPreviousPage
      hasNextPage
      __typename
    }
    __typename
  }
}

fragment NewTitleGraphql on NewTitlesEdge {
  cursor
  newOffer(platform: $platform) {
    ...NewWatchNowOffer
    __typename
  }
  node {
    __typename
    ... on MovieOrSeason {
      id
      objectId
      objectType
      content(country: $country, language: $language) {
        title
        shortDescription
        fullPath
        scoring {
          imdbVotes
          imdbScore
          tmdbPopularity
          tmdbScore
          tomatoMeter
          certifiedFresh
          __typename
        }
        posterUrl(profile: $profile, format: $format)
        runtime
        genres {
          translation(language: $language)
          __typename
        }
        ... on SeasonContent {
          seasonNumber
          __typename
        }
        upcomingReleases @include(if: $showDateBadge) {
          releaseDate
          package {
            id
            shortName
            __typename
          }
          releaseCountDown(country: $country)
          __typename
        }
        isReleased
        __typename
      }
      availableTo(
        country: $country
        platform: $platform
        packages: $availableToPackages
      ) @include(if: $showDateBadge) {
        availableCountDown(country: $country)
        package {
          id
          shortName
          __typename
        }
        availableToDate
        __typename
      }
      ... on Movie {
        likelistEntry {
          createdAt
          __typename
        }
        dislikelistEntry {
          createdAt
          __typename
        }
        seenlistEntry {
          createdAt
          __typename
        }
        watchlistEntryV2 {
          createdAt
          __typename
        }
        __typename
      }
      ... on Season {
        likelistEntry {
          createdAt
          __typename
        }
        dislikelistEntry {
          createdAt
          __typename
        }
        show {
          __typename
          id
          objectId
          objectType
          content(country: $country, language: $language) {
            title
            shortDescription
            fullPath
            scoring {
              imdbVotes
              imdbScore
              tmdbPopularity
              tmdbScore
              __typename
            }
            posterUrl(profile: $profile, format: $format)
            runtime
            genres {
              translation(language: $language)
              __typename
            }
            __typename
          }
          likelistEntry {
            createdAt
            __typename
          }
          dislikelistEntry {
            createdAt
            __typename
          }
          watchlistEntryV2 {
            createdAt
            __typename
          }
          seenState(country: $country) {
            progress
            __typename
          }
        }
        __typename
      }
      __typename
    }
  }
  __typename
}

fragment NewWatchNowOffer on Offer {
  ...WatchNowOffer
  lastChangeRetailPrice(language: $language)
  lastChangePercent
  __typename
}

fragment WatchNowOffer on Offer {
  __typename
  id
  standardWebURL
  preAffiliatedStandardWebURL
  streamUrl
  streamUrlExternalPlayer
  package {
    id
    icon
    packageId
    clearName
    shortName
    technicalName
    iconWide(profile: S160)
    hasRectangularIcon(country: $country, platform: WEB)
    __typename
  }
  retailPrice(language: $language)
  retailPriceValue
  lastChangeRetailPriceValue
  currency
  presentationType
  monetizationType
  availableTo
  dateCreated
  newElementCount
}
"""

SEASON_EPISODES = """query GetSeasonEpisodes($nodeId: ID!, $country: Country!, $language: Language!, $platform: Platform! = WEB, $limit: Int, $offset: Int) {
  node(id: $nodeId) {
    id
    __typename
    ... on Season {
      episodes(limit: $limit, offset: $offset) {
        ...Episode
        __typename
      }
      __typename
    }
  }
}

fragment Episode on Episode {
  id
  objectId
  objectType
  seenlistEntry {
    createdAt
    __typename
  }
  uniqueOfferCount: offerCount(
    country: $country
    platform: $platform
    filter: {bestOnly: true}
  )
  flatrate: offers(
    country: $country
    platform: $platform
    filter: {monetizationTypes: [FLATRATE_AND_BUY, FLATRATE, ADS, CINEMA, FREE], bestOnly: true, preAffiliate: true}
  ) {
    id
    package {
      id
      clearName
      packageId
      __typename
    }
    __typename
  }
  buy: offers(
    country: $country
    platform: $platform
    filter: {monetizationTypes: [BUY], bestOnly: true, preAffiliate: true}
  ) {
    id
    package {
      id
      clearName
      packageId
      __typename
    }
    __typename
  }
  rent: offers(
    country: $country
    platform: $platform
    filter: {monetizationTypes: [RENT], bestOnly: true, preAffiliate: true}
  ) {
    id
    package {
      id
      clearName
      packageId
      __typename
    }
    __typename
  }
  free: offers(
    country: $country
    platform: $platform
    filter: {monetizationTypes: [ADS, FREE], bestOnly: true, preAffiliate: true}
  ) {
    id
    package {
      id
      clearName
      packageId
      __typename
    }
    __typename
  }
  fast: offers(
    country: $country
    platform: $platform
    filter: {monetizationTypes: [FAST], bestOnly: true, preAffiliate: true}
  ) {
    id
    package {
      id
      clearName
      packageId
      __typename
    }
    __typename
  }
  content(country: $country, language: $language) {
    __typename
    title
    shortDescription
    episodeNumber
    seasonNumber
    isReleased
    runtime
    upcomingReleases {
      releaseCountDown(country: $country)
      releaseDate
      releaseType
      label
      package {
        id
        packageId
        shortName
        clearName
        monetizationTypes
        icon(profile: S100)
        iconWide(profile: S160)
        hasRectangularIcon(country: $country, platform: WEB)
        planOffers(country: $country, platform: $platform) {
          retailPrice(language: $language)
          durationDays
          presentationType
          isTrial
          retailPriceValue
          currency
          __typename
        }
        __typename
      }
      __typename
    }
  }
  __typename
}
"""

URL_TITLE_DETAILS = """query GetUrlTitleDetails($fullPath: String!, $country: Country!, $language: Language!, $episodeMaxLimit: Int, $platform: Platform! = WEB, $allowSponsoredRecommendations: SponsoredRecommendationsInput, $format: ImageFormat, $backdropProfile: BackdropProfile, $excludeTextRecommendationTitle: Boolean = true, $streamingChartsFilter: StreamingChartsFilter, $first: Int! = 10, $fallbackToForeignOffers: Boolean = true, $excludePackages: [String!] = []) {
  urlV2(fullPath: $fullPath) {
    id
    metaDescription
    metaKeywords
    metaRobots
    metaTitle
    heading1
    heading2
    htmlContent
    node {
      ...TitleDetails
      ...BuyBoxOffers
      ...TitleDetailModules
      __typename
    }
    __typename
  }
}

fragment TitleDetails on MovieOrShowOrSeason {
  id
  objectType
  objectId
  __typename
  justwatchTVOffers: offers(
    country: $country
    platform: $platform
    filter: {packages: ["jwt"], preAffiliate: true}
  ) {
    ...WatchNowOffer
    __typename
  }
  disneyOffersCount: offerCount(
    country: $country
    platform: $platform
    filter: {packages: ["dnp"]}
  )
  starOffersCount: offerCount(
    country: $country
    platform: $platform
    filter: {packages: ["srp"]}
  )
  uniqueOfferCount: offerCount(
    country: $country
    platform: $platform
    filter: {bestOnly: true}
  )
  offers(country: $country, platform: $platform, filter: {preAffiliate: true}) {
    ...TitleOffer
    __typename
  }
  watchNowOffer(country: $country, platform: $platform) {
    ...WatchNowOffer
    __typename
  }
  availableTo(country: $country, platform: $platform) {
    availableCountDown(country: $country)
    availableToDate
    package {
      id
      shortName
      __typename
    }
    __typename
  }
  fallBackClips: content(country: $country, language: "en") {
    clips(country: $country, language: "en") {
      ...TrailerClips
      __typename
    }
    videobusterClips: clips(
      providers: [VIDEOBUSTER]
      country: $country
      language: "en"
    ) {
      ...TrailerClips
      __typename
    }
    dailymotionClips: clips(
      providers: [DAILYMOTION]
      country: $country
      language: "en"
    ) {
      ...TrailerClips
      __typename
    }
    __typename
  }
  content(country: $country, language: $language) {
    backdrops {
      backdropUrl
      __typename
    }
    fullBackdrops: backdrops(profile: S1920, format: JPG) {
      backdropUrl
      __typename
    }
    clips {
      ...TrailerClips
      __typename
    }
    videobusterClips: clips(providers: [VIDEOBUSTER]) {
      ...TrailerClips
      __typename
    }
    dailymotionClips: clips(providers: [DAILYMOTION]) {
      ...TrailerClips
      __typename
    }
    externalIds {
      imdbId
      wikidataId
      __typename
    }
    fullPath
    posterUrl
    fullPosterUrl: posterUrl(profile: S718, format: JPG)
    runtime
    isReleased
    scoring {
      imdbScore
      imdbVotes
      tmdbPopularity
      tmdbScore
      jwRating
      tomatoMeter
      certifiedFresh
      __typename
    }
    shortDescription
    title
    originalReleaseYear
    originalReleaseDate
    upcomingReleases {
      releaseCountDown(country: $country)
      releaseDate
      releaseType
      label
      package {
        id
        packageId
        shortName
        clearName
        monetizationTypes
        icon(profile: S100)
        iconWide(profile: S160)
        hasRectangularIcon(country: $country, platform: WEB)
        planOffers(country: $country, platform: $platform) {
          retailPrice(language: $language)
          durationDays
          presentationType
          isTrial
          retailPriceValue
          currency
          __typename
        }
        __typename
      }
      __typename
    }
    genres {
      shortName
      translation(language: $language)
      __typename
    }
    subgenres {
      content(country: $country, language: $language) {
        shortName
        name
        __typename
      }
      __typename
    }
    textRecommendations(first: $first) {
      ...TextRecommendation
      __typename
    }
    ... on MovieOrShowOrSeasonContent {
      subgenres {
        content(country: $country, language: $language) {
          url: moviesUrl {
            fullPath
            __typename
          }
          __typename
        }
        __typename
      }
      __typename
    }
    ... on MovieOrShowContent {
      originalTitle
      ageCertification
      credits {
        ...Credit
        __typename
      }
      interactions {
        dislikelistAdditions
        likelistAdditions
        votesNumber
        __typename
      }
      productionCountries
      __typename
    }
    ... on MovieContent {
      tags {
        technicalName
        translatedName
        __typename
      }
      __typename
    }
    ... on ShowContent {
      tags {
        technicalName
        translatedName
        __typename
      }
      __typename
    }
    ... on SeasonContent {
      seasonNumber
      interactions {
        dislikelistAdditions
        likelistAdditions
        votesNumber
        __typename
      }
      tags {
        technicalName
        translatedName
        __typename
      }
      __typename
    }
    __typename
  }
  recommendedByCount
  watchedByCount
  popularityRank(country: $country) {
    rank
    trend
    trendDifference
    __typename
  }
  streamingCharts(country: $country, filter: $streamingChartsFilter) {
    edges {
      streamingChartInfo {
        rank
        trend
        trendDifference
        updatedAt
        daysInTop10
        daysInTop100
        daysInTop1000
        daysInTop3
        topRank
        __typename
      }
      __typename
    }
    __typename
  }
  likelistEntry {
    createdAt
    __typename
  }
  dislikelistEntry {
    createdAt
    __typename
  }
  ... on MovieOrShow {
    watchlistEntryV2 {
      createdAt
      __typename
    }
    customlistEntries {
      createdAt
      genericTitleList {
        id
        __typename
      }
      __typename
    }
    similarTitlesV2(
      country: $country
      allowSponsoredRecommendations: $allowSponsoredRecommendations
    ) {
      sponsoredAd {
        ...SponsoredAd
        __typename
      }
      __typename
    }
    __typename
  }
  ... on Movie {
    permanentAudiences
    seenlistEntry {
      createdAt
      __typename
    }
    __typename
  }
  ... on Show {
    permanentAudiences
    totalSeasonCount
    seenState(country: $country) {
      progress
      seenEpisodeCount
      __typename
    }
    tvShowTrackingEntry {
      createdAt
      __typename
    }
    offers(country: $country, platform: $platform, filter: {preAffiliate: true}) {
      ...TitleOffer
      __typename
    }
    seasons(sortDirection: DESC) {
      id
      objectId
      objectType
      totalEpisodeCount
      availableTo(country: $country, platform: $platform) {
        availableToDate
        availableCountDown(country: $country)
        package {
          id
          shortName
          __typename
        }
        __typename
      }
      offers(
        country: $country
        platform: $platform
        filter: {monetizationTypes: [BUY, RENT], preAffiliate: true, fallbackToForeignOffers: $fallbackToForeignOffers}
      ) {
        package {
          clearName
          shortName
          __typename
        }
        monetizationType
        retailPrice(language: $language)
        retailPriceValue
        __typename
      }
      content(country: $country, language: $language) {
        posterUrl
        seasonNumber
        fullPath
        title
        upcomingReleases {
          releaseDate
          releaseCountDown(country: $country)
          __typename
        }
        isReleased
        originalReleaseYear
        __typename
      }
      show {
        __typename
        id
        objectId
        objectType
        watchlistEntryV2 {
          createdAt
          __typename
        }
        content(country: $country, language: $language) {
          title
          __typename
        }
      }
      fallBackClips: content(country: $country, language: "en") {
        clips(country: $country, language: "en") {
          ...TrailerClips
          __typename
        }
        videobusterClips: clips(
          providers: [VIDEOBUSTER]
          country: $country
          language: "en"
        ) {
          ...TrailerClips
          __typename
        }
        dailymotionClips: clips(
          providers: [DAILYMOTION]
          country: $country
          language: "en"
        ) {
          ...TrailerClips
          __typename
        }
        __typename
      }
      __typename
    }
    recentEpisodes: episodes(
      sortDirection: DESC
      limit: 3
      releasedInCountry: $country
    ) {
      ...Episode
      __typename
    }
    __typename
  }
  ... on Season {
    totalEpisodeCount
    episodes(limit: $episodeMaxLimit) {
      ...Episode
      __typename
    }
    show {
      __typename
      id
      objectId
      objectType
      totalSeasonCount
      customlistEntries {
        createdAt
        genericTitleList {
          id
          __typename
        }
        __typename
      }
      tvShowTrackingEntry {
        createdAt
        __typename
      }
      fallBackClips: content(country: $country, language: "en") {
        clips(country: $country, language: "en") {
          ...TrailerClips
          __typename
        }
        videobusterClips: clips(
          providers: [VIDEOBUSTER]
          country: $country
          language: "en"
        ) {
          ...TrailerClips
          __typename
        }
        dailymotionClips: clips(
          providers: [DAILYMOTION]
          country: $country
          language: "en"
        ) {
          ...TrailerClips
          __typename
        }
        __typename
      }
      content(country: $country, language: $language) {
        title
        ageCertification
        fullPath
        genres {
          shortName
          __typename
        }
        subgenres {
          content(country: $country, language: $language) {
            shortName
            name
            __typename
          }
          __typename
        }
        credits {
          ...Credit
          __typename
        }
        productionCountries
        externalIds {
          imdbId
          __typename
        }
        upcomingReleases {
          releaseDate
          releaseType
          package {
            id
            shortName
            planOffers(country: $country, platform: $platform) {
              retailPrice(language: $language)
              durationDays
              presentationType
              isTrial
              retailPriceValue
              currency
              __typename
            }
            __typename
          }
          __typename
        }
        backdrops {
          backdropUrl
          __typename
        }
        posterUrl
        isReleased
        clips {
          ...TrailerClips
          __typename
        }
        videobusterClips: clips(providers: [VIDEOBUSTER]) {
          ...TrailerClips
          __typename
        }
        dailymotionClips: clips(providers: [DAILYMOTION]) {
          ...TrailerClips
          __typename
        }
        __typename
      }
      seenState(country: $country) {
        progress
        __typename
      }
      watchlistEntryV2 {
        createdAt
        __typename
      }
      dislikelistEntry {
        createdAt
        __typename
      }
      likelistEntry {
        createdAt
        __typename
      }
      similarTitlesV2(
        country: $country
        allowSponsoredRecommendations: $allowSponsoredRecommendations
      ) {
        sponsoredAd {
          ...SponsoredAd
          __typename
        }
        __typename
      }
    }
    seenState(country: $country) {
      progress
      __typename
    }
    __typename
  }
}

fragment WatchNowOffer on Offer {
  __typename
  id
  standardWebURL
  preAffiliatedStandardWebURL
  streamUrl
  streamUrlExternalPlayer
  package {
    id
    icon
    packageId
    clearName
    shortName
    technicalName
    iconWide(profile: S160)
    hasRectangularIcon(country: $country, platform: WEB)
    __typename
  }
  retailPrice(language: $language)
  retailPriceValue
  lastChangeRetailPriceValue
  currency
  presentationType
  monetizationType
  availableTo
  dateCreated
  newElementCount
}

fragment TitleOffer on Offer {
  id
  presentationType
  monetizationType
  newElementCount
  retailPrice(language: $language)
  retailPriceValue
  currency
  lastChangeRetailPriceValue
  type
  country
  package {
    id
    packageId
    clearName
    shortName
    technicalName
    icon(profile: S100)
    iconWide(profile: S160)
    planOffers(country: $country, platform: WEB) {
      title
      retailPrice(language: $language)
      isTrial
      durationDays
      retailPriceValue
      children {
        title
        retailPrice(language: $language)
        isTrial
        durationDays
        retailPriceValue
        __typename
      }
      __typename
    }
    __typename
  }
  plans(platform: WEB) {
    title
    retailPrice(language: $language)
    isTrial
    durationDays
    retailPriceValue
    children {
      title
      retailPrice(language: $language)
      isTrial
      durationDays
      retailPriceValue
      __typename
    }
    __typename
  }
  standardWebURL
  preAffiliatedStandardWebURL
  streamUrl
  streamUrlExternalPlayer
  elementCount
  availableTo
  subtitleLanguages
  videoTechnology
  audioTechnology
  audioLanguages(language: $language)
  __typename
}

fragment TrailerClips on Clip {
  sourceUrl
  externalId
  provider
  name
  __typename
}

fragment TextRecommendation on TextRecommendation {
  __typename
  id
  headline
  body
  bodyHTML
  originalHeadline
  originalBody
  originalBodyHTML
  watchIf
  skipIf
  customProfileType
  tags {
    technicalName
    translatedName
    __typename
  }
  watchedAt
  watchedOn {
    ...Package
    __typename
  }
  likeCount
  likedByUser
  ownedByUser
  profile {
    ...ProfileInfo
    __typename
  }
  updatedAt
  title @skip(if: $excludeTextRecommendationTitle) {
    ...PosterTitle
    __typename
  }
  video {
    externalId
    name
    provider
    publishedAt
    sourceUrl
    streamUrl
    __typename
  }
}

fragment Package on Package {
  clearName
  id
  shortName
  technicalName
  packageId
  selected
  monetizationTypes
  icon
  addonParent(country: $country, platform: WEB) {
    id
    __typename
  }
  __typename
}

fragment ProfileInfo on Profile {
  __typename
  id: uuid
  displayName
  firstName
  lastName
  location
  country
  bio
  avatarUrl
  isComplete
  externalUrls {
    type
    name
    url
    __typename
  }
  ownedByUser
  profileUrl
  profileType
  contentPersonId
  textRecommendationsCount
}

fragment PosterTitle on MovieOrShowOrSeason {
  __typename
  id
  objectId
  objectType
  content(country: $country, language: $language) {
    title
    posterUrl
    fullPath
    upcomingReleases {
      releaseDate
      releaseCountDown(country: $country)
      __typename
    }
    scoring {
      imdbScore
      imdbVotes
      tmdbPopularity
      tmdbScore
      jwRating
      tomatoMeter
      certifiedFresh
      __typename
    }
    __typename
  }
  watchNowOffer(country: $country, platform: $platform) {
    ...WatchNowOffer
    __typename
  }
  availableTo(country: $country, platform: $platform) {
    availableToDate
    availableCountDown(country: $country)
    __typename
  }
  ... on Season {
    content(country: $country, language: $language) {
      seasonNumber
      __typename
    }
    show {
      __typename
      id
      objectId
      objectType
      content(country: $country, language: $language) {
        title
        fullPath
        __typename
      }
      watchNowOffer(country: $country, platform: $platform) {
        ...WatchNowOffer
        __typename
      }
    }
    __typename
  }
  ...TitleListData
}

fragment TitleListData on MovieOrShowOrSeason {
  __typename
  id
  objectId
  objectType
  dislikelistEntry {
    createdAt
    __typename
  }
  likelistEntry {
    createdAt
    __typename
  }
  ... on MovieOrShow {
    watchlistEntryV2 {
      createdAt
      __typename
    }
    customlistEntries {
      createdAt
      __typename
    }
    __typename
  }
  ... on Show {
    seenState(country: $country) {
      progress
      __typename
    }
    tvShowTrackingEntry {
      createdAt
      __typename
    }
    __typename
  }
  ... on Season {
    seenState(country: $country) {
      progress
      __typename
    }
    show {
      __typename
      id
      objectId
      objectType
      watchlistEntryV2 {
        createdAt
        __typename
      }
      seenState(country: $country) {
        progress
        __typename
      }
      tvShowTrackingEntry {
        createdAt
        __typename
      }
      customlistEntries {
        createdAt
        __typename
      }
    }
    __typename
  }
}

fragment Credit on Credit {
  role
  name
  characterName
  personId
  portraitUrl(profile: S332)
  profilePath
  __typename
}

fragment SponsoredAd on SponsoredRecommendationAd {
  bidId
  holdoutGroup
  campaign {
    name
    backgroundImages {
      imageURL
      size
      __typename
    }
    countdownTimer
    creativeType
    disclaimerText
    externalTrackers {
      type
      data
      __typename
    }
    hideDetailPageButton
    hideImdbScore
    hideJwScore
    hideRatings
    hideContent
    posterOverride
    playSRVideoAsGif
    promotionalImageUrl
    promotionalVideo {
      url
      __typename
    }
    promotionalTitle
    promotionalText
    promotionalProviderLogo
    promotionalProviderWideLogo
    watchNowLabel
    watchNowOffer {
      ...WatchNowOffer
      __typename
    }
    nodeOverrides {
      nodeId
      promotionalImageUrl
      watchNowOffer {
        standardWebURL
        __typename
      }
      __typename
    }
    node {
      nodeId: id
      __typename
      ... on MovieOrShowOrSeason {
        content(country: $country, language: $language) {
          fullPath
          posterUrl
          title
          originalReleaseYear
          scoring {
            imdbScore
            jwRating
            __typename
          }
          genres {
            shortName
            translation(language: $language)
            __typename
          }
          externalIds {
            imdbId
            __typename
          }
          backdrops(format: $format, profile: $backdropProfile) {
            backdropUrl
            __typename
          }
          isReleased
          __typename
        }
        objectId
        objectType
        offers(country: $country, platform: $platform, filter: {preAffiliate: true}) {
          monetizationType
          presentationType
          package {
            id
            packageId
            __typename
          }
          id
          __typename
        }
        __typename
      }
      ... on MovieOrShow {
        watchlistEntryV2 {
          createdAt
          __typename
        }
        __typename
      }
      ... on Show {
        seenState(country: $country) {
          seenEpisodeCount
          __typename
        }
        __typename
      }
      ... on Season {
        content(country: $country, language: $language) {
          seasonNumber
          __typename
        }
        show {
          __typename
          id
          objectId
          objectType
          content(country: $country, language: $language) {
            originalTitle
            __typename
          }
          watchlistEntryV2 {
            createdAt
            __typename
          }
        }
        __typename
      }
      ... on GenericTitleList {
        followedlistEntry {
          createdAt
          name
          __typename
        }
        id
        type
        content(country: $country, language: $language) {
          name
          visibility
          __typename
        }
        titles(country: $country, first: 40) {
          totalCount
          edges {
            cursor
            node: nodeV2 {
              content(country: $country, language: $language) {
                fullPath
                posterUrl
                title
                originalReleaseYear
                scoring {
                  imdbVotes
                  imdbScore
                  tomatoMeter
                  certifiedFresh
                  jwRating
                  __typename
                }
                isReleased
                __typename
              }
              id
              objectId
              objectType
              __typename
            }
            __typename
          }
          __typename
        }
        __typename
      }
    }
    __typename
  }
  __typename
}

fragment Episode on Episode {
  id
  objectId
  objectType
  seenlistEntry {
    createdAt
    __typename
  }
  uniqueOfferCount: offerCount(
    country: $country
    platform: $platform
    filter: {bestOnly: true}
  )
  flatrate: offers(
    country: $country
    platform: $platform
    filter: {monetizationTypes: [FLATRATE_AND_BUY, FLATRATE, ADS, CINEMA, FREE], bestOnly: true, preAffiliate: true}
  ) {
    id
    package {
      id
      clearName
      packageId
      __typename
    }
    __typename
  }
  buy: offers(
    country: $country
    platform: $platform
    filter: {monetizationTypes: [BUY], bestOnly: true, preAffiliate: true}
  ) {
    id
    package {
      id
      clearName
      packageId
      __typename
    }
    __typename
  }
  rent: offers(
    country: $country
    platform: $platform
    filter: {monetizationTypes: [RENT], bestOnly: true, preAffiliate: true}
  ) {
    id
    package {
      id
      clearName
      packageId
      __typename
    }
    __typename
  }
  free: offers(
    country: $country
    platform: $platform
    filter: {monetizationTypes: [ADS, FREE], bestOnly: true, preAffiliate: true}
  ) {
    id
    package {
      id
      clearName
      packageId
      __typename
    }
    __typename
  }
  fast: offers(
    country: $country
    platform: $platform
    filter: {monetizationTypes: [FAST], bestOnly: true, preAffiliate: true}
  ) {
    id
    package {
      id
      clearName
      packageId
      __typename
    }
    __typename
  }
  content(country: $country, language: $language) {
    __typename
    title
    shortDescription
    episodeNumber
    seasonNumber
    isReleased
    runtime
    upcomingReleases {
      releaseCountDown(country: $country)
      releaseDate
      releaseType
      label
      package {
        id
        packageId
        shortName
        clearName
        monetizationTypes
        icon(profile: S100)
        iconWide(profile: S160)
        hasRectangularIcon(country: $country, platform: WEB)
        planOffers(country: $country, platform: $platform) {
          retailPrice(language: $language)
          durationDays
          presentationType
          isTrial
          retailPriceValue
          currency
          __typename
        }
        __typename
      }
      __typename
    }
  }
  __typename
}

fragment BuyBoxOffers on MovieOrShowOrSeasonOrEpisode {
  __typename
  offerCount(country: $country, platform: $platform)
  maxOfferUpdatedAt(country: $country, platform: $platform)
  offersHistory(
    country: $country
    platform: $platform
    filterV2: {monetizationTypes: [FLATRATE, FLATRATE_AND_BUY, RENT, FREE, ADS, BUY, FAST], bestOnly: true, preAffiliate: true, fallbackToForeignOffers: $fallbackToForeignOffers, excludePackages: $excludePackages}
  ) {
    ...OffersHistory
    __typename
  }
  flatrate: offers(
    country: $country
    platform: $platform
    filter: {monetizationTypes: [FLATRATE, FLATRATE_AND_BUY, CINEMA], bestOnly: true, preAffiliate: true, fallbackToForeignOffers: $fallbackToForeignOffers, excludePackages: $excludePackages}
  ) {
    ...TitleOffer
    __typename
  }
  buy: offers(
    country: $country
    platform: $platform
    filter: {monetizationTypes: [BUY], bestOnly: true, preAffiliate: true, fallbackToForeignOffers: $fallbackToForeignOffers, excludePackages: $excludePackages}
  ) {
    ...TitleOffer
    offerSeasons
    minRetailPrice(country: $country, platform: $platform, language: $language)
    __typename
  }
  rent: offers(
    country: $country
    platform: $platform
    filter: {monetizationTypes: [RENT], bestOnly: true, preAffiliate: true, fallbackToForeignOffers: $fallbackToForeignOffers, excludePackages: $excludePackages}
  ) {
    ...TitleOffer
    offerSeasons
    minRetailPrice(country: $country, platform: $platform, language: $language)
    __typename
  }
  free: offers(
    country: $country
    platform: $platform
    filter: {monetizationTypes: [FREE, ADS], bestOnly: true, preAffiliate: true, fallbackToForeignOffers: $fallbackToForeignOffers, excludePackages: $excludePackages}
  ) {
    ...TitleOffer
    __typename
  }
  fast: offers(
    country: $country
    platform: $platform
    filter: {monetizationTypes: [FAST], bestOnly: true, preAffiliate: true, fallbackToForeignOffers: $fallbackToForeignOffers, excludePackages: $excludePackages}
  ) {
    ...FastOffer
    __typename
  }
  bundles(country: $country, platform: WEB) {
    node {
      id
      clearName
      icon(profile: S100)
      technicalName
      bundleId
      packages(country: $country, platform: $platform) {
        icon
        id
        iconWide(profile: S160)
        clearName
        packageId
        __typename
      }
      __typename
    }
    promotionUrl
    offer {
      ...TitleOffer
      __typename
    }
    __typename
  }
  ... on MovieOrShowOrSeason {
    promotedBundles(country: $country, platform: WEB) {
      node {
        id
        clearName
        icon(profile: S100)
        technicalName
        bundleId
        packages(country: $country, platform: $platform) {
          icon
          id
          clearName
          packageId
          iconWide(profile: S160)
          __typename
        }
        __typename
      }
      promotionUrl
      offer {
        ...TitleOffer
        __typename
      }
      __typename
    }
    promotedOffers(
      country: $country
      platform: WEB
      filter: {bestOnly: true, preAffiliate: true}
    ) {
      ...TitleOffer
      minRetailPrice(country: $country, platform: $platform, language: $language)
      __typename
    }
    __typename
  }
}

fragment OffersHistory on OfferHistory {
  __typename
  id
  country
  dateRanges {
    end
    start
    __typename
  }
  package {
    icon
    id
    iconWide(profile: S160)
    clearName
    packageId
    monetizationTypes
    __typename
  }
}

fragment FastOffer on Offer {
  ...TitleOffer
  availableTo
  availableFromTime
  availableToTime
  __typename
}

fragment TitleDetailModules on MovieOrShowOrSeason {
  titleModules(supportedContentTypes: []) {
    content {
      ... on ModuleContentTitles {
        titles {
          node {
            ...SimilarTitle
            __typename
          }
          __typename
        }
        __typename
      }
      ... on ModuleContentStreamingCharts {
        Titles {
          fullPath
          jwEntityID
          posterUrl
          title
          showTitle
          seasonNumber
          rankInfo {
            rank
            trend
            trendDifference
            updatedAt
            daysInTop10
            daysInTop100
            daysInTop1000
            daysInTop3
            topRank
            __typename
          }
          __typename
        }
        __typename
      }
      __typename
    }
    fomoScore
    template {
      anchor
      contentType
      technicalName
      __typename
    }
    __typename
  }
  __typename
}

fragment SimilarTitle on MovieOrShowOrSeason {
  id
  objectId
  objectType
  content(country: $country, language: $language) {
    title
    posterUrl
    fullPath
    genres {
      translation(language: $language)
      __typename
    }
    backdrops {
      backdropUrl
      __typename
    }
    scoring {
      imdbVotes
      imdbScore
      tomatoMeter
      certifiedFresh
      jwRating
      __typename
    }
    interactions {
      votesNumber
      __typename
    }
    __typename
  }
  ... on MovieOrShow {
    watchlistEntryV2 {
      createdAt
      __typename
    }
    likelistEntry {
      createdAt
      __typename
    }
    dislikelistEntry {
      createdAt
      __typename
    }
    __typename
  }
  ... on Movie {
    seenlistEntry {
      createdAt
      __typename
    }
    __typename
  }
  ... on Show {
    seenState(country: $country) {
      progress
      seenEpisodeCount
      __typename
    }
    __typename
  }
  ... on Season {
    content(country: $country, language: $language) {
      seasonNumber
      __typename
    }
    show {
      id
      objectId
      objectType
      __typename
      content(country: $country, language: $language) {
        title
        __typename
      }
    }
    __typename
  }
  __typename
}
"""
