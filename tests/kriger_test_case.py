import unittest
import numpy as np
from wx_logs.kriger import Kriger

class KrigerTestCase(unittest.TestCase):

  def test_simple_krige(self):
    ul = (-10, 10)
    lr = (10, -10)
    k = Kriger(ul, lr, 1.0)
    k.set_data([[0, 0, 0], [0, 0, 0], [0, 0, 0]])

    # Test the krige method
    output_array = k.interpolate('Exponential', 3, None)

    self.assertEqual(output_array.shape, (21, 21))

    # make sure all the values are zero
    self.assertTrue(np.all(output_array == 0))

  def test_simple_krige_but_data_out_of_bounds(self):
    ul = (-10, 10)
    lr = (10, -10)
    k = Kriger(ul, lr, 1.0)

    # set data should throw exception bc of point 2
    with self.assertRaises(Exception):
      k.set_data([[0, 0, 0], [100, 1000, 0], [0, 0, 0]])

  def test_krige_but_invalid_data_size(self):
    ul = (-10, 10)
    lr = (10, -10)
    k = Kriger(ul, lr, 1.0)

    # set data should throw exception bc of point 2
    with self.assertRaises(Exception):
      k.set_data([[0, 0, 0], [0, 0, 0, 0]])

  def test_3d_kriging_with_simple_data(self):
    ul = (-10, 10, 0)
    lr = (10, -10, 10)
    k = Kriger(ul, lr, 1.0)

    # in this case it is x,y,z,v
    k.set_data([[0, 0, 0, 0], [0, 0, 5, 0], [0, 0, 10, 0]])
    output_array = k.interpolate()
    self.assertEqual(output_array.shape, (21, 21, 11))

    # look at value on the ul layer and confirm zero
    self.assertEqual(output_array[0, 0, 0], 0)

  def test_simple_krige_with_all_100s(self):
    ul = (-10, 10)
    lr = (10, -10)
    k = Kriger(ul, lr, 1.0)
    k.set_data([[0, 0, 100], [1, 1, 100], [2, 0, 100]])
    output_array = k.interpolate()
    self.assertEqual(output_array.shape, (21, 21))

    # make sure all values are around 100
    self.assertTrue(np.all(output_array > 99.999))
    self.assertTrue(np.all(output_array < 101.0000))

  def test_kriged_values_are_correct(self):
    ul = (-10, 10)
    lr = (10, -10)
    k = Kriger(ul, lr, 1.0)
    k.set_data([[0, 0, 100], [1, 1, 100], [2, 0, 100]])
    output_array = k.interpolate()

  def test_kriging_on_a_bigger_grid(self):
    ul = (-10, 10)
    lr = (10, -10)
    k = Kriger(ul, lr, 0.5)
    k.set_data([[-10, 10, 100], [0, 0, 0], [10, -10, 0]])
    output_array = k.interpolate('Exponential', 1, True)
    self.assertEqual(output_array.shape, (41, 41))

    # assert that lower right corner is less than one
    lower_right_corner_value = output_array[-1, -1]
    self.assertLess(lower_right_corner_value, 1)

    # lower left corner should be nan
    lower_left_corner_value = output_array[-1, 0]
    self.assertTrue(np.isnan(lower_left_corner_value))

    # export a geotiff and make sure we get bytes
    geotiff = k.geotiff()
    self.assertTrue(isinstance(geotiff, bytearray))

  def test_kriging_on_linear_gradient(self):
    data = np.array([
      [0, 0, 0],  [1, 0, 1],  
      [0, -1, 1], [1, -1, 2]
    ])
    kriger = Kriger(ul=(0,0), lr=(1,-1), cell_size=1.0)
    kriger.set_data(data)
    result = kriger.interpolate()
    self.assertEqual(result.shape, (2, 2))
    expected = np.array([[0.0, 1.0],[1.0, 2.0]])
    np.testing.assert_almost_equal(result, expected, decimal=1)

    # round result to 1 decimal place
    result = np.round(result, 1)
    np.testing.assert_array_equal(result, expected)

    # make sure all values >= 0 
    self.assertTrue(np.all(result >= 0))

