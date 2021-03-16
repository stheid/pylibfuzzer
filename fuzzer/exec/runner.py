import yaml


def main(conf='fuzzer.yaml'):
    # TODO read yaml
    # create fuzzer with from configuration
    # select mutators if fuzzer mutation-based and model exists

    with open(conf, 'r') as stream:
        try:
            conf = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    print(conf)


if __name__ == '__main__':
    main()
