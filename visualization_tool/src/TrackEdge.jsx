// Edge between neighbouring columns: horizontal out of the source, vertical on the source card's own track in the
// gap (data.centerX, from assignTracks), horizontal into the target. The label sits on the last horizontal piece,
// anchored at the target card's edge (it starts just outside the card and grows towards the track), so labels of
// edges that share a track do not stack and short segments do not push the label into the card.
import { BaseEdge, EdgeLabelRenderer, getSmoothStepPath } from '@xyflow/react';

export default function TrackEdge({ id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition,
  data, style, markerEnd, label, labelStyle }) {
  // spread connection points (assignPorts): offsets from the middle of the card side
  const sY = sourceY + (data.sOff || 0), tY = targetY + (data.tOff || 0);
  const [path] = getSmoothStepPath({
    sourceX, sourceY: sY, targetX, targetY: tY, sourcePosition, targetPosition, centerX: data.centerX, borderRadius: 8,
  });
  const fromRight = data.centerX > targetX; // target card is left of the track: its handle is its right edge
  const shift = fromRight ? 'translate(0, -50%)' : 'translate(-100%, -50%)';
  const lx = targetX + (fromRight ? 14 : -16);
  return (
    <>
      <BaseEdge id={id} path={path} style={style} markerEnd={markerEnd} />
      {label && (
        <EdgeLabelRenderer>
          <div className="edge-label" style={{
            ...labelStyle, color: labelStyle.fill,
            transform: `translate(${lx}px, ${tY}px) ${shift}`,
          }}>{label}</div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
