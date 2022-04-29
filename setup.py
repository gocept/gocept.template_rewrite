# This should be only one line. If it must be multi-line, indent the second
# line onwards to keep the PKG-INFO file format intact.
"""A tool to rewrite parts of template files (DTML, ZPT).
"""

from setuptools import find_packages
from setuptools import setup
import glob


setup(
    name='gocept.template_rewrite',
    version='1.1',

    python_requires='>=3.6, <4',
    install_requires=[
        'setuptools',
    ],

    extras_require={
        'test': [
            'pytest',
            'pytest-mock',
        ],
    },

    entry_points={
        'console_scripts': [
            'template-rewrite = gocept.template_rewrite.main:main'
        ],
    },

    author='gocept <mail@gocept.com>',
    author_email='mail@gocept.com',
    license='MIT',
    url='https://github.com/gocept/gocept.template_rewrite/',

    keywords='Zope DTML ZPT pagetemplates migrate Python 3',
    classifiers="""\
Development Status :: 4 - Beta
Framework :: Zope
Intended Audience :: Developers
License :: OSI Approved
License :: OSI Approved :: MIT License
Operating System :: OS Independent
Programming Language :: Python
Programming Language :: Python :: 3
Programming Language :: Python :: 3 :: Only
Programming Language :: Python :: 3.6
Programming Language :: Python :: 3.7
Programming Language :: Python :: 3.8
Programming Language :: Python :: 3.9
Programming Language :: Python :: 3.10
Programming Language :: Python :: Implementation :: CPython
Topic :: Text Processing :: Filters
"""[:-1].split('\n'),
    description=__doc__.strip(),
    long_description='\n\n'.join(open(name).read() for name in (
        'README.rst',
        'HACKING.rst',
        'CHANGES.rst',
    )),

    namespace_packages=['gocept'],
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    data_files=[('', glob.glob('*.txt')),
                ('', glob.glob('*.rst'))],
    zip_safe=False,
)
