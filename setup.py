# coding: utf-8
"""
Setup module.
"""
from __future__ import absolute_import

# External imports
from setuptools import find_packages
from setuptools import setup


# Run setup
setup(
    name='AoikLiveReload',

    version='0.1.0',

    description=(
        'Detect module file changes and reload the program.'
    ),

    long_description="""`Documentation on Github
<https://github.com/AoiKuiyuyou/AoikLiveReload>`_""",

    url='https://github.com/AoiKuiyuyou/AoikLiveReload',

    author='Aoi.Kuiyuyou',

    author_email='aoi.kuiyuyou@google.com',

    license='MIT',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
    ],

    keywords='live reload',

    package_dir={
        '': 'src'
    },

    packages=find_packages('src'),

    include_package_data=True,

    install_requires=[
        'watchdog >= 0.8.3',
    ],
)
