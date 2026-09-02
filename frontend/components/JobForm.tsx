"use client";

import { useState } from "react";
import type { CustomOrganismIn, JobRequest, OrganismName } from "@/lib/types";

const PREDEFINED: { name: OrganismName; scientific: string; common: string }[] =
  [
    { name: "MOUSE", scientific: "Mus musculus", common: "mouse" },
    { name: "ALPACA", scientific: "Vicugna pacos", common: "alpaca" },
    { name: "CYNO", scientific: "Macaca fascicularis", common: "cynomolgus monkey" },
    { name: "CHICKEN", scientific: "Gallus gallus", common: "chicken" },
    { name: "RABBIT", scientific: "Oryctolagus cuniculus", common: "rabbit" },
    { name: "LLAMA", scientific: "Lama glama", common: "llama" },
  ];

interface Props {
  onSubmit: (req: JobRequest) => void;
  submitting: boolean;
}

export default function JobForm({ onSubmit, submitting }: Props) {
  const [proteinId, setProteinId] = useState("");
  const [proteinName, setProteinName] = useState("");
  const [selected, setSelected] = useState<Set<OrganismName>>(
    new Set(PREDEFINED.map((o) => o.name))
  );
  const [custom, setCustom] = useState<CustomOrganismIn[]>([]);
  const [customName, setCustomName] = useState("");
  const [customTax, setCustomTax] = useState("");

  function toggle(name: OrganismName) {
    const next = new Set(selected);
    if (next.has(name)) next.delete(name);
    else next.add(name);
    setSelected(next);
  }

  function addCustom() {
    const tax = parseInt(customTax, 10);
    if (!customName.trim() || Number.isNaN(tax)) return;
    setCustom([...custom, { scientific_name: customName.trim(), tax_id: tax }]);
    setCustomName("");
    setCustomTax("");
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit({
      protein_id: proteinId.trim(),
      protein_name: proteinName.trim(),
      organism_names: Array.from(selected),
      custom_organisms: custom,
    });
  }

  const total = selected.size + custom.length;
  const allOn = selected.size === PREDEFINED.length;

  return (
    <form onSubmit={submit}>
      <h2>Query</h2>

      <fieldset>
        <legend>Protein</legend>
        <div className="fieldset-body">
          <p>
            <label htmlFor="protein-name">Name </label>
            <input
              type="text"
              id="protein-name"
              size={10}
              value={proteinName}
              onChange={(e) => setProteinName(e.target.value)}
              placeholder="EGFR"
              required
            />
            {"  "}
            <label htmlFor="protein-id">UniProt accession </label>
            <input
              type="text"
              id="protein-id"
              size={10}
              className="mono"
              value={proteinId}
              onChange={(e) => setProteinId(e.target.value.toUpperCase())}
              placeholder="P00533"
              required
            />
          </p>
      
        </div>
      </fieldset>

      <fieldset>
        <legend>Orthologs</legend>
        <div className="fieldset-body">
          <ul>
            {PREDEFINED.map((o) => (
              <li key={o.name}>
                <input
                  type="checkbox"
                  id={`org-${o.name}`}
                  checked={selected.has(o.name)}
                  onChange={() => toggle(o.name)}
                />{" "}
                <label htmlFor={`org-${o.name}`}>
                  <i>{o.scientific}</i> <span className="meta">{o.common}</span>
                </label>
              </li>
            ))}
            {custom.map((c, i) => (
              <li key={`${c.tax_id}-${i}`}>
                <input type="checkbox" checked readOnly aria-label={c.scientific_name} />{" "}
                <i>{c.scientific_name}</i>{" "}
                <span className="meta">taxon {c.tax_id}</span>{" "}
                <a
                  href="#remove"
                  onClick={(e) => {
                    e.preventDefault();
                    setCustom(custom.filter((_, j) => j !== i));
                  }}
                >
                  remove
                </a>
              </li>
            ))}
          </ul>
          <p>
            <a
              href="#toggle-all"
              onClick={(e) => {
                e.preventDefault();
                setSelected(
                  allOn ? new Set() : new Set(PREDEFINED.map((o) => o.name))
                );
              }}
            >
              {allOn ? "Clear all" : "Select all"}
            </a>
          </p>
      
        </div>
      </fieldset>

      <fieldset>
        <legend>Add an organism</legend>
        <div className="fieldset-body">
          <p>
            <label htmlFor="custom-name">Scientific name </label>
            <input
              type="text"
              id="custom-name"
              size={16}
              value={customName}
              onChange={(e) => setCustomName(e.target.value)}
              placeholder="Canis lupus"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addCustom();
                }
              }}
            />
            {"  "}
            <label htmlFor="custom-tax">NCBI taxon ID </label>
            <input
              type="number"
              id="custom-tax"
              className="mono"
              style={{ width: "6rem" }}
              value={customTax}
              onChange={(e) => setCustomTax(e.target.value)}
              placeholder="9615"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addCustom();
                }
              }}
            />
            {"  "}
            <input
              type="button"
              value="Add"
              onClick={addCustom}
              disabled={!customName.trim() || !customTax}
            />
          </p>
      
        </div>
      </fieldset>

      <p>
        <input
          type="submit"
          value={submitting ? "Working…" : "Run query"}
          disabled={submitting || !proteinId || !proteinName || total === 0}
        />{" "}
        <small>
          {total} organism{total === 1 ? "" : "s"} selected
        </small>
      </p>
    </form>
  );
}
