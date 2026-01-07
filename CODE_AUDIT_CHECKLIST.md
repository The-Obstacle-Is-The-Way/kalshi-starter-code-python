# Code Audit Checklist - AI & Human-Generated Code

**Purpose:** Systematic checklist for detecting bugs, anti-patterns, and security vulnerabilities in codebases—especially those containing AI-generated code.

**Last Updated:** 2026-01-07
**Sources:** Web research from 2025-2026 industry reports, OWASP, security researchers, and engineering blogs.

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

## Changelog

| Date | Change |
|------|--------|
| 2026-01-07 | Initial creation from web research |
