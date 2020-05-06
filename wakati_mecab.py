#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import codecs
import subprocess
import glob
import simplejson as json
from mojimoji import han_to_zen
import MeCab
from logging import getLogger
from logging import StreamHandler
from logging import Formatter
from logging import DEBUG
import click

# 辞書のリスト
DICS = [
    'juman',    # JUMAN辞書
    'neologd',  # IPA NeologD辞書
]
# WikiExtractor で本文を抜き出したディレクトリ名
CORPORA_DIR = 'corpora'
# 出力先ディレクトリ名
PARSED_DIR = 'parsed'
# Loggerの設定
logger = getLogger(__file__)
logger.setLevel(DEBUG)
formatter = Formatter('%(asctime)s: %(levelname)s: %(message)s')
handler = StreamHandler()
handler.setLevel(DEBUG)
handler.setFormatter(formatter)
logger.addHandler(handler)



# Tokenizer を生成
def get_taggers():
    # 辞書のパスのリストアップ
    dicdir = subprocess.run(
        ["mecab-config", "--dicdir"],
        check=True, stdout=subprocess.PIPE, text=True
    ).stdout.rstrip()
    dicpaths = dict()
    # MacOS で Homebrew 等を使って入れた場合
    dicpaths["juman"] = f"{dicdir}/jumandic"
    # IPA NeologD の git clone からそのまま make install した場合
    dicpaths["neologd"] = f"{dicdir}/mecab-ipadic-neologd"
    # Tokenizer の生成
    taggers = dict()
    for d in DICS:
        dpath = dicpaths[d]
        taggers[d] = MeCab.Tagger(f"-Owakati -d{dpath}")
    return taggers


# 分かち書きしたものを書き込むファイル
class parsedFile():
    def __init__(self, cf, whole=False):
        self.fds = dict()
        if whole:
            os.makedirs(f"{PARSED_DIR}", exist_ok=True)
            self.fds['raw'] = open(f"{PARSED_DIR}/raw.txt", "wt")
            for d in DICS:
                self.fds[d] = open(f"{PARSED_DIR}/{d}.txt", "wt")
        else:
            assert(cf is not None)
            cfs = cf.split('/')
            part = cfs[1]
            fn = cfs[2]
            os.makedirs(f"{PARSED_DIR}/raw/{part}", exist_ok=True)
            self.fds['raw'] = open(f"{PARSED_DIR}/raw/{part}/{fn}", "wt")
            for d in DICS:
                os.makedirs(f"{PARSED_DIR}/{d}/{part}", exist_ok=True)
                self.fds[d] = open(f"{PARSED_DIR}/{d}/{part}/{fn}", "wt")
        return self

    def get(self, d):
        return self.fds[d]

    def close(self):
        self.fds['raw'].close()
        for d in DICS:
            self.fds[d].close()
        return


def parse_text(fds, raw_text):
    # 返す配列（センテンスのリスト）
    ctexts = list()
    # 改行で分割する
    texts = [
        x.strip() for x in raw_text.split("\n") if x != title
    ]
    # 何もなかったら終了
    if len(texts) == 0:
        return ctexts
    # キープする文字列
    ctext = ''
    # 改行で分割した文字列毎の処理
    for t in texts:
        if len(t) == 0 and len(ctext) != 0:
            # 空行なので、今までの文字列を（あれば）センテンスに登録
            ctexts.append(ctext)
            ctext = ''
        elif len(t) > 0:
            # ただの改行なので、キープしてた文字列につなげる
            ctext += t
    # 最後まで残っていた文字列を登録
    if len(ctext) > 0:
        ctexts.append(ctext)
    # 何も残らなかったら終了
    if len(ctexts) == 0:
        return ctexts
    # utf の関係で消えてしまった文字の前後の記号を調整する
    ctexts = [han_to_zen(x).replace(
        "\u3000", ''
    ).replace(
        "、、", "、"
    ).replace(
        "（、", "（"
    ).replace(
        "（，", "（"
    ).replace(
        "、）", "）"
    ).replace(
        "，）", "）"
    ).replace(
        "（）", ''
    ).replace(
        "「」", ''
    ).replace(
        "、。", "。"
    ).replace(' ', '') for x in ctexts]
    return ctexts


# 分かち書きしてファイルに書き込む
def tokenize_sentences(cf, li, fds, taggers, ctexts):
    # センテンス毎に処理
    for c in ctexts:
        # そのままを書き込む
        fds.get('raw').write(c + "\n")
        # 辞書毎の処理
        for d in DICS:
            # 単語に分かち書きして分割
            p = taggers[d].parse(c).split(' ')
            # 変な文字が紛れている場合があるので、それを取り除く
            px = list()
            for pp in p:
                x = codecs.decode(
                    codecs.encode(
                        pp, encoding="utf-8", errors="ignore"
                    ), encoding="utf-8", errors="ignore"
                )
                if x != '' and x != ' ':
                    px.append(x)
            # 分割した単語を空白でつなげる
            pp = ' '.join(px)
            # ファイルに書き込む
            try:
                fds.get(d).write(pp.strip() + "\n")
            except Exception:
                logger.error(f"{cf}: {li}")
                logger.error(p)
                sys.exit(-1)
    return


# メイン関数
@click.command()
@click.option(
    '--whole', is_flag=True, default=False,
    help="１個のファイルに書き出す"
)
def main(whole):
    # Tokenizer の生成
    taggers = get_taggers()
    if whole:
        fds = parsedFile(None, whole=whole)
    # ファイルを読み込んで分かち書き
    cfnames = glob.glob('corpora/*/*')
    for cf in cfnames:
        logger.info(cf)
        if not whole:
            fds = parsedFile(cf, whole=whole)
        with open(cf, "rt") as rf:
            li = 1
            l = rf.readline()
            while l:
                # １行ずつJSONを読み込んでいく
                try:
                    e = json.loads(l)
                # エラーは無視して次の行
                except Exception:
                    li += 1
                    l = rf.readline()
                    continue
                title = e.get('title')
                eid = e.get('id')
                raw_text = e.get('text').strip()
                # 本文が取れなかったら次の行
                if raw_text is None:
                    li += 1
                    l = rf.readline()
                    continue
                # 本文からセンテンスの配列を得る
                ctexts = parse_texts(raw_text)
                # 何もなかったら次の行
                if len(ctexts) == 0:
                    li += 1
                    l = rf.readline()
                    continue
                # 分かち書きして書き込む
                tokenize_sentences(cf, li, fds, taggers, ctexts)
                # 次の行
                li += 1
                l = rf.readline()
        if not whole:
            fds.close()
    if whole:
        fds.close()
    return


if __name__ == "__main__":
    main()
