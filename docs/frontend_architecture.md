# SentinelAI Frontend Architecture Guide

## Technology Stack

| Technology | Version | Purpose |
|-----------|---------|---------|
| Next.js | 16.2.9 | React framework (App Router) |
| React | 19.2.4 | UI library |
| TypeScript | 5.x | Type safety |
| Tailwind CSS | 4.x | Utility-first styling |
| Zustand | 5.0.14 | State management |
| React Query | 5.101.1 (TanStack) | Server state management |
| React Flow | 11.11.4 | Graph/node visualization |
| Recharts | 3.9.0 | Charts and analytics |
| Framer Motion | 12.41.0 | Animations |
| Lucide React | 1.21.0 | Icons |
| dagre | 0.8.5 | Graph layout algorithm |
| date-fns | 4.4.0 | Date utilities |
| Vitest | (dev) | Testing framework |
| Puppeteer | 25.2.1 (dev) | E2E/screenshot testing |

## Project Structure

```
sentinel_frontend/
  src/
    app/                          # Next.js App Router
      (dashboard)/                # Route group - authenticated pages
        ai-investigation/page.tsx
        analytics/page.tsx
        attack-graph/page.tsx
        audit-logs/page.tsx
        canvas/[identityId]/page.tsx
        cloudtrail/page.tsx
        dashboard/page.tsx
        identities/page.tsx
        ingestion/page.tsx
        integrations/page.tsx
        integrations/aws/page.tsx
        organization/page.tsx
        reports/page.tsx
        risk-findings/page.tsx
        risk-findings/[id]/page.tsx
        settings/page.tsx
        team/page.tsx
      login/page.tsx              # Public - login
      signup/page.tsx             # Public - registration
      forgot-password/page.tsx    # Public - password reset
      reset-password/page.tsx     # Public - password reset
      verify-email/page.tsx       # Public - email verification
      onboarding/page.tsx         # Post-signup onboarding
      privacy/page.tsx            # Privacy policy
      terms/page.tsx              # Terms of service
      status/page.tsx             # System status
      layout.tsx                  # Root layout
      page.tsx                    # Landing page
      globals.css                 # Global styles
    components/                   # Reusable components (30 TSX files)
      Providers.tsx               # App-level providers (QueryClient, etc.)
    lib/
      api.ts                      # API client
      store.ts                    # Zustand global store
      utils.ts                    # Utility functions
      stage1.config.ts            # Stage 1 feature configuration
    types/
      index.ts                    # Core TypeScript types
      stage1.ts                   # Stage 1 specific types
      canvas.ts                   # Canvas/graph types
    mocks/
      handlers.ts                 # MSW request handlers
      server.ts                   # MSW server setup
    setupTests.ts                 # Test configuration
```

## Routing Architecture

### App Router (Next.js 16)

Uses Next.js App Router with **route groups**:

- `(dashboard)/` - Route group for authenticated dashboard pages. Shares a common layout with sidebar navigation.
- Root-level pages - Public pages (login, signup, landing)

### Pages Overview

| Page | Path | Description |
|------|------|-------------|
| Landing | `/` | Marketing/landing page |
| Login | `/login` | Email/password + Google OAuth login |
| Signup | `/signup` | New account registration |
| Dashboard | `/dashboard` | Executive/SOC security overview |
| Identities | `/identities` | Machine identity inventory |
| Risk Findings | `/risk-findings` | Security findings list |
| Finding Detail | `/risk-findings/[id]` | Individual finding analysis |
| AI Investigation | `/ai-investigation` | AI-powered identity investigation |
| Attack Graph | `/attack-graph` | Interactive Neo4j graph visualization |
| Canvas | `/canvas/[identityId]` | Identity-focused investigation canvas |
| Analytics | `/analytics` | Security analytics and trends |
| Ingestion | `/ingestion` | Data ingestion management |
| CloudTrail | `/cloudtrail` | CloudTrail event viewer |
| Reports | `/reports` | Report generation and history |
| Audit Logs | `/audit-logs` | System audit trail |
| Integrations | `/integrations` | Integration management |
| AWS Integration | `/integrations/aws` | AWS-specific configuration |
| Settings | `/settings` | User/workspace settings |
| Organization | `/organization` | Organization management |
| Team | `/team` | Team member management |

## State Management (Zustand)

**File**: `src/lib/store.ts`

Global state managed with Zustand + `persist` middleware (stored in `localStorage` as `sentinel-storage`):

```typescript
interface GlobalState {
  isUploading: boolean;              // File upload status
  theme: 'Dark' | 'Light' | 'System'; // UI theme
  currentWorkspaceId: string | null;  // Active workspace
  autoRefreshInterval: number | null; // Dashboard refresh (default: 5000ms)
  dashboardView: 'executive' | 'soc'; // Dashboard perspective
  userRole: string | null;           // Current user role
  userFullName: string | null;       // Current user name
}
```

Auth tokens are stored separately in `localStorage` as `auth-storage`.

## API Integration Layer

**File**: `src/lib/api.ts`

Centralized `ApiClient` class handling:

- **Base URL**: `NEXT_PUBLIC_API_URL` env var (default: `http://localhost:8000/api/v1`)
- **Auth headers**: Auto-injects `Authorization: Bearer <token>` from localStorage
- **Workspace header**: Auto-injects `X-Workspace-ID` from Zustand store
- **Error handling**: Parses JSON error responses, extracts `detail` or `error.message`

**Methods**:
| Method | Usage |
|--------|-------|
| `api.get(endpoint)` | GET requests with auth |
| `api.post(endpoint, body)` | POST with JSON or FormData |
| `api.put(endpoint, body)` | PUT with JSON |
| `api.download(endpoint, filename)` | Download file as blob |

## Testing

| Tool | Purpose |
|------|---------|
| Vitest | Unit and component tests |
| MSW (Mock Service Worker) | API mocking for tests |
| Puppeteer | E2E and screenshot testing |

**Commands**:
```bash
npm run test            # Run tests once
npm run test:watch      # Watch mode
npm run test:coverage   # Coverage report
```

## Environment Configuration

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend API base URL |

## Build & Deployment

```bash
npm run dev      # Development server (webpack mode)
npm run build    # Production build
npm run start    # Start production server
npm run lint     # ESLint check
```

Deployed on **Netlify** (see `netlify.toml` in project root) and **Vercel**.
