# OrthoScope Frontend

Next.js (App Router) + TypeScript + Tailwind + Mol\*. Talks to the FastAPI
backend at [src/api.py](../src/api.py).

## Setup

```bash
cd frontend
cp .env.local.example .env.local   # edit if backend isn't on localhost:8000
npm install
npm run dev
```

Then open http://localhost:3000.

The backend must be running separately:

```bash
cd ../src
pip install fastapi "uvicorn[standard]"
uvicorn api:app --reload --port 8000
```

`next.config.mjs` proxies `/api/*` and `/files/*` to the backend, so the
browser hits same-origin and CORS is a non-issue in dev.

## Layout

```
frontend/
├── app/
│   ├── layout.tsx              root shell, loads Tailwind + Mol* CSS
│   ├── page.tsx                home: form + inline results (sync API for now)
│   ├── jobs/[id]/page.tsx      stub for the future async job page
│   └── globals.css
├── components/
│   ├── JobForm.tsx             protein input + organism picker
│   ├── ResultsView.tsx         tabbed results (Info / 3D / Sequence / Orthologs / STRING)
│   └── MolStarViewer.tsx       wraps Mol* — feed it a pdb_url and it renders
├── lib/
│   ├── types.ts                mirror of Pydantic models in src/api.py
│   └── api.ts                  fetch wrapper, typed
├── next.config.mjs             API proxy
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

## What you'll want to do next

1. **Replace `lib/types.ts` with generated types.** Once the backend stabilises:
   ```bash
   npx openapi-typescript http://localhost:8000/openapi.json -o lib/api-types.ts
   ```
   Then update `lib/types.ts` to re-export from there.

2. **Polish with shadcn/ui.** When you want better-looking forms/tabs/dialogs:
   ```bash
   npx shadcn@latest init
   npx shadcn@latest add button input checkbox dialog tabs
   ```
   The current components use plain Tailwind and are easy to swap out.

3. **Add React Query.** Once the API moves to async jobs you'll want polling
   and cache invalidation. Wrap `app/layout.tsx`'s `<body>` in a
   `<QueryClientProvider>` and convert `app/page.tsx`'s `useState` to
   `useMutation` / `useQuery`.

4. **Wire up `app/jobs/[id]/page.tsx`.** When the backend exposes
   `GET /jobs/{id}` and `GET /jobs/{id}/events` (SSE), this page becomes the
   primary results destination. `JobForm` should `router.push("/jobs/" + id)`
   after submit instead of rendering inline.

5. **Auth via NextAuth.** Add `app/api/auth/[...nextauth]/route.ts`, gate the
   form behind a sign-in, and have the backend trust a session JWT.

## Mol\* notes

- The viewer loads the AlphaFold PDB served by the backend's `/files/*`
  static mount. No data leaves the user's browser after fetch.
- Default preset shows the cartoon backbone. To color by `features[]` (ECD,
  TM, etc.), use the plugin's `Selection` / `Color` builders in a follow-up
  effect inside `MolStarViewer.tsx`.
- The CSS import in `app/globals.css` is `molstar/build/viewer/molstar.css`.
  If a future Mol\* release moves it, the build will fail loud — easy fix.
