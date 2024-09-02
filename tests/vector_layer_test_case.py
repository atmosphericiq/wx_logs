import unittest
from osgeo import ogr, osr
from wx_logs import VectorLayer

class VectorLayerTestCase(unittest.TestCase):

  def test_layer_has_name(self):
    layer = VectorLayer()
    layer.createmem('test')
    layer.create_layer('test', 'POINT', 4326)
    self.assertEqual(layer.get_name(), 'test')

  def test_layer_couple_features(self):
    layer = VectorLayer()
    layer.createmem('test')
    layer.create_layer('test', 'POINT', 4326)
    feature1 = layer.blank_feature()
    feature2 = layer.blank_feature()

    # make a osgeo geom
    point = ogr.Geometry(ogr.wkbPoint)
    point.AddPoint(1, 1)
    feature1.SetGeometry(point)
    layer.add_feature(feature1)

    self.assertEqual(layer.get_feature_count(), 1)

    # add another
    point = ogr.Geometry(ogr.wkbPoint)
    point.AddPoint(2, 2)
    feature2.SetGeometry(point)
    layer.add_feature(feature2)

    self.assertEqual(layer.get_feature_count(), 2)

  def test_feature_gets_added_properly(self):
    layer = VectorLayer()
    layer.createmem('test')
    layer.create_layer('test', 'POINT', 4326)
    geom1 = ogr.Geometry(ogr.wkbPoint)
    geom1.AddPoint(1, 1)
    feature1 = layer.blank_feature(geom1)
    added_feature = layer.add_feature(feature1)
    self.assertEqual(layer.get_feature_count(), 1)
    self.assertEqual(geom1.GetX(), feature1.GetGeometryRef().GetX())
    self.assertEqual(geom1.GetY(), feature1.GetGeometryRef().GetY())
    self.assertEqual(geom1.GetX(), added_feature.GetGeometryRef().GetX())
    self.assertEqual(geom1.GetY(), added_feature.GetGeometryRef().GetY())

    # now get the first feature from the layer
    first_feature = layer.get_feature()
    self.assertEqual(first_feature.GetGeometryRef().GetX(), geom1.GetX())
    self.assertEqual(first_feature.GetGeometryRef().GetY(), geom1.GetY())

    # now test the layer extent, which should line up
    (ul, lr) = layer.get_extent()
    self.assertEqual(ul, (1, 1))
    self.assertEqual(lr, (1, 1))

  def test_extent_ul(self):
    layer = VectorLayer()
    layer.createmem('test')
    layer.create_layer('test', 'POINT', 4326)
    point1 = ogr.Geometry(ogr.wkbPoint)
    point1.AddPoint(-1, -1)
    point2 = ogr.Geometry(ogr.wkbPoint)
    point2.AddPoint(2, 2)

    self.assertEqual(point1.GetX(), -1)
    self.assertEqual(point1.GetY(), -1)

    layer.add_feature(layer.blank_feature(point1))
    layer.add_feature(layer.blank_feature(point2))
    self.assertEqual(layer.get_feature_count(), 2)

    (ul, lr) = layer.get_extent()
    self.assertEqual(ul, (-1, 2))
    self.assertEqual(lr, (2, -1))
