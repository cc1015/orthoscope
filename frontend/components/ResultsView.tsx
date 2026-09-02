"use client";

import MolStarViewer from "@/components/MolStarViewer";
import { fileUrl } from "@/lib/api";
import type { FeatureOut, JobResponse, WarningOut } from "@/lib/types";

const HUMAN_COLOR = 0x2f7a4f;
const ORTHOLOG_COLOR = 0x8e4a96;

const FEATURE_COLOR: Record<string, string> = {
  ECD: "#2f7a4f",
  CHAIN: "#2f7a4f",
  TM: "#b23a2e",
  SIGNAL: "#8e4a96",
  CYTO: "#8e4a96",
  GLYCOSYLATION: "#b57722",
};

export default function ResultsView({ result }: { result: JobResponse }) {
  const { human, orthologs } = result;
  const p = human.passport_table_data;
  const aliases = Array.isArray(p.aliases) ? p.aliases.join(", ") : p.aliases;
  const length = Number(p.length) || human.seq.length;

  return (
    <div>
      <h2>{p.rec_name || human.name}</h2>

      <div className="stats">
        <Stat k="Length" v={`${p.length} aa`} />
        <Stat k="Mass" v={`${p.mass} kDa`} />
        <Stat k="Features" v={String(human.features.length)} />
        <Stat k="Orthologs" v={String(orthologs.length)} />
      </div>

      {result.warnings.length > 0 && <Warnings warnings={result.warnings} />}

      <table>
        <tbody>
          <Row label="Target name" value={p.rec_name} />
          <Row label="Aliases" value={aliases} />
          <Row label="Gene" value={p.gene_id} />
          <Row label="UniProt" value={<span className="mono">{human.id}</span>} />
        </tbody>
      </table>

      <p className="meta">
        Jump to: <a href="#orthologs">Orthologs</a> &middot;{" "}
        <a href="#domains">Domains</a> &middot;{" "}
        <a href="#structure">Structure</a> &middot;{" "}
        <a href="#sequence">Sequence</a> &middot;{" "}
        <a href="#network">Network</a>
      </p>

      <hr />

      <Orthologs orthologs={orthologs} human={human} />

      <hr />

      <Domains features={human.features} length={length} />

      <hr />

      <Structure human={human} />

      <hr />

      <Sequence human={human} />

      <hr />

      <Network human={human} />
    </div>
  );
}

function Stat({ k, v }: { k: string; v: string }) {
  return (
    <div className="stat">
      <span className="k">{k}</span>
      <span className="v">{v}</span>
    </div>
  );
}

function Row({ label, value }: { label: string; value?: React.ReactNode }) {
  return (
    <tr>
      <th style={{ width: "9rem" }}>{label}</th>
      <td>{value || <span className="meta">&mdash;</span>}</td>
    </tr>
  );
}

function Orthologs({
  orthologs,
  human,
}: {
  orthologs: JobResponse["orthologs"];
  human: JobResponse["human"];
}) {
  const referenceUrl = fileUrl(human.reference_pdb_url);
  const superposed = orthologs.filter(
    (o) => o.aligned_pdb_url || o.structure_alignment_image_url
  );

  return (
    <section>
      <h3 id="orthologs">Orthologs</h3>
      {orthologs.length === 0 ? (
        <p>No orthologs were found.</p>
      ) : (
        <>
          <table>
            <thead>
              <tr>
                <th>Organism</th>
                <th>Accession</th>
                <th className="num">RMSD (Å)</th>
                <th>Files</th>
              </tr>
            </thead>
            <tbody>
              {orthologs.map((o) => (
                <tr key={`${o.organism}-${o.id}`}>
                  <td>
                    <i>{o.scientific_name}</i>
                  </td>
                  <td className="mono">{o.id}</td>
                  <td className="num">
                    {o.rmsd != null ? (
                      o.rmsd.toFixed(2)
                    ) : (
                      <span className="meta">&mdash;</span>
                    )}
                  </td>
                  <td>
                    {o.fasta_url && (
                      <a href={fileUrl(o.fasta_url)!} download>
                        FASTA
                      </a>
                    )}
                    {o.fasta_url && o.pdb_url && " · "}
                    {o.pdb_url && (
                      <a href={fileUrl(o.pdb_url)!} download>
                        PDB
                      </a>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {superposed.length > 0 && (
            <div className="grid grid-2">
                {superposed.map((o) => {
                  const alignedUrl = fileUrl(o.aligned_pdb_url);
                  return (
                    <div className="panel panel-flush" key={o.id}>
                      <h4>
                        <i>{o.scientific_name}</i>
                      </h4>
                      {alignedUrl && referenceUrl ? (
                        <MolStarViewer
                          height={300}
                          structures={[
                            { url: referenceUrl, color: HUMAN_COLOR },
                            { url: alignedUrl, color: ORTHOLOG_COLOR },
                          ]}
                        />
                      ) : (
                        <img
                          src={fileUrl(o.structure_alignment_image_url)!}
                          alt={`Structural alignment of ${o.scientific_name} onto human`}
                        />
                      )}
                      <p className="caption">
                        <Swatch color={HUMAN_COLOR} /> human{"  "}
                        <Swatch color={ORTHOLOG_COLOR} />{" "}
                        <i>{o.scientific_name}</i>
                        {o.rmsd != null && (
                          <> &mdash; RMSD {o.rmsd.toFixed(2)} Å</>
                        )}
                        {alignedUrl && (
                          <>
                            {" "}
                            &middot;{" "}
                            <a href={alignedUrl} download>
                              aligned PDB
                            </a>
                          </>
                        )}
                      </p>
                    </div>
                  );
                })}
            </div>
          )}
        </>
      )}
    </section>
  );
}

function Domains({
  features,
  length,
}: {
  features: FeatureOut[];
  length: number;
}) {
  if (!features.length || !length) {
    return (
      <section>
        <h3 id="domains">Domains</h3>
        <p>No features annotated.</p>
      </section>
    );
  }

  const tracks = Array.from(new Set(features.map((f) => f.annotation)));
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => Math.round(f * length));

  return (
    <section>
      <h3 id="domains">Domains</h3>

      <div style={{ margin: "0.75rem 0" }}>
        {tracks.map((t) => (
          <div
            key={t}
            style={{
              display: "grid",
              gridTemplateColumns: "8.5rem 1fr",
              gap: "0.6rem",
              alignItems: "center",
              marginBottom: "0.3rem",
            }}
          >
            <span className="meta">{t}</span>
            <div className="track">
              {features
                .filter((f) => f.annotation === t)
                .map((f, i) => (
                  <span
                    key={i}
                    title={`${f.annotation} ${f.start}–${f.end}${f.note ? ` · ${f.note}` : ""}`}
                    style={{
                      left: `${((f.start - 1) / length) * 100}%`,
                      width: `max(2px, ${((f.end - f.start + 1) / length) * 100}%)`,
                      background: FEATURE_COLOR[f.annotation] ?? "#1b1b19",
                    }}
                  />
                ))}
            </div>
          </div>
        ))}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "8.5rem 1fr",
            gap: "0.6rem",
          }}
        >
          <span />
          <div className="axis">
            {ticks.map((t) => (
              <span key={t}>{t}</span>
            ))}
          </div>
        </div>
      </div>

      <details>
        <summary>All {features.length} features</summary>
        <table>
          <thead>
            <tr>
              <th>Type</th>
              <th className="num">Start</th>
              <th className="num">End</th>
              <th>Note</th>
            </tr>
          </thead>
          <tbody>
            {features.map((f, i) => (
              <tr key={i}>
                <td>
                  <span
                    style={{
                      display: "inline-block",
                      width: "0.55rem",
                      height: "0.55rem",
                      marginRight: "0.4rem",
                      background: FEATURE_COLOR[f.annotation] ?? "#1b1b19",
                    }}
                    aria-hidden
                  />
                  {f.annotation}
                </td>
                <td className="num">{f.start}</td>
                <td className="num">{f.end}</td>
                <td>{f.note || <span className="meta">&mdash;</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </section>
  );
}

function Structure({ human }: { human: JobResponse["human"] }) {
  if (!human.pdb_url) {
    return (
      <section>
        <h3 id="structure">Structure</h3>
        <p>No predicted structure available.</p>
      </section>
    );
  }

  const legend = Object.keys(FEATURE_COLOR).filter((k) =>
    human.features.some((f) => f.annotation === k)
  );

  return (
    <section>
      <h3 id="structure">Structure</h3>
      <div className="grid grid-2">
        <div className="panel panel-flush">
          <h4>AlphaFold model</h4>
          <MolStarViewer
            height={300}
            structures={[{ url: fileUrl(human.pdb_url)! }]}
          />
          <p className="caption">
            <a href={fileUrl(human.pdb_url)!} download>
              PDB
            </a>
          </p>
        </div>

        {human.annotated_structure_image_url && (
          <div className="panel panel-flush">
            <h4>Coloured by feature</h4>
            <img
              src={fileUrl(human.annotated_structure_image_url)!}
              alt="AlphaFold structure coloured by annotated feature"
            />
            <p className="caption">
              {legend.map((k, i) => (
                <span key={k}>
                  {i > 0 && "  "}
                  <span
                    style={{
                      display: "inline-block",
                      width: "0.55rem",
                      height: "0.55rem",
                      marginRight: "0.25rem",
                      background: FEATURE_COLOR[k],
                    }}
                    aria-hidden
                  />
                  {k}
                </span>
              ))}
            </p>
          </div>
        )}
      </div>
    </section>
  );
}

function Sequence({ human }: { human: JobResponse["human"] }) {
  const downloads = [
    { url: human.fasta_url, label: "FASTA" },
    { url: human.genbank_url, label: "Annotated GenBank" },
    { url: human.alignment_fasta_url, label: "MAFFT alignment" },
  ].filter((d) => d.url);

  const lines = human.seq.match(/.{1,60}/g) ?? [];

  return (
    <section>
      <h3 id="sequence">Sequence</h3>
      <p className="meta">
        {human.seq.length} aa &middot;{" "}
        {downloads.map((d, i) => (
          <span key={d.label}>
            {i > 0 && " · "}
            <a href={fileUrl(d.url)!} download>
              {d.label}
            </a>
          </span>
        ))}
      </p>
      <details>
        <summary>Show residues</summary>
        <pre>
          {lines
            .map((line, i) => `${String(i * 60 + 1).padStart(5, " ")}  ${line}`)
            .join("\n")}
        </pre>
      </details>
    </section>
  );
}

function Network({ human }: { human: JobResponse["human"] }) {
  return (
    <section>
      <h3 id="network">Interaction network</h3>
      {human.string_image_url ? (
        <div className="panel panel-flush">
          <h4>STRING physical partners</h4>
          <img
            src={fileUrl(human.string_image_url)!}
            alt="STRING interaction network"
          />
          <p className="caption">
            <a
              href={`https://string-db.org/cgi/network?identifiers=${human.id}`}
              target="_blank"
              rel="noreferrer"
            >
              View at STRING
            </a>
          </p>
        </div>
      ) : (
        <p>No interaction network was returned.</p>
      )}
    </section>
  );
}

function Warnings({ warnings }: { warnings: WarningOut[] }) {
  return (
    <details>
      <summary>
        {warnings.length} step{warnings.length === 1 ? "" : "s"} did not
        complete
      </summary>
      <table>
        <thead>
          <tr>
            <th>Stage</th>
            <th>Organism</th>
            <th>Detail</th>
          </tr>
        </thead>
        <tbody>
          {warnings.map((w, i) => (
            <tr key={i}>
              <td>{w.stage}</td>
              <td>
                {w.organism ? <i>{w.organism}</i> : <span className="meta">&mdash;</span>}
              </td>
              <td>{w.message}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  );
}

function Swatch({ color }: { color: number }) {
  return (
    <span
      style={{
        display: "inline-block",
        width: "0.55rem",
        height: "0.55rem",
        marginRight: "0.25rem",
        background: `#${color.toString(16).padStart(6, "0")}`,
      }}
      aria-hidden
    />
  );
}
