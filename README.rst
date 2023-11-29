=======================
gocept.template_rewrite
=======================

.. caution::
  This is package is archived as gocept does maintain it anymore. If you
  are interested in working with it, please contact mail@gocept.com or the
  contributors to get the respective permissions.


.. image:: https://img.shields.io/pypi/v/gocept.template_rewrite.svg
    :target: https://pypi.org/project/gocept.template_rewrite/

.. image:: https://img.shields.io/pypi/pyversions/gocept.template_rewrite.svg
    :target: https://pypi.org/project/gocept.template_rewrite/

.. image:: https://github.com/gocept/gocept.template_rewrite/workflows/tests/badge.svg
    :target: https://github.com/gocept/gocept.template_rewrite/actions?query=workflow%3Atests

.. image:: https://coveralls.io/repos/github/gocept/gocept.template_rewrite/badge.svg
    :target: https://coveralls.io/github/gocept/gocept.template_rewrite

A tool to rewrite parts of template files (DTML, ZPT and XPT).

The initial use case is to have a pluggable system to convert Python 2
expressions in templates to Python 3.

This package runs on Python 3.6 up to 3.10.


Requirements
============

For the rewrite to work properly, it is necessary to have this structure
``attr="value"`` for attributes in tags with no whitespaces around the ``=``,
as otherwise the values will get lost.

Caveats
=======

- During rewrite double hyphens within HTML-comments are removed as the Chameleon
  engine in Zope 4 (and the `actual specification`_) is very strict about it.

- The underlying lib2to3 does not take into account, that the `cmp` function
  is no longer available in Python 3.

- This tool converts Python 2 to Python 3 - that means the code may not be
  compatible with Python 2 any more. For these edge cases manual changes are required to make it
  compatible with both versions.

.. _actual specification: http://www.htmlhelp.com/reference/wilbur/misc/comment.html
