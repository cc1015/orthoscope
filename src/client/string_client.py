from pathlib import Path
from time import sleep

from client import http
from errors import UpstreamError
from utils.file_utils import ensure_directory, safe_open_write


class StringClient():
    """
    Represents STRING client.

    Attributes:
        BASE_URL (str): Base url.
    """
    BASE_URL = "https://string-db.org/api"
    SERVICE = "STRING-DB"

    def fetch(self, protein_name, **kwargs) -> str:
        """
        Gets STRING network image file of given protein.

        Args:
            protein_name (str): Protein of interest.

        Returns:
            str: Image file path.
        """
        params = {
            "identifiers": kwargs.get('string_id'),
            "species": 9606,
            "network_flavor": "confidence",
            "network_type": "physical",
            "add_color_nodes": 20,
        }

        url = "/".join([self.BASE_URL, "image", "network"])
        r = http.post(url, service=self.SERVICE, data=params)

        if not r.ok:
            raise UpstreamError(
                f"STRING-DB returned HTTP {r.status_code} for the network image.",
            )
        if not r.headers.get("content-type", "").startswith("image/"):
            raise UpstreamError(
                "STRING-DB returned a non-image response for the network request.",
            )

        output_dir = Path(__file__).parent.parent.parent
        file_name = output_dir / f"output_{protein_name}" / "string_network.png"
        ensure_directory(file_name.parent)

        with safe_open_write(file_name, 'wb') as fh:
            fh.write(r.content)

        sleep(1)
        return str(file_name)
