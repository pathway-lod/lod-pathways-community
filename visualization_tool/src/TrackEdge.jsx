// Edge between neighbouring columns: horizontal out of the source, vertical on the source card's own track in the
// gap, horizontal into the target. The track is stored as a fraction of the gap (data.trackFrac, from assignTracks)
// and mapped onto the live gap here, so the vertical segment follows when a card is dragged (2026-11-12).
// The label sits on the last horizontal piece, anchored at the target card's edge (it starts just outside the card
// and grows towards the track), so labels of edges that share a track do not stack and short segments do not push
// the label into the card. Its side comes from the side of the card the arrow enters, so it never lands on the card.
import { BaseEdge, EdgeLabelRenderer, getSmoothStepPath, Position } from '@xyflow/react';

export default function TrackEdge({ id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition,
  data, style, markerEnd, label, labelStyle }) {
  // spread connection points (assignPorts): offsets from the middle of the card side
  const sY = sourceY + (data.sOff || 0), tY = targetY + (data.tOff || 0);
  const left = Math.min(sourceX, targetX), right = Math.max(sourceX, targetX);
  const centerX = left + (data.trackFrac ?? 0.5) * (right - left);
  const [path] = getSmoothStepPath({
    sourceX, sourceY: sY, targetX, targetY: tY, sourcePosition, targetPosition, centerX, borderRadius: 8,
  });
  const fromRight = targetPosition === Position.Right; // arrow enters the target's right edge: label right of it
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
