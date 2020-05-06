#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sentencepiece as spm

prefix = "models/sentence_piece"
input_file = "parsed/raw.txt"
command = f"--input={input_file} --model_prefix={prefix} vocab_size=32000 --control_symbols=[PAD],[CLS],[SEP],[MASK]"
spm.SentencePieceTrainer.Train(command)
