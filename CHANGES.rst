======================================
Change log for gocept.template_rewrite
======================================

1.1 (2022-04-29)
================

- Convert single quotes used for HTML attributes into double quotes.
  (`#25 <https://github.com/gocept/gocept.template_rewrite/pull/25>`_)

- Add support for Python 3.9 and 3.10.

- Ensure compatibility with ``pytest >= 6.0``.

- Use GHA as CI system.


1.0 (2020-04-07)
================

- Print exact location of error in case of problems parsing Page Templates.

- Add parameter `--collect-errors` that continues to parse all given files and
  prints all found parsing errors but exits with an error and does not replace
  any files if an error was found. This replaces the argument
  `--only-show-errors` present in earlier versions. This allows to create a
  full list of errors to be fixed before a rewrite is possible.

- Add notes about more caveats.

- File discovery now also includes TrustedFSPageTemplate files, which
  are registered with the file ending `.xpt`.
