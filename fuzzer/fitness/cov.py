import re


def cov_fitness(s: bytes) -> int:
    return int(re.match(r'cov:\s*(\d+)', s.decode())[1])
