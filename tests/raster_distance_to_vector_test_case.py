import unittest
import numpy as np
from wx_logs.algorithms.raster_distance_to_vector import RasterDistanceToVector
from wx_logs.raster_band import RasterBand
from wx_logs.vector_layer import VectorLayer

class RasterDistanceToVectorTestCase(unittest.TestCase):

  def test_distance_to_vector(self):
    b = RasterBand()
    b.load_url('s3://public-images.engineeringdirector.com/dem/snowfall.2017.lowres.tif')
    b.load_band(1)

    s = VectorLayer()
    s.load_url('https://public-images.engineeringdirector.com/dem/illinois.boundaries.gpkg')

    # total map is 600 cols wide
    self.assertEqual(b.width(), 600)
  
    r = RasterDistanceToVector(b, 4)
    new_band = r.calculate_distances(s, 8.0)
    self.assertEqual(new_band.width(), b.width())

    # lat/lng for champaign, il
    lat = 40.1164
    lng = -88.2434
    new_band_value = new_band.get_value(lng, lat)
    self.assertEqual(new_band_value, 0)

    # lat/lng for milwaukee
    lat = 43.0389
    lng = -87.9065
    new_band_value = new_band.get_value(lng, lat)
    self.assertEqual(new_band_value, 0.5551733374595642)

    # now write to file
    new_band.save_to_file('/tmp/distance.tif')
