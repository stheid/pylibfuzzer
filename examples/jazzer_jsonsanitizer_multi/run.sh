#!/bin/bash

for ((i=0; i<100; i++))
do
	for goal in configs/goals/*
	do
    for mut in configs/mutations/*
    do
	    PYTHONPATH=../../pylibfuzzer:../.. python  /home/sheid/Project/pylibfuzzer/pylibfuzzer/exec/runner.py --conf "configs/default.yml,$goal,$mut"
	  done
  done
done
