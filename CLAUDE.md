# tfplan-viewer 開発ガイド

## プロジェクト概要

tfplan-viewerは、Terraformの`plan.json`とスキーマディレクトリ（`schema/d*/*.json`）からHTMLパラメータシートを生成するツールです。

## 最重要資料

**`spec/`ディレクトリの仕様書を必ず参照すること:**
- `spec/architecture.md` - アーキテクチャ全体の設計（Phase構成、データフロー、設定ファイル）
- `spec/main_script.md` - メインスクリプトの仕様
- `spec/schema_script.md` - スキーマ管理スクリプトの仕様（schema_manager.py, schema_loader.py）
- `spec/conventions.md` - 開発規約（モジュール設計、データフロー、命名、テスト設計）

## ディレクトリ構造

```
tfplan-viewer/
├── CLAUDE.md                # このファイル（開発ガイド）
├── README.md                # ユーザー向けドキュメント
├── done.md                  # 開発履歴
├── bin/
│   ├── tfplan-viewer.py     # メインスクリプト（HTML生成）
│   └── schema_manager.py    # スキーマ分割管理ツール
├── lib/
│   ├── schema_loader.py     # スキーマディレクトリ読み込み・統合
│   ├── data_extraction.py   # Phase 1: データ抽出
│   ├── special_processor.py # Phase 2-1: 特殊リソース処理
│   ├── reference_resolver.py# Phase 2-2: 参照解決
│   ├── view_converter.py    # Phase 2-3: ビュー変換
│   ├── file_organizer.py    # Phase 3: ファイル編成
│   ├── html_view.py         # HTML生成
│   ├── special_config.py    # 設定: 特殊リソース
│   ├── identifier_config.py # 設定: 識別子
│   └── resource_config.py   # 設定: リソース
├── agents/                  # Claude Codeカスタムサブエージェント
│   └── schema-description.md
├── skills/                  # Claude Codeスキル
│   └── schema-description/
├── spec/                    # 仕様書
├── tests/                   # テストケース
│   ├── phase1_test.sh〜phase3_test.sh  # 各Phaseテスト
│   ├── run_all_phases.sh    # 1テストの全Phase実行
│   ├── run_all_tests.sh     # 全テスト実行
│   ├── schema_test.sh       # スキーマ分割テスト
│   ├── init.sh / clean.sh   # テスト初期化・クリーン
│   ├── test001/             # 基本的なリソース
│   ├── test002/             # リソース間参照
│   ├── test003/             # モジュール構造
│   └── test004/             # 複雑な参照・description付き
└── .gitignore
```

## メインスクリプト（tfplan-viewer.py）

plan.jsonとスキーマから、リソースタイプ別のHTMLパラメータシートを生成する。

```bash
bin/tfplan-viewer.py -p plan.json [-s schema_dir] [-o html_output] [--title "タイトル"]
```

- `-s`はスキーマディレクトリ（デフォルト: `schema`）
- 3フェーズ（データ抽出→データ加工→HTML生成）をメモリ内で一括実行
- 特殊リソース設定・識別子設定のカスタマイズ可能（`--special-config`, `--identifier-config`）

## スキーマ分割管理ツール（schema_manager.py）

plan.jsonとschema.jsonからリソースタイプ別の個別JSONファイルを`schema/d*/`に生成する。

```bash
bin/schema_manager.py -p plan.json -s schema.json [-o schema]
```

- 初回: `schema/d0000/`に全リソースタイプを出力
- 2回目以降: 新規リソースタイプのみ`d0001/`, `d0002/`...に差分出力

### 日本語description

スキーマJSONの各属性に日本語descriptionを追加できる。`skills/schema-description/`にスキルが、`agents/schema-description.md`にサブエージェント定義がある。

## テスト方法

### 個別Phaseのテスト
```bash
cd /path/to/tfplan-viewer/tests
./phase1_test.sh test001
./phase2_1_test.sh test001
./phase2_2_test.sh test001
./phase2_3_test.sh test001
./phase3_test.sh test001
```

### 全Phase実行（1つのテスト）
```bash
cd /path/to/tfplan-viewer/tests
./run_all_phases.sh test001
```

### 全テスト実行
```bash
cd /path/to/tfplan-viewer/tests
./run_all_tests.sh
```

### スキーマ分割テスト
```bash
cd /path/to/tfplan-viewer/tests
./schema_test.sh test001
```

### 通常モード（統合実行）
```bash
cd /path/to/tfplan-viewer/tests/test001
../../bin/tfplan-viewer.py -p plan.json -s schema
```

テストでschema/ディレクトリがない場合はschema.jsonにフォールバックする。

## 開発規約

モジュール設計・データフロー・命名・テスト設計の詳細は `spec/conventions.md` を参照。
