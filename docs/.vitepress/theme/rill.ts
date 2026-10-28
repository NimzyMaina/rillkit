// Procedural rill networks: a few fine channels converging downhill.
// Everything is seeded, so server and client render identical markup.

export interface Rill {
  d: string
  order: number
  w: number
  dur: number
  delay: number
  /** 0 stream blue, 1 ack green, 2 retry amber, 3 dlq coral */
  tone: number
}

type Pt = [number, number]

export function rng(seed: number) {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const f = (n: number) => Math.round(n * 10) / 10

/** Catmull-Rom spline through points, emitted as cubic beziers. */
export function smooth(p: Pt[]): string {
  if (p.length < 2) return ''
  let d = `M${f(p[0][0])} ${f(p[0][1])}`
  for (let i = 0; i < p.length - 1; i++) {
    const p0 = p[i - 1] || p[i]
    const p1 = p[i]
    const p2 = p[i + 1]
    const p3 = p[i + 2] || p2
    const c1x = p1[0] + (p2[0] - p0[0]) / 6
    const c1y = p1[1] + (p2[1] - p0[1]) / 6
    const c2x = p2[0] - (p3[0] - p1[0]) / 6
    const c2y = p2[1] - (p3[1] - p1[1]) / 6
    d += `C${f(c1x)} ${f(c1y)} ${f(c2x)} ${f(c2y)} ${f(p2[0])} ${f(p2[1])}`
  }
  return d
}

export interface RillOptions {
  width: number
  height: number
  /** x positions (0..1) where trunks leave the bottom edge */
  trunks: number[]
  maxPaths?: number
  step?: number
  /** minimum x (0..1) of the canvas that branches may occupy */
  bounds?: [number, number]
}

const WIDTHS = [0.9, 1.15, 1.4, 1.7, 2]

/** Grow drainage networks upslope from the mouths, then flip each path so it flows downhill. */
export function makeRills(seed: number, o: RillOptions): Rill[] {
  const r = rng(seed)
  const step = o.step ?? 14
  const max = o.maxPaths ?? 16
  const [bx0, bx1] = o.bounds ?? [-0.05, 1.05]
  const UP = -Math.PI / 2
  const out: Rill[] = []
  interface Job { x: number; y: number; th: number; steps: number; order: number; tone: number }
  const queue: Job[] = o.trunks.map((t) => ({
    x: t * o.width,
    y: o.height + 20,
    th: UP + (r() - 0.5) * 0.3,
    steps: Math.round((o.height / step) * 1.15),
    order: 4,
    tone: 0,
  }))
  const pBranch = [0, 0.05, 0.08, 0.1, 0.11]
  let side = 1
  while (queue.length && out.length < max) {
    const j = queue.shift()!
    const pts: Pt[] = [[j.x, j.y]]
    let { x, y, th } = j
    const wob = 0.25 + r() * 0.25
    const freq = 0.25 + r() * 0.25
    const ph = r() * 6.28
    for (let i = 0; i < j.steps; i++) {
      th += (r() - 0.5) * 0.28 + Math.cos(i * freq + ph) * wob * 0.22
      th += (UP - th) * 0.07
      const s = step * (0.8 + r() * 0.5)
      x += Math.cos(th) * s
      y += Math.sin(th) * s
      if (y < -30 || x < o.width * bx0 || x > o.width * bx1) break
      pts.push([x, y])
      if (i > 2 && j.order > 0 && r() < pBranch[j.order] && out.length + queue.length < max) {
        side = -side
        queue.push({
          x, y,
          th: th + side * (0.5 + r() * 0.55),
          steps: Math.max(5, Math.round(j.steps * (0.55 + r() * 0.25))),
          order: j.order - 1,
          // most branches stay stream-blue; the rest are the three outcomes
          tone: j.order <= 3 && r() < 0.88 ? 1 + Math.floor(r() * 3) : j.tone,
        })
      }
    }
    if (pts.length < 4) continue
    pts.reverse()
    out.push({
      d: smooth(pts),
      order: j.order,
      w: WIDTHS[j.order],
      dur: 26 + r() * 18,
      delay: -r() * 30,
      tone: j.tone,
    })
  }
  // thick ones last so they sit on top
  return out.sort((a, b) => a.order - b.order)
}

export interface Divider {
  d: string
  branch: string
  width: number
  height: number
}

/** A thin meandering channel with one tributary, for section dividers. */
export function makeDivider(seed: number, width = 1120, height = 44): Divider {
  const r = rng(seed)
  const mid = height / 2
  const pts: Pt[] = []
  const n = 14
  let y = mid
  for (let i = 0; i <= n; i++) {
    y += (r() - 0.5) * 16
    y += (mid - y) * 0.35
    pts.push([(i / n) * width, y])
  }
  const k = 4 + Math.floor(r() * 5)
  const [bx, by] = pts[k]
  const side = r() < 0.5 ? -1 : 1
  const branch = smooth([
    [bx, by],
    [bx + 30, by + side * (6 + r() * 6)],
    [bx + 70, by + side * (14 + r() * 4)],
    [bx + 120, by + side * (16 + r() * 4)],
  ])
  return { d: smooth(pts), branch, width, height }
}
