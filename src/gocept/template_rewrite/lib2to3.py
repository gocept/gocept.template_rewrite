import lib2to3.pgen2.parse
import lib2to3.refactor
import logging


log = logging.getLogger(__name__)


tool = lib2to3.refactor.RefactoringTool(
    lib2to3.refactor.get_fixers_from_package("lib2to3.fixes"))


def rewrite_using_2to3(src):
    """Rewrite a python expression using 2to3."""
    consolidated_src = src.lstrip()
    try:
        tree = tool.refactor_string(consolidated_src + '\n', "<stdin>")
    except lib2to3.pgen2.parse.ParseError:
        log.error('*** SyntaxError: Cannot parse: %r', src, exc_info=True)
        raise
    result = str(tree)[:-1]
    if result == consolidated_src:
        return src  # include leading white space
    return result
