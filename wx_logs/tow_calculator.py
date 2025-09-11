import datetime
import numpy as np
from .data_coverage import YearCoverageAnalyzer

TOW_RH_THRESHOLD = 80
TOW_T_THRESHOLD = 0
HOURS_PER_YEAR = 8760

# Calculates annual TOW (time of wetness) - number of hours per year
# with RH > 80% and T > 0. Important for corrosion rate calculations.
class TOWCalculator:

  def __init__(self, precision=4, threshold=0.75):
    self._data = {}
    self._precision = precision
    self._threshold = threshold

  def _validate_dt(self, dt):
    if not isinstance(dt, datetime.datetime):
      raise ValueError('dt must be a datetime object, got %s' % type(dt))
    year = dt.year
    if year not in self._data.keys():
      self.create_empty_year(year)
    day = dt.day
    month = dt.month
    hour = dt.hour
    return (year, month, day, hour)

  def annualize(self, valid_hours, tow_hours):
    if valid_hours == 0:
      return None
    pct_of_valid = float(tow_hours) / float(valid_hours)
    return int(round(pct_of_valid * HOURS_PER_YEAR, 0))

  # return a multi year average, excluding years with QA failures
  def get_averages(self):
    years = self.get_years()
    total_hours = 0
    tow_hours = 0
    max_hours = 0
    valid_years = 0
    for year in years.keys():
      if years[year]['qa_state'] == 'PASS':
        total_hours += years[year]['total_hours']
        tow_hours += years[year]['time_of_wetness_actual']
        max_hours += years[year]['max_hours']
        valid_years += 1

    projected_tow = self.annualize(total_hours, tow_hours)
    return {'annual_time_of_wetness': projected_tow,
      'valid_years': valid_years}

  # return an array for each year in data that looks like
  # {'total_hours': N, 'time_of_wetness': N, 'percent_valid': N}
  def get_years(self):
    years = {}
    for year in self._data.keys():
      max_hours = len(self._data[year].keys())
      total_hours = 0
      tow_hours = 0
      for (month, day, hour) in self._data[year].keys():
        temp_readings = self._data[year][(month, day, hour)]['t']
        rh_readings = self._data[year][(month, day, hour)]['rh']
        if len(temp_readings) == 0 or len(rh_readings) == 0:
          continue
        total_hours += 1
        mean_t = np.mean(temp_readings)
        mean_rh = np.mean(rh_readings)
        if mean_t > TOW_T_THRESHOLD and mean_rh > TOW_RH_THRESHOLD:
          tow_hours += 1
      percent_valid = round(float(total_hours) / float(max_hours),
        self._precision)
      qa_state = 'PASS' if percent_valid > self._threshold else 'FAIL'
      if qa_state == 'PASS':
        projected_tow = self.project_tow(total_hours, max_hours, tow_hours)
      else:
        projected_tow = None
      payload = {'max_hours': max_hours, 
        'total_hours': total_hours,
        'time_of_wetness': projected_tow,
        'time_of_wetness_actual': tow_hours,
        'qa_state': qa_state,
        'percent_valid': percent_valid}
      years[year] = payload
    return years

  # extrapolate total tow based on missing values
  def project_tow(self, hours_with_data, max_hours, current_tow):
    return int(round((current_tow / hours_with_data) * max_hours, 0))

  # creates an empty year with one row for every hour 
  # of the year
  def create_empty_year(self, year):
    if year not in self._data.keys():
      self._data[year] = {}
    for month in range(1, 13):
      days_in_month = 31
      if month == 2 and year % 4 == 0:
        days_in_month = 29 # leap year
      elif month == 2:
        days_in_month = 28
      elif month in [4, 6, 9, 11]:
        days_in_month = 30
      for day in range(1, days_in_month + 1):
        for hour in range(24):
          self._data[year][(month, day, hour)] = {'t': [], 'rh': []}

  def add_temperature(self, temperature, dt):
    (year, month, day, hour) = self._validate_dt(dt)
    self._data[year][(month, day, hour)]['t'].append(temperature)

  def add_humidity(self, rh, dt):
    (year, month, day, hour) = self._validate_dt(dt)
    self._data[year][(month, day, hour)]['rh'].append(rh)

  # Analyze temporal coverage for TOW data using the new coverage analyzer.
  # Args:
  #   year: Specific year to analyze (if None, uses the most common year)
  #   measurement_type: 'temperature' or 'humidity' to analyze coverage
  # Returns:
  #   Dict with coverage analysis results
  def assess_year_coverage(self, year=None, measurement_type='temperature'):
    analyzer = YearCoverageAnalyzer()
    datetime_list = self._get_tow_datetime_list(year, measurement_type)
    return analyzer.analyze_coverage(datetime_list, year)
  
  # Check if we have adequate year coverage for TOW data.
  # Args:
  #   year: Specific year to analyze
  #   measurement_type: 'temperature' or 'humidity'
  # Returns:
  #   Boolean indicating if coverage is adequate
  def has_adequate_year_coverage(self, year=None,
    measurement_type='temperature'):
    coverage = self.assess_year_coverage(year, measurement_type)
    return coverage['adequate_coverage']

  # Get list of datetime objects for TOW data for a specific measurement type.
  # Args:
  #   year: Year to extract data from (if None, uses all years)
  #   measurement_type: 'temperature' or 'humidity'
  # Returns:
  #   List of datetime objects where measurements exist
  def _get_tow_datetime_list(self, year, measurement_type):
    datetime_list = []
    
    years_to_check = [year] if year else list(self._data.keys())
    
    for check_year in years_to_check:
      if check_year not in self._data:
        continue
        
      for (month, day, hour) in self._data[check_year].keys():
        data_point = self._data[check_year][(month, day, hour)]
        
        # Check if we have data for the requested measurement type
        has_data = False
        if measurement_type.lower() in ['temperature', 'temp', 't']:
          has_data = len(data_point['t']) > 0
        elif measurement_type.lower() in ['humidity', 'rh']:
          has_data = len(data_point['rh']) > 0
        else:
          # For 'both' or unknown, require both temperature and humidity
          has_data = len(data_point['t']) > 0 and len(data_point['rh']) > 0
        
        if has_data:
          dt = datetime.datetime(check_year, month, day, hour)
          datetime_list.append(dt)
    
    return datetime_list

  # Enhanced version of get_years() that includes temporal coverage analysis.
  # Returns:
  #   Dict with yearly data including both traditional QA and new coverage analysis
  def get_years_with_coverage(self):
    years_data = self.get_years()
    
    for year in years_data.keys():
      # Add coverage analysis for temperature and humidity
      temp_coverage = self.assess_year_coverage(year, 'temperature')
      humidity_coverage = self.assess_year_coverage(year, 'humidity')
      
      # Add coverage data to the existing payload
      years_data[year]['coverage_analysis'] = {
        'temperature': {
          'overall_score': temp_coverage['overall_score'],
          'seasonal_coverage': temp_coverage['seasonal_coverage'],
          'monthly_coverage': temp_coverage['monthly_coverage'],
          'adequate_coverage': temp_coverage['adequate_coverage'],
          'days_with_data': temp_coverage['days_with_data'],
          'largest_gap_days': temp_coverage['largest_gap_days']
        },
        'humidity': {
          'overall_score': humidity_coverage['overall_score'],
          'seasonal_coverage': humidity_coverage['seasonal_coverage'],
          'monthly_coverage': humidity_coverage['monthly_coverage'],
          'adequate_coverage': humidity_coverage['adequate_coverage'],
          'days_with_data': humidity_coverage['days_with_data'],
          'largest_gap_days': humidity_coverage['largest_gap_days']
        },
        # Enhanced QA state that considers both data density and temporal distribution
        'enhanced_qa_state': self._calculate_enhanced_qa_state(
          years_data[year]['qa_state'], 
          temp_coverage['adequate_coverage'],
          humidity_coverage['adequate_coverage']
        )
      }
    
    return years_data

  # Calculate enhanced QA state considering both traditional density and
  # temporal coverage.
  # Args:
  #   traditional_qa: Traditional QA state ('PASS' or 'FAIL')
  #   temp_adequate: Boolean for temperature coverage adequacy
  #   humidity_adequate: Boolean for humidity coverage adequacy
  # Returns:
  #   Enhanced QA state string
  def _calculate_enhanced_qa_state(self, traditional_qa, temp_adequate,
    humidity_adequate):
    if traditional_qa == 'FAIL':
      return 'FAIL_DENSITY'  # Failed due to insufficient data density
    elif not temp_adequate or not humidity_adequate:
      return 'FAIL_COVERAGE'  # Failed due to poor temporal distribution
    else:
      return 'PASS'  # Passes both density and coverage checks
