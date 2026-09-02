import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from errors import UpstreamError

DEFAULT_TIMEOUT = 30
DOWNLOAD_TIMEOUT = 120


def _build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "POST"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


SESSION = _build_session()


def request(method: str, url: str, *, service: str, timeout: int = DEFAULT_TIMEOUT, **kwargs):
    try:
        return SESSION.request(method, url, timeout=timeout, **kwargs)
    except requests.Timeout as e:
        raise UpstreamError(
            f"{service} did not respond within {timeout}s.",
            hint="The service may be busy. Try again in a moment.",
        ) from e
    except requests.exceptions.SSLError as e:
        raise UpstreamError(
            f"Could not verify {service}'s TLS certificate.",
            hint="If you are behind a TLS-inspecting proxy, point REQUESTS_CA_BUNDLE "
                 "at its CA certificate rather than disabling verification.",
        ) from e
    except requests.RequestException as e:
        raise UpstreamError(
            f"Could not reach {service}: {type(e).__name__}.",
            hint="Check your network connection.",
        ) from e


def get(url: str, *, service: str, **kwargs):
    return request("GET", url, service=service, **kwargs)


def post(url: str, *, service: str, **kwargs):
    return request("POST", url, service=service, **kwargs)


def json_or_raise(response, *, service: str):
    try:
        return response.json()
    except ValueError as e:
        raise UpstreamError(
            f"{service} returned a non-JSON response (HTTP {response.status_code}).",
        ) from e
