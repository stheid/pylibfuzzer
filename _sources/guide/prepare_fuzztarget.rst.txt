1. export instrumented fuzztarget with jazzer

::

  ./bazelisk-linux-amd64 build  //:jazzer_release
  cd bazel-bin/jazzer_release
  ./jazzer --cp=examples_deploy.jar --target_class=com.example.FastJsonFuzzer --dump_classes_dir=out

classpath and targetclass need to be replaced accordingly



2. export cfg with SA-tool



3. copy cfg into pylibfuzzers working directory.