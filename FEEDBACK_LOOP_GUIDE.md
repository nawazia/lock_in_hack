# Feedback Loop & Audit System Guide

## Overview

The travel planning system now includes an intelligent **feedback loop** that automatically detects and fixes errors in the itinerary. When critical issues are found, the system routes back to the appropriate agent for re-processing.

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│  Pipeline Flow with Feedback Loops                              │
└─────────────────────────────────────────────────────────────────┘

Interface → Flights → Hotels → Budget → Activities → Ranking → Itinerary → Audit
     ↑         ↑                ↑                                ↑           │
     │         │                │                                │           │
     └─────────┴────────────────┴────────────────────────────────┴───────────┘
                    Feedback loop if critical issues found
```

### 3-Tier Error Handling

#### 1. **Auto-Fix (Immediate)**
Non-critical issues that can be automatically corrected:
- ✓ Date inconsistencies → Adjust itinerary dates to match flight times
- ✓ Invalid ratings → Cap or scale ratings to 0-5 range
- ✓ Negative prices → Set to $0.00
- ✓ Blog URLs → Remove invalid booking URLs

#### 2. **Feedback Loop (Iterative)**
Critical issues that require re-running agents:
- ⚠️ Location mismatches → Route back to **Flight Agent**
- ⚠️ Major price validation errors → Route back to **Budget Agent**
- ⚠️ Unresolvable date issues → Route back to **Itinerary Agent**

#### 3. **Max Iterations (Safety)**
- System will attempt up to **3 iterations** by default
- Prevents infinite loops
- Configurable via `max_iterations` parameter

## Error Categories

### Auto-Fixable Errors

| Error Type | Detection | Auto-Fix |
|------------|-----------|----------|
| Date inconsistency | Flight arrival ≠ itinerary start | Adjust dates to match flight |
| Invalid rating | Rating > 5.0 or < 0 | Cap to 5.0 or scale from /10 |
| Negative price | Price < 0 | Set to $0.00 |
| Blog/guide URLs | URL contains "blog", "guide", "article" | Remove URL |

### Critical Errors (Trigger Feedback Loop)

| Error Type | Severity | Routing Target |
|------------|----------|----------------|
| Location mismatch | Critical | → Flight Agent |
| Wrong destination | Critical | → Flight Agent |
| Major price issues | High | → Budget Agent |
| Unresolvable dates | High | → Itinerary Agent |

## Running the Demo

### Normal Mode
```bash
python travel_example.py
```

### Error Demo Mode
```bash
python travel_example_demo_errors.py
```

The demo mode will:
1. Create a normal itinerary
2. Inject 5 intentional errors:
   - Date inconsistency (10 days off)
   - Invalid rating (12.5/5)
   - Location mismatch (Singapore vs Hong Kong)
   - Negative price (-$50)
   - Blog URL instead of booking site
3. Show how the audit agent:
   - Detects all issues
   - Auto-fixes 4 issues
   - Flags 1 critical issue for feedback loop
   - Categorizes issues by type

## Example Output

```
AUDIT RESULTS
Issues Found: 4
Fixes Applied: 4
Critical Issues Remaining: 1

Issues Detected:
  ⚠ Location mismatch: Found 'Singapore' but expected 'Hong Kong'
  ⚠ Hotel rating has invalid rating 12.5/5 (max is 5.0)
  ⚠ Hotel has blog/article URL instead of booking site
  ⚠ Activity has negative price: $-50.0

Fixes Applied:
  ✓ Capped Hotel rating from 12.5 to 5.0
  ✓ Removed invalid booking URL for hotel
  ✓ Set Activity price to $0.00 (was $-50.0)
  ✓ Adjusted itinerary dates to match flight arrival

⚠️  CRITICAL ISSUES REMAINING:
  ❌ Location mismatch: Found 'Singapore' but expected 'Hong Kong'

→ Would route back to: Flight Agent (to search for correct location)
```

## Configuration

### In Code
```python
from agents.travel_orchestrator import TravelOrchestrator

# Default: 3 max iterations
orchestrator = TravelOrchestrator()

# Custom max iterations
# (Set higher if expecting complex issues)
```

### In State Schema
```python
# models/travel_schemas.py
iteration_count: int = Field(0, description="Current iteration")
max_iterations: int = Field(3, description="Max iterations before stopping")
```

## Key Files

| File | Purpose |
|------|---------|
| `agents/audit_agent.py` | Core error detection & auto-fix logic |
| `agents/travel_orchestrator.py` | Routing logic & feedback loop control |
| `models/travel_schemas.py` | State schema with iteration tracking |
| `travel_example_demo_errors.py` | Demo script showing error handling |

## Benefits

### 1. **Robustness**
- Automatically handles data quality issues
- Prevents invalid itineraries from reaching users
- Self-correcting system

### 2. **Transparency**
- All fixes are logged and shown to users
- Clear indication when feedback loops occur
- Detailed audit trail

### 3. **Efficiency**
- Auto-fixes simple issues immediately
- Only triggers expensive re-runs for critical issues
- Bounded by max iterations

## Extending the System

### Adding New Error Types

1. **Add detection logic** in `audit_agent.py`:
```python
def validate_new_field(self, field_value):
    if invalid_condition:
        issue = "Description of issue"
        self.issues_found.append(issue)
        self.critical_issues.append(issue)  # If critical
        self.issue_types.append("new_error_type")
```

2. **Add routing rule** in `travel_orchestrator.py`:
```python
def _route_after_audit(self, state):
    if "new_error_type" in issue_types:
        return "appropriate_agent"
```

### Adding Auto-Fix Rules

```python
def validate_new_field(self, field_value, auto_fix=True):
    if invalid_condition:
        issue = "Issue description"
        self.issues_found.append(issue)

        if auto_fix:
            # Attempt to fix
            fixed_value = fix_logic(field_value)
            fix_msg = f"Fixed: {field_value} → {fixed_value}"
            self.fixes_applied.append(fix_msg)
            return fixed_value
```

## Troubleshooting

### Issue: Infinite loops
**Solution**: Reduce `max_iterations` or improve auto-fix logic

### Issue: Too many false positives
**Solution**: Adjust validation thresholds in `audit_agent.py`

### Issue: Not detecting errors
**Solution**: Add logging in validation methods to debug

## Future Enhancements

- [ ] Machine learning-based error prediction
- [ ] User preferences for auto-fix aggressiveness
- [ ] A/B testing different routing strategies
- [ ] Detailed metrics dashboard for audit performance
- [ ] Configurable validation rules via config file
