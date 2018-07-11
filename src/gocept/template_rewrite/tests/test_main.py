from ..main import main
import os
import pkg_resources
import shutil


def test_main__main__1(tmpdir, caplog):
    """It converts all files in the given directory."""
    dir = str(tmpdir.join('fixture'))
    shutil.copytree(
        pkg_resources.resource_filename(
            'gocept.template_rewrite.tests', 'fixture'), dir)
    main([dir])
    assert ['broken.pt',
            'one.pt',
            'two.dtml'] == sorted(os.listdir(dir))
    assert caplog.text.count('Processing') == 3
    assert caplog.text.count('Parsing error') == 1
