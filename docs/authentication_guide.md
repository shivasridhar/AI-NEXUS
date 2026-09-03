# SentinelAI Authentication & Authorization Guide

## Overview

SentinelAI uses a custom JWT-based authentication system with **bcrypt** password hashing, **Google OAuth 2.0** integration, and **Redis-backed token blacklisting**. Multi-tenancy is enforced through organization/workspace hierarchy with role-based access control (RBAC).

## Technology Stack

| Component | Technology |
|-----------|------------|
| Password Hashing | bcrypt |
| Token Format | JWT (HS256) |
| Token Library | PyJWT |
| OAuth Provider | Google OAuth 2.0 |
| Token Blacklist | Redis |
| Rate Limiting | SlowAPI |

---

## Authentication Flows

### 1. Local Registration (`POST /api/v1/auth/register`)

```
Client                     Backend                    Database
  |                          |                          |
  |-- POST /register ------->|                          |
  |   {email, password,      |                          |
  |    full_name,             |                          |
  |    organization_name,     |-- Check email unique --->|
  |    workspace_name}        |<-- OK ------------------|
  |                          |                          |
  |                          |-- Create Organization -->|
  |                          |-- Create Workspace ----->|
  |                          |-- Create User (admin) -->|
  |                          |<-- Committed ------------|
  |                          |                          |
  |<-- {access_token,        |                          |
  |     refresh_token,        |                          |
  |     token_type: "bearer"} |                          |
```

**Rate limit**: 5 requests/minute

**Password requirements** (enforced in schema):
- Minimum 12 characters, maximum 128
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character

### 2. Local Login (`POST /api/v1/auth/login`)

```
Client                     Backend                    Database        EventBus
  |                          |                          |               |
  |-- POST /login ---------->|                          |               |
  |   {email, password}      |-- Find user by email --->|               |
  |                          |<-- User record ----------|               |
  |                          |                          |               |
  |                          |-- bcrypt.verify -------->|               |
  |                          |                          |               |
  |                          |-- Publish LOGIN_SUCCESS ----------------->|
  |                          |                          |               |
  |<-- {access_token,        |                          |               |
  |     refresh_token}        |                          |               |
```

**Rate limit**: 10 requests/minute

### 3. Google OAuth (`POST /api/v1/auth/google`)

```
Client                     Backend                 Google API       Database
  |                          |                        |               |
  |-- POST /google --------->|                        |               |
  |   {credential}           |-- verify_oauth2_token->|               |
  |                          |<-- idinfo -------------|               |
  |                          |                        |               |
  |                          |-- Validate issuer, email_verified      |
  |                          |                        |               |
  |                          |-- Lookup by google_id --------------->|
  |                          |   (or email fallback)                  |
  |                          |                        |               |
  |                          |   [New user?] --> provision_new_account|
  |                          |   [Existing?] --> link google_id       |
  |                          |                        |               |
  |<-- {access_token,        |                        |               |
  |     refresh_token}        |                        |               |
```

**Rate limit**: 10 requests/minute

**Google token validation checks**:
- Token verified against `GOOGLE_CLIENT_ID`
- Issuer must be `accounts.google.com` or `https://accounts.google.com`
- `email_verified` must be true
- Email and sub (google_id) must be present

### 4. Token Refresh (`POST /api/v1/auth/refresh`)

```
Client                     Backend                    Redis
  |                          |                          |
  |-- POST /refresh -------->|                          |
  |   {refresh_token}        |-- Decode JWT ----------->|
  |                          |-- Check type="refresh"   |
  |                          |-- Check blacklist ------>|
  |                          |<-- Not blacklisted ------|
  |                          |                          |
  |<-- {access_token}        |                          |
```

### 5. Logout (`POST /api/v1/auth/logout`)

```
Client                     Backend                    Redis
  |                          |                          |
  |-- POST /logout --------->|                          |
  |   {refresh_token?}       |-- Decode refresh token   |
  |                          |-- Extract JTI            |
  |                          |-- SETEX blacklist:{jti} ->|
  |                          |   TTL = token expiry     |
  |                          |                          |
  |<-- {message: "ok"}       |                          |
```

---

## JWT Token Structure

### Access Token
```json
{
  "exp": 1234567890,
  "sub": "user-uuid-here",
  "type": "access"
}
```
- **Algorithm**: HS256
- **Expiry**: 30 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- **Signed with**: `SECRET_KEY` environment variable

### Refresh Token
```json
{
  "exp": 1234567890,
  "sub": "user-uuid-here",
  "type": "refresh",
  "jti": "unique-hex-token-id"
}
```
- **Expiry**: 7 days (configurable via `REFRESH_TOKEN_EXPIRE_MINUTES`)
- **JTI**: Unique identifier for blacklisting support

---

## Role-Based Access Control (RBAC)

### Roles

| Role | Level | Description |
|------|-------|-------------|
| `admin` | Highest | Full access, user management, organization settings |
| `analyst` | Mid | Security analysis, investigations, report generation |
| `viewer` | Low | Read-only access to dashboards and reports |
| `user` | Default | Default role on registration (same as viewer) |

### Permission Matrix

| Action | admin | analyst | viewer |
|--------|-------|---------|--------|
| View dashboards | Yes | Yes | Yes |
| View reports | Yes | Yes | Yes |
| Run AI investigations | Yes | Yes | No |
| Trigger ingestion | Yes | Yes | No |
| Generate reports | Yes | Yes | No |
| Manage integrations | Yes | No | No |
| Manage users | Yes | No | No |
| Organization settings | Yes | No | No |

### Using RBAC in Endpoints

```python
from app.api.dependencies import require_admin, require_analyst, require_viewer

# Pre-built role checkers:
# require_admin   -> allows: ["admin"]
# require_analyst  -> allows: ["admin", "analyst"]
# require_viewer   -> allows: ["admin", "analyst", "viewer"]

@router.get("/admin-only")
def admin_endpoint(user: User = Depends(require_admin)):
    ...

@router.get("/analyst-and-above")
def analyst_endpoint(user: User = Depends(require_analyst)):
    ...
```

---

## Multi-Tenancy & Workspace Isolation

### Hierarchy

```
Organization (tenant boundary)
  |
  +-- User (belongs to one org)
  |
  +-- Workspace (logical environment)
       |
       +-- All data (access_logs, findings, etc.)
```

### Workspace Resolution

Every authenticated API request must include the `X-Workspace-ID` header:

```python
def get_current_workspace(
    x_workspace_id: str = Header(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Workspace:
    # 1. Validate UUID format
    # 2. Query workspace WHERE id = x_workspace_id AND organization_id = user.organization_id
    # 3. Return 403 if workspace not found or not in user's org
```

This ensures a user can never access data from another organization's workspace.

---

## API Authentication Dependency Chain

```
Request
  |
  v
OAuth2PasswordBearer (extract token from Authorization header)
  |
  v
get_current_user (decode JWT, lookup user in DB)
  |
  v
get_current_active_user (check user.is_active)
  |
  v
RoleChecker (optional - verify role permissions)
  |
  v
get_current_workspace (validate X-Workspace-ID against user's org)
```

---

## Security Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | (required) | JWT signing key - MUST be set in production |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_MINUTES` | 10080 (7 days) | Refresh token lifetime |
| `GOOGLE_CLIENT_ID` | (optional) | Google OAuth client ID |

### Security Best Practices

1. **SECRET_KEY**: Generate with `python -c "import secrets; print(secrets.token_hex(32))"`
2. **Token blacklisting**: Uses Redis with automatic TTL expiry
3. **Rate limiting**: Applied to auth endpoints via SlowAPI
4. **Password hashing**: bcrypt with auto-generated salt
5. **Google OAuth**: Validates issuer, email verification, and handles account linking
6. **CORS**: Explicit origin allowlist (never `*` with credentials)
7. **Audit logging**: Login events published to EventBus for audit trail
