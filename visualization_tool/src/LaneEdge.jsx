// Edge that skips over a column: leaves the source at the top, runs along a free lane above all cards and drops
// into the target from the top (like the anchoredToMetabolite arrow on the slides). Other edges use smoothstep.
import { BaseEdge, EdgeLabelRenderer } from '@xyflow/react';

export default function LaneEdge({ id, sourceX, sourceY, targetX, targetY, data, style, markerEnd, label, labelStyle }) {
  const y = data.laneY, r = 10;
  const dir = targetX > sourceX ? 1 : -1;
  const path = [
    `M${sourceX},${sourceY}`, `L${sourceX},${y + r}`, `Q${sourceX},${y} ${sourceX + dir * r},${y}`,
    `L${targetX - dir * r},${y}`, `Q${targetX},${y} ${targetX},${y + r}`, `L${targetX},${targetY}`,
  ].join(' ');
  return (
    <>
      <BaseEdge id={id} path={path} style={style} markerEnd={markerEnd} />
      {label && (
        <EdgeLabelRenderer>
          <div className="edge-label" style={{
            ...labelStyle, color: labelStyle.fill,
            transform: `translate(-50%, -50%) translate(${(sourceX + targetX) / 2}px, ${y}px)`,
          }}>{label}</div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
