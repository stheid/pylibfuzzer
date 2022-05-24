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

  $ pip install git+https://github.com/stheid/pylibfuzzer.git

Installation of MCTS dependency
'''''''''''''''''''''''''''''''

::

  $ git clone https://github.com/stheid/MCTS-Fuzzer.git
  $ ./gradlew :shadow

Now you can refer to the built shadow jar in the experiment configuration. When developing it is advicable to setup gradle build run configuration in Pycharm and run it before executing the MCTS fuzzer. In this case the git submodule can be leveraged.


Getting started
---------------

To execute the code one must create the main configuration file, similar to the :code:`experiment.yaml` files in the :code:`examples` folders

::

  $ python -m pylibfuzzer