import numpy as np
import dateparser
import datetime

def simple_confirm_value_in_range(field_name, value, min_value, max_value):
  if value is None or value == '':
    return
  value = float(value)
  if value < min_value or value > max_value:
    raise ValueError(f"Invalid value for {field_name}: {value}")
  return value

# interpret whether a value should be None
# which is none, numpy nan, empty string, etc
def should_value_be_none(value):
  if value is None:
    return None
  if isinstance(value, str) and value == '':
    return None
  if isinstance(value, float) and np.isnan(value):
    return None
  return value

def validate_dt_or_convert_to_datetime_obj(dt):
  if isinstance(dt, datetime.datetime):
    return dt
  elif isinstance(dt, str):
    return dateparser.parse(dt)
  else:
    raise ValueError(f"Invalid datetime object: {dt}")
