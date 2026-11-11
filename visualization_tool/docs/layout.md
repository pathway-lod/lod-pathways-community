# Layout (src/layout.js)

Deterministic, written by hand (no graph-layout library). Input: the cards and edges of `buildView`, the measured
card sizes, the layout mode, and a function that gives a label's pixel width. Output: a `Map` id → `{x, y}`, plus
`pos.colXs` (x of every column, used to detect edges that skip a column).

Constants: `COL_W` 400 (card width; must match `.card` in styles.css), `GAP_X` 170 (minimum gap between columns),
`GAP_Y` 40 (between cards in a column), `BLOCK_GAP` 90 (between claim blocks), `LABEL_PAD` 70 (gap = widest label +
this), `PORT_MARGIN` 18; KG trees: `SIB_GAP` 60 (between sibling subtrees), `KG_GAP_X` 80 (between trees side by
side, slide layout), `V_MARGIN` 22 + `V_STEP` 14 per track + `V_LABEL` 34 (gap between tree rows).

## 1. Columns

Two arrangements (`LAYOUTS`), chosen with the "slide layout" checkbox / `layout=slide`:

| Mode | Columns (left → right) | Effect |
|---|---|---|
| `compact` (default) | runs · data + evidence · claims · knowledge graph | every link goes to a neighbouring column |
| `slide` | data · claims · evidence · knowledge graph · runs | the look of slides 24/25; claim → anchor edges skip the evidence column and run over the top (lane edges) |

In both, the knowledge graph is drawn as trees growing downward (see 3.), which start at the knowledge-graph column
and extend to the right of it. Every column after it (runs, in the slide layout) starts right of the widest tree.
`pos.colOf` records the column of each card (a tree card can sit right of its column), so that "does this edge skip a
column" is decided by columns, not by the card's x.

Without any claim (unknown vocabulary, profile *none*): columns = link distance from the cards nothing points to
(`depthColumns`, breadth-first; cycles without a root go to column 0), each column stacked with `placeColumn`.

**Column x positions** (`columnX`): each gap between neighbouring columns is
`max(GAP_X, widest label of the edges that cross it + LABEL_PAD)`, so labels never run into cards. Labels of edges
that skip columns (lanes) do not count.

## 2. Claims and their side column (`placeClaimBlocks`)

The side column is the evidence column (slide) or the data + evidence column (compact).

1. **Order of claims** (`orderClaims`): generated claims before proposals, otherwise input order (`claimRank`).
   Then a depth-first walk keeps related claims adjacent: from each claim that no other claim points to, follow its
   outgoing claim links, then incoming ones, then claims that share a side card. So a BGC-pathway link sits directly
   above the BGC it is about, and two annotations of the same feature are neighbours.
2. **Blocks**: for each claim in that order, its *own* side cards (linked to this claim only; in compact the data
   cards first, then evidence) are stacked with `GAP_Y`; the claim is vertically centred on that stack, or the stack
   on the claim if the claim is taller. Blocks are separated by `BLOCK_GAP`.
3. **Shared side cards** (linked to several claims, e.g. feature 589 on slide 25) go *between* blocks: after the
   block of the first of their claims, with `BLOCK_GAP/2` around them.
4. Side cards with no shown claim (orphans) are stacked below everything.

## 3. Other columns

- **data** (slide layout only; in compact it is part of the blocks) and **runs**: `placeColumn` sorts the cards by
  their *desired* y (mean centre of their already placed neighbours) and places each at that y, pushed down to
  avoid overlapping the card above.
- **knowledge graph** as trees growing downward (`kgTrees`, `placeKg`): cards linked to each other (KG-to-KG edges,
  e.g. metabolite → pathways) form a group (connected component). Depth inside a group = link distance in either
  direction from the cards linked from outside the group (the anchors of claims; a group nothing outside links to
  starts at its first card). Parent of a card = its first neighbour one level up. Tidy tree: width of a subtree =
  max(card width, its children's subtrees side by side, `SIB_GAP` apart); every card is centred over its subtree, so subtrees never overlap. The tree is then
  shifted so that its first anchor is at the KG column (the gap to the claims stays as wide as the label) but no card
  goes further left than the column before + `KG_MARGIN` 40: the children use the free space below the claim → anchor
  edge; only a tree too wide for that moves right.. Row 0 (the anchors) sits at the mean height of the cards pointing into the group; each
  further row below the tallest card of the row above, with room for the edge tracks and labels between rows.
  Groups are ordered by that height; compact: stacked below each other (`BLOCK_GAP/2` apart, never above the
  previous group's bottom); slide: side by side (`KG_GAP_X`), because claim → anchor edges drop from a lane above
  all cards and would otherwise run through the trees above.
  Parent–child edges (`pos.vertical`) are drawn bottom → top. Before 2026-11-11 a group was one vertical stack and
  an edge from the top card to the third ran behind the second (slide 25: metabolite → PWY-6684 looked like
  PWY-2821 → PWY-6684).

## 3b. Grid of graphs (`layoutGrid`, selections from the global view, compact only)

The view is split into connected graphs (union-find over all edges); each is laid out with `layout()`; graphs are
packed in rows, largest first (card count; ties: input order), `GRID_GAP_X` 220 / `GRID_GAP_Y` 200 apart; a row
ends before it gets wider than max(widest graph, `GRID_ASPECT` 1.7 x sqrt(total area)). Every card keeps its graph's
own column positions in `pos.colXsOf`, which `handlesFor` uses instead of `pos.colXs`, so columns of graphs in
other rows never turn an edge into a lane. The slide layout does not use the grid (its lanes run above all cards).

## 4. Edge routing (after layout, called from App.jsx)

1. **Sides** (`handlesFor`): target in a column to the right → right side → left side; to the left → the reverse;
   KG tree parent–child pairs (`pos.vertical`) and cards in the same column → bottom → top (or top → bottom). If another column lies between the two ends (`pos.colXs`), the
   edge becomes a **lane** edge: up from the top of the source, along a horizontal lane above all cards
   (26 px apart per lane), down into the top of the target (`LaneEdge.jsx`). Only the slide layout produces lanes.
2. **Connection points** (`assignPorts`): the k edges on one side of a card get k evenly spaced points
   (margin `PORT_MARGIN`), ordered by the centre height (left/right sides) or centre x (top/bottom sides) of the card
   at the other end. Stored as offsets from the
   side's middle (`sOff`, `tOff`), so they survive dragging a card.
3. **Bend positions** (`assignTracks`): every edge between neighbouring columns gets its own vertical segment
   (`centerX`). Per gap, each source card gets a band of tracks; bands are ordered by the card's height (the top
   card's band nearest to it). Inside a band, the card's upward edges (target above its connection point) bend
   nearest-first starting from the top connection point; downward edges nearest-first from the bottom one. Upward
   and downward edges of one card never meet, so they share track slots (band width = max(#up, #down)). With the
   cards arranged as above, this keeps a card's own fan from crossing itself and mostly avoids crossings between
   neighbouring claims.
   **Horizontal tracks** (`assignVTracks`, for top/bottom edges, drawn by `VTrackEdge.jsx`): in the gap below the
   upper card of each edge; that card's fan splits into edges going left and right, and on each side the edge to the
   farthest card turns first (highest track), so a fan never crosses itself. Fans of different cards in one tree row
   do not overlap (tidy tree) and reuse the same track heights.
4. **Labels**: on the last horizontal piece, anchored at the target card's edge (`TrackEdge.jsx`). The same label
   at the same arrowhead is shown once.
5. **Fit**: `fitBounds` over the cards and the lanes above them.

## Why not a general graph layout

Force layouts were rejected (the example force views were "muddy"; the slides read in columns). ELK (layered) was
considered and kept as the option for large subsets; the hand-written layout is predictable and encodes the
evidence pattern directly. See docs/decisions.md.

## Changing the layout

- Check every query in the table in CLAUDE.md with `npm run shot`; slide 25 in both modes is the reference.
- A new display option must go into `viewKey` (App.jsx).
- Keep `layout()` free of vocabulary: it sees only roles (`claim`, `evidence`, `run`, `kg`, `data`), states and ids.
