import datetime
import numpy as np

TOW_RH_THRESHOLD = 80
TOW_T_THRESHOLD = 0
HOURS_PER_YEAR = 8760

# this class is designed to calculate annual TOW (time of wetness)
# for a given year which is the number of hours in a year that
# the surface is wet. This is important for the calculation of
# corrosion rates for metals.
# number of hours per year with RH > 80% and T > 0
class TOWCalculator:

  def __init__(self, precision=4):
    self._data = {}
    self._precision = precision

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

    # ok now do the same projection we do below
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
      percent_valid = round(float(total_hours) / float(max_hours), self._precision)
      qa_state = 'PASS' if percent_valid > 0.75 else 'FAIL'
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
    return round((current_tow / hours_with_data) * max_hours, 2)

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
