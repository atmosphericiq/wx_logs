from setuptools import setup, find_packages

setup(
  name='wx_logs',
  version='0.2.15',
  author='Tom Hayden',
  author_email='thayden@gmail.com',
  packages=find_packages(exclude=['tests', 'tests.*']),
  include_package_data=True,
  install_requires=['dateparser', 'numpy', 'pytz'],
  entry_points={
    'console_scripts': [],
  },
)

