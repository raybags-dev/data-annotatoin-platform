import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Datasets from './pages/Datasets'
import Upload from './pages/Upload'
import DatasetDetail from './pages/DatasetDetail'
import Review from './pages/Review'
import Export from './pages/Export'

export default function App() {
  return (
    <BrowserRouter basename="/annotation">
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/datasets" element={<Datasets />} />
          <Route path="/datasets/upload" element={<Upload />} />
          <Route path="/datasets/:id" element={<DatasetDetail />} />
          <Route path="/datasets/:id/review" element={<Review />} />
          <Route path="/datasets/:id/export" element={<Export />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
