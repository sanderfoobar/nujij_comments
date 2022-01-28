__version__ = '2.0.0'

import sys
import glob
from setuptools import setup, find_packages, Extension

dushi = Extension('dushi',
                  sources=glob.glob("dushi/*.cpp"),
                  include_dirs=['dushi'],)

setup(
    name='nujij_comments',
    packages=find_packages(),
    version=__version__,
    description='NUjij Comments IRC Live Feed ',
    long_description="NUjij Comments IRC Live Feed ",
    author='sander@sanderf.nl',
    include_package_data=True,
    zip_safe=False,
    ext_modules=[dushi],
    classifiers=[
        'Environment :: Console',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
)
