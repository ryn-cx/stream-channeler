# TODO: Validate
import requests
from loguru import logger


class IPValidationError(Exception):
    """Raised when the current IP address does not match the expected IP."""


class _IPCache:
    ip: str | None = None


def check_ip_matches(expected_ip: str) -> None:
    """
    Validates the current IP address against an expected IP.

    The IP address is fetched once and cached for subsequent calls.
    Raises IPValidationError if the current IP doesn't match the expected IP.

    Args:
        expected_ip: The IP address to validate against.

    Raises:
        IPValidationError: If the current IP doesn't match the expected IP.
    """
    # Check and cache IP on first call
    if _IPCache.ip is None:
        _IPCache.ip = requests.get(
            "https://checkip.amazonaws.com",
            timeout=5,
        ).text.strip()

    if _IPCache.ip != expected_ip:
        error_msg = f"Invalid IP address: current IP {_IPCache.ip} does not match expected IP {expected_ip}"
        logger.error(error_msg)
        raise IPValidationError(error_msg)


def check_ip_not_matches(blocked_ip: str) -> None:
    """
    Validates the current IP address is NOT a blocked IP.

    The IP address is fetched once and cached for subsequent calls.
    Raises IPValidationError if the current IP matches the blocked IP.

    Args:
        blocked_ip: The IP address that should not be allowed.

    Raises:
        IPValidationError: If the current IP matches the blocked IP.
    """
    # Check and cache IP on first call
    if _IPCache.ip is None:
        _IPCache.ip = requests.get(
            "https://checkip.amazonaws.com",
            timeout=5,
        ).text.strip()

    if _IPCache.ip == blocked_ip:
        error_msg = (
            f"Invalid IP address: current IP {_IPCache.ip} matches bad IP {blocked_ip}"
        )
        logger.error(error_msg)
        raise IPValidationError(error_msg)

    if _IPCache.ip == "changethis":
        error_msg = "Invalid IP address: current IP is set to 'changethis', please update configuration."
        logger.error(error_msg)
        raise IPValidationError(error_msg)
