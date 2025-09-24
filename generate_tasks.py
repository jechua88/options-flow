from textwrap import dedent

tasks = []

def add_task(task_id, depends, what, acceptance, tests):
    tasks.append((task_id, depends, what, acceptance, tests))

add_task(1, [], "Scaffold repository with src/tests dirs, pyproject, Makefile, Streamlit + FastAPI entrypoints, README", "`make run` boots API on :8000 and UI on :8501 locally without errors", "`make test` placeholder passes on fresh clone")
add_task(2, [1], "Define DuckDB schema DDL script and load demo parquet sample for SPY/QQQ/AAPL", "Running `python scripts/init_db.py --demo` creates tables trades_raw/nbbo_at_trade/trades_labeled/rollups_min/open_interest_eod and loads demo rows", "Unit `tests/test_schema.py` validates table existence and sample row counts")
add_task(3, [1], "Implement Polygon adapter package handling auth, WebSocket trade subscribe, REST helpers with retry/backoff", "`pytest tests/vendors/test_Polygon.py` passes and sample subscribe logs first trade", "Integration stub hitting mocked Polygon server succeeds within 3 retries")
add_task(4, [3], "Build NBBO cache module storing latest bid/ask per option with expiry-aware keys and quote-at-trade fallback", "Simulated feed keeps cache hot for SPY contracts without stale misses beyond configured TTL", "Unit tests cover cache hit/miss, fallback REST call, and timestamp expiry")
add_task(5, [4], "Create side classifier applying epsilon rule max(0.01 USD, 5 percent spread) with BUY/SELL/MID outputs", "Classifier matches expected labels for curated edge-case fixture set (mid prints, crossed markets)", "`pytest tests/classifiers/test_side_label.py` green with >95% branch coverage")
add_task(6, [5], "Develop sweep clustering heuristic grouping same contract trades within 200ms and same side", "Replay of sample burst produces aggregated sweep IDs with consistent notional sums", "Unit tests feed synthetic bursts and assert cluster boundaries and totals")
add_task(7, [2,6], "Implement per-minute rollup job writing to rollups_min and windowed CTE helpers", "Rolling query over last 60 minutes returns net premium totals matching manual calc within demo", "`pytest tests/services/test_rollups.py` passes including 5s refresh simulation")
add_task(8, [7], "Expose FastAPI endpoints (/top,/prints,/ticker/{sym},/export.csv) with Pydantic models and SSE hook", "curl requests return JSON/CSV with filters applied and schema validated", "`pytest tests/api/test_endpoints.py::test_smoke_demo` succeeding against demo DB")
add_task(9, [8], "Ship Streamlit UI page with live table, filters, prints feed, ticker detail drawer, CSV download button", "User can interactively filter demo data and download CSV containing same rows", "Playwright smoke in `tests/e2e/test_streamlit.py` confirms critical elements render")
add_task(10, [2], "Write nightly EOD open interest fetcher updating open/close labels next day", "Scheduled run populates open_interest_eod with polygon sample and refreshes unusual flags", "Unit test mocks polygon client and verifies label transitions after job")
add_task(11, [1], "Add structured logging, rotation, ingest heartbeat, and FastAPI /health reporting queue depth", "`curl /health` returns JSON with `status: ok` and recent ingest timestamp", "`pytest tests/observability/test_health.py` exercises log formatting + heartbeat")
add_task(12, [1], "Author Dockerfile (optional) and CI workflow running lint/type/test on push", "GitHub Actions run completes lint, mypy, pytest stages using docker image", "Local `act` or pipeline dry run passes with green checks")
add_task(13, [2,8,9], "Implement offline demo mode wiring so API/UI serve seeded parquet without polygon credentials", "`make demo` starts API+UI using sample data and all dashboards render without external calls", "`pytest tests/e2e/test_demo_mode.py` runs against demo flag verifying endpoints and UI data")

next_id = 14

categories = [
    {
        'name': 'Repo Automation',
        'count': 59,
        'base': 1,
        'module_fmt': 'scripts/tooling/task_{n}.py',
        'features': [
            'pre-commit hook enforcement', 'ruff lint rule sync', 'mypy strict mode tune', 'Makefile help target', 'pyproject classifier metadata',
            'dependency pin review', 'devcontainer base', 'editorconfig tweaks', 'gitignore refinement', 'license header injector',
            'contrib guidelines note', 'changelog template stub', 'version bump helper', 'poetry lock refresh', 'hatch env alias',
            'pytest.ini tuning', 'coverage config baseline', 'task runner alias', 'release checklist doc', 'pip-tools export helper'
        ],
        'tests_fmt': 'Run `make lint` to validate {feature} works.'
    },
    {
        'name': 'Config Settings',
        'count': 50,
        'base': 1,
        'module_fmt': 'config/settings.py',
        'features': [
            'environment var parsing', 'default window values', 'symbol allowlist handling', 'batch size tuneable', 'NBBO cache TTL',
            'epsilon override flag', 'demo mode toggle', 'polygon credentials validation', 'logging level mapping', 'API pagination limits'
        ],
        'tests_fmt': 'Use `pytest tests/config/test_settings.py::{test}` to confirm parsing.'
    },
    {
        'name': 'Vendor Adapter',
        'count': 70,
        'base': 3,
        'module_fmt': 'vendors/Polygon/client.py',
        'features': [
            'heartbeat handler', 'reconnect jitter', 'subscription ack parsing', 'trade schema validation', 'quote schema validation',
            'sequence gap detection', 'backoff multiplier tuning', 'auth token refresh', 'ping/pong monitor', 'rate-limit handling'
        ],
        'tests_fmt': 'Mock WebSocket fixture verifies {feature} scenario.'
    },
    {
        'name': 'NBBO Handling',
        'count': 50,
        'base': 4,
        'module_fmt': 'ingest/nbbo_cache.py',
        'features': [
            'cache warmup routine', 'stale entry eviction', 'multi-expiry separation', 'quote snapshot persistence', 'NBBO gap logging',
            'fallback REST batching', 'cache metrics export', 'midpoint helper', 'quote lag guardrail', 'quote replay support'
        ],
        'tests_fmt': '`pytest tests/nbbo/test_cache.py::{test}` asserts {feature} pathways.'
    },
    {
        'name': 'Side Classification',
        'count': 40,
        'base': 5,
        'module_fmt': 'services/side_classifier.py',
        'features': [
            'penny-wide handling', 'zero spread fallback', 'odd-lot scaling', 'locked market detection', 'crossed market guard',
            'epsilon per symbol tuning', 'midpoint tolerance log', 'multileg ignore', 'late quote rejection', 'unknown tagging'
        ],
        'tests_fmt': '`pytest tests/classifiers/test_side_label.py::{test}` covers {feature} edge.'
    },
    {
        'name': 'Sweep Clustering',
        'count': 40,
        'base': 6,
        'module_fmt': 'services/sweep_cluster.py',
        'features': [
            'same side enforcement', 'time gap threshold', 'venue mixing logic', 'huge notional guard', 'partial fill merge',
            'cluster id generator', 'batch flush timer', 'orphan trade handling', 'sweep metrics emitter', 'mid-price variance log'
        ],
        'tests_fmt': '`pytest tests/services/test_sweeps.py::{test}` validates {feature} case.'
    },
    {
        'name': 'Rollups Engine',
        'count': 100,
        'base': 7,
        'module_fmt': 'services/rollups.py',
        'features': [
            'minute aggregation view', 'window materialization', 'net premium calc', 'call-put split', 'zero DTE ratio',
            'top strike ranking', 'strike expiry join', 'ticker ordering metric', 'rollup backfill', 'rollup validation alert'
        ],
        'tests_fmt': '`pytest tests/services/test_rollups.py::{test}` ensures {feature} math.'
    },
    {
        'name': 'API Layer',
        'count': 110,
        'base': 8,
        'module_fmt': 'api/main.py',
        'features': [
            'dependency injection wiring', 'pagination envelope', 'filter coercion', 'window query binding', 'CSV streaming',
            'SSE heartbeat', 'error handling', 'cache headers', 'auth stub', 'demo mode routing'
        ],
        'tests_fmt': '`pytest tests/api/test_endpoints.py::{test}` guards {feature} behavior.'
    },
    {
        'name': 'UI Enhancements',
        'count': 120,
        'base': 9,
        'module_fmt': 'ui/app.py',
        'features': [
            'table refresh cadence', 'filter chip styling', 'prints feed autoscroll', 'ticker modal layout', 'csv button feedback',
            '0DTE badge', 'call/put color legend', 'window selector', 'min notional slider', 'sweep tooltip'
        ],
        'tests_fmt': 'Playwright step `tests/e2e/test_streamlit.py::{test}` checks {feature} UX.'
    },
    {
        'name': 'OI Processing',
        'count': 45,
        'base': 10,
        'module_fmt': 'services/oi_loader.py',
        'features': [
            'download retry', 'file checksum', 'temp table load', 'delta upsert', 'open-close calc',
            'unusual flag recompute', 'schedule guard', 'no data alert', 'timezone adjust', 'historical backfill'
        ],
        'tests_fmt': '`pytest tests/services/test_oi_loader.py::{test}` simulates {feature} path.'
    },
    {
        'name': 'Observability',
        'count': 45,
        'base': 11,
        'module_fmt': 'observability/logging.py',
        'features': [
            'structured log schema', 'rotation policy', 'ingest heartbeat metric', 'queue depth gauge', 'API latency histogram',
            'error alert hook', 'health payload cache', 'log level toggle', 'SSE monitor', 'UI telemetry bridge'
        ],
        'tests_fmt': '`pytest tests/observability/test_logging.py::{test}` verifies {feature} output.'
    },
    {
        'name': 'CI Docker',
        'count': 30,
        'base': 12,
        'module_fmt': 'ci/workflows/build.yml',
        'features': [
            'lint job matrix', 'type check stage', 'pytest stage', 'docker build cache', 'docker push guard',
            'artifact upload', 'workflow dispatch', 'schedule nightly', 'slack notification', 'badge update'
        ],
        'tests_fmt': 'Use `act -W .github/workflows/main.yml` to simulate {feature}.'
    },
    {
        'name': 'Testing Suite',
        'count': 102,
        'base': 5,
        'module_fmt': 'tests/',
        'features': [
            'fixture cleanup', 'fake trade generator', 'fake quote generator', 'duckdb temp setup', 'api client helper',
            'ui playwright fixtures', 'sweep scenario builder', 'epsilon edge fixtures', 'oi snapshot fixture', 'performance benchmark'
        ],
        'tests_fmt': 'Run `pytest -k {test}` to ensure {feature} coverage.'
    },
    {
        'name': 'Documentation',
        'count': 60,
        'base': 1,
        'module_fmt': 'docs/',
        'features': [
            'architecture overview', 'ingest flow diagram', 'schema reference', 'api usage guide', 'ui usage guide',
            'demo mode steps', 'deployment checklist', 'troubleshooting', 'faq entry', 'glossary term'
        ],
        'tests_fmt': 'Manual review ensures {feature} is current.'
    },
    {
        'name': 'Performance Optimization',
        'count': 40,
        'base': 7,
        'module_fmt': 'perf/',
        'features': [
            'duckdb index tune', 'ingest batch size tweak', 'NBBO cache profiling', 'rollup SQL optimization', 'api query plan',
            'ui render throttle', 'websocket buffer', 'sse compression', 'csv export speed', 'playwright perf script'
        ],
        'tests_fmt': 'Run `pytest tests/perf/test_profiles.py::{test}` capturing {feature} metric.'
    },
    {
        'name': 'Security Hardening',
        'count': 40,
        'base': 1,
        'module_fmt': 'security/',
        'features': [
            'dotenv validation', 'secret masking', 'dependency audit', 'fastapi csrf stub', 'streamlit auth stub',
            'rate limit policy', 'log redaction', 'tls doc', 'docker scan', 'supply chain note'
        ],
        'tests_fmt': '`pytest tests/security/test_controls.py::{test}` exercises {feature} requirement.'
    }]

current_id = next_id

for category in categories:
    prev = None
    features = category['features']
    feature_len = len(features)
    for i in range(category['count']):
        tid = current_id
        feature = features[i % feature_len]
        module = category['module_fmt'].format(n=i+1)
        test_name = feature.replace(' ', '_') + f"_{i+1}"
        depends = [category['base']]
        if prev:
            depends.append(prev)
        what = f"Extend {category['name']} by implementing {feature} (iteration {i+1}) in {module}."
        acceptance = f"Feature works: manual check shows {feature} available with expected behavior for iteration {i+1}."
        tests = category['tests_fmt'].format(feature=feature, test=test_name)
        add_task(tid, depends, what, acceptance, tests)
        prev = tid
        current_id += 1

assert current_id == 1015

tasks.sort(key=lambda x: x[0])

for task_id, depends, what, acceptance, tests in tasks:
    depends_str = '-' if not depends else '[' + ','.join(str(d) for d in depends) + ']'
    print(f"Task {task_id} (Depends: {depends_str}) What: {what}; Acceptance: {acceptance}; Tests: {tests}")

