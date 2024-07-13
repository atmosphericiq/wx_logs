from setuptools import setup, find_packages

setup(
  name='wx_logs',  # Replace with your project name
  version='0.1',
  packages=find_packages(),
  install_requires=[
    'dateparser', 
    'numpy', 
    'logging', 
    'pytz'],
  entry_points={
    'console_scripts': [],
  },
)

