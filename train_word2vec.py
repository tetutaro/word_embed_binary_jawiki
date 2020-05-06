#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import click
import fasttext
from gensim.models.word2vec import LineSentence, Word2Vec

DICS = ['juman', 'neologd']


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
    if dic == "sentence_piece":
        fname = f"parsed/sentence_piece.txt"
        mname = "models/word2vec_sentence_piece.model"
        bname = "models/word2vec_kv_sentence_piece.bin"
    else:
        fname = f"parsed/{dic}_origform.txt"
        mname = f"models/word2vec_mecab_{dic}.model"
        bname = f"models/word2vec_kv_mecab_{dic}.bin"
    # 文章の読み込み
    sentences = LineSentence(fname)
    # Word2Vec の学習
    model = Word2Vec(
        size=300, window=5, min_count=20, iter=10,
        sg=0, hs=0, negative=5, cbow_mean=1
    )
    model.build_vocab(sentences)
    model.train(
        sentences,
        total_examples=model.corpus_count,
        epochs=model.epochs
    )
    # モデルのバイナリの書き出し
    model.save(mname)
    # ベクトルファイルの書き出し
    model.wv.save_word2vec_format(bname, binary=True)
    return


if __name__ == "__main__":
    main()
