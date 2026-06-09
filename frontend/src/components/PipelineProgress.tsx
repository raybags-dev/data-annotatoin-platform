import type { ProcessingEntry } from '../lib/types'

const STAGES = ['ingest', 'validate', 'clean', 'label']
const STATUS_COLOR: Record<string, string> = {
  completed: 'bg-green-500',
  running: 'bg-yellow-400 animate-pulse',
  failed: 'bg-red-500',
  pending: 'bg-gray-700',
}

export default function PipelineProgress({ history, status }: { history: ProcessingEntry[]; status: string }) {
  return (
    <div className="flex items-center gap-0">
      {STAGES.map((s, i) => {
        const entry = history.filter(h => h.stage === s).at(-1)
        const state = entry?.status ?? 'pending'
        return (
          <div key={s} className="flex items-center">
            <div className="flex flex-col items-center gap-1">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${STATUS_COLOR[state]} ${state === 'completed' ? 'text-white' : 'text-gray-300'}`}>
                {state === 'completed' ? '✓' : i + 1}
              </div>
              <span className="text-xs text-gray-500 capitalize">{s}</span>
            </div>
            {i < STAGES.length - 1 && <div className={`w-10 h-0.5 mb-4 ${entry?.status === 'completed' ? 'bg-green-500' : 'bg-gray-700'}`} />}
          </div>
        )
      })}
    </div>
  )
}
