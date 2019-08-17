import lib2to3.pgen2.parse
import lib2to3.refactor
import logging


log = logging.getLogger(__name__)

fixes = lib2to3.refactor.get_fixers_from_package('lib2to3.fixes')
fixes = [f for f in fixes if not f.endswith('fix_next')]

tool = lib2to3.refactor.RefactoringTool(fixes)


def rewrite_using_2to3(src, lineno, tag, filename):
    """Rewrite a python expression using 2to3.

    All fixers except `fix_next` are used. This one would change `iter.next()`
    to next(iter)`. In Zope are some objects which implement a proper `.next()`
    without being and iterator.
    """
    consolidated_src = src.lstrip()
    tree = tool.refactor_string(consolidated_src + '\n', "<stdin>")
    result = str(tree)[:-1]
    if result == consolidated_src:
        return src  # include leading white space
    return result
