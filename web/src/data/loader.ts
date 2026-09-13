import type { DataIndex, GraphData, MetaData, RunData } from './schema'

const base = `${import.meta.env.BASE_URL.replace(/\/$/, '')}/data`

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${base}/${path}`)
  if (!res.ok) throw new Error(`Failed to load ${path}: ${res.status}`)
  return (await res.json()) as T
}

export const loadIndex = (): Promise<DataIndex> => getJson('index.json')
export const loadMeta = (): Promise<MetaData> => getJson('meta.json')
export const loadGraph = (): Promise<GraphData> => getJson('graph.json')
export const loadRun = (id: string): Promise<RunData> => getJson(`runs/${id}.json`)
