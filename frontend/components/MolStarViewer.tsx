"use client";

import { useEffect, useRef } from "react";
import { createPluginUI } from "molstar/lib/mol-plugin-ui";
import { renderReact18 } from "molstar/lib/mol-plugin-ui/react18";
import { DefaultPluginUISpec } from "molstar/lib/mol-plugin-ui/spec";
import type { PluginUIContext } from "molstar/lib/mol-plugin-ui/context";
import { Color } from "molstar/lib/mol-util/color";

export interface StructureSpec {
  url: string;
  color?: number;
}

interface Props {
  structures: StructureSpec[];
  height?: number;
}

export default function MolStarViewer({ structures, height = 480 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const pluginRef = useRef<PluginUIContext | null>(null);
  const key = structures.map((s) => `${s.url}:${s.color ?? ""}`).join("|");

  useEffect(() => {
    let disposed = false;
    let plugin: PluginUIContext | null = null;

    async function init() {
      if (!containerRef.current) return;
      plugin = await createPluginUI({
        target: containerRef.current,
        render: renderReact18,
        spec: {
          ...DefaultPluginUISpec(),
          layout: {
            initial: { isExpanded: false, showControls: false },
          },
        },
      });
      if (disposed) {
        plugin.dispose();
        return;
      }
      pluginRef.current = plugin;

      for (const spec of structures) {
        const data = await plugin.builders.data.download(
          { url: spec.url },
          { state: { isGhost: true } }
        );
        const trajectory = await plugin.builders.structure.parseTrajectory(
          data,
          "pdb"
        );

        if (spec.color === undefined) {
          await plugin.builders.structure.hierarchy.applyPreset(
            trajectory,
            "default"
          );
          continue;
        }

        const model = await plugin.builders.structure.createModel(trajectory);
        const structure = await plugin.builders.structure.createStructure(model);
        const component =
          await plugin.builders.structure.tryCreateComponentStatic(
            structure,
            "polymer"
          );
        if (component) {
          await plugin.builders.structure.representation.addRepresentation(
            component,
            {
              type: "cartoon",
              color: "uniform",
              colorParams: { value: Color(spec.color) },
            }
          );
        }
      }

      if (!disposed) plugin.managers.camera.reset();
    }

    init().catch((e) => console.error("Mol* init failed", e));

    return () => {
      disposed = true;
      pluginRef.current?.dispose();
      pluginRef.current = null;
    };
  }, [key]);

  return <div ref={containerRef} style={{ height, position: "relative" }} />;
}
