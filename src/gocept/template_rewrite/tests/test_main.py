from ..main import main
import pathlib
import pkg_resources
import pytest
import shutil

FIXTURE_DIR = pkg_resources.resource_filename(
    'gocept.template_rewrite.tests', 'fixture')


@pytest.fixture('function')
def files(tmpdir):
    dir = str(tmpdir.join('fixture'))
    shutil.copytree(FIXTURE_DIR, dir)
    yield pathlib.Path(dir)


def test_main__main__1(files, caplog):
    """It converts all files in the given directory."""
    main([str(files)])
    assert ['broken.pt',
            'one.pt',
            'two.dtml'] == sorted(x.name for x in files.iterdir())
    assert caplog.text.count('Processing') == 3
    assert caplog.text.count('Parsing error') == 1


def test_main__main__2(files):
    """It does not touch the original files on `--keep-files`."""
    main([str(files), '--keep-files'])
    assert [
        'broken.pt',
        'broken.pt.out',
        'one.pt',
        'one.pt.out',
        'two.dtml',
        'two.dtml.out',
    ] == sorted(x.name for x in files.iterdir())
    for file in pathlib.Path(FIXTURE_DIR).iterdir():
        source = file.read_text()
        dest = files.joinpath(file.name).read_text()
        assert dest == source
