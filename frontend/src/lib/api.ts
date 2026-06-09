import axios from 'axios'
import type { Dataset, DashboardStats, LabelingConfig } from './types'

const http = axios.create({ baseURL: '' })

export const api = {
  // Datasets
  listDatasets: () => http.get<Dataset[]>('/api/v1/datasets').then(r => r.data),
  getDataset: (id: string) => http.get<Dataset>(`/api/v1/datasets/${id}`).then(r => r.data),
  uploadDataset: (name: string, file: File) => {
    const fd = new FormData()
    fd.append('name', name)
    fd.append('file', file)
    return http.post<Dataset>('/api/v1/datasets', fd).then(r => r.data)
  },
  deleteDataset: (id: string) => http.delete(`/api/v1/datasets/${id}`),
  setLabelingConfig: (id: string, config: LabelingConfig) =>
    http.put(`/api/v1/datasets/${id}/labeling-config`, config).then(r => r.data),

  // Pipeline
  runPipeline: (id: string, stages?: string[]) =>
    http.post(`/api/v1/pipeline/${id}/run`, { stages }).then(r => r.data),
  runStage: (id: string, stage: string) =>
    http.post(`/api/v1/pipeline/${id}/stage/${stage}`).then(r => r.data),
  listStages: () => http.get('/api/v1/pipeline/stages').then(r => r.data),

  // Annotations
  listRecords: (id: string, skip = 0, limit = 50) =>
    http.get(`/api/v1/annotations/${id}/records`, { params: { skip, limit } }).then(r => r.data),
  annotationStats: (id: string) =>
    http.get(`/api/v1/annotations/${id}/stats`).then(r => r.data),
  reviewRecord: (recordId: string, action: string, human_label?: string) =>
    http.patch(`/api/v1/annotations/record/${recordId}/review`, { action, human_label }).then(r => r.data),
  approveAll: (id: string) =>
    http.post(`/api/v1/annotations/${id}/approve-all`).then(r => r.data),

  // Dashboard
  dashboard: () => http.get<DashboardStats>('/api/v1/dashboard').then(r => r.data),

  // Export URLs (direct links)
  exportUrl: (id: string, fmt: string) => `${http.defaults.baseURL}/api/v1/exports/${id}/${fmt}`,
  getReport: (id: string) => http.get(`/api/v1/exports/${id}/report`).then(r => r.data),

  // Kaggle
  kaggleSearch: (q: string) =>
    http.get('/api/v1/kaggle/search', { params: { q } }).then(r => r.data),
  kaggleDownload: (handle: string) =>
    http.post('/api/v1/kaggle/download', { handle }).then(r => r.data),
  kaggleIngest: (download_id: string, filename: string, name: string) =>
    http.post<Dataset>('/api/v1/kaggle/ingest', { download_id, filename, name }).then(r => r.data),
}
