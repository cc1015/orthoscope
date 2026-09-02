from client.ncbi_client import NCBIClient


class NCBIOrthologFinder():
    ncbi_client = NCBIClient()

    def get_orthologs(self, gene_id, taxon_list) -> dict:
        data = self.ncbi_client.get_orthologs(gene_id, taxon_list)

        reports = data.get('reports') or []

        tax_gene_map = {
            report['gene']['tax_id']: report['gene']['gene_id']
            for report in reports
            if 'gene' in report and 'tax_id' in report['gene'] and 'gene_id' in report['gene']
        }

        final_map = {}
        for tax_id, g_id in tax_gene_map.items():
            protein_ref = self.ncbi_client.get_protein_reference_id(g_id)
            if protein_ref:
                final_map[tax_id] = protein_ref

        return final_map
