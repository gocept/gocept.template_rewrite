import lib2to3.refactor

tool = lib2to3.refactor.RefactoringTool(
    lib2to3.refactor.get_fixers_from_package("lib2to3.fixes"))


def rewite_using_2to3(src):
    """Rewrite a python expression using 2to3."""
    consolidated_src = src.lstrip()
    tree = tool.refactor_string(consolidated_src + '\n', "<stdin>")
    result = str(tree)[:-1]
    if result == consolidated_src:
        return src  # include leading white space
    return result
