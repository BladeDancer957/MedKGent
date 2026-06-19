#!/bin/bash

python main.py \
  --model qwen-plus \
  --base_dir ./data_samples \
  --N 50 \
  --confidence_threshold 0.6 \
  "$@"


  