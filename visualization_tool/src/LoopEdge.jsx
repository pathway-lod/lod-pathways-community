// Edge between two cards of the same column that are not neighbours in a tree (2026-11-13, D40: a run informed by
// another run, both roots of their own run trees): out of the source's right side, down (or up) on a track just right
// of both cards, into the target's right side. A straight vertical edge would run behind the cards between them.
// data.level (from layout.js, pos.loops): 1 = innermost track; nested loops get tracks further right.
// Connection points are spread along the border (data.sOff / data.tOff, assignPorts). Label beside the arrowhead.
import { BaseEdge, EdgeLabelRenderer } from '@xyflow/react';

const LOOP_GAP = 26, LOOP_STEP = 14, r = 8;

export default function LoopEdge({ id, sourceX, sourceY, targetX, targetY, data, style, markerEnd, label, labelStyle }) {
  const sy = sourceY + (data.sOff || 0), ty = targetY + (data.tOff || 0);
  const left = data.side === 'left', out = left ? -1 : 1; // data.side: the side of the cards the loop runs on
  const x = (left ? Math.min(sourceX, targetX) : Math.max(sourceX, targetX)) + out * (LOOP_GAP + ((data.level || 1) - 1) * LOOP_STEP);
  const dy = ty > sy ? 1 : -1;
  const path = [`M${sourceX},${sy}`, `L${x - out * r},${sy}`, `Q${x},${sy} ${x},${sy + dy * r}`,
    `L${x},${ty - dy * r}`, `Q${x},${ty} ${x - out * r},${ty}`, `L${targetX},${ty}`].join(' ');
  return (
    <>
      <BaseEdge id={id} path={path} style={style} markerEnd={markerEnd} />
      {label && (
        <EdgeLabelRenderer>
          <div className="edge-label" style={{
            ...labelStyle, color: labelStyle.fill,
            transform: `translate(${x + out * 6}px, ${ty}px) translate(${left ? '-100%' : '0'}, -50%)`,
          }}>{label}</div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
