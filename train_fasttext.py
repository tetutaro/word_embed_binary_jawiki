#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import click
import fasttext
from gensim.models.keyedvectors import KeyedVectors

DICS = ['juman', 'neologd', 'sentence_piece']


@click.command()
@click.option(
    "--dic", "-d", default=None,
    help=f"{DICS}"
)
def main(dic):
    if not dic in DICS:
        print("辞書を正しく入力してください")
        sys.exit(-1)
    # 各種ファイル名の設定
    fname = f"parsed/{dic}.txt"
    if dic == "sentence_piece":
        mname = "models/fasttext_sentence_piece.bin"
        vname = "models/fasttext_sentence_piece.vec"
        kname = "models/fasttext_kv_sentence_piece.bin"
    else:
        mname = f"models/fasttext_mecab_{dic}.bin"
        vname = f"models/fasttext_mecab_{dic}.vec"
        kname = f"models/fasttext_kv_mecab_{dic}.bin"
    # fastText の学習
    ft = fasttext.train_unsupervised(
        fname, model='skipgram', dim=300, epoch=10, minCount=20
    )
    # モデルのバイナリの書き出し
    ft.save_model(mname)
    # ベクトルファイルの書き出し
    words = ft.get_words()
    with open(vname, 'wt') as wf:
        wf.write(str(len(words)) + " " + str(ft.get_dimension()) + "\n")
        for w in words:
            v = ft.get_word_vector(w)
            vstr = ""
            for vi in v:
                vstr += " " + str(vi)
            try:
                wf.write(w + vstr + "\n")
            except Exception:
                pass
    # ベクトルファイルを gensim の KeyedVectors として読み込んで
    # バイナリで書き出す
    kv = KeyedVectors.load_word2vec_format(vname, binary=False)
    kv.save_word2vec_format(kname, binary=True)
    return


if __name__ == "__main__":
    main()
