from gocept.template_rewrite.dtml import DTMLRegexRewriter
from gocept.template_rewrite.lib2to3 import rewrite_using_2to3
from gocept.template_rewrite.pagetemplates import PTParserRewriter
import argparse
import logging
import os
import os.path
import pdb  # noqa


log = logging.getLogger(__name__)


parser = argparse.ArgumentParser(
    description='Rewrite Python expressions in DTML and ZPT template files.')
parser.add_argument('path', type=str, default='.',
                    help='path to look for *.dtml, *.pt and *.sql files')
parser.add_argument('--keep_files', action='store_true',
                    help='keep the original files, create *.out files instead')
parser.add_argument('-D', '--debug', action='store_true',
                    help='enter debugger on errors')


class FileHandler(object):
    """Handle the rewrite of batches of files."""

    dtml_files = []
    zpt_files = []
    output_files = []

    def _rewrite_action(self, input_string, *args, **kwargs):
        """Use the default action: `rewrite_using_2to3`.

        Can be overwritten at __init__.
        """
        return rewrite_using_2to3(input_string, *args, **kwargs)

    def __init__(self, path, keep_files=False, rewrite_action=None):
        self.path = path
        if rewrite_action:
            self.rewrite_action = rewrite_action
        else:
            self.rewrite_action = self._rewrite_action
        self.keep_files = keep_files

    def __call__(self):
        self.collect_files(self.path)
        self.process_files()
        if not self.keep_files:
            self.replace_files()

    def collect_files(self, path):
        for root, dirs, files in os.walk(path):
            for file_ in files:
                if file_.endswith('.dtml') or file_.endswith('.sql'):
                    self.dtml_files.append(os.path.join(root, file_))
                if file_.endswith('.pt'):
                    self.zpt_files.append(os.path.join(root, file_))

    def _process_file(self, file_, rewriter):
        """Process one file."""
        file_out = file_ + '.out'
        with open(file_, 'r') as input_file, \
                open(file_out, 'w', encoding='utf-8') as output_file:
            log.warning('Processing %s', file_)
            try:
                rw = rewriter(
                    input_file.read(), self.rewrite_action, filename=file_)
            except UnicodeDecodeError:
                log.error('Error', exc_info=True)
            else:
                output_file.write(rw())
                self.output_files.append(file_out)

    def process_files(self):
        """Process all collected files."""
        for file_ in self.dtml_files:
            self._process_file(file_, DTMLRegexRewriter)
        for file_ in self.zpt_files:
            self._process_file(file_, PTParserRewriter)

    def replace_files(self):
        for file_ in self.output_files:
            os.rename(file_, file_[:-4])


def main():
    """Act as an entry point."""
    args = parser.parse_args()
    fh = FileHandler(args.path, args.keep_files)
    try:
        fh()
    except Exception:
        if args.debug:
            pdb.post_mortem()
        raise
