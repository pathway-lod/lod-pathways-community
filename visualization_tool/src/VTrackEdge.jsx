// Edge between a card and one below it (knowledge-graph trees, same-column links): vertical out of the source's
// bottom (or top), horizontal on its own track in the gap between the rows, vertical into the target. The track is
// stored as a fraction of the way from source to target (data.trackFrac, from assignVTracks) and mapped onto the live
// ends here, so it follows when a card is dragged (2026-11-12). Connection points are spread along the border
// (data.sOff / data.tOff: x offsets, assignPorts). The label sits just outside the target card, beside the arrowhead.
import { BaseEdge, EdgeLabelRenderer } from '@xyflow/react';

export default function VTrackEdge({ id, sourceX, sourceY, targetX, targetY, data, style, markerEnd, label, labelStyle }) {
  const sx = sourceX + (data.sOff || 0), tx = targetX + (data.tOff || 0);
  const y = sourceY + (data.trackFrac ?? 0.5) * (targetY - sourceY), r = 8;
  const down = targetY > sourceY;
  const dir = tx > sx ? 1 : -1;
  const bend = Math.min(r, Math.abs(tx - sx) / 2);
  const path = Math.abs(tx - sx) < 1
    ? `M${sx},${sourceY} L${tx},${targetY}`
    : [`M${sx},${sourceY}`, `L${sx},${y - (down ? bend : -bend)}`, `Q${sx},${y} ${sx + dir * bend},${y}`,
      `L${tx - dir * bend},${y}`, `Q${tx},${y} ${tx},${y + (down ? bend : -bend)}`, `L${tx},${targetY}`].join(' ');
  const ly = targetY + (down ? -12 : 12);
  return (
    <>
      <BaseEdge id={id} path={path} style={style} markerEnd={markerEnd} />
      {label && (
        <EdgeLabelRenderer>
          <div className="edge-label" style={{
            ...labelStyle, color: labelStyle.fill,
            transform: `translate(${tx + 8}px, ${ly}px) translate(0, -50%)`,
          }}>{label}</div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
