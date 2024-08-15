import datetime
import numpy as np

# this class is designed to calculate annual TOW (time of wetness)
# for a given year which is the number of hours in a year that
# the surface is wet. This is important for the calculation of
# corrosion rates for metals.
# number of hours per year with RH > 80% and T > 0
class TOWCalculator:

  def __init__(self):
    self._data = {}

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
        if mean_t > 0 and mean_rh > 80:
          tow_hours += 1
      percent_valid = float(total_hours) / float(max_hours)
      qa_state = 'PASS' if percent_valid > 0.75 else 'FAIL'
      if qa_state == 'PASS':
        projected_tow = self.project_tow(total_hours, max_hours, tow_hours)
      else:
        projected_tow = None
      payload = {'max_hours': max_hours, 
        'total_hours': total_hours,
        'time_of_wetness': projected_tow,
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
