import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "OrthoScope",
  description: "Automatic cross-species protein analysis.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <h1>OrthoScope</h1>
        <p className="meta">Automatic cross-species protein analysis.</p>

        <p className="meta">
          Given a protein name and UniProt accession, OrthoScope will:
        </p>
        <ul className="meta">
          <li>find all orthologs</li>
          <li>align and report RMSD</li>
          <li>render 3D structure</li>
          <li>show associated protein networks</li>
        </ul>

        {children}

        <hr />
        <address>
          Data from UniProt, AlphaFold, STRING and NCBI. Alignments by MAFFT
          and PyMOL.
        </address>
      </body>
    </html>
  );
}
