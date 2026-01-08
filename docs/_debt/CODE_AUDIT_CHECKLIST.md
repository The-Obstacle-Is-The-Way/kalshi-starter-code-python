# Code Audit Checklist - AI & Human-Generated Code

**Purpose:** Systematic checklist for detecting bugs, anti-patterns, and security vulnerabilities in codebases—especially those containing AI-generated code.

**Last Updated:** 2026-01-08
**Sources:** Web research from 2025-2026 industry reports, OWASP, security researchers, and engineering blogs.

---

# ⚠️ CRITICAL: Mock/Hardcoded Data in Production Code Paths

> **THIS IS THE #1 PRIORITY CHECK. DO THIS FIRST.**

## The Most Dangerous AI Anti-Pattern: Reward Hacking

**Why this is egregious:** Mock data in production code paths is the ultimate form of "reward hacking" — the code looks complete, tests may pass, demos look good, but **zero actual work is being done**. This is the AI equivalent of a contractor installing a fake wall that looks real but has nothing behind it.

### Historical Example Found (2026-01-07)

```python
# Historical example (this repo, pre-SPEC-018 CLI refactor): src/kalshi_research/cli.py
@research_app.command("backtest")
def research_backtest(start, end, db_path):
    # ... validation code that looks legit ...

    # Mock output for now  <-- THE SMOKING GUN
    table = Table(title="Backtest Results")
    table.add_row("Total Trades", "10")       # FAKE
    table.add_row("Win Rate", "60.0%")        # FAKE
    table.add_row("Total P&L", "$150.00")     # FAKE
    table.add_row("Sharpe Ratio", "1.5")      # FAKE
    console.print(table)
```

**The insidious part:** The `ThesisBacktester` class exists and works! The CLI just doesn't use it.

### Why This Happens

1. **AI satisfies the interface first** — Creates a command that runs without errors
2. **AI leaves "implementation for later"** — But makes it look complete
3. **Tests may pass** — Because tests verify output format, not correctness
4. **Demos look good** — Output is well-formatted, appears professional
5. **No runtime errors** — Code executes successfully

### Checklist: Mock Data Detection

- [ ] **`# Mock` comments** — Explicit admission of fake data
- [ ] **`# for now` comments** — Placeholder that was never replaced
- [ ] **`# placeholder` comments** — Same as above
- [ ] **`# TODO` in production paths** — Feature never completed
- [ ] **Hardcoded numeric strings in output** — `"10"`, `"60.0%"`, `"$150.00"`
- [ ] **Static table rows** — `table.add_row("Metric", "hardcoded_value")`
- [ ] **Functions that don't use their parameters** — Accept `start`, `end`, `db_path` but ignore them
- [ ] **CLI commands with no actual implementation** — Accept options but do nothing with them
- [ ] **Docstrings saying "placeholder" or "stub"**
- [ ] **Return values that look plausible but are static** — `return {"status": "success", "count": 10}`

### Detection Commands

```bash
# Find explicit mock comments
grep -rn "# [Mm]ock\|# for now\|# placeholder\|# stub" --include="*.py" src/

# Find hardcoded numbers in table output (suspicious)
grep -rn "add_row.*\"\d" --include="*.py" src/

# Find CLI commands with TODO/placeholder docstrings
grep -rn "\"\"\".*placeholder\|\"\"\".*stub\|\"\"\".*TODO" --include="*.py" src/

# Find functions that accept parameters but don't use them
# (Manual review required - look for unused arguments)

# Cross-reference: Does implementation exist but CLI doesn't use it?
# 1. Find CLI commands
grep -rn "@.*\.command" --include="*.py" src/
# 2. For each command, verify it calls actual implementation
```

### Verification Strategy

For EVERY CLI command and public API function:

1. **Trace the data flow** — Does input actually affect output?
2. **Test with edge cases** — Does `--start 2020-01-01` produce different results than `--start 2025-01-01`?
3. **Compare to implementation** — If `ThesisBacktester` exists, does the CLI use it?
4. **Check parameter usage** — Are all parameters actually used or ignored?
5. **Diff multiple runs** — Does output change with different inputs?

### Historical Known Violations (Fixed)

| File | Lines | Issue | Status |
|------|-------|-------|--------|
| `cli.py` (removed; now `cli/research.py`) | N/A | `kalshi research backtest` previously output hardcoded fake results | ✅ Fixed |
| `cli.py` (removed; now `cli/alerts.py`) | N/A | `--daemon` flag previously accepted but not implemented | ✅ Fixed |

### The Fix Pattern

```python
# BAD: Mock data
@command("backtest")
def backtest(start, end, db_path):
    table.add_row("Trades", "10")  # FAKE

# GOOD: Wire to actual implementation
@command("backtest")
def backtest(start, end, db_path):
    backtester = ThesisBacktester()
    result = await backtester.run(start, end, db_path)  # REAL
    table.add_row("Trades", str(result.total_trades))   # REAL
```

### Why This Matters

- **User trust destroyed** — They think they're backtesting but getting fake data
- **Decisions made on lies** — Trading decisions based on fake backtest results
- **Time wasted** — User thinks feature works, doesn't investigate further
- **Technical debt hidden** — Looks complete, so never gets fixed

### References

- [Reward Hacking in AI Systems](https://arxiv.org/abs/2209.13085)
- [Specification Gaming Examples](https://deepmind.com/blog/specification-gaming)
- This checklist itself: Added after discovering mock data in production on 2026-01-07

---

## Quick Reference: Detection Commands

```bash
# Run all quality gates
uv run ruff check .           # Lint
uv run ruff format --check .  # Format
uv run mypy src/ --strict     # Type check
uv run pytest --cov           # Tests + coverage

# Secret detection
grep -rn "password\|secret\|api_key\|token" --include="*.py" .
grep -rn "sk-\|pk_\|ghp_\|AKIA" --include="*.py" .  # Common key prefixes

# Exception swallowing
grep -rn "except.*:" --include="*.py" . | grep -v "except.*Error"
grep -rn "pass$" --include="*.py" .  # Bare pass after except

# TODO/FIXME hunting
grep -rn "TODO\|FIXME\|XXX\|HACK" --include="*.py" .
```

---

## 1. Silent Failures & Exception Swallowing

**Why it matters:** [The "most diabolical Python antipattern"](https://realpython.com/the-most-diabolical-python-antipattern/) — bugs become invisible, debugging becomes impossible.

### Checklist

- [ ] **Bare `except:` blocks** — Catches everything including `KeyboardInterrupt` and `SystemExit`
- [ ] **`except Exception: pass`** — Silently swallows all errors
- [ ] **`except Exception as e:` without logging** — Error captured but never reported
- [ ] **Empty `except` blocks with only `pass`** — No error handling whatsoever
- [ ] **Async exceptions swallowed** — Background tasks failing silently
- [ ] **Context managers without proper `__exit__` error handling**

### Detection Pattern
```bash
# Find bare except blocks
grep -rn "except:" --include="*.py" .

# Find except with pass (silent swallowing)
grep -rn -A1 "except.*:" --include="*.py" . | grep "pass"

# Find broad exception catches
grep -rn "except Exception" --include="*.py" .
```

### Correct Pattern
```python
# BAD
try:
    risky_operation()
except:
    pass

# GOOD
try:
    risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise  # or handle appropriately
```

**Sources:**
- [How to Avoid Silent Failures in Python Code](https://www.index.dev/blog/avoid-silent-failures-python)
- [Errors Should Never Pass Silently - Pybites](https://pybit.es/articles/error_handling/)

---

## 2. Type Safety Issues

**Why it matters:** [45% of production bugs stem from type-related errors](https://devputers.medium.com/how-mypy-saved-my-python-app-from-production-disasters-cde765bc14e3) (Stack Overflow 2025 survey).

### Checklist

- [ ] **`Any` type used excessively** — Defeats type checking entirely
- [ ] **`# type: ignore` without justification** — Hiding type errors
- [ ] **Missing return type annotations** — Implicit `Any` return
- [ ] **`Optional[]` without null checks** — NoneType errors at runtime
- [ ] **Dict with `Any` values** — `dict[str, Any]` loses type info
- [ ] **Missing generic parameters** — `list` instead of `list[str]`
- [ ] **Untyped function parameters** — Public API without type hints
- [ ] **`cast()` overuse** — Lying to the type checker

### Detection Pattern
```bash
# Find type ignores
grep -rn "type: ignore" --include="*.py" .

# Find Any usage
grep -rn ": Any" --include="*.py" .
grep -rn "-> Any" --include="*.py" .

# Find missing return types (functions without ->)
grep -rn "def .*(.*):" --include="*.py" . | grep -v " -> "
```

### Correct Pattern
```python
# BAD
def process(data):  # Untyped
    return data.get("value")  # Could be None

# GOOD
def process(data: dict[str, str]) -> str | None:
    return data.get("value")
```

**Sources:**
- [Mastering Type-Safe Python in 2025: Pydantic and MyPy](https://toolshelf.tech/blog/mastering-type-safe-python-pydantic-mypy-2025/)
- [MyPy Strict Mode Configuration](https://johal.in/mypy-strict-mode-configuration-enforcing-type-safety-in-large-python-codebases/)

---

## 3. Mutable Default Arguments

**Why it matters:** [Most common surprise for new Python programmers](https://docs.python-guide.org/writing/gotchas/) — causes shared state bugs.

### Checklist

- [ ] **`def func(items=[]):`** — List shared across all calls
- [ ] **`def func(config={}):`** — Dict shared across all calls
- [ ] **`def func(data=set()):`** — Set shared across all calls
- [ ] **Class attributes with mutable defaults** — Shared across instances

### Detection Pattern
```bash
# Find mutable default arguments
grep -rn "def.*=\[\]" --include="*.py" .
grep -rn "def.*={}" --include="*.py" .
grep -rn "def.*=set()" --include="*.py" .
```

### Correct Pattern
```python
# BAD
def add_item(item, items=[]):
    items.append(item)
    return items

# GOOD
def add_item(item, items: list | None = None) -> list:
    if items is None:
        items = []
    items.append(item)
    return items
```

**Sources:**
- [Python Mutable Defaults Are The Source of All Evil](https://florimond.dev/en/posts/2018/08/python-mutable-defaults-are-the-source-of-all-evil)
- [Common Gotchas — The Hitchhiker's Guide to Python](https://docs.python-guide.org/writing/gotchas/)

---

## 4. Resource & Connection Leaks

**Why it matters:** Connection pool exhaustion, file handle leaks, memory bloat.

### Checklist

- [ ] **Files opened without `with` statement** — Not guaranteed to close
- [ ] **Database connections not returned to pool** — Pool exhaustion
- [ ] **HTTP clients not closed** — Socket leaks
- [ ] **`multiprocessing.Pool` without context manager** — Resource leaks
- [ ] **Async context managers not awaited properly**
- [ ] **Missing `finally` blocks for cleanup**

### Detection Pattern
```bash
# Find file opens without context manager
grep -rn "open(" --include="*.py" . | grep -v "with "

# Find connection/session creation without context
grep -rn "Session()" --include="*.py" . | grep -v "with "
grep -rn "connect(" --include="*.py" . | grep -v "with "
```

### Correct Pattern
```python
# BAD
conn = pool.getconn()
cursor = conn.cursor()
cursor.execute(query)
# Forgot to return connection!

# GOOD
async with pool.connection() as conn:
    async with conn.cursor() as cursor:
        await cursor.execute(query)
# Automatically returned to pool
```

**Sources:**
- [The Python "with" Trick That Will Fix Your Resource Leaks](https://viju-londhe.medium.com/the-python-with-trick-that-will-fix-your-resource-leaks-ec77b280f636)
- [psycopg3 Connection Pool Docs](https://www.psycopg.org/psycopg3/docs/advanced/pool.html)

---

## 5. N+1 Query Problems

**Why it matters:** [Silent performance killer](https://dev.to/lovestaco/the-n1-query-problem-the-silent-performance-killer-2b1c) — 100 items = 101 queries.

### Checklist

- [ ] **Lazy-loaded relationships accessed in loops** — Classic N+1
- [ ] **Missing `joinedload`/`selectinload` in SQLAlchemy**
- [ ] **Serializers triggering relationship loads** — Marshmallow/Pydantic
- [ ] **Nested API responses without eager loading**
- [ ] **No query logging in development** — Can't see the problem

### Detection Pattern
```bash
# Find relationship access patterns (potential N+1)
grep -rn "\.items\|\.children\|\.related" --include="*.py" .

# Check for eager loading usage
grep -rn "joinedload\|selectinload\|subqueryload" --include="*.py" .

# Enable SQLAlchemy query logging
# In config: echo=True or logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### Correct Pattern
```python
# BAD - N+1 queries
books = session.query(Book).all()
for book in books:
    print(book.author.name)  # Triggers query per book!

# GOOD - Eager loading
from sqlalchemy.orm import selectinload

books = session.query(Book).options(selectinload(Book.author)).all()
for book in books:
    print(book.author.name)  # No additional queries
```

**Sources:**
- [10 SQLAlchemy Relationship Patterns That Don't Become N+1 Hell](https://medium.com/@Modexa/10-sqlalchemy-relationship-patterns-that-dont-become-n-1-hell-9643dbc68712)
- [SQLAlchemy Performance Anti-Patterns](https://dev.to/zchtodd/sqlalchemy-performance-anti-patterns-and-their-fixes-4bmm)

---

## 6. Async/Concurrency Bugs

**Why it matters:** Race conditions are intermittent and hard to reproduce.

### Checklist

- [ ] **Shared mutable state across await points** — Race condition
- [ ] **Missing `asyncio.Lock` for critical sections**
- [ ] **Blocking calls in async functions** — Event loop blocked
- [ ] **`asyncio.create_task` without awaiting/storing reference** — Task lost
- [ ] **Thread-unsafe asyncio object access**
- [ ] **CPU-bound work in async context** — Should use executor

### Detection Pattern
```bash
# Find shared state patterns
grep -rn "global\|self\." --include="*.py" . | grep -B2 "await"

# Find blocking calls in async
grep -rn "time.sleep\|requests\." --include="*.py" .

# Find create_task without reference
grep -rn "create_task" --include="*.py" . | grep -v "=.*create_task"
```

### Correct Pattern
```python
# BAD - Race condition
shared_data = {}

async def update(key, value):
    if key not in shared_data:  # Check
        await some_io()          # Await - other coroutine runs!
        shared_data[key] = value # Write - may overwrite!

# GOOD - Protected with lock
lock = asyncio.Lock()

async def update(key, value):
    async with lock:
        if key not in shared_data:
            await some_io()
            shared_data[key] = value
```

**Sources:**
- [Avoiding Race Conditions in Python in 2025](https://medium.com/pythoneers/avoiding-race-conditions-in-python-in-2025-best-practices-for-async-and-threads-4e006579a622)
- [Asyncio Race Conditions - Super Fast Python](https://superfastpython.com/asyncio-race-conditions/)

---

## 7. Hardcoded Secrets & Credentials

**Why it matters:** [61% of organizations have secrets exposed in repos](https://blog.gitguardian.com/why-its-urgent-to-deal-with-your-hard-coded-credentials/) — #1 breach vector.

### Checklist

- [ ] **API keys in source code** — `api_key = "sk-..."`
- [ ] **Database credentials hardcoded** — Connection strings with passwords
- [ ] **JWT secrets in code** — Should be in env vars
- [ ] **AWS/GCP/Azure keys** — AKIA*, projects/*, etc.
- [ ] **Private keys committed** — `.pem`, `.key` files
- [ ] **Secrets in git history** — Rotated but still in commits
- [ ] **`.env` files committed** — Should be in `.gitignore`

### Detection Pattern
```bash
# Common secret patterns
grep -rn "password\s*=" --include="*.py" .
grep -rn "api_key\s*=" --include="*.py" .
grep -rn "secret\s*=" --include="*.py" .
grep -rn "token\s*=" --include="*.py" .

# Cloud provider key prefixes
grep -rn "AKIA\|sk-\|pk_\|ghp_\|ghu_" --include="*.py" .

# Check for .env in git
git ls-files | grep -E "\.env|credentials|secrets"

# Scan git history
git log -p | grep -E "password|secret|api_key|token" | head -50
```

### Correct Pattern
```python
# BAD
DATABASE_URL = "postgresql://user:password123@localhost/db"

# GOOD
import os
DATABASE_URL = os.environ["DATABASE_URL"]

# BETTER - with validation
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    api_key: str

    class Config:
        env_file = ".env"
```

**Sources:**
- [Hardcoded Secrets: The Unseen Security Risk](https://medium.com/@tolubanji/hardcoded-secrets-the-unseen-security-risk-lurking-in-your-code-102396345115)
- [Managing the Risks of Hard-Coded Secrets - Codacy](https://blog.codacy.com/hard-coded-secrets)

---

## 8. AI-Generated Code: Hallucinated APIs & Libraries

**Why it matters:** [19.7% of AI code samples reference non-existent packages](https://arxiv.org/html/2501.19012v1) — "slopsquatting" supply chain attacks.

### Checklist

- [ ] **Imports that don't resolve** — Library doesn't exist
- [ ] **Method calls on wrong objects** — API hallucination
- [ ] **Deprecated/removed API usage** — LLM trained on old data
- [ ] **Non-existent function parameters** — Made-up kwargs
- [ ] **Fictional library recommendations** — Package doesn't exist in PyPI
- [ ] **Wrong method signatures** — Parameters in wrong order

### Detection Pattern
```bash
# Verify all imports actually exist
python -c "import ast; [print(node.names[0].name) for node in ast.walk(ast.parse(open('file.py').read())) if isinstance(node, ast.Import)]"

# Check if packages exist
pip index versions <package_name>

# Run imports in isolation
python -c "from module import thing"  # Will fail if hallucinated
```

### Verification Steps
1. **Run `pip install` for new dependencies** — Verify they exist
2. **Check PyPI/npm for package** — Manual verification
3. **Read library documentation** — Verify API matches usage
4. **Run type checker** — Will catch many API mismatches
5. **Execute the code** — Hallucinations crash at runtime

**Sources:**
- [Package hallucination: LLMs may deliver malicious code](https://www.helpnetsecurity.com/2025/04/14/package-hallucination-slopsquatting-malicious-code/)
- [Importing Phantoms: Measuring LLM Package Hallucination](https://arxiv.org/html/2501.19012v1)

---

## 9. AI-Generated Tests: Self-Validating Assumptions

**Why it matters:** AI tests often validate hallucinated behaviors, not actual requirements.

### Checklist

- [ ] **Tests mirror implementation exactly** — No independent verification
- [ ] **Tests only check happy path** — No edge cases
- [ ] **Mocked everything** — Tests don't exercise real code
- [ ] **Tests pass but code is wrong** — AI validated its own assumptions
- [ ] **No failure mode testing** — Only success paths
- [ ] **Circular validation** — Test written after code, matches code exactly

### Detection Pattern
```bash
# Check mock density (too many mocks = weak tests)
grep -rn "@mock\|@patch\|Mock()\|MagicMock" tests/ | wc -l

# Check assertion count (few assertions = weak tests)
grep -rn "assert" tests/ | wc -l

# Run mutation testing
pip install mutmut
mutmut run  # Injects bugs, checks if tests catch them
```

### Verification Steps
1. **Write tests BEFORE implementation** — TDD prevents self-validation
2. **Ask AI for failure modes** — "How could this break?"
3. **Use mutation testing** — MutPy, mutmut verify test strength
4. **Review tests independently** — Don't trust AI-generated tests blindly
5. **Test edge cases explicitly** — Empty, null, boundary values

**Sources:**
- [AI-Generated Tests are Lying to You](https://davidadamojr.com/ai-generated-tests-are-lying-to-you/)
- [AI Test Generation Reshapes the QA Engineer's Role](https://medium.com/@roman_fedyskyi/ai-test-generation-reshapes-the-qa-engineers-role-83af6ef90cd9)

---

## 10. Security Vulnerabilities (OWASP)

**Why it matters:** [45% of AI-generated code contains OWASP Top 10 vulnerabilities](https://www.veracode.com/blog/genai-code-security-report/).

### Checklist

- [ ] **SQL Injection** — String formatting in queries
- [ ] **XSS (Cross-Site Scripting)** — Unescaped user input in HTML
- [ ] **Command Injection** — `os.system()`, `subprocess` with user input
- [ ] **Path Traversal** — `../` in file paths from user input
- [ ] **Insecure Deserialization** — `pickle.loads()` on untrusted data
- [ ] **Weak Cryptography** — MD5, SHA1 for passwords, ECB mode
- [ ] **SSRF** — Server-side requests with user-controlled URLs
- [ ] **Missing Input Validation** — Trusting all input

### Detection Pattern
```bash
# SQL injection risks
grep -rn "execute.*%" --include="*.py" .
grep -rn "f\".*SELECT\|f\".*INSERT\|f\".*UPDATE" --include="*.py" .

# Command injection risks
grep -rn "os.system\|subprocess.call\|subprocess.run" --include="*.py" .

# Insecure deserialization
grep -rn "pickle.loads\|yaml.load\(" --include="*.py" .

# Path traversal risks
grep -rn "open.*request\|open.*user\|open.*input" --include="*.py" .

# Use security linters
pip install bandit
bandit -r src/
```

### Correct Pattern
```python
# BAD - SQL injection
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# GOOD - Parameterized query
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))

# BAD - Command injection
os.system(f"convert {user_filename}")

# GOOD - Safe subprocess
subprocess.run(["convert", user_filename], check=True)
```

**Sources:**
- [Veracode 2025 GenAI Code Security Report](https://www.veracode.com/blog/genai-code-security-report/)
- [OWASP Top 10 LLM & Gen AI Vulnerabilities 2025](https://www.brightdefense.com/resources/owasp-top-10-llm/)

---

## 11. Incomplete Implementations (TODO/FIXME)

**Why it matters:** AI often leaves placeholder code that looks complete but isn't.

### Checklist

- [ ] **`TODO` comments in production code** — Unfinished work
- [ ] **`FIXME` markers** — Known bugs not addressed
- [ ] **`pass` in function bodies** — Stub implementations
- [ ] **`raise NotImplementedError`** — Intentionally incomplete
- [ ] **Hardcoded return values** — `return 0`, `return []`, `return {}`
- [ ] **Commented-out code** — Dead code that may confuse

### Detection Pattern
```bash
# Find TODO/FIXME markers
grep -rn "TODO\|FIXME\|XXX\|HACK\|BUG" --include="*.py" .

# Find stub implementations
grep -rn "pass$" --include="*.py" .
grep -rn "NotImplementedError" --include="*.py" .

# Find suspicious hardcoded returns
grep -rn "return 0$\|return \[\]$\|return {}$\|return None$" --include="*.py" .
```

### Verification Steps
1. **Search for all TODOs** — Track in issue tracker
2. **Review all `pass` statements** — Ensure intentional
3. **Check test coverage** — Stubs often have 0% coverage
4. **Run integration tests** — Unit tests may pass on stubs

---

## 12. Circular Imports & Dependency Issues

**Why it matters:** Type hints increase circular import likelihood; breaks at runtime.

### Checklist

- [ ] **Runtime `ImportError: cannot import name`** — Circular dependency
- [ ] **`TYPE_CHECKING` imports used at runtime** — Should only be for hints
- [ ] **Missing `from __future__ import annotations`** — Forward refs not working
- [ ] **Tightly coupled modules** — Design smell

### Detection Pattern
```bash
# Find potential circular imports
# Look for modules that import each other
grep -rn "from.*import\|import.*" --include="*.py" src/ | \
  awk -F: '{print $1, $2}' | sort | uniq -c | sort -rn

# Check for TYPE_CHECKING usage
grep -rn "TYPE_CHECKING" --include="*.py" .

# Run import check
python -c "import src.module"  # Will fail on circular imports
```

### Correct Pattern
```python
# BAD - Runtime circular import
from other_module import OtherClass  # Circular!

class MyClass:
    def method(self) -> OtherClass: ...

# GOOD - TYPE_CHECKING guard
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from other_module import OtherClass

class MyClass:
    def method(self) -> OtherClass: ...  # String forward ref
```

**Sources:**
- [Python Type Hints: Fix Circular Imports - Adam Johnson](https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/)
- [Fixing Circular Imports with Protocol](https://pythontest.com/fix-circular-import-python-typing-protocol/)

---

## 13. Outdated Dependencies & APIs

**Why it matters:** LLMs trained on old data suggest deprecated patterns.

### Checklist

- [ ] **Deprecated library usage** — e.g., `asyncio.get_event_loop()` in 3.10+
- [ ] **Removed API calls** — API changed since LLM training
- [ ] **Old cryptographic methods** — MD5, SHA1, DES
- [ ] **Legacy Python syntax** — `%` formatting vs f-strings
- [ ] **Deprecated type hints** — `typing.List` vs `list` (3.9+)
- [ ] **Unmaintained dependencies** — No updates in 2+ years

### Detection Pattern
```bash
# Check for deprecation warnings
python -W all -c "import your_module"

# Check dependency ages
pip list --outdated

# Find old typing patterns
grep -rn "typing.List\|typing.Dict\|typing.Set\|typing.Tuple" --include="*.py" .

# Check for % string formatting
grep -rn '"%.*%' --include="*.py" .
```

### Verification Steps
1. **Run with `-W all`** — See all deprecation warnings
2. **Check library changelogs** — Breaking changes since LLM training
3. **Use `pip-audit`** — Security vulnerabilities in deps
4. **Update lock files** — `pip list --outdated`

---

## Automated Audit Script

Save as `scripts/audit.sh`:

```bash
#!/bin/bash
set -e

echo "=== Code Audit ==="

echo -e "\n[1/10] Linting..."
uv run ruff check . || echo "❌ Ruff found issues"

echo -e "\n[2/10] Type checking..."
uv run mypy src/ --strict || echo "❌ MyPy found issues"

echo -e "\n[3/10] Security scan..."
uv run bandit -r src/ -ll || echo "❌ Bandit found issues"

echo -e "\n[4/10] Silent exception swallowing..."
grep -rn "except.*:" --include="*.py" src/ | grep -c "pass$" && echo "⚠️ Found silent exceptions" || echo "✅ No silent exceptions"

echo -e "\n[5/10] TODO/FIXME markers..."
grep -rn "TODO\|FIXME\|XXX" --include="*.py" src/ || echo "✅ No TODOs found"

echo -e "\n[6/10] Mutable default arguments..."
grep -rn "def.*=\[\]\|def.*={}" --include="*.py" src/ || echo "✅ No mutable defaults"

echo -e "\n[7/10] Hardcoded secrets scan..."
grep -rn "password\|api_key\|secret" --include="*.py" src/ | grep -v "os.environ\|getenv" || echo "✅ No hardcoded secrets"

echo -e "\n[8/10] Type ignores count..."
echo "Found $(grep -rn "type: ignore" --include="*.py" src/ | wc -l) type ignores"

echo -e "\n[9/10] Tests..."
uv run pytest --tb=short || echo "❌ Tests failed"

echo -e "\n[10/10] Coverage..."
uv run pytest --cov=src --cov-fail-under=80 || echo "⚠️ Coverage below 80%"

echo -e "\n=== Audit Complete ==="
```

---

## References

### AI-Generated Code Risks
- [My LLM coding workflow going into 2026 - Addy Osmani](https://addyosmani.com/blog/ai-coding-workflow/)
- [8 AI Code Generation Mistakes Devs Must Fix To Win 2026](https://vocal.media/futurism/8-ai-code-generation-mistakes-devs-must-fix-to-win-2026)
- [AI-authored code needs more attention, contains worse bugs - The Register](https://www.theregister.com/2025/12/17/ai_code_bugs/)
- [Security Pitfalls of AI Code Generation Tools — 2025 Update](https://medium.com/@derekdw/security-pitfalls-of-ai-code-generation-tools-2025-update-8ded7e50244d)

### Security
- [Veracode 2025 GenAI Code Security Report](https://www.veracode.com/blog/genai-code-security-report/)
- [OWASP Gen AI Security Project](https://genai.owasp.org/)
- [AI-Generated Code Security Checklist: 7 Policies for CISOs](https://www.opsmx.com/blog/ai-generated-code-security-checklist-7-policies-every-ciso-needs/)
- [OpenSSF Security-Focused Guide for AI Code Assistant Instructions](https://best.openssf.org/Security-Focused-Guide-for-AI-Code-Assistant-Instructions)

### Python Anti-Patterns
- [Error Handling Anti-Patterns - charlax/antipatterns](https://github.com/charlax/antipatterns/blob/master/error-handling-antipatterns.md)
- [SQLAlchemy Anti-Patterns - charlax/antipatterns](https://github.com/charlax/antipatterns/blob/master/sqlalchemy-antipatterns.md)
- [10 Python anti-patterns ruining your code](https://medium.com/@devlinktips/10-python-anti-patterns-ruining-your-code-and-what-to-do-instead-e304c457bc98)

### Type Safety
- [Mastering Type-Safe Python in 2025](https://toolshelf.tech/blog/mastering-type-safe-python-pydantic-mypy-2025/)
- [Python Typing in 2025: A Comprehensive Guide](https://khaled-jallouli.medium.com/python-typing-in-2025-a-comprehensive-guide-d61b4f562b99)

---

## 14. Python Truthiness Traps

**Why it matters:** Conflating `None`, `0`, `""`, `[]`, `{}`, `False` causes subtle bugs.

### Checklist

- [ ] **`if value:` when checking for None** — `0` and `""` are falsy but valid
- [ ] **`if not value:` instead of `if value is None:`** — Empty collections treated as None
- [ ] **CLI argument handling** — `--limit 0` treated as "not set"
- [ ] **Optional return values** — Valid falsy returns missed
- [ ] **XML/HTML element checks** — Empty elements are falsy but exist

### Detection Pattern

```bash
# Find potential truthiness bugs
grep -rn "if limit:" --include="*.py" .
grep -rn "if not.*:" --include="*.py" . | grep -v "is not None"
grep -rn "or None" --include="*.py" .  # Suspicious fallback
```

### Correct Pattern

```python
# BAD: Truthiness trap
if limit:  # 0 is treated as "not set"!
    results = results[:limit]

# GOOD: Explicit None check
if limit is not None:
    results = results[:limit]

# BAD: Empty collection vs None
if not items:  # Could be [] (valid empty) or None (error)
    return default

# GOOD: Distinguish empty from missing
if items is None:
    raise ValueError("items required")
if not items:
    logger.warning("Empty items list")
```

**Sources:**
- [Truthy and Falsy Gotchas - Inspired Python](https://www.inspiredpython.com/article/truthy-and-falsy-gotchas)
- [Common Gotchas — Hitchhiker's Guide](https://docs.python-guide.org/writing/gotchas/)

---

## 15. Silent Fallbacks Masking Failures

**Why it matters:** "Successful" pipelines that silently corrupt data.

### Checklist

- [ ] **Default values hiding failures** — `result = api_call() or default_value`
- [ ] **`dict.get(key, default)`** where default masks missing required data
- [ ] **`getattr(obj, 'field', None)`** without checking if None is valid
- [ ] **Retry loops that give up silently** — Max retries → empty result
- [ ] **Fallback empty collections** — `return []` when API fails
- [ ] **Optional parameters with dangerous defaults** — `timeout=None` = infinite

### Detection Pattern

```bash
# Find fallback patterns
grep -rn "or \[\]" --include="*.py" .
grep -rn "or {}" --include="*.py" .
grep -rn "\.get(.*,.*)" --include="*.py" .
grep -rn "getattr.*None" --include="*.py" .
```

### Correct Pattern

```python
# BAD: Silent fallback masks failure
def get_scores():
    try:
        return fetch_from_api()
    except Exception:
        return []  # Looks like success with no data!

# GOOD: Explicit failure
def get_scores() -> list[Score]:
    try:
        return fetch_from_api()
    except ApiError as e:
        logger.error(f"API failed: {e}")
        raise  # Let caller decide
```

**Sources:**
- [When Successful Pipelines Quietly Corrupt Data](https://medium.com/towards-data-engineering/when-successful-pipelines-quietly-corrupt-your-data-4a134544bb73)

---

## 16. Silent Type Coercion & Data Loss

**Why it matters:** Pydantic/Python silently truncates data.

### Checklist

- [ ] **`int` fields receiving floats** — `10.9` → `10` (silent truncation)
- [ ] **Missing `StrictInt`, `StrictFloat`, `StrictStr`** — Pydantic coerces by default
- [ ] **String to number coercion** — `"123abc"` behavior varies
- [ ] **Datetime string parsing** — Silent UTC assumption
- [ ] **Decimal precision loss** — Float intermediates corrupt calculations

### Detection Pattern

```bash
# Find non-strict Pydantic fields
grep -rn ": int" --include="*.py" src/ | grep -v "StrictInt"
grep -rn ": float" --include="*.py" src/ | grep -v "StrictFloat"
```

### Correct Pattern

```python
# BAD: Silent data loss
class Config(BaseModel):
    threshold: int  # 10.9 becomes 10 silently!

# GOOD: Strict typing prevents coercion
from pydantic import StrictInt, StrictFloat

class Config(BaseModel):
    threshold: StrictInt  # 10.9 raises ValidationError
    ratio: StrictFloat
```

**Sources:**
- [Pydantic Strict Mode](https://docs.pydantic.dev/latest/concepts/strict_mode/)
- [Pydantic Drawbacks - Hrekov](https://hrekov.com/blog/pydantic-drawbacks)

---

## 17. Floating Point & Numerical Bugs

**Why it matters:** `0.1 + 0.2 != 0.3` — IEEE 754 representation limits.

### Checklist

- [ ] **Direct `==` comparison of floats** — Almost always wrong
- [ ] **Fixed epsilon that doesn't scale** — May be huge or tiny relative to values
- [ ] **NaN comparisons** — `NaN != NaN` by definition
- [ ] **Division by near-zero** — Produces infinity
- [ ] **Accumulating rounding errors** — Summing many floats
- [ ] **Financial calculations with float** — Use `Decimal` instead

### Detection Pattern

```bash
# Find direct float comparisons
grep -rn "== 0\.\|!= 0\." --include="*.py" .
grep -rn "== 1\.\|!= 1\." --include="*.py" .
```

### Correct Pattern

```python
import math

# BAD: Direct comparison
if result == 0.3:  # May never be true!
    process()

# GOOD: Use math.isclose() or numpy.isclose()
if math.isclose(result, 0.3, rel_tol=1e-9):
    process()

# BAD: NaN comparison
if value > threshold:  # NaN comparisons are always False
    process()

# GOOD: Check for NaN first
if not math.isnan(value) and value > threshold:
    process()
```

**Sources:**
- [Floating-Point Comparison Guide](https://floating-point-gui.de/errors/comparison/)

---

## 18. NumPy/Pandas Silent Failures

**Why it matters:** Broadcasting silently produces wrong results.

### Checklist

- [ ] **Shape mismatch silently broadcast** — Operations on incompatible shapes
- [ ] **Chained indexing assignment** — `df[col][row] = val` may not work
- [ ] **Object dtype masking types** — String columns as object
- [ ] **Integer overflow** — NumPy wraps around silently
- [ ] **In-place mutations** — `df.drop(inplace=True)` side effects

### Detection Pattern

```bash
# Find chained indexing
grep -rn "\]\[" --include="*.py" . | grep -v "def\|#"

# Find potential in-place operations
grep -rn "inplace=True" --include="*.py" .
```

### Correct Pattern

```python
import numpy as np
import pandas as pd

# BAD: Silent broadcasting may produce unexpected shapes
result = array_a * array_b  # Are shapes compatible?

# GOOD: Explicit shape assertions
assert array_a.shape == array_b.shape, f"Shape mismatch"
result = array_a * array_b

# BAD: Chained indexing
df["col"]["row"] = value  # May be a copy!

# GOOD: Use .loc or .iloc
df.loc["row", "col"] = value
```

**Sources:**
- [NumPy Broadcasting](https://numpy.org/doc/stable/user/basics.broadcasting.html)
- [Pandas Indexing and Selecting](https://pandas.pydata.org/docs/user_guide/indexing.html)

---

## 19. Off-by-One & Fencepost Errors

**Why it matters:** Classic programming bug — appears in ranges, indices, boundaries.

### Checklist

- [ ] **`range(n)` confusion** — 0 to n-1, not 0 to n
- [ ] **Loop boundary** — `<= n` vs `< n`
- [ ] **User-facing 1-based vs internal 0-based** — Conversion errors
- [ ] **Slice endpoints** — `items[start:end]` excludes `end`
- [ ] **Length vs index** — n elements = indices 0 to n-1

### Correct Pattern

```python
# BAD: Off-by-one in user input handling
choice = int(input("Enter choice (1-3): "))
items[choice]  # Should be items[choice - 1]!

# GOOD: Convert 1-based to 0-based
items[choice - 1]

# BAD: Fencepost in loop
for i in range(len(items) + 1):  # One too many!
    process(items[i])  # IndexError on last

# GOOD: Correct range
for i in range(len(items)):
    process(items[i])
```

---

## 20. JSON Serialization Edge Cases

**Why it matters:** Crashes in production on edge case data.

### Checklist

- [ ] **`datetime` objects not serializable** — Works until one record has datetime
- [ ] **`Decimal` precision loss via float** — Financial calculations corrupted
- [ ] **`Enum` members not serializable**
- [ ] **`UUID` objects not serializable**
- [ ] **Circular references** — Infinite loops
- [ ] **`None` vs `"null"` string confusion**

### Correct Pattern

```python
import json
from datetime import datetime

# BAD: Crashes on datetime
data = {"created_at": datetime.now()}
json.dumps(data)  # TypeError!

# GOOD: Custom encoder
def json_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError(f"Not serializable: {type(obj)}")

json.dumps(data, default=json_serializer)

# BETTER: Use orjson (handles datetime/enum natively)
import orjson
orjson.dumps(data)
```

---

## 21. Mock Overuse & Test False Positives

**Why it matters:** Tests pass but production fails — mocks accept wrong signatures.

### Checklist

- [ ] **Missing `autospec=True`** — Mocks accept any signature
- [ ] **Mocking internal logic** — Should mock external dependencies only
- [ ] **Tests verify mock called, not behavior**
- [ ] **Mocked return values don't match real API**
- [ ] **Global module patches** — `@patch('requests.post')` too broad

### Detection Pattern

```bash
# Check for mock without autospec
grep -rn "@patch\|@mock" tests/ | grep -v "autospec"

# Check mock density (too many = weak tests)
grep -rn "Mock()\|MagicMock" tests/ | wc -l
```

### Correct Pattern

```python
# BAD: Mock accepts wrong signature
@patch('module.api_call')
def test_function(mock_call):
    mock_call.return_value = {"data": []}
    result = func("arg1", "EXTRA_ARG")  # No error!

# GOOD: autospec enforces real signature
@patch('module.api_call', autospec=True)
def test_function(mock_call):
    mock_call.return_value = {"data": []}
    result = func("arg1", "EXTRA_ARG")  # TypeError!
```

**Sources:**
- [Pytest Common Mocking Problems](https://pytest-with-eric.com/mocking/pytest-common-mocking-problems/)

---

## 22. ML Reproducibility Bugs

**Why it matters:** Random seed choice causes 44-45% accuracy variation.

### Checklist

- [ ] **Random seed not set** — Results vary between runs
- [ ] **Multiple RNG sources not seeded** — Python, NumPy, PyTorch, CUDA
- [ ] **GPU non-determinism** — cuDNN benchmarking
- [ ] **Parallel execution variance** — Threading introduces randomness
- [ ] **Library versions not pinned**

### Correct Pattern

```python
import random
import numpy as np

def set_seed(seed: int) -> None:
    """Set all random seeds for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    # If using PyTorch:
    # torch.manual_seed(seed)
    # torch.cuda.manual_seed_all(seed)
    # torch.backends.cudnn.deterministic = True
```

---

## 23. Data Leakage & Train-Test Contamination

**Why it matters:** 648 papers affected by data leakage (Princeton research).

### Checklist

- [ ] **Preprocessing before split** — Scaling fit on full dataset
- [ ] **Feature engineering uses test data** — Statistics across all data
- [ ] **Time series future leakage** — Using future to predict past
- [ ] **Duplicate samples across splits**
- [ ] **Target leakage** — Features that encode target

### Correct Pattern

```python
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# BAD: Preprocessing before split
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)  # Uses ALL data!
X_train, X_test = train_test_split(X_scaled)

# GOOD: Split first, fit only on train
X_train, X_test = train_test_split(X)
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)  # Fit on train only
X_test = scaler.transform(X_test)  # Transform test
```

**Sources:**
- [Princeton Reproducibility Study](https://reproducible.cs.princeton.edu/)

---

## 24. Jupyter Notebook Anti-Patterns

**Why it matters:** 73% of published notebooks are non-reproducible. Hidden state, out-of-order execution, and memory leaks are endemic.

### Checklist

**Hidden State & Out-of-Order Execution:**
- [ ] **Cells executed out of order** — Results don't match code visible in cells
- [ ] **Deleted cells leave orphaned state** — Variables from deleted cells still exist in kernel
- [ ] **Re-running cells multiple times** — Accumulating side effects (appends, counter increments)
- [ ] **No "Restart & Run All" verification** — Notebook works interactively but fails fresh

**Global Variable Pollution & Memory Leaks:**
- [ ] **Large intermediate variables not deleted** — All cell variables are global scope
- [ ] **Printing large arrays repeatedly** — Each print leaks memory (7GB per 10 runs in one study)
- [ ] **Exception in cell leaks locals** — PyTorch tensors can exhaust GPU memory
- [ ] **Repeated cell execution memory growth** — Memory never released without kernel restart

**Module Reload Issues:**
- [ ] **Changed module code not reflected** — Need `%autoreload 2` or `importlib.reload()`
- [ ] **Class imports don't autoreload** — Must import module, not `from module import Class`
- [ ] **Enum identity breaks after reload** — `MyEnum.VALUE is MyEnum.VALUE` returns False
- [ ] **C extensions can't autoreload** — NumPy/Pandas changes require kernel restart

**Reproducibility Problems:**
- [ ] **Ambiguous execution order** — Cell [5] depends on [7] which runs first
- [ ] **Random seeds not set at start** — Non-deterministic results across runs
- [ ] **Hardcoded absolute paths** — `/Users/alice/data/...` won't work for others
- [ ] **Missing dependency versions** — `pip freeze > requirements.txt` not included
- [ ] **Data files not version controlled** — Notebook references unavailable data

**Production Anti-Patterns:**
- [ ] **Logic in notebooks, not modules** — Can't unit test notebook cells
- [ ] **No error handling for %run chains** — Master notebook ignores sub-notebook failures
- [ ] **Hardcoded credentials** — API keys in cells visible to anyone with notebook access
- [ ] **Outputs committed to git** — Bloats repo, may contain sensitive data

### Detection Commands

```bash
# Find notebooks with hardcoded paths (Unix absolute paths)
grep -rn "/Users/\|/home/" notebooks/ --include="*.ipynb"

# Find notebooks with potential credentials
grep -rn "api_key\|password\|secret\|token" notebooks/ --include="*.ipynb"

# Strip outputs before commit (install nbstripout)
nbstripout --install  # Sets up git filter

# Check if notebooks run clean
jupyter nbconvert --execute --to notebook notebook.ipynb
```

### Correct Pattern

```python
# BAD: Global scope pollution
df = pd.read_csv("data.csv")  # Lives forever
processed = df[df['col'] > 0]  # Lives forever
result = processed.groupby('x').mean()  # Lives forever

# GOOD: Use functions to scope variables
def process_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    processed = df[df['col'] > 0]
    return processed.groupby('x').mean()

result = process_data("data.csv")  # Only result lives in global

# BAD: Hardcoded path
data = pd.read_csv("/Users/ray/project/data/train.csv")

# GOOD: Relative or configurable path
from pathlib import Path
DATA_DIR = Path(__file__).parent.parent / "data"
data = pd.read_csv(DATA_DIR / "train.csv")

# GOOD: First cell of every notebook
%load_ext autoreload
%autoreload 2

import numpy as np
import random
import torch

# Set seeds for reproducibility
SEED = 42
np.random.seed(SEED)
random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)
```

### Sources

- [Bug Analysis in Jupyter Notebook Projects (ICSE 2025)](https://conf.researchr.org/details/icse-2025/icse-2025-journal-first-papers/25/Bug-Analysis-in-Jupyter-Notebook-Projects-An-Empirical-Study)
- [Understanding and Improving Quality of Jupyter Notebooks (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8106381/)
- [Why Do ML Notebooks Crash? (arXiv 2024)](https://arxiv.org/html/2411.16795v2)
- [Python Memory Management in Jupyter (Mikulski)](https://mikulskibartosz.name/python-memory-management-in-jupyter-notebook)
- [Jupyter Leaks Local Variables (GitHub Issue)](https://github.com/jupyter/notebook/issues/6147)
- [IPython Autoreload Documentation](https://ipython.readthedocs.io/en/9.0.2/config/extensions/autoreload.html)

---

## Audit Statistics (2025-2026 Research)

| Metric | Value | Source |
|--------|-------|--------|
| AI code logic errors vs human | 1.75x more | CodeRabbit 2025 |
| AI code security issues vs human | 1.57x more | CodeRabbit 2025 |
| AI code XSS vulnerabilities | 2.74x more | CodeRabbit 2025 |
| Silent failures causing bugs | 40% of investigations | PSF Survey 2025 |
| Data engineers fixing pipelines | 44% of time | Gartner 2025 |
| AI-generated code with vulns | 30-50% | IEEE/Academic 2025 |
| Papers with data leakage | 648 across 30 fields | Princeton 2025 |
| Notebooks non-reproducible | 73% | ICSE 2025 |
| ML notebook crashes from out-of-order | 19.4% | arXiv 2024 |

---

## Weekly Quick Audit (15 min)

1. `grep -r "except:" src/` — Bare excepts
2. `grep -r "except Exception:" src/` — Check for `pass` after
3. `grep -r "api_key\|secret\|password" src/` — Hardcoded secrets
4. `grep -r "if limit:" src/` — Truthiness traps
5. Review recent PRs for silent fallbacks
6. `jupyter nbconvert --execute notebooks/*.ipynb` — Notebooks run clean

## Monthly Deep Audit (2 hours)

1. Run through full checklist
2. Check test coverage for edge cases
3. Audit Pydantic models for Strict types
4. Review async code for race conditions
5. Verify random seeds are set for ML code
6. Verify all notebooks have "Restart & Run All" tested
7. Document findings in `docs/_bugs/`

---

## Changelog

| Date       | Change                                           |
|------------|--------------------------------------------------|
| 2026-01-07 | **CRITICAL: Added Mock Data in Production anti-pattern at TOP** |
| 2026-01-07 | Added Jupyter notebook anti-patterns (24)        |
| 2026-01-07 | Added ML/research categories (14-23)             |
| 2026-01-07 | Initial creation from web research               |
