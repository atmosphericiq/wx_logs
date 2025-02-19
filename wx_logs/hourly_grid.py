from datetime import datetime, timedelta
import numpy as np

VALID_DATA_THRESHOLD = 0.8

class HourlyGrid:

  def __init__(self, default_value=None):
    self.hours = {} # dict keyed by the hour value
    self.report_count = {}
    self._start = None
    self._end = None
    self._default_value = default_value
    self._is_empty = True # is it all NULL values
    self._precision = 4
    self._number_of_reports = 0

  # recalculate hour grid
  # this is called when we change the start or end
  # date for the grid
  def _recalc(self):
    # turn start back into a dt object
    start_dt = self._start
    end_dt = self._end
    while start_dt < end_dt:
      hour = start_dt
      if hour not in self.hours:
        self.hours[hour] = self._default_value
        self.report_count[hour] = 0
      start_dt += timedelta(hours=1)

  # recalc only the bottom bc were appending
  def _recalc_bottom(self, old_end):
    max_hour_in_hours = old_end
    while max_hour_in_hours < self._end:
      try:
        self.hours[max_hour_in_hours]
      except KeyError:
        self.hours[max_hour_in_hours] = self._default_value
        self.report_count[max_hour_in_hours] = 0
      max_hour_in_hours += timedelta(hours=1)

  # get the total number of hours in the grid
  def get_total_hours(self):
    return len(self.hours)

  # update the start and end based on this
  # value and then populate 
  def _update_range(self, dt):
    hour = dt.replace(minute=0, second=0, microsecond=0)

    recalc = False
    recalc_bottom = False
    if self._start is None:
      self._start = hour
      recalc = True
    elif dt < self._start:
      self._start = hour
      recalc = True

    if self._end is None:
      self._end = hour
      recalc = True
    elif dt > self._end:
      old_end = self._end
      self._end = hour # set the new end
      recalc_bottom = True

    if recalc:
      self._recalc()
    if recalc_bottom:
      self._recalc_bottom(old_end) # calc only bottom of stack

  def get_start(self):
    return self._start

  def get_end(self):
    return self._end

  def add(self, dt, value):
    # export the dt as the hour value
    # which is 2024-01-01 00
    hour = dt.replace(minute=0, second=0, microsecond=0)
    self._update_range(dt)
    if value is not None:
      value = float(value)
    self.hours[hour] = value
    try:
      self.report_count[hour] 
    except Exception:
      self.report_count[hour] = 0
    self.report_count[hour] += 1

    if value is not None:
      self._is_empty = False
    self._number_of_reports += 1

  # reported count returns sum of hours_count instead of parsing hours
  # so we get the number of reports for th year
  def get_reported_count(self, start=None, end=None):
    if self._is_empty:
      return None
    if len(self.hours) == 0:
      return None
    if start is None:
      return sum([v for v in self.report_count.values()])
    else:
      return sum([v for h, v in self.report_count.items() if h >= start and h <= end])

  # return a simple count of non-null elements
  def get_count(self, start=None, end=None):
    if self._is_empty:
      return None
    if len(self.hours) == 0:
      return None
    if start is None:
      return len([v for v in self.hours.values() if v is not None])
    else:
      return len([v for h, v in self.hours.items() if h >= start and h <= end and v is not None])

  # sum up all the values in the hourly grid
  def get_total(self, start=None, end=None):
    if self._is_empty:
      return None
    if len(self.hours) == 0:
      return None
    if start == None:
      hour_values = [v for v in self.hours.values() if v is not None]
    else:
      hour_values = [v for h, v in self.hours.items() if h >= start and h <= end and v is not None]
    totaled = np.sum(hour_values)

    # if its an int64, just make it an int
    if type(totaled) == np.int64:
      return int(totaled)
    return totaled

  def _prepare_metric(self, start=None, end=None):
    if self._is_empty:
      return None
    if len(self.hours) == 0:
      return None
    if start is None:
      hour_values = [v for v in self.hours.values() if v is not None]
    else:
      hour_values = [v for h, v in self.hours.items() if h >= start and h <= end and v is not None]
    if len(hour_values) == 0:
      return None
    return hour_values

  def get_mean(self, start=None, end=None):
    hour_values = self._prepare_metric(start, end)
    if hour_values is None:
      return None
    return np.round(np.mean(hour_values), self._precision)

  # return the min/max value in the grid (excluding NULL)
  def get_min(self, start=None, end=None):
    hour_values = self._prepare_metric(start, end)
    if hour_values is None:
      return 0.0  # Default to 0 if no non-null values above zero exist
    min_value = np.round(np.min(hour_values), self._precision)
    if type(min_value) == np.int64:
      return float(min_value)
    return min_value

  def get_max(self, start=None, end=None):
    hour_values = self._prepare_metric(start, end)
    if hour_values is None:
      return 0.0  # Default to 0 if no non-null values above zero exist
    max_value = np.round(np.max(hour_values), self._precision)
    if type(max_value) == np.int64:
      return float(max_value)
    return max_value

  # create a dict of years and their totals
  def get_total_by_year(self):
    years = {}
    for hour, value in self.hours.items():
      year = hour.year
      if value is not None:  # Ensure we only sum non-null values
        if year not in years:
          years[year] = 0
        years[year] += value
    return years

  # for years where we have enough valid records then
  # just like with time of wetness, we need to determine
  # and then extrapolate the mm of rainfall
  def get_average_for_valid_years(self):
    totals_by_year = self.get_total_by_year_detailed()
    if totals_by_year is None:
      return None
    totals = []
    for (year, data) in totals_by_year.items():
      if data['count'] == None: 
        continue
      if data['count'] / 8760 > 0.8: # threshold
        totals.append(data['estimated_total_mm'])
    if len(totals) == 0:
      return None
    return np.round(np.mean(totals), self._precision)
  
  # {2022: {'total': 8760, 'mean': 1.0, 'min': 1.0, 'max': 1.0}
  # return a grid like that
  def get_total_by_year_detailed(self):
    if self._start is None or self._end is None:
      return None
    start_year = self._start.year
    end_year = self._end.year
    result = {}
    while start_year <= end_year:
      range_start = datetime(start_year, 1, 1)
      range_end = datetime(start_year, 12, 31, 23)
      total = self.get_total(range_start, range_end)
      count = self.get_count(range_start, range_end)
      reported_count = self.get_reported_count(range_start, range_end)
      
      # Determine hours in the year: 8760 or 8784 for leap years
      hours_in_year = 8784 if (start_year % 4 == 0 and (start_year % 100 != 0 or start_year % 400 == 0)) else 8760
      
      # Calculate estimated total
      if count is None or count <= 0:
        estimated_total = 0
      else:
        estimated_total = total * hours_in_year / count

      result[start_year] = {
        'total_mm': total,
        'min_mm': self.get_min(range_start, range_end),
        'max_mm': self.get_max(range_start, range_end),
        'mean_mm': self.get_mean(range_start, range_end),
        'count': count,
        'reported_count': reported_count,
        'estimated_total_mm': estimated_total,
        'qa_state': 'PASS' if count is not None and count / hours_in_year > VALID_DATA_THRESHOLD else 'FAIL'
      }
      start_year += 1
    return result

  # return the number of reports
  def get_number_reports(self):
    return self._number_of_reports
