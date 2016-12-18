# coding: utf-8
"""
Package.
"""
from __future__ import absolute_import

# Local imports
from . import aoiklivereload as _aoiklivereload


# Support usage like:
# `from aoiklivereload import LiveReloader`
# instead of:
# `from aoiklivereload.aoiklivereload import LiveReloader`
#
# The use of `getattr` aims to bypass `pydocstyle`'s `__all__` check.
#
# For `aoiklivereload.aoiklivereload`'s each public attribute name
for key in getattr(_aoiklivereload, '__all__'):
    # Store the attribute in this module
    globals()[key] = getattr(_aoiklivereload, key)

# Delete the module reference
del _aoiklivereload
