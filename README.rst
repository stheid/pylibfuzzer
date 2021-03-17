===========
PyLibFuzzer
===========

| |license| |doc|

.. |license| image:: https://img.shields.io/github/license/stheid/pylibfuzzer
    :target: LICENSE

.. |doc| image:: https://img.shields.io/badge/doc-success-success
    :target: https://stheid.github.io/pylibfuzzer

This project is merely intended for prototyping and used in together with libfuzzer to develop
machine learning based fuzzers that can be automatically evaluated on fuzzbench.

* Free software: GNU General Public License v3
* Documentation: https://stheid.github.io/pylibfuzzer


Installation
------------

::

  $ pip install git+git://github.com/stheid/pylibfuzzer.git


Getting started
---------------

.. code-block:: python

    from pylibfuzzer.exec.runner import main

    if __name__ == '__main__':
        main()