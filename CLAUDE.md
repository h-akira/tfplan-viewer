# tfplan-viewer 開発ガイド

## プロジェクト概要

tfplan-viewerは、Terraformの`plan.json`と`schema.json`からHTMLパラメータシートを生成するツールです。

## 最重要資料

**`spec/`ディレクトリの仕様書を必ず参照すること:**
- `spec/architecture.md` - アーキテクチャ全体の設計（Phase構成、データフロー、設定ファイル）
- `spec/main_script.md` - メインスクリプトの仕様
- `spec/rule.md` - 実装ルール（コーディング規約、データフロー規約、命名規約）

これらの仕様書が、各機能の入出力、テスト方法を定義しています。

## ディレクトリ構造

```
tfplan-viewer/
├── CLAUDE.md                # このファイル（開発ガイド）
├── README.md                # ユーザー向けドキュメント
├── done.md                  # 開発履歴
├── .gitignore              # Git除外設定
├── bin/                    # 実行ファイル
│   ├── tfplan-viewer.py    # メインスクリプト（全Phase実行）
│   └── schema_dump.py      # スキーマ抽出ユーティリティ
├── lib/                    # ライブラリモジュール（各Phase実装）
│   ├── data_extraction.py       # Phase 1
│   ├── special_processor.py     # Phase 2-1
│   ├── reference_resolver.py    # Phase 2-2
│   ├── view_converter.py        # Phase 2-3
│   ├── file_organizer.py        # Phase 3
│   ├── special_config.py        # 設定: 特殊リソース
│   ├── identifier_config.py     # 設定: 識別子
│   ├── resource_config.py       # 設定: リソース
│   └── html_view.py             # HTML生成
├── spec/                   # 仕様書（最重要）
│   ├── architecture.md     # アーキテクチャ設計
│   ├── main_script.md      # メインスクリプト仕様
│   └── rule.md             # 実装ルール
├── tests/                  # テストケース
│   ├── phase1_test.sh      # Phase 1テストスクリプト
│   ├── phase2_1_test.sh    # Phase 2-1テストスクリプト
│   ├── phase2_2_test.sh    # Phase 2-2テストスクリプト
│   ├── phase2_3_test.sh    # Phase 2-3テストスクリプト
│   ├── phase3_test.sh      # Phase 3テストスクリプト
│   ├── run_all_phases.sh   # 1つのテストの全Phase実行
│   ├── run_all_tests.sh    # 全テスト実行
│   ├── test001/            # 基本的なリソース
│   ├── test002/            # リソース間参照
│   ├── test003/            # モジュール構造
│   └── test004/            # 複雑な参照
└── generated-diagrams/     # アーキテクチャ図
```

## テスト方法

テストスクリプトは`tests/`ディレクトリに共通スクリプトとして配置されています。引数でテストディレクトリを指定します。

### 個別Phaseのテスト
```bash
cd tests
./phase1_test.sh test001      # Phase 1のみ
./phase2_1_test.sh test001    # Phase 2-1のみ
./phase2_2_test.sh test001    # Phase 2-2のみ
./phase2_3_test.sh test001    # Phase 2-3のみ
./phase3_test.sh test001      # Phase 3のみ
```

### 全Phase実行（1つのテスト）
```bash
cd tests
./run_all_phases.sh test001   # test001の全Phaseを実行
```

### 全テスト実行
```bash
cd tests
./run_all_tests.sh            # test001〜test004の全テストを実行
```

### 通常モード（全Phase統合実行）
```bash
cd tests/test001
../../bin/tfplan-viewer.py -p plan.json -s schema.json -o html_output
```

## コーディング規約

### インデント
- 2スペース（タブ不可）

### コメント
- ソースコード: 英語
- ドキュメント: 日本語

### git操作
- `git add .` や `git add -A` は禁止
- 個別ファイル指定または `git add -u` を使用
- `git push` は特別な指示がない限り禁止（ユーザーが実行）

### 作業ディレクトリ
- コマンド実行時は必ず`cd`で絶対パスを使用して移動
