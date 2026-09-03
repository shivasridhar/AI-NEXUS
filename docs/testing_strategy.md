# SentinelAI Testing Strategy

## Overview

SentinelAI uses **pytest** for backend testing and **Vitest** with **MSW** (Mock Service Worker) for frontend testing. CI runs CloudTrail regression tests via GitHub Actions.

## Backend Testing (pytest)

### Configuration

**`sentinel_backend/pytest.ini`**:
```ini
[pytest]
pythonpath = .
testpaths = tests .
```

**`sentinel_backend/conftest.py`**:
- Adds `sentinel_backend/` to `sys.path`
- Loads `.env` via `dotenv`

### Test Categories

| Category | Files | Description |
|----------|-------|-------------|
| Unit Tests | `test.py` | Core functionality tests |
| AI Tests | `test_ai.py`, `test_ai_real.py` | AI service mocked and real API tests |
| Auth Tests | `test_auth_flow.py` | Authentication flow validation |
| Normalization | `test_normalization.py` | Data normalization pipeline |
| Ingestion | `test_ingest_idempotency.py` | Deduplication and idempotency |
| Empty Records | `test_empty_records.py` | Edge case: empty/null data handling |
| Reports | `test_report.py` | Report generation pipeline |
| Gemini | `test_gemini.py` | Gemini API integration tests |
| Upload | `test_upload_script.py` | File upload handling |
| E2E | `e2e_test.py` | End-to-end API flow tests |
| CloudTrail Regression | `tests/test_cloudtrail_regression.py` | CI-triggered regression suite |

### Running Tests

```bash
cd sentinel_backend

# Run all tests
pytest -v

# Run specific test file
pytest test_auth_flow.py -v

# Run with coverage
pytest --cov=app --cov-report=html

# Run only AI tests
pytest test_ai.py -v

# Run E2E tests
pytest e2e_test.py -v
```

### Test Database

- CI uses a separate PostgreSQL service (`sentinel_test` database)
- Connection via `DATABASE_URL` environment variable
- Tests that need a real database use the CI Postgres instance

## Frontend Testing (Vitest + MSW)

### Configuration

**`sentinel_frontend/src/setupTests.ts`** - Global test setup

**Mock Service Worker (MSW)**:
- `src/mocks/handlers.ts` - API request handlers for mocking
- `src/mocks/server.ts` - MSW server configuration

### Running Tests

```bash
cd sentinel_frontend

# Run all tests
npm run test

# Watch mode
npm run test:watch

# Coverage report
npm run test:coverage
```

## CI/CD Testing (GitHub Actions)

### CloudTrail Regression Suite

**Trigger**: Push/PR to `main`/`master` that modifies:
- `sentinel_backend/app/services/cloudtrail_parser.py`
- `sentinel_backend/app/services/ingestion.py`
- `sentinel_backend/app/services/ingestion_pipeline/**`
- `sentinel_backend/app/services/connectors/**`

**Environment**:
- Ubuntu latest
- Python 3.12
- PostgreSQL 15 (service container)

**Steps**:
1. Checkout code
2. Setup Python 3.12 with pip cache
3. Install dependencies + pytest + testcontainers
4. Run `tests/test_cloudtrail_regression.py -v`

## Test Writing Guidelines

### Backend Test Pattern

```python
# test_example.py
import pytest
from app.services.some_service import SomeService

def test_should_do_something():
    """Test description matching the behavior being verified."""
    # Arrange
    service = SomeService()
    input_data = {...}
    
    # Act
    result = service.process(input_data)
    
    # Assert
    assert result.status == "completed"
    assert len(result.findings) > 0
```

### Frontend Test Pattern

```typescript
// Component.test.tsx
import { render, screen } from '@testing-library/react';
import { Component } from './Component';

describe('Component', () => {
  it('should render correctly', () => {
    render(<Component />);
    expect(screen.getByText('Expected Text')).toBeInTheDocument();
  });
});
```

## Test Data

- `sentinel_backend/sample_cloudtrail.json` - Sample CloudTrail events
- `sentinel_backend/valid_sample.json` / `NEW_TEST_PAYLOAD.json` - Test payloads
- `testfiles/` directory - Additional test fixtures
