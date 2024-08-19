import unittest
from wx_logs import RasterBand

class RasterBandTestCase(unittest.TestCase):

  def test_RasterBand(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    self.assertEqual(b.band_count(), 1)

  def test_file_does_not_exist(self):
    b = RasterBand()
    self.assertRaises(ValueError, b.load_url,
      'https://public-images.engineeringdirector.com/dem/snowfall.2017bad.tif')

  def test_loading_band_not_there(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    self.assertEqual(b.band_count(), 1)
    self.assertRaises(ValueError, b.load_band, 2)

  def test_raster_from_numpy_array(self):
    arr = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    b = RasterBand()
    b.load_array(arr)
    self.assertEqual(b.band_count(), 1)

  def test_raster_from_numpy_array_with_nodata(self):
    arr = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    b = RasterBand()
    b.load_array(arr, (1,1), (1,1), -99)
    self.assertEqual(b.band_count(), 1)
    self.assertEqual(b.get_nodata(), -99)

  # Upper Left  (-126.0000000,  55.0000000) (126d 0' 0.00"W, 55d 0' 0.00"N)
  # Lower Left  (-126.0000000,  21.0000000) (126d 0' 0.00"W, 21d 0' 0.00"N)
  # Upper Right ( -66.0000000,  55.0000000) ( 66d 0' 0.00"W, 55d 0' 0.00"N)
  # Lower Right ( -66.0000000,  21.0000000) ( 66d 0' 0.00"W, 21d 0' 0.00"N)
  # Center      ( -96.0000000,  38.0000000) ( 96d 0' 0.00"W, 38d 0' 0.00"N)
  def test_get_coordinates(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    self.assertEqual(b.band_count(), 1)
    (ul, lr) = b.get_bbox()
    self.assertEqual(ul, (-126.0, 55.0))
    self.assertEqual(lr, (-66.0, 21.0))

  def test_get_center(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    self.assertEqual(b.band_count(), 1)
    (center_x, center_y) = b.get_center()
    self.assertEqual(center_x, -96.0)
    self.assertEqual(center_y, 38.0)
 
  # -88.6111, 47.1472 = None
  def test_get_value_at_location_with_nodata(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    self.assertEqual(b.band_count(), 1)
    b.set_nodata(-99999)
    value = b.get_value(-88.6111, 47.1472)
    self.assertEqual(value, None)

  # -88.4888, 48.1410 = 73.42019
  def test_get_value_at_location(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    self.assertEqual(b.band_count(), 1)
    value = b.get_value(-88.4888, 48.1410)
    self.assertEqual(value, 73.42019)

  # -97.449, 26.008 = 0 snow
  def test_get_value_at_location_with_zero(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    self.assertEqual(b.band_count(), 1)
    value = b.get_value(-97.449, 26.008)
    self.assertEqual(value, 0)

  def test_get_value_at_location(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    self.assertEqual(b.band_count(), 1)
    value = b.get_value(-95.724, 48.546)
    self.assertAlmostEqual(value, 47.079227, places=2)

  # -94.096, 48.973 = None
  def test_get_value_at_location_with_nodata_weird(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    self.assertEqual(b.band_count(), 1)
    b.set_nodata(-99999)
    value = b.get_value(-94.096, 48.973)
    self.assertEqual(value, None)

  def test_load_band_get_size(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    self.assertEqual(b.band_count(), 1)
    size = b.shape()
    self.assertEqual(size, (1500, 850))

  def test_nodata_value(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    self.assertEqual(b.get_nodata(), -99999)
    b.set_nodata(None)
    self.assertEqual(b.get_nodata(), None)

  # 0,0 should be null because it is a corner and set as nodata
  def test_get_value_outside_bounds_throws_exception(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    self.assertEqual(b.band_count(), 1)
    self.assertRaises(ValueError, b.get_value, 0, 0)

  def test_get_shape_but_didnt_load_band(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    self.assertRaises(ValueError, b.shape)
