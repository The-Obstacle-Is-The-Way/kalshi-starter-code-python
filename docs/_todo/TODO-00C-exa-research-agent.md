# TODO-00C: Exa Research Agent (FUTURE)

**Priority**: P2 (Advanced feature)
**Status**: DEFERRED
**Created**: 2026-01-09
**Spec**: [SPEC-024: Exa Research Agent](../_specs/SPEC-024-exa-research-agent.md)
**Complexity**: HIGH (~1200 lines of spec code)

---

## Overview

Implement an autonomous research agent that orchestrates multiple Exa operations for deep market research. This is a **major feature** that builds on the existing Exa integration.

## Why Deferred?

1. **High complexity**: Full agent implementation with planning, execution, synthesis
2. **MCP alternative exists**: Users can use Exa MCP server for interactive research
3. **Current workflow works**: Manual Exa commands + thesis tracking suffice for now
4. **Testing burden**: Agent behavior is hard to test reliably

## What SPEC-024 Would Provide

- Autonomous multi-step research workflows
- `kalshi agent research TICKER --depth deep --budget 0.50`
- Structured research reports with bull/bear cases
- Probability estimation from research
- Cost tracking and budget limits

## Prerequisites Before Implementation

Before tackling this:
- [ ] TODO-010 (Liquidity Analysis) complete - research needs liquidity context
- [ ] Real-world validation of Exa usage patterns
- [ ] Clear use case requiring automation vs interactive research
- [ ] Budget for Exa API costs during development/testing

## Estimated Effort

- Phase 1 (Core Agent): 8-12 hours
- Phase 2 (Synthesis): 4-6 hours
- Phase 3 (Reporting): 2-4 hours
- Phase 4 (CLI): 2-4 hours
- **Total**: 16-26 hours

## Alternative: MCP-Based Research

For now, users can:
1. Use [Exa MCP Server](https://github.com/exa-labs/exa-mcp-server) in Claude Desktop/Code
2. Run interactive research sessions
3. Formalize findings using existing CLI commands

## Related

- [SPEC-024](../_specs/SPEC-024-exa-research-agent.md) - Full specification
- SPEC-020 through SPEC-023 (Archived) - Exa foundation (implemented)
- [TODO-005 (Archived)](../_archive/todo/TODO-005-market-open-date-validation.md) - TemporalValidator for research

---

**Note**: This is a placeholder TODO (00C series) for complex future work. When you decide to implement, break it into smaller TODOs (TODO-XXX series) with clear acceptance criteria.
