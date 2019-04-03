from gocept.template_rewrite.dtml import DTMLRegexRewriter
from gocept.template_rewrite.lib2to3 import rewrite_using_2to3
from gocept.template_rewrite.pagetemplates import PTParserRewriter
from gocept.template_rewrite.pagetemplates import PTParseError
import argparse
import logging
import os
import os.path
import pathlib
import pdb  # noqa


log = logging.getLogger(__name__)


parser = argparse.ArgumentParser(
    description='Rewrite Python expressions in DTML and ZPT template files.')
parser.add_argument('paths', type=str, nargs='+', metavar='path',
                    help='paths of files which should be rewritten or '
                    'directories containing such files')
parser.add_argument('--keep-files', action='store_true',
                    help='keep the original files, create *.out files instead')
parser.add_argument('--only-check-syntax', action='store_true',
                    help='Do not convert but only report syntax errors in'
                    ' the sources')
parser.add_argument('--force', choices=['pt', 'dtml'], default=None,
                    help='Treat all files as PageTemplate (pt) resp.'
                    'DocumentTemplate (dtml).')
parser.add_argument('-D', '--debug', action='store_true',
                    help='enter debugger on errors')


class FileHandler(object):
    """Handle the rewrite of batches of files."""

    def __init__(self, paths, settings):
        self.dtml_files = []
        self.zpt_files = []
        self.output_files = []
        self.paths = paths
        self.keep_files = settings.keep_files
        self.only_check_syntax = settings.only_check_syntax
        self.force_type = settings.force

    def __call__(self):
        for path in self.paths:
            self.collect_files(pathlib.Path(path))
        self.process_files()
        if not self.keep_files and not self.only_check_syntax:
            self.replace_files()

    def rewrite_action(self, input_string, *args, **kwargs):
        """Use `rewrite_using_2to3` as default action.

        Can be overwritten in subclass.
        """
        return rewrite_using_2to3(input_string, *args, **kwargs)

    def collect_files(self, path):
        if path.is_dir():
            for root, dirs, files in os.walk(str(path)):
                for file_ in files:
                    self._classify_file(pathlib.Path(root, file_))
        else:
            self._classify_file(path)

    def _classify_file(self, path):
        if self.force_type == 'dtml':
            self.dtml_files.append(path)
        elif self.force_type == 'pt':
            self.zpt_files.append(path)
        elif path.suffix in ('.dtml', '.sql'):
            self.dtml_files.append(path)
        elif path.suffix in ('.pt', '.html'):
            self.zpt_files.append(path)

    def _process_file(self, path, rewriter):
        """Process one file."""
        log.warning('Processing %s', path)
        try:
            rw = rewriter(
                path.read_text(), self.rewrite_action, filename=str(path))
        except UnicodeDecodeError:  # pragma: no cover
            log.error('Error', exc_info=True)
        else:
            try:
                result = rw()
            except PTParseError as err:
                if err.filename is None:
                    err.filename = path
                err.print()
                if not self.only_check_syntax:
                    raise
            except Exception:
                log.error('Uncaught error in %s', path)
                raise

            if not self.only_check_syntax:
                file_out = pathlib.Path(str(path) + '.out')
                file_out.write_text(result, encoding='utf-8')
                self.output_files.append(file_out)

    def process_files(self):
        """Process all collected files."""
        for file_ in self.dtml_files:
            self._process_file(file_, DTMLRegexRewriter)
        for file_ in self.zpt_files:
            self._process_file(file_, PTParserRewriter)

    def replace_files(self):
        for path in self.output_files:
            path.rename(path.parent / path.stem)


def main(args=None):
    """Act as an entry point."""
    args = parser.parse_args(args)
    fh = FileHandler(args.paths, args)
    try:
        fh()
    except Exception:  # pragma: no cover
        if args.debug:
            pdb.post_mortem()
        raise
