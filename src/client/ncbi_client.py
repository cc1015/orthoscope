from bs4 import BeautifulSoup

from client import http
from errors import UpstreamError


class NCBIClient():
    """
    Represents NCBI client.
    """
    SERVICE = "NCBI"

    def get_orthologs(self, gene_id, taxon_list) -> dict:
        """
        Gets taxon_list orthologs of given gene_id.
        """
        url = f"https://api.ncbi.nlm.nih.gov/datasets/v2/gene/id/{gene_id}/orthologs"
        r = http.get(url, service=self.SERVICE, params={"taxon_filter": taxon_list})

        if not r.ok:
            return {}
        return http.json_or_raise(r, service=self.SERVICE)

    def get_protein_reference_id(self, gene_id):
        """
        Gets protein ortholog information.

        Returns a (source, id) tuple, or "" if nothing usable is on the page.
        """
        url = f"https://www.ncbi.nlm.nih.gov/gene/{gene_id}"
        r = http.get(url, service=self.SERVICE)

        if not r.ok:
            return ""

        soup = BeautifulSoup(r.text, "html.parser")
        section = soup.find("section", class_="rprt-section gene-reference-sequences")
        if not section:
            return ""

        mrna_sections = section.find_all("h4", id=lambda x: x and x.startswith("mrnaandproteins"))
        if not mrna_sections:
            return ""

        ol = mrna_sections[0].find_next("ol")
        if not ol:
            return ""

        items = ol.find_all("li")
        if not items:
            return ""

        for label in ("UniProtKB/Swiss-Prot", "UniProtKB/TrEMBL"):
            for item in items:
                dt = item.find("dt", string=lambda s, l=label: s and l in s)
                if dt:
                    link = dt.find_next("a")
                    if link:
                        return ('uniprot', link.get_text(strip=True))

        p_tag = items[0].find("p")
        if p_tag and "→" in p_tag.text:
            parts = p_tag.text.split("→")[1].strip().split()
            if parts:
                return ('ncbi', parts[0])

        return ""

    def get_entry(self, protein_id):
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        params = {
            "db": "protein",
            "id": protein_id,
            "rettype": "fasta",
            "retmode": "text",
        }
        r = http.get(url, service=self.SERVICE, params=params)

        if not r.ok or not r.text.startswith(">"):
            raise UpstreamError(
                f"NCBI returned no usable FASTA for {protein_id} "
                f"(HTTP {r.status_code}).",
            )
        return ('ncbi', r.text)
