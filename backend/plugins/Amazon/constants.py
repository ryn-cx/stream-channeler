# Clicking a link to a title on primevideo.com
#   https://www.primevideo.com/detail/0GTKUFQSFLP1YVFDMW9IR56I90
PRIME_VIDEO_URL_REGEX = r"\/detail\/(?P<link_id>[A-Z0-9]{10,})"


# Clicking a link to a title on amazon.com
#   https://www.amazon.com/gp/video/detail/B0D9MYVLNM
AMAZON_URL_REGEX = r"\/gp\/video\/detail\/(?P<link_id>[A-Z0-9]{10,})"
