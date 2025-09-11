# Coverage Analysis in wx_logs

This document explains how temporal coverage analysis works in the wx_logs package, particularly for Time of Wetness (TOW) calculations and enhanced quality assurance.

## Overview

The coverage analysis system evaluates how well weather data is distributed throughout a year, focusing on temporal adequacy rather than raw data density. This is crucial for TOW calculations where consistent year-round coverage is more important than having many data points clustered in specific periods.

## Key Concepts

### Traditional QA vs Coverage-Only QA

- **Traditional QA**: Simple density check - requires ≥75% of possible hourly readings
- **Coverage-Only Enhanced QA**: Evaluates temporal distribution patterns, ignoring density

### Coverage vs Density

- **Density**: Total percentage of possible time slots filled (e.g., 2000/8760 hours = 23%)
- **Coverage**: How well data spans across different temporal periods (seasons, months, days)

A dataset can have low density but excellent coverage (e.g., daily readings = 4% density, 100% temporal coverage).

## Coverage Analysis Components

### 1. Seasonal Coverage

Evaluates data distribution across the four meteorological seasons:
- **Spring**: March, April, May
- **Summer**: June, July, August  
- **Fall**: September, October, November
- **Winter**: December, January, February

**Calculation**:
```python
seasons_with_data = count_seasons_with_adequate_data()
seasonal_coverage = (seasons_with_data / 4.0) * 100
```

**Adequacy Threshold**: A season is considered "adequate" if it has data for ≥50% of its days.

### 2. Monthly Coverage

Evaluates data presence across all 12 months of the year.

**Calculation**:
```python
months_with_data = count_months_with_any_data()
monthly_coverage = (months_with_data / 12.0) * 100
```

### 3. Days with Data

Counts the total number of unique days that have at least one measurement.

**Calculation**:
```python
days_with_data = len(set(date.date() for date in measurement_timestamps))
```

### 4. Largest Gap Analysis

Identifies the longest consecutive period without any measurements.

**Calculation**:
```python
gaps = []
sorted_dates = sorted(unique_measurement_dates)
for i in range(1, len(sorted_dates)):
    gap_days = (sorted_dates[i] - sorted_dates[i-1]).days - 1
    if gap_days > 0:
        gaps.append(gap_days)
largest_gap_days = max(gaps) if gaps else 0
```

### 5. Overall Coverage Score

A composite score combining multiple coverage metrics:

**Calculation**:
```python
# Weights for different components
seasonal_weight = 0.4    # 40% - most important for TOW
monthly_weight = 0.3     # 30% - good granularity
gap_penalty_weight = 0.2 # 20% - penalize large gaps
days_weight = 0.1        # 10% - basic coverage

# Calculate components
seasonal_score = seasonal_coverage  # 0-100
monthly_score = monthly_coverage    # 0-100
gap_penalty = min(100, largest_gap_days * 2)  # Penalty for gaps
days_score = min(100, (days_with_data / 300) * 100)  # ~300 days ideal

# Composite score
overall_score = (
    seasonal_score * seasonal_weight +
    monthly_score * monthly_weight + 
    (100 - gap_penalty) * gap_penalty_weight +
    days_score * days_weight
)
```

## Coverage Adequacy Determination

### Temperature and Humidity Coverage

Each measurement type (temperature, humidity) is evaluated independently:

**Adequacy Criteria**:
```python
def is_coverage_adequate(coverage_metrics):
    # Must have data in at least 3 of 4 seasons (75%)
    seasonal_adequate = coverage_metrics['seasonal_coverage'] >= 75
    
    # Must have data in at least 9 of 12 months (75%)
    monthly_adequate = coverage_metrics['monthly_coverage'] >= 75
    
    # Must not have gaps longer than 60 days
    gap_adequate = coverage_metrics['largest_gap_days'] <= 60
    
    # Overall score must be reasonable
    score_adequate = coverage_metrics['overall_score'] >= 70
    
    return seasonal_adequate and monthly_adequate and gap_adequate and score_adequate
```

## Enhanced QA State Logic

The enhanced QA system now uses **coverage-only** evaluation:

```python
def calculate_enhanced_qa_state(temp_adequate, humidity_adequate):
    """
    Coverage-only QA: Evaluate based on temporal adequacy only.
    Traditional density checks are ignored.
    """
    if temp_adequate and humidity_adequate:
        return 'PASS'
    else:
        return 'FAIL_COVERAGE'
```

### QA States Explained

- **`PASS`**: Both temperature and humidity have adequate temporal coverage
- **`FAIL_COVERAGE`**: One or both variables have inadequate temporal distribution
- **`FAIL_DENSITY`**: *(Deprecated)* Previously used for insufficient data density

## Practical Examples

### Example 1: Daily Research Station Data

**Scenario**: Weather station with one measurement per day for a full year
- **Density**: 365/8760 = 4.2%
- **Days with data**: 365
- **Seasonal coverage**: 100% (all seasons covered)
- **Monthly coverage**: 100% (all months covered)  
- **Largest gap**: 1 day
- **Overall score**: ~95%

**Result**: `PASS` - Excellent temporal coverage despite low density

### Example 2: Airport Station (3 months)

**Scenario**: Hourly data for January, April, July only
- **Density**: ~2200/8760 = 25%
- **Days with data**: ~93
- **Seasonal coverage**: 75% (3 of 4 seasons)
- **Monthly coverage**: 25% (3 of 12 months)
- **Largest gap**: ~90 days
- **Overall score**: ~45%

**Result**: `FAIL_COVERAGE` - Poor temporal distribution

### Example 3: Clustered High-Density Data

**Scenario**: Dense hourly data for first 6 months, sparse for last 6 months
- **Density**: 80%
- **Days with data**: 300
- **Seasonal coverage**: 100%
- **Monthly coverage**: 100%
- **Largest gap**: ~2 days
- **Overall score**: ~85%

**Result**: Likely `PASS` - Good overall distribution despite uneven density

## Configuration and Thresholds

### Adjustable Parameters

```python
# Coverage adequacy thresholds (in wx_logs/tow_calculator.py)
SEASONAL_COVERAGE_THRESHOLD = 75    # Minimum % seasons needed
MONTHLY_COVERAGE_THRESHOLD = 75     # Minimum % months needed  
MAX_ACCEPTABLE_GAP_DAYS = 60        # Maximum gap in days
MIN_OVERALL_SCORE = 70              # Minimum composite score

# Season adequacy threshold
SEASON_ADEQUACY_THRESHOLD = 0.5     # 50% of days in season
```

### Customization

These thresholds can be modified in the `TOWCalculator` class to adjust sensitivity:

```python
# More lenient coverage requirements
calculator.seasonal_threshold = 50  # Accept 2 of 4 seasons
calculator.gap_threshold = 90       # Allow 90-day gaps

# Stricter coverage requirements  
calculator.seasonal_threshold = 90  # Require nearly all seasons
calculator.gap_threshold = 30       # No gaps over 30 days
```

## Output Format

The coverage analysis is included in JSON output when enhanced QA is enabled:

```json
{
  "coverage_analysis": {
    "enhanced_qa_state": "PASS",
    "temperature": {
      "adequate_coverage": true,
      "seasonal_coverage": 100.0,
      "monthly_coverage": 100.0,
      "days_with_data": 365,
      "largest_gap_days": 1,
      "overall_score": 94.8
    },
    "humidity": {
      "adequate_coverage": true,
      "seasonal_coverage": 100.0,
      "monthly_coverage": 100.0, 
      "days_with_data": 365,
      "largest_gap_days": 1,
      "overall_score": 94.8
    }
  }
}
```

## Scientific Rationale

### Why Coverage Over Density?

For Time of Wetness calculations, **temporal representativeness** is more important than **data quantity**:

1. **Seasonal Patterns**: TOW varies significantly between seasons due to temperature and humidity cycles
2. **Biological Relevance**: Plant diseases and corrosion processes depend on consistent environmental exposure patterns
3. **Statistical Validity**: A few well-distributed measurements provide better annual estimates than many clustered measurements

### Real-World Applications

- **Agricultural Research**: Daily readings from research stations provide excellent TOW estimates
- **Corrosion Studies**: Consistent monitoring is more valuable than intensive short-term sampling  
- **Climate Analysis**: Long-term trends require temporal consistency over high-frequency sampling

## Migration from Legacy QA

### Behavioral Changes

**Before (Hybrid QA)**:
- Daily data → `FAIL_DENSITY` (4% density too low)
- Result: Many scientifically valid datasets rejected

**After (Coverage-Only QA)**:
- Daily data → `PASS` (excellent temporal coverage)
- Result: More years available for analysis while maintaining quality

### Backward Compatibility

- **API**: No breaking changes to method signatures
- **Traditional QA**: Still available and unchanged
- **Default Behavior**: Enhanced QA remains the default
- **Legacy Support**: Old `FAIL_DENSITY` logic documented but deprecated

## Testing and Validation

The coverage analysis system includes comprehensive tests covering:

- Daily, weekly, and hourly data patterns
- Seasonal and clustered data distributions  
- Edge cases (minimal data, single measurements)
- Boundary conditions for all thresholds
- Comparison between traditional and enhanced QA

See `tests/weather_station_enhanced_qa_test_case.py` for detailed test scenarios.
