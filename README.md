# word_embed_binary_jawiki
日本語Wikipediaで学習した Word2Vec, fastText, SentencePiece のバイナリを作る

## 作り方

- [日本語Wikipediaのダンプサイト](https://dumps.wikimedia.org/jawiki/)から適当なタイミングのbz2をダウンロードする(jawiki-YYYYMMDD-pages-articles-multistream.xml.bz2)
- [WikiExtractor](https://github.com/attardi/wikiextractor)を拝借する
- [MeCab](https://taku910.github.io/mecab/)とMecab用の辞書をインストールする
    - MeCab本体はMacOSならば `brew install mecab`
    - Juman辞書はMacOSならば `brew install mecab-jumandic`
    - IPA NEologd辞書は[本家](https://github.com/neologd/mecab-ipadic-neologd)を参照
- Word2Vec, fastText, SentencePiece をインストールする
    - `pip install gensim fasttext sentencepiece`
- WikiExtractorでWikipediaダンプから本文を抽出
    - `python WikiExtractor.py --json -o corpora jawiki-YYYYMMDD-pages-articles-multistream.xml.bz2`
- `wakati_mecab.py` で分かち書きする
    - めんどくさいので IPA, Juman と NEologd をいっぺんにやっている
    - `parsed` というディレクトリの下に出来る
        - `raw.txt` が WikiExtractor の出力をさらに整形して１行１文章としたもの
        - `ipa.txt` が１行１文章半角空白区切りのIPA辞書で分かち書きしたもの
        - `juman.txt` が１行１文章半角空白区切りのJuman辞書で分かち書きしたもの
        - `neologd.txt` が１行１文章半角空白区切りのNEologd辞書で分かち書きしたもの
    - 結構時間がかかるので、ファイル分割したほうが速いかと思って、デフォルトでファイル分割、`--whole` オプションを付けるとひとつのファイルに書き出すという実装をしたけど、結局`--whole`しか試してない
    - 前処理としては、`mojimoji.han_to_zen()`での半角→全角、文字コードの関係で消えてしまったので句読点や括弧が続いてしまったもの、括弧の中が空になってしまったものの除去、ぐらいしかしてない
    - ここでは、日本語の本当の「文」ではなく、段落を「文章」としている。複数の「文」をまとめて扱いたいケースが多いと思うから。ここらへんは色々議論があると思う
- `train_sentence_piece.py` でSentencePieceを学習してバイナリを書き出す
    - 学習するのは `parsed/raw.txt`
    - バイナリは `models` ディレクトリの下に作られる
- `wakati_sentence_piece.py` でSentencePieceで分かち書きしたものを作る
    - 使うデータは `parsed/raw.txt`
    - 使うモデルは `models/sentence_piece.model`（上で作ったやつ）
    - 出来るファイルは `parsed/sentence_piece.txt`
        - １行１文章、セパレータは半角空白
- `train_fasttext.py` でfastTextを学習させバイナリを作る
    - `--dic [juman/neologd/sentence_piece]` で分かち書きしたものを選択する
    - バイナリは `models` ディレクトリの下に作られる
        - `models/fasttext_XXX.bin` が facebook 版 fastText のバイナリ
        - `models/fasttext_XXX.vec` が学習した単語ベクトルを gensim の word2vec 形式で書き出したもの
        - `models/fasttext_kv_XXX.bin` が上をバイナリ形式にしたもの
        - 使うにはサイズがコンパクトな `fasttext_kv_XXX.bin` が良いが、再学習させるには元のバイナリが必要
        - `XXX` 部分は、`mecab_juman`, `mecab_neologd`, `sentence_piece` のどれか
- `wakati_origform_mecab.py` で、分かち書きしつつ各単語を表層ではなく原形に置き換えたものを作る
    - 使うデータは `parsed/raw.txt`
    - `parsed/juman_origform.txt` がJuman辞書を使ったもの
    - `parsed/neologd_origform.txt` がNeologd辞書を使ったもの
        - １行１文章、セパレータは半角空白
        - 両方を一気に作る
    - `parsed/raw.txt` を使っているので、前処理とか文章の定義は `wakati_mecab.py` に準ずる
- `train_word2vec.py` でword2vecで学習したバイナリを作る
    - `--dic [juman/neologd/sentence_piece]` で分かち書きしたものを選択する
    - 使うファイルは、juman, neologd の場合は上で作った origform のもの
    - sentence_piece の場合は、ただ分かち書きしたもの
        - word2vec と sentencepiece は相性が悪いと思っているので、試してない
    - バイナリは `models` ディレクトリの下に作られる
        - `models/word2vec_XXX.bin` と npy ファイル群が word2vec のバイナリ
        - `models/word2vec_kv_XXX.bin` が上を word2vec 形式 keyedvectors のバイナリにしたもの
        - 使うにはサイズがコンパクトな `word2vec_kv_XXX.bin` が良いが、再学習させるには元のバイナリが必要
        - `XXX` 部分は、`mecab_juman`, `mecab_neologd`, `sentence_piece` のどれか

## 使い方

- `[fasttext,word2vec]_kv_[mecab_juman,mecab_neologd,sentence_piece].bin` を `from gensim.models.keyedvectors import KeyedVectors; kvs = KeyedVectors.load_word2vec_format(<path_to_bin>, binary=True)` のようにして使う
- どのバイナリを使うかは case by case

## 各種パラメータ

- fastText
    - ベクトル次元: 300, epoch数: 10, 単語の min count: 20
- Word2Vec
    - fastText が skipgram なので、せっかくだから（？） CBOW
    - 後は fastText に揃えている
    - negative sampling は 5
