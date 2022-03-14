from setuptools import setup, find_packages

setup(
    name='pylibfuzzer',
    version='0.0.7',
    packages=find_packages(),
    include_package_data=True,

    author='Stefan Heid',
    author_email='stefan.heid@upb.de',
    description='Python implementation of test case generation to interface with libfuzzer which will handle the execution',
    long_description=open('README.rst').read(),
    entry_points={'console_scripts': [
        'pylibfuzzer = pylibfuzzer.exec.runner:main ',
    ]},
    license='GPLv3',
    keywords='libfuzzer, fuzzing',
    url='https://github.com/stheid/pylibfuzzer',
    install_requires=open('requirements.txt').read(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.8',
        'Development Status :: 2 - Pre-Alpha',
        'Operating System :: POSIX :: Linux',
        'Topic :: Security',
        'Topic :: Software Development :: Bug Tracking',
        'Framework :: Sphinx'
    ]
)
