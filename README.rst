=======================
gocept.template_rewrite
=======================

.. image:: https://travis-ci.org/gocept/gocept.template_rewrite.svg?branch=master
    :target: https://travis-ci.org/gocept/gocept.template_rewrite

.. image:: https://coveralls.io/repos/github/gocept/gocept.template_rewrite/badge.svg
    :target: https://coveralls.io/github/gocept/gocept.template_rewrite

A tool to rewrite parts of template files (DTML, ZPT and XPT).

The initial use case is to have a pluggable system to convert Python 2
expressions in templates to Python 3.

This package runs on Python 3.6 and 3.7.


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
