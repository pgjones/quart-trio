import os

from setuptools import setup, find_packages

PROJECT_ROOT = os.path.dirname(__file__)

with open(os.path.join(PROJECT_ROOT, 'README.rst')) as file_:
    long_description = file_.read()

INSTALL_REQUIRES = [
    'hypercorn[trio] >= 0.6.0',
    'quart >= 0.14.0',
    'trio >= 0.9.0',
]

setup(
    name='Quart-Trio',
    version='0.7.0',
    python_requires='>=3.7.0',
    description="A Quart extension to provide trio support.",
    long_description=long_description,
    url='https://gitlab.com/pgjones/quart-trio/',
    author='P G Jones',
    author_email='philip.graham.jones@googlemail.com',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    packages=find_packages("src"),
    package_dir={"": "src"},
    py_modules=['quart_trio'],
    install_requires=INSTALL_REQUIRES,
    tests_require=INSTALL_REQUIRES + [
        'pytest',
        'pytest-trio',
    ],
    include_package_data=True,
)
