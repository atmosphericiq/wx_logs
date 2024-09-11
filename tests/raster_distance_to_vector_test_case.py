import unittest
import numpy as np
from wx_logs.algorithms.raster_distance_to_vector import RasterDistanceToVector
from wx_logs.raster_band import RasterBand
from wx_logs.vector_layer import VectorLayer

class RasterDistanceToVectorTestCase(unittest.TestCase):

  def test_distance_to_vector(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/global.gdem.2022-01.05res.tif')
    b.load_band(1)

    s = VectorLayer()
    s.load_url('https://public-images.engineeringdirector.com/dem/illinois.boundaries.gpkg')

    r = RasterDistanceToVector(b)
    r.calculate_distances(s)

