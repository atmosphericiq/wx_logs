def test_zero_null_real_precipitation_values(self):
    a = WeatherStation('STATION')
    dt = datetime.datetime(2020, 1, 1, 0, 0, 0)
    # Add a mix of 0, None, and real values
    a.add_precipitation_mm(10, 60, dt)
    a.add_precipitation_mm(0, 60, dt + datetime.timedelta(hours=1))
    a.add_precipitation_mm(None, 60, dt + datetime.timedelta(hours=2))
    a.add_precipitation_mm(5, 60, dt + datetime.timedelta(hours=3))
    a.add_precipitation_mm('', 60, dt + datetime.timedelta(hours=4))
    a.add_precipitation_mm(np.nan, 60, dt + datetime.timedelta(hours=5))

    # Expected total is 15 (10 + 0 + 5 + 0 + 0)
    self.assertEqual(a.get_precipitation_mm('SUM'), 15)

    # Expected mean is (10 + 0 + 5)/5 due to valid hours
    self.assertAlmostEqual(a.get_precipitation_mm('MEAN'), 3.0, places=1)
