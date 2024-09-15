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

    r = RasterDistanceToVector(b)
    new_band = r.calculate_distances(s)

    self.assertEqual(new_band.width(), b.width())
    #self.assertEqual(new_band.sum(), 1000)

    # lat/lng for champaign, il
    lat = 40.1164
    lng = -88.2434
    new_band_value = new_band.get_value(lng, lat)
    self.assertEqual(new_band_value, 0)
