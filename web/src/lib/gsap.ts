import { gsap } from 'gsap'
import { useGSAP } from '@gsap/react'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { ScrollToPlugin } from 'gsap/ScrollToPlugin'
import { Flip } from 'gsap/Flip'
import { SplitText } from 'gsap/SplitText'
import { DrawSVGPlugin } from 'gsap/DrawSVGPlugin'
import { MotionPathPlugin } from 'gsap/MotionPathPlugin'

// Register once, at module level.
gsap.registerPlugin(useGSAP, ScrollTrigger, ScrollToPlugin, Flip, SplitText, DrawSVGPlugin, MotionPathPlugin)

gsap.defaults({ ease: 'power3.out', duration: 0.8 })

export const REDUCE = '(prefers-reduced-motion: reduce)'
export const MOTION = '(prefers-reduced-motion: no-preference)'

export { gsap, useGSAP, ScrollTrigger, Flip, SplitText, DrawSVGPlugin, MotionPathPlugin }
