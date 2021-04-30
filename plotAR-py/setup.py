#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.md') as readme_file:
    readme = readme_file.read()

with open('HISTORY.md') as history_file:
    history = history_file.read()

requirements = [ 'pandas', 'numpy', 'requests', 'tornado', 'pyqrcode', 'click', 'usd-core', ]

setup_requirements = ['pytest-runner', 'scikit-learn', 'jupyterlab', 'skyfield', 'beautifulsoup4', ]

test_requirements = ['pytest', ]

setup(
    author="Philipp Thomann",
    author_email='pht@gmx.ch',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    description="Walk through your data",
    install_requires=requirements,
    license="Affero GPL 3",
    long_description=readme + '\n\n' + history,
    long_description_content_type='text/markdown',
    include_package_data=True,
    keywords='plotar',
    name='plotar',
    packages=find_packages(include=['plotar']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/thomann/plotAR ',
    version='0.8.1',
    data_files=[
        ('etc/jupyter/jupyter_notebook_config.d', ['plotar/etc/plotar-server-extension.json']),
    ],
    zip_safe=False,
)
