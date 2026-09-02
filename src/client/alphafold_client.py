from client import http
from errors import UpstreamError


class AlphaFoldClient:
    """
    Represents AlphaFold client.

    Attributes:
        BASE_URL (str): Base url.
    """
    BASE_URL = "https://alphafold.ebi.ac.uk"
    SERVICE = "AlphaFold"

    def get_af_pdb(self, protein_id: str, **kwargs) -> dict:
        """
        Gets AlphaFold PDB file of given protein.

        Args:
            protein_id (str): Protein of interest.

        Returns:
            dict: File name and content, or {} if AlphaFold has no model.
        """
        url = f"{self.BASE_URL}/api/prediction/{protein_id}"
        r = http.get(url, service=self.SERVICE)

        if not r.ok:
            return {}

        pdb_list = http.json_or_raise(r, service=self.SERVICE)
        if not pdb_list:
            return {}

        response_dict = next(
            (p for p in pdb_list if p.get('uniprotAccession') == protein_id),
            pdb_list[0],
        )

        pdb_url = response_dict.get('pdbUrl')
        if not pdb_url:
            return {}

        pdb_r = http.get(
            pdb_url, service=self.SERVICE, timeout=http.DOWNLOAD_TIMEOUT
        )
        if not pdb_r.ok:
            raise UpstreamError(
                f"AlphaFold listed a model for {protein_id} but the PDB "
                f"download failed (HTTP {pdb_r.status_code})."
            )

        return {
            'file_name': pdb_url.rsplit("/", 1)[-1],
            'content': pdb_r.content,
        }
