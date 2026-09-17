# TODO: Validate
"""An Amazon channel's source is pictured by the channel's own logo.

The logo a source is given when a title on it is imported, written onto the
sources that were made before the plugin read one. Each is the logo the offer
card carried on a page already stored for that channel.
"""

from alembic import op

revision = "c6f1a8d3e527"
down_revision = "b5e7c210d934"
branch_labels = None
depends_on = None


_CHANNEL_LOGOS = """
VALUES
    ('A&E Crime Central on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/aetncrimecentral/logos/channels-logo-focus._CB583952641_.png'),
    ('ALLBLK on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/s-z/umc/logos/channels-logo-focus._CB554102811_.png'),
    ('AMC+ on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/amcplus/logos/channels-logo-focus._CB558057714_.png'),
    ('Acorn TV on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/acorn/logos/channels-logo-focus._CB801031857_.png'),
    ('Ameba on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/amebatv/logos/channels-logo-white._CB582211343_.png'),
    ('BBC Select on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/bbcselect/logos/channels-logo-focus._CB579409821_.png'),
    ('BFI Player Classics on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/bfiplayer/logos/channels-logo-white._CB582209991_.png'),
    ('Best Westerns Ever on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/bestwesternsever/logos/channels-logo-white._CB582209900_.png'),
    ('Best of British Television on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/bestofbritish/logos/channels-logo-white._CB582211159_.png'),
    ('BritBox on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/britbox/logos/channels-logo-focus._CB773548496_.png'),
    ('BroadwayHD on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/broadwayhd/logos/channels-logo-focus._CB582209994_.png'),
    ('CJ ENM Selects on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/cjus/logos/channels-logo-white._CB541110641_.png'),
    ('Cinemax on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/cinemax/logos/channels-logo-white._CB769029336_.png'),
    ('Cineverse on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/cineverseus/logos/channels-logo-white._CB552929291_.png'),
    ('Cohen Media Channel on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/cohen/logos/channels-logo-white._CB582210432_.png'),
    ('Crunchyroll on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/crunchyrollus/logos/channels-logo-white._CB544481510_.png'),
    ('Curiosity Stream on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/curiositystreamstandard/logos/channels-logo-focus._CB565300023_.png'),
    ('Curiosity University on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/curiosityuniversityus/logos/channels-logo-focus._CB564714994_.png'),
    ('Daring Docs on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/daringdocs/logos/channels-logo-white._CB581186023_.png'),
    ('Dekkoo on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/dekkoo/logos/channels-logo-white._CB582210474_.png'),
    ('Demand Africa on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/s-z/theafricachannelus/logos/channels-logo-focus._CB581181417_.png'),
    ('Docurama on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/docuramaFilms/logos/channels-logo-white._CB582210219_.png'),
    ('Doki on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/g-l/jedge/logos/channels-logo-white._CB581345092_.png'),
    ('Dove Channel on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/dove/logos/channels-logo-white._CB550639367_.png'),
    ('Dox on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/dox/logos/channels-logo-white._CB581344924_.png'),
    ('Echoboom Sports on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/echoboom/logos/channels-logo-white._CB581339112_.png'),
    ('Eros Now on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/erosnow/logos/channels-logo-white._CB584008901_.png'),
    ('FUEL TV+ on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/s-z/vaporvue/logos/channels-logo-focus._CB581339213_.png'),
    ('Fandor on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/fandor/logos/channels-logo-white._CB581339118_.png'),
    ('Fear Factory on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/fearfactory/logos/channels-logo-white._CB561548019_.png'),
    ('Film Movement Plus on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/filmmovementus/logos/channels-logo-white._CB581223616_.png'),
    ('FilmBox+ Now on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/filmbox/logos/channels-logo-focus._CB804614991_.png'),
    ('FlixLatino on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/flixlatino/logos/channels-logo-focus._CB581340618_.png'),
    ('France Channel on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/france_channel/logos/channels-logo-focus._CB581339475_.png'),
    ('Full Moon on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/fullmoon/logos/channels-logo-white._CB581339275_.png'),
    ('Fuse+ on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/fuse/logos/channels-logo-white._CB561646194_.png'),
    ('Gaia on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/g-l/gaia/logos/channels-logo-white._CB582500270_.png'),
    ('Great American Pure Flix on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/m-r/pureflixus1/logos/channels-logo-focus._CB804963743_.png'),
    ('HBO Max on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/g-l/hbomaxus/logos/channels-logo-focus._CB790368861_.png'),
    ('HIDIVE on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/g-l/hidiveus/logos/channels-logo-focus._CB583953377_.png'),
    ('HISTORY Vault on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/g-l/historyvault/logos/channels-logo-focus._CB567315583_.png'),
    ('Hallmark+ on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/g-l/hallmark/logos/channels-logo-white._CB565032671_.png'),
    ('Here TV on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/g-l/heretv/logos/channels-logo-white._CB581350553_.png'),
    ('Hi-YAH! on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/g-l/hiyah/logos/channels-logo-white._CB584007768_.png'),
    ('Howdy on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/g-l/howdyus/logos/channels-logo-focus._CB786000264_.png'),
    ('Indie Club on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/g-l/indieclub/logos/channels-logo-white._CB581350927_.png'),
    ('IndiePix Unlimited on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/g-l/indiepix/logos/channels-logo-white._CB581173456_.png'),
    ('Inside Outside on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/g-l/insideoutside/logos/channels-logo-white._CB581349597_.png'),
    ('Kartoon Channel on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/g-l/kidgenius/logos/channels-logo-white._CB581349519_.png'),
    ('Kidstream on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/g-l/kidstream/logos/channels-logo-focus._CB804278666_.png'),
    ('Kino Film Collection on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/g-l/kinofilmcollectionus/logos/channels-logo-focus._CB584014573_.png'),
    ('Lifetime Movie Club on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/g-l/lifetimemovieclub/logos/channels-logo-white._CB582497175_.png'),
    ('Lionsgate+ on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/g-l/lionsgateplusus/logos/channels-logo-white._CB783594218_.png'),
    ('MGM+ on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/epix/logos/channels-logo-focus._CB558067261_.png'),
    ('MHz Choice on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/m-r/mhzchoice/logos/channels-logo-white._CB568905102_.png'),
    ('MIDNIGHT PULP on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/contv/logos/channels-logo-white._CB581346361_.png'),
    ('MUBI on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/m-r/mubi/logos/channels-logo-white._CB560101538_.png'),
    ('Magnolia Selects on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/m-r/magnoliaselects/logos/channels-logo-white._CB581187047_.png'),
    ('Marquee TV on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/m-r/marqueetvus/logos/channels-logo-focus._CB795898777_.png'),
    ('Minno Kids on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/m-r/minnokidsus/logos/channels-logo-focus._CB803609515_.png'),
    ('Monsters and Nightmares on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/m-r/mandn/logos/channels-logo-white._CB581345507_.png'),
    ('MovieSphere+ on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/s-z/tribecashortlist/logos/channels-logo-focus._CB540608047_.png'),
    ('OUTtv on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/m-r/outtvus/logos/channels-logo-white._CB581346251_.png'),
    ('Outside TV Features on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/m-r/outside/logos/channels-logo-white._CB581348393_.png'),
    ('PBS Documentaries on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/m-r/pbsdoc/logos/channels-logo-focus._CB768745647_.png'),
    ('PBS Living on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/m-r/pbsliving/logos/channels-logo-white._CB583953200_.png'),
    ('PBS Masterpiece on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/m-r/masterpiece/logos/channels-logo-white._CB556028109_.png'),
    ('Paramount+ on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/cbsaacf/logos/channels-logo-focus._CB762699243_.png'),
    ('Passionflix on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/m-r/passionflix/logos/channels-logo-white._CB581387651_.png'),
    ('Pinoy Box Office on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/m-r/pbo/logos/channels-logo-white._CB581387299_.png'),
    ('PlayKids Learning on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/g-l/hopsterus/logos/channels-logo-focus._CB785717091_.png'),
    ('Qello Concerts on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/m-r/qelloconcerts/logos/channels-logo-focus._CB582484483_.png'),
    ('RetroCrush on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/s-z/viewster/logos/channels-logo-focus._CB581387119_.png'),
    ('Revry on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/m-r/revry/logos/channels-logo-white._CB581386467_.png'),
    ('STARZ on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/s-z/starzSub/logos/channels-logo-focus._CB761191956_.png'),
    ('Screambox on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/s-z/screambox/logos/channels-logo-white._CB550329513_.png'),
    ('ScreenPix on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/s-z/screenpix/logos/channels-logo-white._CB583953157_.png'),
    ('Sensical on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/s-z/sensicalus/logos/channels-logo-focus._CB549065053_.png'),
    ('Shout! TV on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/s-z/shoutfactory/logos/channels-logo-white._CB795359602_.png'),
    ('Shudder on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/s-z/shuddertv/logos/channels-logo-white._CB757005485_.png'),
    ('Sony Pictures Core on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/s-z/spcoreus/logos/channels-logo-focus._CB777877023_.png'),
    ('Stingray Djazz on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/s-z/stingraydjazz/logos/channels-logo-white._CB581386909_.png'),
    ('Strand Releasing on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/s-z/strandreleasing/logos/channels-logo-white._CB581389519_.png'),
    ('Sundance Now on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/docclub/logos/channels-logo-focus._CB558043814_.png'),
    ('Tastemade on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/s-z/tastemade/logos/channels-logo-white._CB551532349_.png'),
    ('The Coda Collection on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/codacollection/logos/channels-logo-white._CB582209998_.png'),
    ('The Surf Network on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/s-z/thesurfnetwork/logos/channels-logo-focus._CB581389944_.png'),
    ('True Royalty on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/s-z/trueroyalty/logos/channels-logo-white._CB584008439_.png'),
    ('UP Faith & Family on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/s-z/upfaithfamily/logos/channels-logo-white._CB561270323_.png'),
    ('Vemox Cine on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/s-z/vemoxcine/logos/channels-logo-white._CB581388792_.png'),
    ('ViX Gratis on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/s-z/vixus/logos/channels-logo-white._CB558043534_.png'),
    ('ViX Premium on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/s-z/vixplusus/logos/channels-logo-white._CB558043175_.png'),
    ('Viaplay on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/s-z/viaplayus/logos/channels-logo-white._CB560422780_.png'),
    ('Warriors & Gangsters on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/s-z/wag/logos/channels-logo-white._CB581388714_.png'),
    ('Wonder Project on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/s-z/wonderprojectus/logos/channels-logo-focus._CB799323327_.png'),
    ('XLTV on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/s-z/xltv/logos/channels-logo-white._CB581398632_.png'),
    ('XiveTV Documentaries on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/s-z/xivetv/logos/channels-logo-white._CB581400301_.png'),
    ('Yippee Kids TV on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/s-z/yippeetvus/logos/channels-logo-focus._CB779335278_.png'),
    ('aspireTV+ on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/aspireTVus/logos/channels-logo-focus._CB567532506_.png'),
    ('discovery+ on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/a-f/discoveryplus/logos/channels-logo-white._CB773000790_.png'),
    ('iNDIEFLIX on Amazon', 'https://m.media-amazon.com/images/G/01/digital/video/merch/subs/benefit-id/g-l/indieflix/logos/channels-logo-focus._CB777814596_.png')
"""

_SET_CHANNEL_LOGOS = f"""
    UPDATE source
    SET favicon_url = channel_logo.logo_url
    FROM plugin, ({_CHANNEL_LOGOS}) AS channel_logo (source_key, logo_url)
    WHERE plugin.id = source.plugin_id
      AND plugin.key = 'Amazon'
      AND source.key = channel_logo.source_key
      AND source.favicon_url IS DISTINCT FROM channel_logo.logo_url
"""

_RESTORE_CHANNEL_LOGOS = f"""
    UPDATE source
    SET favicon_url = 'https://www.primevideo.com/favicon.ico'
    FROM plugin, ({_CHANNEL_LOGOS}) AS channel_logo (source_key, logo_url)
    WHERE plugin.id = source.plugin_id
      AND plugin.key = 'Amazon'
      AND source.key = channel_logo.source_key
"""


# TODO: Validate
def upgrade() -> None:
    op.execute(_SET_CHANNEL_LOGOS)


# TODO: Validate
def downgrade() -> None:
    op.execute(_RESTORE_CHANNEL_LOGOS)
