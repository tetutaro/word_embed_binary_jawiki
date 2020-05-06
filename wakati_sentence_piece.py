#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import glob
import simplejson as json
import sentencepiece as spm
from mojimoji import han_to_zen

sp = spm.SentencePieceProcessor()
sp.Load("models/sentence_piece.model")

rf = open("parsed/raw.txt", "rt")
wf = open("parsed/sentence_piece.txt", "wt")

li = 1
l = rf.readline()
while l:
    l = l.strip()
    if len(l) < 1:
        li += 1
        l = rf.readline()
        continue
    p = sp.EncodeAsPieces(l)
    if len(p) == 0:
        li += 1
        l = rf.readline()
        continue
    if p[0].startswith("▁"):
        p[0] = p[0][1:]
    px = ' '.join([han_to_zen(x) for x in p if x != '']).strip()
    try:
        wf.write(px + "\n")
    except Exception:
        print(li)
        print(l)
        sys.exit(-1)
    li += 1
    l = rf.readline()

rf.close()
wf.close()
