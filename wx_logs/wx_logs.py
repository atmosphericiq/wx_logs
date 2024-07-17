import json
import dateparser
import numpy as np
import math
import logging
import datetime
import pytz

logger = logging.getLogger(__name__)

class wx_logs:

  VALID_TYPES = ['STATION', 'BOUY']

  def __init__(self, reading_type=None, precision=2):
    self._precision = precision
    assert reading_type in self.VALID_TYPES, f"Invalid reading type: {reading_type}"
    self._reading_type = reading_type

    self.station_id = None
    self.owner = None
    self.name = None

    self.location = None
    self.timezone = None
    self.qa_status = 'PASS'
    self.on_error = 'RAISE'

    self.wind_vectors = {}
    self.wind_values = {}
    self.air_temp_c_values = {}
    self.air_pressure_hpa_values = {}
    self.air_humidity_values = {}
    self.air_dewpoint_c_values = {}

    # also store wind speed and bearing as sep
    # values for easier access
    self.wind_speed_values = {}
    self.wind_bearing_values = {}

    # pm25 and pm10 are ug/m3
    self.pm_25_values = {}
    self.pm_10_values = {}
    self.ozone_ppb_values = {}
    self.so2_values = {}

  def get_type(self):
    return self._reading_type

  def set_station_id(self, station_id):
    self.station_id = station_id

  def set_station_owner(self, owner):
    self.owner = owner

  def set_station_name(self, name):
    self.name = name

  def get_station_id(self):
    return self.station_id

  def get_station_name(self):
    return self.name

  def get_station_owner(self):
    return self.owner

  def get_owner(self):
    return self.owner

  def set_qa_status(self, status):
    if status not in ['PASS', 'FAIL']:
      raise ValueError(f"Invalid QA status: {status}")
    self.qa_status = status

  def set_on_error(self, on_error):
    on_error = on_error.upper()
    if on_error not in ['RAISE', 'IGNORE', 'FAIL_QA']:
      raise ValueError(f"Invalid on_error: {on_error}")
    self.on_error = on_error

  def get_qa_status(self):
    return self.qa_status

  def is_qa_pass(self):
    return self.qa_status == 'PASS'

  def handle_error(self, message):
    if self.on_error == 'RAISE':
      raise ValueError(message)
    elif self.on_error == 'FAIL_QA':
      self.set_qa_status('FAIL')
      logger.warning(message)
    elif self.on_error == 'IGNORE':
      logger.warning(message)
    else:
      raise ValueError(f"Invalid on_error: {self.on_error}")

  def _dewpoint_to_relative_humidity(self, temp_c, dewpoint_c):
    if dewpoint_c > temp_c: # fully saturated
      return 1.0
    e_temp = 6.11 * math.pow(10, (7.5 * temp_c) / (237.3 + temp_c))
    e_dew = 6.11 * math.pow(10, (7.5 * dewpoint_c) / (237.3 + dewpoint_c))
    relative_humidity = 100 * (e_dew / e_temp)
    return relative_humidity

  # when adding a dewpoint, actually add it to both
  # the dewpoint array and the humidity calculation array
  def add_dewpoint_c(self, dewpoint_c, air_temp_c, dt):
    dt = self._validate_dt_or_convert_to_datetime_obj(dt)
    if dewpoint_c is None:
      return
    if air_temp_c is None:
      self.handle_error("Cannot calculate dewpoint without temperature")
      return
    rh = self._dewpoint_to_relative_humidity(air_temp_c, dewpoint_c)
    self.air_dewpoint_c_values[dt] = dewpoint_c
    self.air_humidity_values[dt] = rh

  def add_temp_c(self, value, dt):
    value = self._should_value_be_none(value)
    if value is None:
      return
    dt = self._validate_dt_or_convert_to_datetime_obj(dt)

    # the max temp seen on earth is 56.7C
    # the min temp seen on earth is -89.2C
    # so validate we are in those ranges
    value = float(value)
    if value < -90 or value > 60:
      self.handle_error(f"Invalid temperature value: {value}")
      return

    self.air_temp_c_values[dt] = value

  def add_humidity(self, value, dt):
    value = self._should_value_be_none(value)
    dt = self._validate_dt_or_convert_to_datetime_obj(dt)
    if value is None:
      return

    value = round(float(value), 0)
    if value < 0 or value > 110:
      self.handle_error(f"Invalid humidity value: {value}")
      return
    if value > 100:
      value = 100
    self.air_humidity_values[dt] = value
  
  # according to EPA negative values are allowed
  # https://www.epa.gov/sites/default/files/2016-10/documents/pm2.5_continuous_monitoring.pdf
  # but for now, lets coalesce to zero
  # but less than -15 is bad!
  def add_pm25(self, value, dt):
    value = self._simple_confirm_value_in_range('pm25', value, -15, 10000)
    if value < 0:
      value = 0
    if value is None:
      return
    dt = self._validate_dt_or_convert_to_datetime_obj(dt)
    self.pm_25_values[dt] = value

  def get_pm25(self, measure='MEAN'):
    measure = measure.upper()
    return self._get_value_metric('pm_25_values', measure)

  def get_pm10(self, measure='MEAN'):
    measure = measure.upper()
    return self._get_value_metric('pm_10_values', measure)

  def get_ozone_ppb(self, measure='MEAN'):
    measure = measure.upper()
    return self._get_value_metric('ozone_ppb_values', measure)

  def get_so2(self, measure='MEAN'):
    measure = measure.upper()
    return self._get_value_metric('so2_values', measure)

  def add_pm10(self, value, dt):
    value = self._simple_confirm_value_in_range('pm10', value, -15, 10000)
    if value is None:
      return
    if value < 0:
      value = 0
    dt = self._validate_dt_or_convert_to_datetime_obj(dt)
    self.pm_10_values[dt] = value

  def add_ozone_ppb(self, value, dt):
    value = self._simple_confirm_value_in_range('ozone', value, 0, 1000)
    if value is None:
      return
    dt = self._validate_dt_or_convert_to_datetime_obj(dt)
    self.ozone_ppb_values[dt] = value

  def add_so2(self, value, dt):
    value = self._simple_confirm_value_in_range('so2', value, 0, 1000)
    if value is None:
      return
    dt = self._validate_dt_or_convert_to_datetime_obj(dt)
    self.so2_values[dt] = value

  def _simple_confirm_value_in_range(self, field_name, value, min_value, max_value):
    if value is None or value == '':
      return
    value = float(value)
    if value < min_value or value > max_value:
      self.handle_error(f"Invalid value for {field_name}: {value}")
      return
    return value

  # interpret whether a value should be None
  # which is none, numpy nan, empty string, etc
  def _should_value_be_none(self, value):
    if value is None:
      return None
    if isinstance(value, str) and value == '':
      return None
    if isinstance(value, float) and np.isnan(value):
      return None
    return value

  def add_pressure_hpa(self, value, dt):
    dt = self._validate_dt_or_convert_to_datetime_obj(dt)
    value = self._should_value_be_none(value)
    if value is None:
      return
    if value is not None:
      value = float(value)
      value = self._simple_confirm_value_in_range('pressure_hpa', value, 500, 1500)
    self.air_pressure_hpa_values[dt] = value

  # merge in another wx_log by copying the values
  # from that one into this one
  def merge_in(self, other_log):
    if self.location != other_log.location:
      raise ValueError("Cannot merge logs with different locations")
    if self._reading_type != other_log.get_type():
      raise ValueError("Cannot merge logs of different types")
    self.air_temp_c_values.update(other_log.air_temp_c_values)
    self.air_humidity_values.update(other_log.air_humidity_values)
    self.air_pressure_hpa_values.update(other_log.air_pressure_hpa_values)
    self.wind_values.update(other_log.wind_values)
    self.wind_vectors.update(other_log.wind_vectors)
    self.pm_25_values.update(other_log.pm_25_values)
    self.pm_10_values.update(other_log.pm_10_values)
    self.ozone_ppb_values.update(other_log.ozone_ppb_values)
    self.so2_values.update(other_log.so2_values)

  def set_timezone(self, tz):
    try:
      pytz.timezone(tz)
    except pytz.exceptions.UnknownTimeZoneError:
      raise ValueError(f"Invalid timezone: {tz}")
    self.timezone = tz

  def get_timezone(self):
    return self.timezone

  def _validate_dt_or_convert_to_datetime_obj(self, dt):
    if isinstance(dt, datetime.datetime):
      return dt
    elif isinstance(dt, str):
      return dateparser.parse(dt)
    else:
      raise ValueError(f"Invalid datetime object: {dt}")

  def _mean(self, values):
    return round(np.mean([v[1] for v in values if v[1] is not None]), self._precision)

  def _min(self, values):
    return round(min([v[1] for v in values if v[1] is not None]), self._precision)

  def _max(self, values):
    return round(max([v[1] for v in values if v[1] is not None]), self._precision)

  def get_temp_c(self, measure='MEAN'):
    measure = measure.upper()
    return self._get_value_metric('air_temp_c_values', measure)

  def get_humidity(self, measure='MEAN'):
    measure = measure.upper()
    return self._get_value_metric('air_humidity_values', measure)

  def get_pressure_hpa(self, measure='MEAN'):
    measure = measure.upper()
    return self._get_value_metric('air_pressure_hpa_values', measure)

  def _string_to_field_values(self, field_name):
    if field_name == 'air_temp_c':
      return self.air_temp_c_values
    elif field_name == 'air_humidity':
      return self.air_humidity_values
    elif field_name == 'air_pressure_hpa':
      return self.air_pressure_hpa_values
    elif field_name == 'wind':
      return self.wind_values
    elif field_name == 'pm_25':
      return self.pm_25_values
    elif field_name == 'pm_10':
      return self.pm_10_values
    elif field_name == 'ozone_ppb':
      return self.ozone_ppb_values
    elif field_name == 'so2':
      return self.so2_values
    else:
      raise ValueError(f"Invalid field name: {field_name}")

  # returns the min and max dates in the dt part of the tuple
  # returns a tuple 
  def get_date_range(self, field_name='air_temp_c', isoformat=True):
    values = self._string_to_field_values(field_name)
    if len(values) == 0:
      return None
    keys = list(values.keys())
    min_date = min(keys)
    max_date = max(keys)
    if isoformat:
      min_date = min_date.isoformat()
      max_date = max_date.isoformat()
    return (min_date, max_date)

  # returns a count of readings for a field for each month
  def get_months(self, field_name='air_temp_c'):
    values = self._string_to_field_values(field_name)
    return self._get_months(list(values.keys()))

  # function which looks at the months in the data
  # and does a best effort to determine if a full year of 
  # data is available. This is useful for determining if
  # a station is operational. You're going to have to be 
  # care and try to determine if the months are roughly balanced
  def is_full_year_of_data(self, field_name='air_temp_c'):
    months = self.get_months(field_name)
    if len(months.keys()) < 12:
      return False
    counts = months.values()
    max_count = max(counts)
    threshold = 0.10 * max_count
    if any([count < threshold for count in counts]):
      return False
    return True

  def _wind_to_vector(self, bearing, speed):
    if speed is None or bearing is None:
      return None
    bearing_rad = np.radians(bearing)
    x = speed * np.sin(bearing_rad)
    y = speed * np.cos(bearing_rad)
    return (x, y)

  def get_wind(self, measure='VECTOR_MEAN'):
    self._recalculate_wind_vectors()
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

  def get_wind_speed(self, measure='MEAN'):
    measure = measure.upper()
    return self._get_value_metric('wind_speed_values', measure)

  def add_wind_speed_knots(self, speed_knots, dt):
    dt = self._validate_dt_or_convert_to_datetime_obj(dt)
    if speed_knots == '':
      speed_knots = None
    if speed_knots is not None:
      speed_knots = float(speed_knots)
    self.add_wind_speed(speed_knots * 0.514444, dt)

  def add_wind_speed(self, speed_m_s, dt):
    dt = self._validate_dt_or_convert_to_datetime_obj(dt)
    if speed_m_s == '':
      speed_m_s = None
    if speed_m_s is not None:
      speed_m_s = round(float(speed_m_s), self._precision)
      speed_m_s = self._simple_confirm_value_in_range('speed_m_s', speed_m_s, 0, 100)
    self.wind_speed_values[dt] = speed_m_s

  def add_wind_bearing(self, bearing, dt):
    dt = self._validate_dt_or_convert_to_datetime_obj(dt)
    if bearing == '':
      bearing = None
    if bearing is not None:
      bearing = round(float(bearing), self._precision)
      if bearing < 0:
        bearing += 360

      # validate bearing between 0 and 360
      self._simple_confirm_value_in_range('bearing', bearing, 0, 360)

    self.wind_bearing_values[dt] = bearing

  # three step process
  # 1. find the unique pairs of speed, bearing dt values
  # 2. see which ones are NOT in wind_vectors
  # 3. call add_wind for those vectors
  # do this in an O(1) fashion
  def _recalculate_wind_vectors(self):
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

  # function which returns a dictionary of wind rose data
  # where the keys are the bearing strings (N, NE, etc)
  # and the values are the mean wind speed for that direction
  def get_wind_rose(self, bins=4):
    self._recalculate_wind_vectors()
    if bins == 4:
      directions = ['N', 'E', 'S', 'W']
    elif bins == 8:
      directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    else:
      raise ValueError("Only 4 or 8 bins are supported")

    result = {direction: {'x': 0, 'y': 0, 'count': 0} for direction in directions}

    bin_size = 360 / bins
    for (dt, (speed, bearing)) in self.wind_values.items():
      (x, y) = self._wind_to_vector(bearing, speed)
      direction = self.bearing_to_direction(bearing, bins)
      result[direction]['x'] += x
      result[direction]['y'] += y 
      result[direction]['count'] += 1

    for direction in result.keys():
      if result[direction]['count'] > 0:
        mean_x = result[direction]['x'] / result[direction]['count']
        mean_y = result[direction]['y'] / result[direction]['count']
        result[direction] = round(np.sqrt(mean_x**2 + mean_y**2), self._precision)
      else:
        result[direction] = 0
    return result

  def add_wind(self, speed, bearing, dt, add_values=True):
    dt = self._validate_dt_or_convert_to_datetime_obj(dt)
    bearing = self._should_value_be_none(bearing)
    speed = self._should_value_be_none(speed)

    if speed is None or bearing is None:
      return

    bearing = float(bearing)
    if bearing < 0:
      bearing += 360
    bearing = int(bearing)
    self._simple_confirm_value_in_range('wind_bearing', bearing, 0, 360)
    speed = float(speed)
    self._simple_confirm_value_in_range('wind_speed', speed, 0, 100)
    self.wind_vectors[dt] = self._wind_to_vector(bearing, speed)
    self.wind_values[dt] = (speed, bearing)
    if add_values == True:
      self.wind_speed_values[dt] = speed
      self.wind_bearing_values[dt] = bearing

  def _get_value_metric(self, field_name, measure):
    field = getattr(self, field_name)
    field_values = list(field.items())

    # remove any none values
    field_values = [v for v in field_values if v is not None]

    if len(field_values) == 0:
      return None
    if measure == 'MEAN':
      return self._mean(field_values)
    elif measure == 'MAX':
      return self._max(field_values)
    elif measure == 'MIN':
      return self._min(field_values)
    else:
      raise ValueError(f"Invalid measure: {measure}")

  # give a set of dates, return a dictionary of 
  # {1: N} where 1 is january and N is number of values
  def _get_months(self, date_list):
    result = {i: 0 for i in range(1, 13)}
    for dt in date_list:
      result[dt.month] += 1
    return result

  def set_location(self, latitude, longitude, elevation=None):
    if elevation == '':
      elevation = None
    if elevation is not None:
      elevation = float(elevation)
      elevation = round(elevation, self._precision)
      if elevation == 0:
        elevation = None
    if latitude == '':
      latitude = None
    if longitude == '':
      longitude = None
    if latitude is not None:
      latitude = float(latitude)
      if latitude < -90 or latitude > 90:
        raise ValueError(f"Invalid latitude: {latitude}")
    if longitude is not None:
      longitude = float(longitude)
      if longitude < -180 or longitude > 180:
        raise ValueError(f"Invalid longitude: {longitude}")
    self.location = {'latitude': latitude,
      'longitude': longitude,
      'elevation': elevation}

  # generates a JSON dictionary of the log
  # but only includes summary information instead of all teh values
  def serialize_summary(self):
    (speed, bearing, dir_string) = self.get_wind('VECTOR_MEAN')
    return json.dumps({
      'type': self._reading_type,
      'station': {
        'id': self.station_id,
        'owner': self.owner,
        'name': self.name,
        'location': self.location,
        'timezone': self.timezone
      },
      'qa_status': self.qa_status,
      'air': {
        'temp_c': {
          'mean': self.get_temp_c('MEAN'),
          'min': self.get_temp_c('MIN'),
          'max': self.get_temp_c('MAX'),
          'count': len(self.air_temp_c_values),
          'date_range': self.get_date_range('air_temp_c'),
          'full_year': self.is_full_year_of_data('air_temp_c')
        },
        'humidity': {
          'mean': self.get_humidity('MEAN'),
          'min': self.get_humidity('MIN'),
          'max': self.get_humidity('MAX'),
          'count': len(self.air_humidity_values),
          'date_range': self.get_date_range('air_humidity'),
          'full_year': self.is_full_year_of_data('air_humidity')
        },
        'pressure_hpa': {
          'mean': self.get_pressure_hpa('MEAN'), 
          'min': self.get_pressure_hpa('MIN'),
          'max': self.get_pressure_hpa('MAX'),
          'count': len(self.air_pressure_hpa_values),
          'date_range': self.get_date_range('air_pressure_hpa'),
          'full_year': self.is_full_year_of_data('air_pressure_hpa')
        },
        'wind': {
          'speed': {
            'vector_mean': speed,
            'mean': self.get_wind_speed('MEAN'),
            'max': self.get_wind_speed('MAX'),
            'min': self.get_wind_speed('MIN'),
            'count': len(self.wind_values)
          },
          'bearing': {
            'vector_mean': bearing,
            'vector_string': dir_string,
            'count': len(self.wind_values)
          },
        },
        'pm25': {
          'mean': self.get_pm25('MEAN'),
          'min': self.get_pm25('MIN'),
          'max': self.get_pm25('MAX'),
          'count': len(self.pm_25_values),
          'date_range': self.get_date_range('pm_25')
        },
        'pm10': {
          'mean': self.get_pm10('MEAN'),
          'min': self.get_pm10('MIN'),
          'max': self.get_pm10('MAX'),
          'count': len(self.pm_10_values),
          'date_range': self.get_date_range('pm_10')
        },
        'ozone_ppb': {
          'mean': self.get_ozone_ppb('MEAN'),
          'min': self.get_ozone_ppb('MIN'),
          'max': self.get_ozone_ppb('MAX'),
          'count': len(self.ozone_ppb_values),
          'date_range': self.get_date_range('ozone_ppb')
        },
        'so2': {
          'mean': self.get_so2('MEAN'),
          'min': self.get_so2('MIN'),
          'max': self.get_so2('MAX'),
          'count': len(self.so2_values),
          'date_range': self.get_date_range('so2')
        }
      }
    }
  )

  def bearing_to_direction(self, bearing, bins=16):
    if bins == 4:
      directions = ['N', 'E', 'S', 'W']
      index = int((bearing + 45) // 90)
      return directions[index % 4]
    elif bins == 8:
      directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
      index = int((bearing + 22.5) // 45)
      return directions[index % 8]
    elif bins == 16:
      directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
        'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
      index = int((bearing + 11.25) // 22.5)
      return directions[index % 16]
    else:
      raise ValueError("Only 4, 8, or 16 bins are supported")

  def get_location(self):
    return self.location
