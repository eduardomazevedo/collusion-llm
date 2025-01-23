#!/bin/bash

rclone copy ./output/completions/uhaul-test.xlsx collusion-llm:output/completions/
rclone copy ./data/completions/uhaul-test.pkl collusion-llm:data/completions/