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
  def _recalc_bottom(self):
    max_hour_in_hours = max(self.hours.keys())
    while max_hour_in_hours < self._end:
      if max_hour_in_hours not in self.hours:
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
      self._end = hour
      recalc_bottom = True

    if recalc:
      self._recalc()
    if recalc_bottom:
      self._recalc_bottom()

  def get_start(self):
    return self._start

  def get_end(self):
    return self._end

  def add(self, dt, value):
    # export the dt as the hour value
    # which is 2024-01-01 00
    hour = dt.replace(minute=0, second=0, microsecond=0)
    self._update_range(dt)
    self.hours[hour] = value

  # sum up all the values in the hourly grid
  def get_total(self):
    return sum(self.hours.values())

  def get_total_by_year(self):
    # create a dict of years and the total for each year
    years = {}
    for hour, value in self.hours.items():
      year = hour.year
      if year not in years:
        years[year] = 0
      years[year] += value
    return years
