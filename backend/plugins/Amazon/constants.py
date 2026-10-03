# Clicking a link to a title on primevideo.com
#   https://www.primevideo.com/detail/0GTKUFQSFLP1YVFDMW9IR56I90
PRIME_VIDEO_URL_REGEX = r"\/detail\/(?P<link_id>[A-Z0-9]{10,})"


# Clicking a link to a title on amazon.com
#   https://www.amazon.com/gp/video/detail/B0D9MYVLNM
AMAZON_URL_REGEX = r"\/gp\/video\/detail\/(?P<link_id>[A-Z0-9]{10,})"


# Clicking a link to a title from Amazon's storefront, which names the title in the
# path ahead of the id as often as it does not.
#   https://www.amazon.com/dp/B005C8DB7E?lv=shuf&channelId=500&plpRedirect=mhFallback
#   https://www.amazon.com/The-Expanse-Season-1/dp/B01H6Z8HLU
AMAZON_PRODUCT_URL_REGEX = r"(?:\/[^\/?#]+)?\/dp\/(?P<link_id>[A-Z0-9]{10,})"
