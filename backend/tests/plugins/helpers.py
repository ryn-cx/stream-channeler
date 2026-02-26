# TODO: Validate


def get_domains(base_domain: str) -> list[str]:
    """Generate a list of possible domain variations for a given base domain."""
    return [
        f"https://www.{base_domain}",
        f"http://www.{base_domain}",
        f"https://{base_domain}",
        f"http://{base_domain}",
        f"www.{base_domain}",
        base_domain,
    ]


def get_urls(base_domains: list[str], subpaths: list[str]) -> list[str]:
    """Generate a list of possible URL variations for a given base URL."""
    for base_domain in base_domains:
        domains = get_domains(base_domain)
        urls: list[str] = []
        for domain in domains:
            for subpath in subpaths:
                urls.append(domain + subpath)
    return urls
