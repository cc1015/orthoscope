from client import http
from errors import NotFound, UpstreamError

_FIELDS = [
    "accession", "protein_name", "organism_name", "sequence", "mass",
    "cc_subcellular_location", "xref_pdb", "cc_function",
    "cc_tissue_specificity", "xref_string", "gene_names", "xref_geneid",
]

_ANNOTATION_FIELDS = (
    "ft_var_seq,ft_variant,ft_non_cons,ft_non_std,ft_non_ter,ft_conflict,"
    "ft_unsure,ft_act_site,ft_binding,ft_dna_bind,ft_site,ft_mutagen,"
    "ft_intramem,ft_topo_dom,ft_transmem,ft_chain,ft_crosslnk,ft_disulfid,"
    "ft_carbohyd,ft_init_met,ft_lipid,ft_mod_res,ft_peptide,ft_propep,"
    "ft_signal,ft_transit,ft_strand,ft_helix,ft_turn,ft_coiled,ft_compbias,"
    "ft_domain,ft_motif,ft_region,ft_repeat,ft_zn_fing"
)


class UniProtClient():
    """
    Represents UniProt client.

    Attributes:
        BASE_URL (str): Base url.
    """
    BASE_URL = "https://rest.uniprot.org"
    SERVICE = "UniProt"

    def get_entry(self, protein_id, **kwargs) -> dict:
        """
        Gets UniProt information.

        Args:
            protein_id (str): Protein of interest.

        Returns:
            dict: UniProt data.
        """
        params = {"fields": _FIELDS}
        headers = {"accept": "application/json"}

        if kwargs.get('search'):
            params["query"] = f"protein_name:{protein_id} AND gene:{kwargs.get('gene')} AND taxonomy_id:{kwargs.get('organism')}"
            path = "search"
        else:
            path = protein_id

        url = '/'.join([self.BASE_URL, "uniprotkb", path])

        if kwargs.get('ref'):
            params = {
                "id": f"UniRef50_{protein_id}",
                "facetFilter": "member_id_type:uniprotkb_id",
                "size": "500",
            }
            headers = {"accept": "application/json"}
            url = '/'.join([self.BASE_URL, "uniref/%7Bid%7D/members"])

        r = http.get(url, service=self.SERVICE, headers=headers, params=params)

        if r.status_code == 404 and not (kwargs.get('search') or kwargs.get('ref')):
            raise NotFound(
                f"UniProt has no entry for accession {protein_id}.",
                hint="Check the accession at https://www.uniprot.org.",
            )

        if not r.ok:
            if kwargs.get('search') or kwargs.get('ref'):
                return {}
            raise UpstreamError(
                f"UniProt returned HTTP {r.status_code} for {protein_id}.",
            )

        return http.json_or_raise(r, service=self.SERVICE)

    def get_fasta(self, protein_id) -> str:
        url = '/'.join([self.BASE_URL, "uniprotkb", protein_id + ".fasta"])
        r = http.get(url, service=self.SERVICE)

        if not r.ok:
            raise UpstreamError(
                f"Could not download the FASTA sequence for {protein_id} "
                f"(HTTP {r.status_code})."
            )
        if not r.text.startswith(">"):
            raise UpstreamError(
                f"UniProt returned an empty or malformed FASTA for {protein_id}."
            )
        return r.text

    def get_annotations(self, protein_id) -> dict:
        url = f"{self.BASE_URL}/uniprotkb/{protein_id}.json"
        r = http.get(
            url, service=self.SERVICE, params={"fields": _ANNOTATION_FIELDS}
        )
        if not r.ok:
            return {}
        return http.json_or_raise(r, service=self.SERVICE)
