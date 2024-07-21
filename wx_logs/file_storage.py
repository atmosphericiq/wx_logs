# file_storage.py
# this is a file storage class which is used to download
# a file from a URL and store it locally
# it also has a method to check the md5 hash of the file
# and if it doesn't match, it will raise an exception
# author: Tom Hayden

import json
import hashlib
import os
import platform
import logging
import datetime
import requests

logger = logging.getLogger(__name__)

class FileStorage:

  def __init__(self):
    self.set_cache_dir()
    self.file_url = None
    self.expected_md5_hash = None
    self.basename = None

  def get_cache_dir(self):
    return self.cache_dir

  def set_file_url(self, file_url):
    self.file_url = file_url

    # figure out the basename from the http url
    self.basename = os.path.basename(self.file_url)

  def set_cache_dir(self):
    if platform.system() == 'Windows':
      self.cache_dir = os.getenv('LOCALAPPDATA')
    else:
      self.cache_dir = os.path.expanduser('~/.cache')
    self.cache_dir = os.path.join(self.cache_dir, 'wx_logs')
    if not os.path.exists(self.cache_dir):
      os.makedirs(self.cache_dir)
 
  def get_full_path_to_file(self):
    return os.path.join(self.cache_dir, self.basename)

  def set_expected_md5_hash(self, md5_hash):
    self.expected_md5_hash = md5_hash

  # return ONLY the basename of the file
  def get_file_name(self):
    return self.basename

  def get_file_size(self):
    return os.path.getsize(self.get_full_path_to_file())

  # md5 hash of the file
  def get_md5_hash(self):
    file_path = self.get_full_path_to_file()
    with open(file_path, 'rb') as f:
      return hashlib.md5(f.read()).hexdigest()

  def delete_file(self):
    file_name = self.get_file_name()
    if os.path.exists(file_name):
      os.remove(file_name)

  # this the main call to download the file, but we should also 
  # make sure to see if it's already there and if so, check the md5 hash
  # and in that case just return bc we are ok
  def download(self):
    if self.file_url is None:
      raise ValueError("No file URL set. call set_file_url()")
    file_name = self.get_full_path_to_file()
    if os.path.exists(file_name):
      if self.expected_md5_hash is not None:
        actual_md5_hash = self.get_md5_hash()
        if actual_md5_hash != self.expected_md5_hash:
          raise ValueError(f"MD5 hash mismatch for file: {self.file_url}")
      return
    logger.info(f"Downloading file: {self.file_url}")
    response = requests.get(self.file_url)
    if response.status_code != 200:
      raise ValueError(f"Invalid response code: {response.status_code}")

    with open(file_name, 'wb') as f:
      f.write(response.content)
    logger.info(f"Downloaded file: {self.file_url}")

    if self.expected_md5_hash is not None:
      actual_md5_hash = self.get_md5_hash()
      if actual_md5_hash != self.expected_md5_hash:
        raise ValueError(f"MD5 hash mismatch for file: {self.file_url}")
