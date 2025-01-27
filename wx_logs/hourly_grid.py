# hourly grid - this allows us to 
# store a value that is hourly in nature, like
# preciptation, and then use it to calculate
# the totals over periods of time
from datetime import datetime, timedelta
import numpy as np

class HourlyGrid:

  def __init__(self, default_value=None):
    self.hours = {} # dict keyed by the hour value
    self._start = None
    self._end = None
    self._default_value = default_value
    self._is_empty = True # is it all NULL values

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
      start_dt += timedelta(hours=1)

  # recalc only the bottom bc were appending
  def _recalc_bottom(self, old_end):
    max_hour_in_hours = old_end
    while max_hour_in_hours < self._end:
      try:
        self.hours[max_hour_in_hours]
      except KeyError:
        self.hours[max_hour_in_hours] = self._default_value
      max_hour_in_hours += timedelta(hours=1)

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
    if value is not None:
      self._is_empty = False

  # return a simple count of elements
  def get_count(self, start=None, end=None):
    if self._is_empty:
      return None
    if len(self.hours) == 0:
      return None
    if start is None:
      return len(self.hours.values())
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

  def get_mean(self, start=None, end=None):
    if self._is_empty:
      return None
    if len(self.hours) == 0:
      return None

    # convert the nan/nulls to 0
    if start is None:
      hour_values = [v if v is not None else 0 for v in self.hours.values()]
    else:
      hour_values = [v if v is not None else 0 for h, v in self.hours.items() if h >= start and h <= end]

    if len(hour_values) == 0:
      return None

    return np.mean(hour_values)

  def get_min(self, start=None, end=None):
    if self._is_empty:
      return None
    if len(self.hours) == 0:
      return None
    if start is None:
      hour_values = [v if v is not None else 0 for v in self.hours.values()]
    else:
      hour_values = [v if v is not None else 0 for h, v in self.hours.items() if h >= start and h <= end]

    if len(hour_values) == 0:
      return None

    return min(hour_values)

  def get_max(self, start=None, end=None):
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

    return max(hour_values)

  def get_total_by_year(self):
    # create a dict of years and the total for each year
    years = {}
    for hour, value in self.hours.items():
      year = hour.year
      if year not in years:
        years[year] = 0
      years[year] += value
    return years

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
      result[start_year] = {
        'total': total,
        'min': float(self.get_min(range_start, range_end)),
        'max': float(self.get_max(range_start, range_end)),
        'mean': float(self.get_mean(range_start, range_end)),
        'count': self.get_count(range_start, range_end)
      }
      start_year += 1
    return result
