import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';


const SIDES = [['left', Position.Left], ['right', Position.Right], ['top', Position.Top], ['bottom', Position.Bottom]];

function Issue({ r }) {
  return (
    <div className={`issue ${r.severity}`}>
      <span className="sev">{r.severity === 'violation' ? '✕' : r.severity === 'pattern' ? '◇' : '!'}</span>
      {r.via ? <b>{r.via}: </b> : null}{r.message}
    </div>
  );
}

function Row({ row, showMissing, inProposal, compact }) {
  if (row.missing && !showMissing) return null;
  const prop = row.state === 'proposal' && !inProposal; // in a proposal card the dashed card already says it
  const cls = `row st-${row.status} ${prop ? 'proposal' : ''} ${row.missing ? 'missing' : ''}`;
  const pred = row.isType ? 'a' : compact(row.pred);
  return (
    <div className={cls}>
      <div className="row-head">
        <span className="pred" title={row.predNote || ''}>
          {pred}{row.isType ? ' ' + row.values.map((v) => v.text).join(', ') : ''}
          {row.unlisted && row.status !== 'kg' ? <span className="tag">not in spec</span> : null}
          {prop ? <span className="tag prop">proposal</span> : null}
        </span>
        {row.reqs.length ? <span className="badge">{row.reqs.join(', ')}</span> : null}
      </div>
      {row.isType
        ? row.values.some((v) => v.note) && <div className="val note">{row.values.map((v) => v.note).filter(Boolean).join('; ')}</div>
        : row.values.map((v, i) => (
          <div key={i} className={`val ${v.state === 'proposal' && row.state !== 'proposal' ? 'proposal' : ''}`}>
            {v.href ? <a href={v.href} target="_blank" rel="noreferrer">{v.text}</a> : v.text}
            {v.note ? <span className="note"> {v.note}</span> : null}
          </div>
        ))}
      {row.missing ? <div className="val note">missing</div> : null}
      {row.issues.map((r, i) => <Issue key={i} r={r} />)}
    </div>
  );
}

function CardNode({ data }) {
  const { card, showMissing, selected, compact } = data;
  const nV = [...card.issues, ...card.rows.flatMap((r) => r.issues)];
  const viol = nV.filter((r) => r.severity === 'violation').length;
  const warn = nV.filter((r) => r.severity === 'warning').length;
  const patt = nV.filter((r) => r.severity === 'pattern').length;
  return (
    <div className={`card role-${card.role} ${card.state === 'proposal' ? 'proposal' : ''} ${selected ? 'selected' : ''}`}>
      {SIDES.map(([s, p]) => (
        <span key={s}>
          <Handle type="source" position={p} id={`s-${s}`} className="h" />
          <Handle type="target" position={p} id={`t-${s}`} className="h" />
        </span>
      ))}
      <div className="card-head">
        <span>{card.title}</span>
        <span className="counts">
          {viol ? <span className="cnt violation">{viol} ✕</span> : null}
          {warn ? <span className="cnt warning">{warn} !</span> : null}
          {patt ? <span className="cnt pattern">{patt} ◇</span> : null}
        </span>
      </div>
      <div className="iri">{card.iri ? compact(card.iri) : 'blank node'}</div>
      <div className="rows">
        {card.rows.map((row, i) => <Row key={i} row={row} showMissing={showMissing} inProposal={card.state === 'proposal'} compact={compact} />)}
      </div>
      {card.issues.length ? <div className="card-issues">{card.issues.map((r, i) => <Issue key={i} r={r} />)}</div> : null}
    </div>
  );
}

export default memo(CardNode);
