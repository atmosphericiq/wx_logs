# data_coverage.py
# A module for analyzing temporal coverage of weather data
# to determine if we have approximately a year's worth of data
# Author: Tom Hayden

import datetime
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

class YearCoverageAnalyzer:
  """
  Analyzes temporal coverage of weather data to determine if we have
  approximately a year's worth of data distributed across time periods.
  """
  
  def __init__(self, adequate_threshold=75.0):
    """
    Initialize the analyzer with configurable thresholds.
    
    Args:
      adequate_threshold: Minimum percentage for "adequate" coverage (default 75%)
    """
    self.adequate_threshold = adequate_threshold
  
  def analyze_coverage(self, datetime_list, year=None):
    """
    Analyze temporal coverage for a list of datetime objects.
    
    Args:
      datetime_list: List of datetime objects representing measurements
      year: Specific year to analyze (if None, uses the most common year)
    
    Returns:
      Dict with coverage analysis results
    """
    if not datetime_list:
      return {
        'overall_score': 0.0,
        'seasonal_coverage': 0.0,
        'monthly_coverage': 0.0,
        'total_measurements': 0,
        'year_analyzed': year,
        'adequate_coverage': False,
        'days_with_data': 0,
        'seasonal_breakdown': {'spring': 0, 'summer': 0, 'fall': 0, 'winter': 0},
        'monthly_breakdown': {i: 0 for i in range(1, 13)},
        'largest_gap_days': 0
      }
    
    # Determine which year to analyze
    if year is None:
      year_counts = defaultdict(int)
      for dt in datetime_list:
        year_counts[dt.year] += 1
      year = max(year_counts.keys(), key=lambda k: year_counts[k])
    
    # Filter to specific year
    year_data = [dt for dt in datetime_list if dt.year == year]
    
    if not year_data:
      return self._empty_result(year)
    
    # Sort data by date
    year_data.sort()
    
    # Calculate basic metrics
    total_measurements = len(year_data)
    days_with_data = len(set(dt.date() for dt in year_data))
    
    # Calculate seasonal and monthly coverage
    seasonal_breakdown = self._calculate_seasonal_coverage(year_data)
    monthly_breakdown = self._calculate_monthly_coverage(year_data)
    
    # Calculate largest gap
    largest_gap_days = self._calculate_largest_gap(year_data, year)
    
    # Calculate coverage scores
    seasonal_coverage = self._score_seasonal_coverage(seasonal_breakdown)
    monthly_coverage = self._score_monthly_coverage(monthly_breakdown)
    
    # Overall score considers multiple factors
    overall_score = self._calculate_overall_score(
      days_with_data, seasonal_coverage, monthly_coverage, largest_gap_days, year
    )
    
    return {
      'overall_score': round(overall_score, 2),
      'seasonal_coverage': round(seasonal_coverage, 2),
      'monthly_coverage': round(monthly_coverage, 2),
      'total_measurements': total_measurements,
      'year_analyzed': year,
      'adequate_coverage': overall_score >= self.adequate_threshold,
      'days_with_data': days_with_data,
      'seasonal_breakdown': seasonal_breakdown,
      'monthly_breakdown': monthly_breakdown,
      'largest_gap_days': largest_gap_days
    }
  
  def _empty_result(self, year):
    """Return empty result structure"""
    return {
      'overall_score': 0.0,
      'seasonal_coverage': 0.0,
      'monthly_coverage': 0.0,
      'total_measurements': 0,
      'year_analyzed': year,
      'adequate_coverage': False,
      'days_with_data': 0,
      'seasonal_breakdown': {'spring': 0, 'summer': 0, 'fall': 0, 'winter': 0},
      'monthly_breakdown': {i: 0 for i in range(1, 13)},
      'largest_gap_days': 0
    }
  
  def _calculate_seasonal_coverage(self, year_data):
    """Calculate number of days with data in each season"""
    seasonal_days = {'spring': set(), 'summer': set(), 'fall': set(), 'winter': set()}
    
    for dt in year_data:
      season = self._get_season(dt.month)
      seasonal_days[season].add(dt.date())
    
    return {season: len(days) for season, days in seasonal_days.items()}
  
  def _calculate_monthly_coverage(self, year_data):
    """Calculate number of days with data in each month"""
    monthly_days = defaultdict(set)
    
    for dt in year_data:
      monthly_days[dt.month].add(dt.date())
    
    return {month: len(days) for month, days in monthly_days.items()}
  
  def _get_season(self, month):
    """Map month number to season"""
    if month in [3, 4, 5]:
      return 'spring'
    elif month in [6, 7, 8]:
      return 'summer'
    elif month in [9, 10, 11]:
      return 'fall'
    else:  # 12, 1, 2
      return 'winter'
  
  def _calculate_largest_gap(self, year_data, year):
    """Calculate the largest gap between measurements in days"""
    if len(year_data) < 2:
      return 0
    
    dates = sorted(set(dt.date() for dt in year_data))
    max_gap = 0
    
    for i in range(1, len(dates)):
      gap = (dates[i] - dates[i-1]).days
      max_gap = max(max_gap, gap)
    
    return max_gap
  
  def _score_seasonal_coverage(self, seasonal_breakdown):
    """Score seasonal coverage based on how well distributed data is across seasons"""
    # Expected days per season (approximate)
    season_expectations = {'spring': 92, 'summer': 93, 'fall': 91, 'winter': 89}
    
    seasonal_scores = []
    for season, expected_days in season_expectations.items():
      actual_days = seasonal_breakdown.get(season, 0)
      # Score based on percentage of season covered, but cap at 100%
      score = min(100.0, (actual_days / expected_days) * 100.0)
      seasonal_scores.append(score)
    
    # Average across all seasons
    return sum(seasonal_scores) / len(seasonal_scores)
  
  def _score_monthly_coverage(self, monthly_breakdown):
    """Score monthly coverage based on how many months have data"""
    months_with_data = sum(1 for days in monthly_breakdown.values() if days > 0)
    return (months_with_data / 12.0) * 100.0
  
  def _calculate_overall_score(self, days_with_data, seasonal_coverage, 
                              monthly_coverage, largest_gap_days, year):
    """Calculate overall coverage score considering multiple factors"""
    # Base score from days covered in year
    is_leap_year = self._is_leap_year(year)
    total_days = 366 if is_leap_year else 365
    
    daily_coverage_score = (days_with_data / total_days) * 100.0
    
    # Penalty for large gaps (gaps > 60 days are concerning)
    gap_penalty = 0
    if largest_gap_days > 60:
      gap_penalty = min(30, (largest_gap_days - 60) * 0.5)  # Up to 30 point penalty
    
    # Weighted combination of factors
    overall_score = (
      daily_coverage_score * 0.4 +      # 40% weight on daily coverage
      seasonal_coverage * 0.4 +         # 40% weight on seasonal distribution  
      monthly_coverage * 0.2             # 20% weight on monthly distribution
    ) - gap_penalty
    
    return max(0.0, overall_score)  # Don't go below 0
  
  def _is_leap_year(self, year):
    """Check if year is a leap year"""
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
