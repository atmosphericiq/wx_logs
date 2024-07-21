import unittest
from wx_logs import file_storage

class FileStorageTestCase(unittest.TestCase):

  def test_file_storage(self):
    f = 'https://public-images.engineeringdirector.com/dem/snowfall.2017.tif'
    s = file_storage()
    s.set_file_url(f)
    s.download()
    self.assertEqual(s.get_file_name(), 'snowfall.2017.tif')
    
    # test that the file is downloaded
    #-rw-rw-r-- 1 tom tom 4919964 Jul 20 17:36 /tmp/snowfall.2017.tif
    self.assertEqual(s.get_file_size(), 4919964)

  def test_file_storage_with_expected_md5_hash(self):
    f = 'https://public-images.engineeringdirector.com/dem/snowfall.2017.tif'
    s = file_storage()
    s.set_file_url(f)
    s.set_expected_md5_hash('6f3da1356a9992c1348c384f87b3ef6d')
    s.download()
    self.assertEqual(s.get_md5_hash(), '6f3da1356a9992c1348c384f87b3ef6d')

  def test_bad_url_throws_exception(self):
    f = 'https://public-images.engineeringdirector.com/dem/snowfall.2017bad.tif'
    s = file_storage()
    s.set_file_url(f)
    self.assertRaises(ValueError, s.download)

  def test_file_storage_with_bad_expected_md5_hash(self):
    f = 'https://public-images.engineeringdirector.com/dem/snowfall.2017.tif'
    s = file_storage()
    s.set_file_url(f)
    s.set_expected_md5_hash('BAD HASH')
    self.assertRaises(ValueError, s.download)

  def test_md5_hash_of_the_file(self):
    f = 'https://public-images.engineeringdirector.com/dem/snowfall.2017.tif'
    s = file_storage()
    s.set_file_url(f)
    s.download()
    self.assertEqual(s.get_md5_hash(), '6f3da1356a9992c1348c384f87b3ef6d')

  def test_file_storage_always_download_so_deletes_old_file(self):
    f = 'https://public-images.engineeringdirector.com/test/prism.tif'
    s = file_storage()
    s.set_expected_md5_hash('e4d80e4c5b8be08045119f56a558f323')
    s.set_file_url(f)
    s.delete_file()

    # now download the file
    s.download()
    self.assertEqual(s.get_md5_hash(), 'e4d80e4c5b8be08045119f56a558f323')
