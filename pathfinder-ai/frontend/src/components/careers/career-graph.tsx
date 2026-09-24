"use client";

import { Background, type Edge, type Node, type NodeProps, ReactFlow, Handle, Position } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";

import { get } from "@/lib/api";
import { cn } from "@/lib/utils";

type GNode = { id: string; label: string; name: string; importance?: string };
type GEdge = { source: string; target: string; type: string; importance?: string; level?: number };

// Columnar layout: requirements on the left, how the role is practised/proven on the right,
// related careers along the top. Deterministic and overlap-free.
const COLUMNS: { types: string[]; title: Record<string, string>; x: number }[] = [
  { types: ["REQUIRES"], title: { REQUIRES: "requires" }, x: -430 },
  { types: ["USES"], title: { USES: "uses" }, x: 250 },
  { types: ["DEMONSTRATED_BY", "BENEFITS_FROM"], title: { DEMONSTRATED_BY: "demonstrated by", BENEFITS_FROM: "benefits from" }, x: 520 },
];
const ROW = 40;

function GraphNode({ data }: NodeProps) {
  const d = data as { label: string; kind: string; strong?: boolean; center?: boolean; delay: number };
  return (
    <div
      style={{ animationDelay: `${d.delay}ms` }}
      className={cn(
        "animate-fade-up whitespace-nowrap rounded-lg border px-3 py-1.5 text-[12px] shadow-soft",
        d.center ? "border-ink bg-ink px-4 py-2.5 text-[14px] font-semibold text-white" : d.strong ? "border-ink bg-surface font-medium text-fg" : "border-line bg-surface text-fg-2",
      )}
    >
      <Handle type="target" position={Position.Left} />
      {!d.center && <span className="mr-1.5 font-mono text-[9px] uppercase tracking-wider text-muted">{d.kind}</span>}
      {d.label}
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

const nodeTypes = { g: GraphNode };

export function CareerGraph({ careerId }: { careerId: string }) {
  const { data } = useQuery({
    queryKey: ["graph", careerId],
    queryFn: () => get<{ nodes: GNode[]; edges: GEdge[]; backend: string }>(`/graph/careers/${careerId}`),
    staleTime: Infinity,
  });

  const { nodes, edges } = useMemo(() => {
    if (!data) return { nodes: [] as Node[], edges: [] as Edge[] };
    const center = `career:${careerId}`;
    const byId = Object.fromEntries(data.nodes.map((n) => [n.id, n]));
    const ns: Node[] = [{ id: center, type: "g", position: { x: 0, y: 0 }, data: { label: byId[center]?.name, kind: "career", center: true, delay: 0 }, draggable: false }];
    const es: Edge[] = [];
    let order = 1;
    const add = (e: GEdge, kind: string, x: number, y: number) => {
      ns.push({ id: e.target, type: "g", draggable: false, position: { x, y },
        data: { label: byId[e.target]?.name ?? e.target, kind, strong: e.importance === "core", delay: 120 + order++ * 40 } });
      es.push({ id: `${center}-${e.target}`, source: center, target: e.target, style: { stroke: e.importance === "core" ? "#9a9a9a" : "#dcdcdc" } });
    };
    const rank: Record<string, number> = { core: 0, important: 1, useful: 2 };
    for (const col of COLUMNS) {
      const group = data.edges
        .filter((e) => e.source === center && col.types.includes(e.type))
        .sort((a, b) => (rank[a.importance ?? "useful"] ?? 3) - (rank[b.importance ?? "useful"] ?? 3));
      group.forEach((e, i) => add(e, col.title[e.type], col.x, (i - (group.length - 1) / 2) * ROW));
    }
    const related = data.edges.filter((e) => e.source === center && e.type === "RELATED_TO");
    const tallest = Math.max(...COLUMNS.map((c) => data.edges.filter((e) => e.source === center && c.types.includes(e.type)).length), 1);
    related.forEach((e, i) => add(e, "related", (i - (related.length - 1) / 2) * 200 - 40, -((tallest / 2) * ROW + 90)));
    return { nodes: ns, edges: es };
  }, [data, careerId]);

  return (
    <div className="relative h-[540px] overflow-hidden rounded-2xl border border-line bg-surface">
      {data && (
        <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView fitViewOptions={{ padding: 0.12 }} minZoom={0.3}
          nodesConnectable={false} elementsSelectable={false} panOnScroll={false} zoomOnScroll={false} proOptions={{ hideAttribution: false }}>
          <Background gap={24} size={1} color="#e6e6e6" />
        </ReactFlow>
      )}
      <div className="pointer-events-none absolute left-4 top-4 flex items-center gap-3 text-[11px] text-muted">
        <span className="eyebrow">Knowledge graph</span>
        {data && <span className="font-mono">{data.backend === "neo4j" ? "Neo4j" : "in-memory graph"}</span>}
      </div>
    </div>
  );
}
