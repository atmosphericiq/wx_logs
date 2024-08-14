import numpy as np
from .helpers import should_value_be_none, simple_confirm_value_in_range, \
  validate_dt_or_convert_to_datetime_obj
from windrose import WindroseAxes
import matplotlib.pyplot as plt

class WindRose:

  def __init__(self, bins=4, precision=2):
    self.bins = bins
    if bins == 4:
      self.directions = ['N', 'E', 'S', 'W']
      self.angles = [x for x in range(0, 360, 90)]
    elif bins == 8:
      self.directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
      self.angles = [x for x in range(0, 360, 45)]
    elif bins == 16:
      self.directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
        'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
      self.angles = [x/10.0 for x in range(0, 3600, 225)]
    else:
      raise ValueError("Only 4 or 8 bins are supported")

    # add a CALM bucket for winds that are calm
    self.directions.append('CALM')
    self.calm_threshold_m_s = 0.5 

    self._precision = precision
    self.wind_vectors = {}
    self.wind_values = {}

    self.wind_speed_values = {}
    self.wind_bearing_values = {}

  def direction_to_angle(self, direction):
    return self.angles[self.directions.index(direction)]

  def get_wind_vectors(self):
    return self.wind_vectors

  def get_wind_values(self):
    return self.wind_values

  def get_wind_speed_values(self):
    return self.wind_speed_values

  def get_wind_bearing_values(self):
    return self.wind_bearing_values

  def add_wind_speed(self, speed_m_s, dt):
    if speed_m_s == '':
      speed_m_s = None
    if speed_m_s is not None:
      speed_m_s = round(float(speed_m_s), self._precision)
      speed_m_s = simple_confirm_value_in_range('speed_m_s', speed_m_s, 0, 100)
    self.wind_speed_values[dt] = speed_m_s

  def add_wind_bearing(self, bearing, dt):
    if bearing == '':
      bearing = None
    if bearing is not None:
      bearing = round(float(bearing), self._precision)
      if bearing < 0:
        bearing += 360

      # validate bearing between 0 and 360
      simple_confirm_value_in_range('bearing', bearing, 0, 360)

    self.wind_bearing_values[dt] = bearing

  # output should look like: {'percent': 0.0, 'mean_wind_speed': None}
  # where percent is the % of the total values that are in the bin
  # and mean_wind_speed is the mean wind speed for that bin
  def get_wind_rose(self):
    result = {direction: {'x': 0, 'y': 0, 'count': 0} for direction in self.directions}

    bin_size = 360 / self.bins
    for (dt, (speed, bearing)) in self.wind_values.items():
      (x, y) = self._wind_to_vector(bearing, speed)

      # if the wind is calm, then just add it to the CALM bucket
      if speed and speed < self.calm_threshold_m_s:
        direction = 'CALM'
      else:
        direction = self.bearing_to_direction(bearing)

      result[direction]['x'] += x
      result[direction]['y'] += y
      result[direction]['count'] += 1

    for direction in result.keys():
      if result[direction]['count'] > 0:
        mean_x = result[direction]['x'] / result[direction]['count']
        mean_y = result[direction]['y'] / result[direction]['count']
        mean_speed = round(np.sqrt(mean_x**2 + mean_y**2), self._precision)
        percent = result[direction]['count'] / len(self.wind_values)
        percent *= 100 # convert to percentage
        result[direction] = {'mean_wind_speed': mean_speed,
          'percent': round(percent, self._precision)}
      else:
        result[direction] = {'mean_wind_speed': None, 'percent': 0.0}
    return result

  # three step process
  # 1. find the unique pairs of speed, bearing dt values
  # 2. see which ones are NOT in wind_vectors
  # 3. call add_wind for those vectors
  # do this in an O(1) fashion
  def recalculate_wind_vectors(self):
    calculated_dts = self.wind_vectors.keys()
    not_calculated_dts = set(self.wind_speed_values.keys()) - set(calculated_dts)
    for dt in not_calculated_dts:
      speed = self.wind_speed_values[dt]
      if speed is None:
        continue
      if dt in self.wind_bearing_values.keys():
        bearing = self.wind_bearing_values[dt]
        if bearing is None:
          continue
        self.add_wind(speed, bearing, dt, False)

  def add_wind(self, speed, bearing, dt, add_values=True):
    if speed is None or bearing is None:
      return

    bearing = float(bearing)
    if bearing < 0:
      bearing += 360
    bearing = int(bearing)
    speed = float(speed)
    self.wind_vectors[dt] = self._wind_to_vector(bearing, speed)
    self.wind_values[dt] = (speed, bearing)
    if add_values == True:
      self.wind_speed_values[dt] = speed
      self.wind_bearing_values[dt] = bearing

  def _wind_to_vector(self, bearing, speed):
    if speed is None or bearing is None:
      return None
    bearing_rad = np.radians(bearing)
    x = speed * np.sin(bearing_rad)
    y = speed * np.cos(bearing_rad)
    return (x, y)

  def bearing_to_direction(self, bearing):
    if self.bins == 4:
      index = int((bearing + 45) // 90)
      return self.directions[index % 4]
    elif self.bins == 8:
      directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
      index = int((bearing + 22.5) // 45)
      return self.directions[index % 8]
    elif self.bins == 16:
      directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
        'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
      index = int((bearing + 11.25) // 22.5)
      return self.directions[index % 16]
    else:
      raise ValueError("Only 4, 8, or 16 bins are supported")

  def get_wind(self, measure='VECTOR_MEAN'):
    self.recalculate_wind_vectors()
    measure = measure.upper()
    if measure == 'VECTOR_MEAN':
      total_x = 0
      total_y = 0
      count = 0
      for dt, (x, y) in self.wind_vectors.items():
        total_x += x
        total_y += y
        count += 1
      if count == 0:
        return (None, None, None)
      avg_speed = np.sqrt(total_x**2 + total_y**2) / count
      bearing_rad = np.arctan2(total_x, total_y)
      bearing_deg = np.degrees(bearing_rad)
      dir_string = self.bearing_to_direction(bearing_deg)
      if bearing_deg < 0:
        bearing_deg += 360
      return (round(avg_speed, self._precision),
        round(bearing_deg, self._precision), dir_string)
    else:
      raise ValueError(f"Invalid measure: {measure}")

  # plot the wind rose
  def plot(self):
    wd = np.array(list(self.get_wind_bearing_values().values()))
    ws = np.array(list(self.get_wind_speed_values().values()))
    ax = WindroseAxes.from_ax()
    ax.bar(wd, ws, normed=True, opening=0.8, edgecolor="white", blowto=True, nsector=self.bins)
    ax.set_legend()
    return ax
