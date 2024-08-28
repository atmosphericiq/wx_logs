import unittest
import os
from osgeo import ogr, osr
import numpy as np
import numpy.testing as npt
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

  def test_loading_raster_with_good_values(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    self.assertEqual(b.shape(), (1500, 850))
    self.assertEqual(b.values().shape, (850, 1500)) # numpy shape is rows, cols

  def test_load_raster_with_dem_data(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/global.gdem.2022-01.05res.tif')
    b.load_band(1)
    self.assertEqual(b.get_projection(), 4326)
    self.assertEqual(b.get_nodata(), -9999)
    extent = b.get_extent()
    self.assertAlmostEqual(extent['min_x'], -180.0001389, places=4)
    self.assertAlmostEqual(extent['min_y'], -82.9998611, places=4)
    self.assertAlmostEqual(extent['max_x'], 179.9998611, places=4)
    self.assertAlmostEqual(extent['max_y'], 83.0001389, places=4)
    self.assertAlmostEqual(b.percentage_nodata(), 1.0 - 0.3834, places=2)

  def test_load_Raster_with_dem_do_pgradient_and_write(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/global.gdem.2022-01.05res.tif')
    b.load_band(1)
    b.set_nodata(-9999)
    (gx, gy) = b.central_diff_gradients()
    self.assertEqual(b.shape(), (3600, 1660))

    # and now load this into its own shape and save to file
    b2 = RasterBand()
    b2 = b.clone_with_new_data(gx)
    self.assertEqual(b2.band_count(), 1)
    self.assertEqual(b2.shape(), (3600, 1660))
    b2.write_to_file('/tmp/test_pgradient.tif', True, True)

    # now do the same with y
    b3 = RasterBand()
    b3 = b.clone_with_new_data(gy)
    self.assertEqual(b3.band_count(), 1)
    self.assertEqual(b3.shape(), (3600, 1660))
    b3.write_to_file('/tmp/test_pgradient_y.tif', True, True)

    # load in Y and confirm shape and nodata
    b4 = RasterBand()
    b4.loadf('/tmp/test_pgradient_y.tif')
    b4.set_band(1)
    self.assertEqual(b4.shape(), (3600, 1660))
    self.assertEqual(b4.get_nodata(), -9999)

  def test_load_snow_raster_view_metadata(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    self.assertEqual(b.get_projection(), 4326)
    metadata = b.get_metadata()
    self.assertEqual(metadata['TIFFTAG_XRESOLUTION'], '100')
    self.assertEqual(metadata['TIFFTAG_YRESOLUTION'], '100')

  def test_loading_from_array_with_rectangle_shape(self):
    arr = [[1, 2, 3, 3], [1, 4, 5, 6], [12, 7, 8, 9]]
    b = RasterBand()
    b.load_array(arr)
    self.assertEqual(b.shape(), (4, 3))
    self.assertEqual(b.values().shape, (3, 4))

  def test_make_perioidic_gradients_from_snow_map(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    b.set_nodata(-99999)
    (gx, gy) = b.central_diff_gradients()
    self.assertEqual(b.shape(), (1500, 850))
    self.assertEqual(b.values().shape, (850, 1500)) # opposite bc it calls values() which is rows, cols
    self.assertEqual(gx.shape, (850, 1500)) # opposite bc it calls values() which is rows, cols
    self.assertEqual(gy.shape, (850, 1500)) # opposite bc it calls values() which is rows, cols
  
    # and now load this into its own shape and save to file
    b2 = RasterBand()
    b2.blank_raster(850, 1500, (1,1), (1,1))
    b2.load_array(gx, -99999)
    self.assertEqual(b2.band_count(), 1)
    self.assertEqual(b2.shape(), (1500, 850))
    self.assertAlmostEqual(b2.sum(), 5020.1255, places=4)

  def test_raster_get_grid_value_at_position(self):
    b = RasterBand()
    b.load_array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]])
    self.assertEqual(b.get_grid_value(1, 1), 5.0)

  def test_apply_arbitrary_function_to_cells_with_nodata(self):
    b = RasterBand()
    b.load_array([[1.0, 2.0, 3.0], [4.0, 5.0, -99.0], [7.0, 8.0, 9.0]], -99.0)
    b.apply_function(lambda x: x * 2)
    expected_values = [[2.0, 4.0, 6.0], [8.0, 10.0, np.nan], [14.0, 16.0, 18.0]]
    self.assertTrue(np.isnan(b.get_grid_value(1,2))) 

  def test_make_raster_in_4326_and_get_point(self):
    b = RasterBand()
    b.blank_raster(3, 3, (360/3, 180/3), (-180,90))
    b.set_projection(4326)
    b.load_array([[1.0, 2.0, 3.0], [4.0, -99.0, 6.0], [7.0, 8.0, 9.0]], -99.0)
    self.assertEqual(b.get_projection(), 4326)
    self.assertEqual(b.get_nodata(), -99.0)
    self.assertEqual(b.get_value(-176.0, 75.0), 1.0)
    self.assertEqual(b.get_value(178.0, -75.0), 9.0)
    self.assertEqual(b.get_value(0.0, 0.0), None)

  def test_reproject_map_with_no_projection_throws(self):
    b = RasterBand()
    b.blank_raster(3, 3, (360/3, 180/3), (-180,90))
    b.load_array([[1.0, 2.0, 3.0], [4.0, -99.0, 6.0], [7.0, 8.0, 9.0]], -99.0)
    self.assertRaises(ValueError, b.reproject, 3857)

  def test_extent_from_an_epsg_code(self):
    b = RasterBand()
    b.blank_raster(3, 3, (360/3, 180/3), (-180,90))
    b.set_projection(4326)
    b.load_array([[1.0, 2.0, 3.0], [4.0, -99.0, 6.0], [7.0, 8.0, 9.0]], -99.0)

    # get_extent_from_epsg
    extent = b.get_bounds_from_epsg(4326)
    self.assertEqual(extent, (-180.0, -90.0, 180, 90.0))
    extent_3857 = b.get_bounds_from_epsg(3857)
    self.assertEqual(extent_3857, (-180.0, -85.06, 180.0, 85.06))

  def test_get_extent_for_data(self):
    b = RasterBand()
    b.blank_raster(3, 3, (360/3, 180/3), (-180,90))
    b.set_projection(4326)
    b.load_array([[1.0, 2.0, 3.0], [4.0, -99.0, 6.0], [7.0, 8.0, 9.0]], -99.0)
    extent = b.get_extent()
    self.assertEqual(extent['min_x'], -180.0)
    self.assertEqual(extent['min_y'], -90.0)
    self.assertEqual(extent['max_x'], 180.0)
    self.assertEqual(extent['max_y'], 90.0)

  def test_save_to_file(self):
    r = RasterBand()
    r.blank_raster(3, 3, (1, 1), (1, 1))
    r.load_array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]])
    out_filepath = '/tmp/test.tif'
    r.set_projection(4326)
    r.save_to_file(out_filepath)
    self.assertTrue(os.path.exists(out_filepath))
    #cleanup file
    #os.remove(out_filepath)

  def test_save_to_file_compress_and_overwrite(self):
    r = RasterBand()
    r.blank_raster(3, 3, (1, 1), (1, 1))
    r.load_array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]])
    out_filepath = '/tmp/test_compressed.tif'
    r.set_projection(4326)
    r.save_to_file(out_filepath, True, True)
    self.assertTrue(os.path.exists(out_filepath))
    #os.remove(out_filepath)

  def test_save_to_file_and_load_from_file_check_upper_left(self):
    r = RasterBand()
    r.blank_raster(4, 4, (2, 2), (-4, 4))
    r.load_array([[1.0, 2.0, 3.0, 10.0], 
      [14.0, 11.0, 4.0, 5.0], 
      [15.0, 16.0, 17.0, 18.0],  
      [12.0, 7.0, 8.0, 9.0]])

    # test extents
    extent = r.get_extent()
    bbox = r.get_bbox()
    self.assertEqual((extent['min_x'], extent['max_y']), bbox[0])
    self.assertEqual((extent['max_x'], extent['min_y']), bbox[1])
    self.assertEqual(bbox[0], (-4, 4))
    self.assertEqual(bbox[1], (4, -4))

    # nwo write to file and reload it backin
    out_filepath = '/tmp/test_load_from_file.tif'
    r.set_projection(4326)
    r.save_to_file(out_filepath)

    self.assertTrue(os.path.exists(out_filepath))
    r2 = RasterBand()
    r2.loadf(out_filepath)
    r2.set_band(1)
    self.assertEqual(r2.width(), r.width())
    self.assertEqual(r2.height(), r.height())
    self.assertEqual(r2.get_projection(), 4326)
    npt.assert_array_equal(r.values(), r2.values())
    self.assertEqual(r.get_value(0,0), r2.get_value(0, 0))
    self.assertEqual(r.get_value(3.5, 3.5), 10.0)

  def test_simple_4326_to_3857_reprojection_small_area(self):
    b = RasterBand()
    b.blank_raster(3, 3, (2, 2), (-3, 3))
    b.set_projection(4326)
    b.load_array([[1.0, 2.0, 3.0], [4.0, -99.0, 6.0], [7.0, 8.0, 9.0]], -99.0)
    new_b = b.reproject(3857)
    self.assertEqual(new_b.get_projection(), 3857)
    self.assertEqual(new_b.get_value(0.0, 0.0), None) # dead middle is no data

    # test this by comparing to the actual points projected
    pt = ogr.Geometry(ogr.wkbPoint)
    pt.AddPoint(-3.0, 3.0)
    old_srs = osr.SpatialReference()
    old_srs.ImportFromEPSG(4326)
    old_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    to_srs = osr.SpatialReference()
    to_srs.ImportFromEPSG(3857)
    pt.Transform(osr.CoordinateTransformation(old_srs, to_srs))
    self.assertEqual(pt.GetX(), new_b.get_extent()['min_x'])
    self.assertEqual(pt.GetY(), new_b.get_extent()['max_y'])

  def test_reproject_real_map_from_3857_to_4326(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017_3857.tif')
    b.load_band(1)
    b.set_nodata(-99999)
    new_b = b.reproject(4326)
    self.assertEqual(new_b.get_projection(), 4326)

  def test_reproject_real_map_from_4326_to_3857(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    b.set_nodata(-99999)
    new_b = b.reproject(3857)
    self.assertEqual(new_b.get_projection(), 3857)

  def test_apply_arbitrary_function_to_cells(self):
    b = RasterBand()
    b.load_array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]])
    b.apply_function(lambda x: x * 2)
    expected_values = [[2.0, 4.0, 6.0], [8.0, 10.0, 12.0], [14.0, 16.0, 18.0]]
    npt.assert_array_equal(b.values(), expected_values)

  def test_central_diff_gradients_back_to_raster(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    b.set_nodata(-99999)
    (gx, gy) = b.central_diff_gradients()
    self.assertEqual(b.shape(), (1500, 850))

    # now make a new raster with this as the array input
    b2 = RasterBand()
    b2.blank_raster(850, 1500, (1,1), (1,1))
    b2.load_array(gx, -99999)
    self.assertEqual(b2.band_count(), 1)
    self.assertEqual(b2.shape(), (1500, 850)) # same widths

  def test_rasterband_clone_method_to_make_a_new_one(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    b.set_nodata(-99999)
    (gx, gy) = b.central_diff_gradients()
    self.assertEqual(b.shape(), (1500, 850))

    # now make a new raster with this as the array input
    b2 = b.clone_with_new_data(gx)
    self.assertEqual(b2.band_count(), 1)
    self.assertEqual(b2.shape(), (1500, 850))
    self.assertEqual(b2.get_projection(), 4326)

  def test_rasterband_projection(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    self.assertEqual(b.get_projection(), 4326)

  def test_raster_from_numpy_array(self):
    arr = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    b = RasterBand()
    b.load_array(arr)
    self.assertEqual(b.band_count(), 1)

  def test_raster_from_numpy_array_with_nodata(self):
    arr = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    b = RasterBand()
    b.blank_raster(3, 3, (1,1), (1,1))
    b.load_array(arr, -99)
    self.assertEqual(b.band_count(), 1)
    self.assertEqual(b.get_nodata(), -99)

  def test_central_diff_gradients(self):
    arr = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    b = RasterBand()
    b.load_array(arr)
    grad_y = np.array([[-1.5, -1.5, -1.5],
      [3, 3, 3],
      [-1.5, -1.5, -1.5]])
    grad_x = np.array([[-0.5,  1.0, -0.5],
      [-0.5, 1.0, -0.5],
      [-0.5, 1.0, -0.5]])
    (gx, gy) = b.central_diff_gradients()
    self.assertTrue(np.array_equal(gx, grad_x), "X gradients do not match")
    self.assertTrue(np.array_equal(gy, grad_y), "Y gradients do not match")

  def test_central_diff_gradients_with_nodata(self):
    arr = [[1, 2, 3], [4, -99, 6], [7, 8, 9]]
    b = RasterBand()
    b.blank_raster(3, 3, (1,1), (1,1))
    b.load_array(arr, -99.0)
    self.assertEqual(b.get_projection(), None)
    grad_y = np.array([[-1.5, np.nan, -1.5],
      [3, 3.0, 3],
      [-1.5, np.nan, -1.5]])
    grad_x = np.array([[-0.5,  1.0, -0.5],
      [np.nan, 1.0, np.nan],
      [-0.5, 1.0, -0.5]])
    (gx, gy) = b.central_diff_gradients()
    self.assertTrue(np.allclose(gx, grad_x, equal_nan=True),
      "X gradients do not match")
    self.assertTrue(np.allclose(gy, grad_y, equal_nan=True), 
      "Y gradients do not match")

  def test_central_diff_grads_with_nodata_on_edge(self):
    arr = [[1, 2, 3], [4, 5, 6], [7, 8, -99.0]]
    b = RasterBand()
    b.blank_raster(3, 3, (1,1), (1,1))
    b.load_array(arr, -99.0)
    grad_y = np.array([[-1.5, -1.5, np.nan],
      [3, 3, np.nan],
      [-1.5, -1.5, -1.5]])
    grad_x = np.array([[-0.5,  1.0, -0.5],
      [-0.5, 1.0, -0.5],
      [np.nan, np.nan, -0.5]])
    (gx, gy) = b.central_diff_gradients()
    self.assertTrue(np.allclose(gx, grad_x, equal_nan=True), "X gradients do not match")
    self.assertTrue(np.allclose(gy, grad_y, equal_nan=True), "Y gradients do not match")

  def test_raster_gradients(self):
    arr = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    b = RasterBand()
    b.load_array(arr)
    grad_y = [[1, 1, 1], [1, 1, 1], [1, 1, 1]]
    grad_x = [[3, 3, 3], [3, 3, 3], [3, 3, 3]]
    (gx, gy) = b.gradients()
    self.assertTrue(np.array_equal(gx, grad_x), "X gradients do not match")
    self.assertTrue(np.array_equal(gy, grad_y), "Y gradients do not match")

  def test_raster_sum_array_with_nodatas(self):
    arr = [[1, 1, 1], [4, 4, 4], [1, 1, -99.0]]
    b = RasterBand()
    b.blank_raster(3, 3, (1,1), (1,1))
    b.set_band(1)
    b.load_array(arr, -99.0)
    self.assertEqual(b.sum(), 17)

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
