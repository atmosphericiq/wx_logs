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

    self.wind_vectors = []
    self.wind_values = []
    self.air_temp_c_values = []
    self.air_pressure_hpa_values = []
    self.air_humidity_values = []
    self.air_dewpoint_c_values = []

    # pm25 and pm10 are ug/m3
    self.pm_25_values = []
    self.pm_10_values = []
    self.ozone_ppb_values = []
    self.so2_values = []

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
    if on_error not in ['RAISE', 'IGNORE']:
      raise ValueError(f"Invalid on_error: {on_error}")
    self.on_error = on_error

  def get_qa_status(self):
    return self.qa_status

  def handle_error(self, message):
    if self.on_error == 'RAISE':
      raise ValueError(message)
    else:
      self.set_qa_status('FAIL')
      logger.warning(message)

  def add_temp_c(self, value, dt):
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

    self.air_temp_c_values.append((dt, value))

  def add_humidity(self, value, dt):
    if value is None or value == '':
      return
    dt = self._validate_dt_or_convert_to_datetime_obj(dt)
    value = round(float(value), 0)
    if value < 0 or value > 100:
      self.handle_error(f"Invalid humidity value: {value}")
      return
    self.air_humidity_values.append((dt, value))
  
  def add_pm25(self, value, dt):
    value = self._simple_confirm_value_in_range(value, 0, 1000)
    if value is None:
      return
    dt = self._validate_dt_or_convert_to_datetime_obj(dt)
    self.pm_25_values.append((dt, value))

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
    value = self._simple_confirm_value_in_range(value, 0, 1000)
    if value is None:
      return
    dt = self._validate_dt_or_convert_to_datetime_obj(dt)
    self.pm_10_values.append((dt, value))

  def add_ozone_ppb(self, value, dt):
    value = self._simple_confirm_value_in_range(value, 0, 1000)
    if value is None:
      return
    dt = self._validate_dt_or_convert_to_datetime_obj(dt)
    self.ozone_ppb_values.append((dt, value))

  def add_so2(self, value, dt):
    value = self._simple_confirm_value_in_range(value, 0, 1000)
    if value is None:
      return
    dt = self._validate_dt_or_convert_to_datetime_obj(dt)
    self.so2_values.append((dt, value))

  def _simple_confirm_value_in_range(self, value, min, max):
    if value is None or value == '':
      return
    value = float(value)
    if value < 0:
      self.handle_error(f"Invalid {field_name} value: {value}")
      return
    return value

  def add_pressure_hpa(self, value, dt):
    dt = self._validate_dt_or_convert_to_datetime_obj(dt)
    self.air_pressure_hpa_values.append((dt, value))

  # merge in another wx_log by copying the values
  # from that one into this one
  def merge_in(self, other_log):
    if self.location != other_log.location:
      raise ValueError("Cannot merge logs with different locations")
    if self._reading_type != other_log.get_type():
      raise ValueError("Cannot merge logs of different types")
    self.air_temp_c_values.extend(other_log.air_temp_c_values)
    self.air_humidity_values.extend(other_log.air_humidity_values)
    self.air_pressure_hpa_values.extend(other_log.air_pressure_hpa_values)

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
    return round(np.mean([v[1] for v in values]), self._precision)

  def _min(self, values):
    return round(min([v[1] for v in values]), self._precision)

  def _max(self, values):
    return round(max([v[1] for v in values]), self._precision)

  def get_temp_c(self, measure='MEAN'):
    measure = measure.upper()
    return self._get_value_metric('air_temp_c_values', measure)

  def get_humidity(self, measure='MEAN'):
    measure = measure.upper()
    return self._get_value_metric('air_humidity_values', measure)

  def get_pressure_hpa(self, measure='MEAN'):
    measure = measure.upper()
    return self._get_value_metric('air_pressure_hpa_values', measure)

  # returns the min and max dates in the dt part of the tuple
  # returns a tuple 
  def get_date_range(self, field_name='air_temp_c'):
    if field_name == 'air_temp_c':
      values = self.air_temp_c_values
    elif field_name == 'air_humidity':
      values = self.air_humidity_values
    elif field_name == 'air_pressure_hpa':
      values = self.air_pressure_hpa_values
    elif field_name == 'wind':
      values = self.wind_values
    elif field_name == 'pm_25':
      values = self.pm_25_values
    elif field_name == 'pm_10':
      values = self.pm_10_values
    elif field_name == 'ozone_ppb':
      values = self.ozone_ppb_values
    elif field_name == 'so2':
      values = self.so2_values
    else:
      raise ValueError(f"Invalid field name: {field_name}")
    if len(values) == 0:
      return None
    min_date = min(values, key=lambda x: x[0])[0]
    max_date = max(values, key=lambda x: x[0])[0]
    return (min_date, max_date)

  def _wind_to_vector(self, bearing, speed):
    if speed is None or bearing is None:
      return None
    bearing_rad = np.radians(bearing)
    x = speed * np.sin(bearing_rad)
    y = speed * np.cos(bearing_rad)
    return (x, y)

  def get_wind(self, measure='VECTOR_MEAN'):
    measure = measure.upper()
    if measure == 'VECTOR_MEAN':
      total_x = 0
      total_y = 0
      count = 0
      for dt, (x, y) in self.wind_vectors:
        total_x += x
        total_y += y
        count += 1
      if count == 0:
        return None
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
    return self._get_value_metric('wind_values', measure)

  def add_wind(self, speed, bearing, dt):
    dt = self._validate_dt_or_convert_to_datetime_obj(dt)
    if speed == '':
      speed = None
    if bearing == '':
      bearing = None

    if bearing:
      bearing = float(bearing)
      if bearing < 0:
        bearing += 360
      bearing = int(bearing)
    if speed:
      speed = float(speed)
      speed = round(speed, self._precision)
      assert speed >= 0, 'Invalid wind speed'
    self.wind_vectors.append((dt, self._wind_to_vector(bearing, speed)))
    self.wind_values.append((dt, speed, bearing))

  def _get_value_metric(self, field_name, measure):
    field_values = getattr(self, field_name)
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
          'count': len(self.air_temp_c_values)
        },
        'humidity': {
          'mean': self.get_humidity('MEAN'),
          'min': self.get_humidity('MIN'),
          'max': self.get_humidity('MAX'),
          'count': len(self.air_humidity_values)
        },
        'pressure_hpa': {
          'mean': self.get_pressure_hpa('MEAN'), 
          'min': self.get_pressure_hpa('MIN'),
          'max': self.get_pressure_hpa('MAX'),
          'count': len(self.air_pressure_hpa_values)
        },
        'wind': {
          'speed': {
            'vector_mean': speed,
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
          'count': len(self.pm_25_values)
        },
        'pm10': {
          'mean': self.get_pm10('MEAN'),
          'min': self.get_pm10('MIN'),
          'max': self.get_pm10('MAX'),
          'count': len(self.pm_10_values)
        },
        'ozone_ppb': self.get_ozone_ppb(),
        'so2': self.get_so2()
      }
    }
  )

  def bearing_to_direction(self, bearing):
    directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
      'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    index = int((bearing + 11.25) // 22.5)
    return directions[index % 16]

  def get_location(self):
    return self.location
