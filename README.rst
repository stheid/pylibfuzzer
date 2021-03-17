===========
PyLibFuzzer
===========

| |license| |doc|

.. |license| image:: https://img.shields.io/github/license/stheid/pylibfuzzer
    :target: LICENSE

.. |doc| image:: https://img.shields.io/badge/doc-success-success
    :target: https://stheid.github.io/pylibfuzzer


* Free software: GNU General Public License v3
* Documentation: https://stheid.github.io/pylibfuzzer


Installation
------------

::

  $ git clone https://github.com/stheid/pylibfuzzer.git
  $ pip install .


Getting started
---------------

.. code-block:: python

    from pylibfuzzer.exec.runner import main

    if __name__ == '__main__':
        main()