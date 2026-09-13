
/** Adds a tabular count-up on `el` to `tl` at `position`. Deterministic (snap to integer steps). */
export function addCountUp(
  tl: gsap.core.Timeline,
  el: Element | null | undefined,
  to: number,
  format: (v: number) => string,
  { duration = 1.6, position, from = 0, ease = 'power2.out' }: { duration?: number; position?: gsap.Position; from?: number; ease?: string } = {},
): void {
  if (!el) return
  const state = { v: from }
  el.textContent = format(from)
  tl.to(
    state,
    {
      v: to,
      duration,
      ease,
      snap: { v: 1 },
      onUpdate: () => {
        el.textContent = format(state.v)
      },
    },
    position,
  )
}
