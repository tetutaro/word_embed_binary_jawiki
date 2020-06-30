#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import codecs
import subprocess
import MeCab
from logging import getLogger
from logging import StreamHandler
from logging import Formatter
from logging import DEBUG

# 辞書のリスト
DICS = [
    'ipa',    # JUMAN辞書
    'juman',    # JUMAN辞書
    'neologd',  # IPA NeologD辞書
]
# 属性リストの中で単語の原型が現れる場所
ORIGFORM_INDEX = {
    'ipa': 6,
    'juman': 4,
    'neologd': 6,
}
# 出力先ディレクトリ名
PARSED_DIR = 'parsed'
# 元となる１行１文章のファイル
RAW_FILE = 'parsed/raw.txt'
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
    dicpaths["ipa"] = f"{dicdir}/ipadic"
    dicpaths["juman"] = f"{dicdir}/jumandic"
    # IPA NeologD の git clone からそのまま make install した場合
    dicpaths["neologd"] = f"{dicdir}/mecab-ipadic-neologd"
    # Tokenizer の生成
    taggers = dict()
    for d in DICS:
        dpath = dicpaths[d]
        taggers[d] = MeCab.Tagger(f"-d{dpath}")
    return taggers


# 分かち書きしたものを書き込むファイル
class parsedFile():
    def __init__(self):
        self.fds = dict()
        os.makedirs(f"{PARSED_DIR}", exist_ok=True)
        for d in DICS:
            self.fds[d] = open(f"{PARSED_DIR}/{d}_origform.txt", "wt")
        return

    def get(self, d):
        return self.fds[d]

    def close(self):
        for d in DICS:
            self.fds[d].close()
        return


# 分かち書きしてファイルに書き込む
def tokenize_sentences(fds, taggers, text):
    # 辞書毎の処理
    for d in DICS:
        # 分かち書きして情報を得る
        pts = taggers[d].parse(text).split('\n')
        # 単語毎の処理
        ps = list()
        for pt in pts:
            node = pt.split("\t")
            if len(node) < 2:
                continue
            word = node[0]  # 表層
            ftrs = node[1].split(",")  # 属性
            ind = ORIGFORM_INDEX[d]
            # 原型があるものは原型を取得。それ以外は表層
            if len(ftrs) < (ind + 1) or ftrs[ind] in ["", "*"]:
                ps.append(word)
            else:
                ps.append(ftrs[ind])
        # 変な文字が紛れている場合があるので、それを取り除く
        px = list()
        for pp in ps:
            x = codecs.decode(
                codecs.encode(
                    pp, encoding="utf-8", errors="ignore"
                ), encoding="utf-8", errors="ignore"
            )
            if x != '' and x != ' ':
                px.append(x)
        # 分割した単語を空白でつなげる
        p = ' '.join(px)
        # ファイルに書き込む
        try:
            fds.get(d).write(p.strip() + "\n")
        except Exception:
            continue
    return


# メイン関数
def main():
    # Tokenizer の生成
    taggers = get_taggers()
    fds = parsedFile()
    # ファイルを読み込んで分かち書き
    with open(RAW_FILE, "rt") as rf:
        line = rf.readline()
        while line:
            line = line.strip()
            # 空行だったら次の行
            if len(line) < 1:
                line = rf.readline()
                continue
            # 分かち書きして書き込む
            tokenize_sentences(fds, taggers, line)
            # 次の行
            line = rf.readline()
    fds.close()
    return


if __name__ == "__main__":
    main()
