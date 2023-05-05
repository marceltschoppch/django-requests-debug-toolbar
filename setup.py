import os

from setuptools import find_packages, setup


with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

# Allow setup.py to be run from any directory
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

version = __import__('requests_panel').__version__

setup(
    name='django-requests-debug-toolbar',
    version=version,
    packages=find_packages(),
    include_package_data=True,
    install_requires=(
        'django-debug-toolbar>=2.2',
    ),
    license='MIT',
    description='A Django Debug Toolbar panel for Requests',
    keywords='django django-debug-toolbar requests debug toolbar',
    long_description=README,
    url='https://github.com/marceltschoppch/django-requests-debug-toolbar',
    author='Marcel Tschopp',
    author_email='info@marceltschopp.ch',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 2.2',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
)
