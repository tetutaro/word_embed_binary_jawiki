#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import codecs
import subprocess
import glob
import simplejson as json
import re
import unicodedata
import MeCab
from logging import getLogger
from logging import StreamHandler
from logging import Formatter
from logging import DEBUG

# 辞書のリスト
DICS = [
    'ipa',
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
    dicpaths["ipa"] = f"{dicdir}/ipadic"
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
    def __init__(self):
        self.fds = dict()
        os.makedirs(f"{PARSED_DIR}", exist_ok=True)
        self.fds['raw'] = open(f"{PARSED_DIR}/raw.txt", "wt")
        for d in DICS:
            self.fds[d] = open(f"{PARSED_DIR}/{d}.txt", "wt")
        return

    def get(self, d):
        return self.fds[d]

    def close(self):
        self.fds['raw'].close()
        for d in DICS:
            self.fds[d].close()
        return


def unicode_normalize(cls: str, s: str) -> str:
    pt = re.compile('([{}]+)'.format(cls))

    def norm(c):
        return unicodedata.normalize('NFKC', c) if pt.match(c) else c

    s = ''.join(norm(x) for x in re.split(pt, s))
    s = re.sub('－', '-', s)
    return s


def remove_extra_spaces(s: str) -> str:
    s = re.sub('[ 　]+', ' ', s)
    blocks = ''.join((
        '\u4E00-\u9FFF',  # CJK UNIFIED IDEOGRAPHS
        '\u3040-\u309F',  # HIRAGANA
        '\u30A0-\u30FF',  # KATAKANA
        '\u3000-\u303F',  # CJK SYMBOLS AND PUNCTUATION
        '\uFF00-\uFFEF'   # HALFWIDTH AND FULLWIDTH FORMS
    ))
    basic_latin = '\u0000-\u007F'

    def remove_space_between(cls1: str, cls2: str, s: str) -> str:
        p = re.compile('([{}]) ([{}])'.format(cls1, cls2))
        while p.search(s):
            s = p.sub(r'\1\2', s)
        return s

    s = remove_space_between(blocks, blocks, s)
    s = remove_space_between(blocks, basic_latin, s)
    s = remove_space_between(basic_latin, blocks, s)
    return s


def normalize_neologd(s: str) -> str:
    s = s.strip()
    s = unicode_normalize('０-９Ａ-Ｚａ-ｚ｡-ﾟ', s)

    def maketrans(f, t):
        return {ord(x): ord(y) for x, y in zip(f, t)}

    s = re.sub('[˗֊‐‑‒–⁃⁻₋−]+', '-', s)  # normalize hyphens
    s = re.sub('[﹣－ｰ—―─━ー]+', 'ー', s)  # normalize choonpus
    s = re.sub('[~∼∾〜〰～]', '', s)  # remove tildes
    s = s.translate(maketrans(
        '!"#$%&\'()*+,-./:;<=>?@[¥]^_`{|}~｡､･｢｣',
        '！”＃＄％＆’（）＊＋，－．／：；＜＝＞？＠［￥］＾＿｀｛｜｝〜。、・「」'
    ))

    s = remove_extra_spaces(s)
    s = unicode_normalize(
        '！”＃＄％＆’（）＊＋，－．／：；＜＞？＠［￥］＾＿｀｛｜｝〜',
        s
    )  # keep ＝,・,「,」
    s = re.sub('[’]', '\'', s)
    s = re.sub('[”]', '"', s)
    return s


def parse_texts(title, raw_text):
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
    ctexts = [normalize_neologd(x).replace(
        "、、", "、"
    ).replace(
        "(、", "("
    ).replace(
        "(,", "("
    ).replace(
        "、)", ")"
    ).replace(
        ",)", ")"
    ).replace(
        "()", ''
    ).replace(
        "「」", ''
    ).replace(
        "、。", "。"
    ) for x in ctexts]
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
            p = taggers[d].parse(c).strip().split(' ')
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
def main():
    # Tokenizer の生成
    taggers = get_taggers()
    fds = parsedFile()
    # ファイルを読み込んで分かち書き
    cfnames = glob.glob('corpora/*/*')
    for cf in cfnames:
        logger.info(cf)
        with open(cf, "rt") as rf:
            li = 1
            line = rf.readline()
            while line:
                # １行ずつJSONを読み込んでいく
                try:
                    e = json.loads(line)
                # エラーは無視して次の行
                except Exception:
                    li += 1
                    line = rf.readline()
                    continue
                title = e.get('title')
                raw_text = e.get('text').strip()
                # 本文が取れなかったら次の行
                if raw_text is None:
                    li += 1
                    line = rf.readline()
                    continue
                # 本文からセンテンスの配列を得る
                ctexts = parse_texts(title, raw_text)
                # 何もなかったら次の行
                if len(ctexts) == 0:
                    li += 1
                    line = rf.readline()
                    continue
                # 分かち書きして書き込む
                tokenize_sentences(cf, li, fds, taggers, ctexts)
                # 次の行
                li += 1
                line = rf.readline()
    fds.close()
    return


if __name__ == "__main__":
    main()
