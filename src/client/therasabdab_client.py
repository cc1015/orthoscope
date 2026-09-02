import pandas as pd
from io import StringIO

from client import http
from errors import UpstreamError


class TherasabdabClient():
    """
    Represents Thera-SabDab client.

    Attributes:
        BASE_URL (str): Base url.
    """
    BASE_URL = "https://opig.stats.ox.ac.uk/webapps/sabdab-sabpred/therasabdab/search/"
    SERVICE = "Thera-SAbDab"

    def fetch(self, protein_name, **kwargs):
        """
        Gets therasabdab data for a given protein.

        Args:
            protein_name (str): Protein of interest.

        Returns:
            dict: dataframe of thereasabdab data table.
        """
        params = {
            "theraformat": "All",
            "yearproposed": "All",
            "clintrial": "All",
            "stat": "All",
            "target": protein_name,
            "structures": "No",
        }

        r = http.post(self.BASE_URL, service=self.SERVICE, data=params)

        if not r.ok:
            raise UpstreamError(
                f"Thera-SAbDab returned HTTP {r.status_code}.",
            )

        if not r.text:
            return {}

        try:
            tables = pd.read_html(StringIO(r.text))
        except ValueError:
            return {}

        return tables[0] if tables else {}
