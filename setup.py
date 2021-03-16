from setuptools import setup

setup(
    name='TODO',
    version="0.0.1",
    packages=['TODO'],
    author="TODO",
    author_email="TODO",
    description="TODO",
    long_description=open('README.rst').read(),
    license="GPLv3",
    keywords="TODO",
    url="https://github.com/stheid/ TODO",
    entry_points={
        'console_scripts': [
            'fuzz_proj = fuzzer.exec.runner:main',
        ]
    },
    install_requires=open('requirements.txt').read(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
    ]
)
