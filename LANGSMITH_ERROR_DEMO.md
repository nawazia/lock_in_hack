# LangSmith Error Demo Guide

## Overview

This guide shows how to run the travel planning system with **intentional error injection** that appears in LangSmith traces, allowing you to see the audit and feedback loop system in action.

## Quick Start

### Option 1: Using the Shell Script

```bash
./run_demo_with_errors.sh
```

### Option 2: Using Environment Variable

```bash
DEMO_ERRORS=true python travel_example.py
```

### Option 3: Permanent Demo Mode

Add to your `.env` file:
```bash
DEMO_ERRORS=true
```

Then run normally:
```bash
python travel_example.py
```

## What Happens

### 1. Error Injection Node (NEW!)

A dedicated `error_injection_node` runs **WITHIN** the LangGraph workflow, between the `itinerary` and `audit` nodes:

```
Interface → Flights → Hotels → Budget → Activities → Ranking → Itinerary
                                                                    ↓
                                                            Error Injection ← (DEMO MODE)
                                                                    ↓
                                                                  Audit
```

### 2. Errors Injected

When `DEMO_ERRORS=true`, the system injects 5 intentional errors:

| # | Error Type | Example | Severity |
|---|------------|---------|----------|
| 1 | Date inconsistency | Flight arrives 2025-12-20 but itinerary starts 2025-12-10 (10 days off) | Auto-fixable |
| 2 | Invalid rating | Hotel rating 12.5/5 (should be max 5.0) | Auto-fixable |
| 3 | Location mismatch | Hotel in Singapore but user requested Hong Kong | Critical → Feedback loop |
| 4 | Negative price | Activity price -$50.00 | Auto-fixable |
| 5 | Invalid URL | Blog URL instead of booking site | Auto-fixable |

### 3. Audit Detection

The audit agent runs and:
- ✓ Detects all 5 errors
- ✓ Auto-fixes 4 errors (dates, ratings, prices, URLs)
- ⚠️ Flags 1 critical error (location mismatch)

### 4. Feedback Loop Triggered

```
Audit detects critical issue (location mismatch)
  ↓
Routing: "Starting iteration 1/3"
  ↓
Route back to: Flight Agent
  ↓
Re-search flights and hotels for correct location
  ↓
Create new itinerary
  ↓
(Error injection SKIPPED on iteration 1+)
  ↓
Audit runs again
  ↓
No critical issues → Pipeline complete
```

## LangSmith Trace Structure

When viewing the trace in LangSmith, you'll see:

### First Iteration

```
travel_orchestrator_process/
├── interface_node ✓
├── flight_node ✓
├── hotel_node ✓
├── budget_node ✓
├── activities_node ✓
├── ranking_node ✓
├── itinerary_node ✓
├── error_injection_node ⚠️  ← ERRORS INJECTED HERE
│   ├── Log: "🔧 DEMO MODE: Injecting intentional errors..."
│   ├── Log: "❌ Injected: Date inconsistency..."
│   ├── Log: "❌ Injected: Invalid rating..."
│   ├── Log: "❌ Injected: Location mismatch..."
│   ├── Log: "❌ Injected: Invalid price..."
│   └── Log: "❌ Injected: Invalid URL..."
└── audit_node ⚠️  ← ERRORS DETECTED HERE
    ├── Log: "Audit found 4 issues"
    ├── Log: "✓ Auto-fixed date consistency"
    ├── Log: "✓ Capped rating from 12.5 to 5.0"
    ├── Log: "✓ Set price to $0.00"
    ├── Log: "✓ Removed invalid URL"
    └── Log: "Critical issues remaining: 1, Types: location_mismatch"
```

### Second Iteration (Feedback Loop)

```
travel_orchestrator_process/ (continued)
├── flight_node ↻ ← RE-RUN
├── hotel_node ↻ ← RE-RUN
├── budget_node ↻
├── activities_node ↻
├── ranking_node ↻
├── itinerary_node ↻
├── error_injection_node ✓  ← SKIPPED (iteration > 0)
│   └── Log: "Error injection skipped (iteration 1)"
└── audit_node ✓  ← NO CRITICAL ISSUES
    └── Log: "No critical issues found, pipeline complete"
```

## Key Logs to Look For in LangSmith

### Error Injection Logs (iteration 0)
```
🔧 DEMO MODE: Injecting intentional errors for testing...
❌ Injected: Date inconsistency: Flight arrives 2025-12-20 but itinerary starts 2025-12-10
❌ Injected: Invalid rating: Hotel rating is 12.5/5 (should be max 5.0)
❌ Injected: Location mismatch: Hotel is in Singapore but user requested Hong Kong
❌ Injected: Invalid price: Activity has negative price: $-50.00
❌ Injected: Invalid URL: Hotel booking URL is a blog/guide
```

### Audit Detection Logs
```
Audit found 4 issues:
  - Location mismatch: Found 'Singapore' but expected 'Hong Kong'
  - Hotel rating has invalid rating 12.5/5 (max is 5.0)
  - Hotel has blog/article URL instead of booking site
  - Activity has negative price: $-50.0
```

### Auto-Fix Logs
```
✓ Capped Hotel rating from 12.5 to 5.0
✓ Removed invalid booking URL for hotel
✓ Set Activity price to $0.00 (was $-50.0)
✓ Adjusted itinerary dates to match flight arrival
```

### Feedback Loop Logs
```
Routing: Critical issues found, starting iteration 1/3
Routing: Location mismatch found, re-running from flight search
```

### Iteration Skip Logs
```
Error injection skipped (iteration 1 - errors only injected on first pass)
```

## Comparing Normal vs Error Demo

| Aspect | Normal Mode | Error Demo Mode |
|--------|-------------|-----------------|
| Environment | `DEMO_ERRORS` not set | `DEMO_ERRORS=true` |
| Error injection node | Skips silently | Injects 5 errors |
| Audit results | Usually 0-1 minor issues | 5 issues injected |
| Feedback loops | Rare (only on real errors) | Likely (location mismatch) |
| LangSmith trace | Linear path | Shows iteration loops |
| Total nodes | ~8 nodes | ~16+ nodes (with iterations) |

## Troubleshooting

### Issue: Errors don't show in LangSmith

**Solution**: Make sure you're using the environment variable method:
```bash
DEMO_ERRORS=true python travel_example.py
```

NOT the old script:
```bash
python travel_example_demo_errors.py  # ❌ Errors injected OUTSIDE workflow
```

### Issue: Infinite loop / recursion error

**Cause**: Errors are being injected on every iteration

**Solution**: Already fixed! The error injection node now checks `iteration_count` and only injects on the first pass.

### Issue: No feedback loop triggered

**Cause**: All errors were auto-fixed

**Solution**: This is expected behavior! The system auto-fixes what it can. To force a feedback loop, you can:
- Disable auto-fix for location mismatches in `audit_agent.py`
- Or inject more severe errors that can't be auto-fixed

## Production Usage

⚠️ **IMPORTANT**: The error injection node is **ONLY for demo/testing**

In production:
1. DO NOT set `DEMO_ERRORS=true`
2. The error injection node will skip automatically
3. Only real errors will trigger the audit system

## Benefits of This Approach

✅ **Traceability**: All error injection happens in LangSmith trace
✅ **Reproducibility**: Same errors injected every time
✅ **Educational**: Clear demonstration of audit + feedback loop
✅ **Safe**: Only activates with explicit environment variable
✅ **No Infinite Loops**: Errors only injected once

## Example LangSmith Output

When you open your LangSmith trace, you should see something like:

```
Run: travel_orchestrator_process (58.2s)
├─ Input: user_query="I want to go to Hong Kong! My budget is..."
├─ Nodes Executed: 16
├─ Iterations: 2
├─ Status: ✓ Completed
└─ Metadata:
   ├─ errors_injected: 5
   ├─ audit_issues_found: 4
   ├─ audit_fixes_applied: 5
   ├─ critical_issues: 0 (after feedback loop)
   └─ iteration_count: 1
```

Navigate to the `error_injection_node` to see detailed logs of what errors were injected!
