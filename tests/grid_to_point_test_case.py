import unittest
import numpy as np
from wx_logs.algorithms.grid_to_point import GridToPoint
from wx_logs.raster_band import RasterBand
from wx_logs.vector_layer import VectorLayer

class GridToPointTestCase(unittest.TestCase):

  def test_simple_conversion(self):
    b = RasterBand()
    b.blank_raster(3, 3, (360/3, 180/3), (-180,90))
    b.set_projection_epsg(4326)
    b.load_array([[1.0, 2.0, 3.0], [4.0, 99.0, 6.0], [7.0, 8.0, 9.0]], -99.0)

    gtp = GridToPoint(b)
    vector_file = gtp.to_vector()
    
    # count the features, should be 9
    self.assertEqual(vector_file.get_feature_count(), 9)

  def test_simple_conversion_with_a_nodata_point(self):
    b = RasterBand()
    b.blank_raster(3, 3, (360/3, 180/3), (-180,90))
    b.set_projection_epsg(4326)
    b.load_array([[1.0, 2.0, 3.0], [4.0, -99.0, 6.0], [7.0, 8.0, 9.0]], -99.0)

    gtp = GridToPoint(b)
    vector_file = gtp.to_vector()
    
    self.assertIsInstance(vector_file, VectorLayer)
    
    # count the points, should be 8
    self.assertEqual(vector_file.get_feature_count(), 8)

  def test_with_a_real_snow_raster(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    gtp = GridToPoint(b)
    vector_file = gtp.to_vector()

    self.assertIsInstance(vector_file, VectorLayer)
    self.assertLess(vector_file.get_feature_count(), b.size()) # fewer points than whole grid
    self.assertGreater(vector_file.get_feature_count(), 0) # more than 0 points
