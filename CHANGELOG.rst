Changelog
=========

0.0.6
-----
- allow for dataset export
- changed build process of the jazzer dependency to get rid of precompiled binaries (examples updated)

0.0.5
-----
- removed old "pipe" interface for libfuzzer
- fixed coverage for fuzzbench (writing generated files to a corpus directory)


0.0.4
-----
- added sparks inspired algorithm https://doi.org/10.1109/ACSAC.2007.27
- added new reward functions
- changed config interface to allow more versitile observation transformation pipelines


0.0.3
-----
- obs_extraction.DirectedCFGRewardExtractor
- exec.runner: can now handle mutiple config files