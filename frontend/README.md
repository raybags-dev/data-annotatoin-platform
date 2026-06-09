# Frontend — React + Vite

React 18 + Vite + TypeScript + Tailwind CSS + TanStack Query + React Router v6 + Recharts.

## Pages

| Route | Page |
|---|---|
| `/` | Dashboard — live stats and charts |
| `/upload` | Upload a new dataset (CSV / JSON / Excel / TXT) |
| `/datasets` | Dataset list with status badges |
| `/datasets/:id` | Dataset detail — pipeline controls, validation/cleaning reports |
| `/review` | Human review — approve / reject / override AI labels |
| `/export` | Export annotated data (CSV / JSON / Excel) |

## Running locally

```bash
npm install
npm run dev   # http://localhost:5174
```

Set `VITE_API_URL` (default `http://localhost:8001`) to point at the backend.

## Docker

Builds a static bundle served by Nginx on port 80. The Nginx config rewrites all routes to `index.html` for client-side routing.
