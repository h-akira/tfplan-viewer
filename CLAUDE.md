# tfplan-viewer 開発ガイド

## プロジェクト概要

tfplan-viewerは、Terraformの`plan.json`と`schema.json`からHTMLパラメータシートを生成するツールです。

## 最重要資料

**`spec/`ディレクトリの仕様書を必ず参照すること:**
- `spec/architecture.md` - アーキテクチャ全体の設計
- `spec/main_script.md` - メインスクリプトの仕様
- `spec/rule.md` - 実装ルール

これらの仕様書が、各機能の入出力、テスト方法を定義しています。

## アーキテクチャ

tfplan-viewerは3つのPhaseで構成されます：

### Phase 1: Data Extraction
- **入力**: `plan.json`, `schema.json`
- **出力**: `extracted.pkl` (OriginValueオブジェクト)
- **モジュール**: `lib/data_extraction.py`
- **機能**:
  - schema.jsonベースの属性抽出
  - computed-only属性の除外
  - リソース参照の抽出
  - モジュール対応

### Phase 2: Data Processing

#### Phase 2-1: Special Resource Processing
- **入力**: `extracted.pkl`
- **出力**: `special.pkl`
- **モジュール**: `lib/special_processor.py`
- **機能**: 依存リソースの親リソースへの統合

#### Phase 2-2: Reference Resolution
- **入力**: `special.pkl`
- **出力**: `reference.pkl`
- **モジュール**: `lib/reference_resolver.py`
- **機能**: リソース参照の解決

#### Phase 2-3: View Conversion
- **入力**: `reference.pkl`
- **出力**: `view.pkl` (ViewValueオブジェクト)
- **モジュール**: `lib/view_converter.py`
- **機能**: 表示用データへの変換

### Phase 3: HTML Generation
- **入力**: `view.pkl`
- **出力**: `html_output/` (HTMLファイル群)
- **モジュール**: `lib/file_organizer.py`, `lib/html_view.py`
- **機能**: リソースタイプ別HTMLファイル生成

## ディレクトリ構造

```
tfplan-viewer/
├── CLAUDE.md                # このファイル（開発ガイド）
├── README.md                # ユーザー向けドキュメント
├── IMPROVEMENTS.md          # 改善提案
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
│   ├── test001/            # 基本的なリソース
│   │   ├── main.tf
│   │   ├── plan.json
│   │   ├── schema.json
│   │   ├── extracted.pkl   # Phase 1出力
│   │   ├── special.pkl     # Phase 2-1出力
│   │   ├── reference.pkl   # Phase 2-2出力
│   │   ├── view.pkl        # Phase 2-3出力
│   │   └── html_output/    # Phase 3出力
│   ├── test002/            # リソース間参照
│   ├── test003/            # モジュール構造
│   └── test004/            # 複雑な参照
└── generated-diagrams/     # アーキテクチャ図
    ├── terraform2sheet_workflow.png
    └── terraform2sheet_architecture.png
```

## テスト方法

各モジュールは`__main__`として単独実行可能です。pickleファイルで前段階の出力を読み込みます。

### Phase 1のテスト
```bash
cd tests/test001
python3 ../../lib/data_extraction.py plan.json schema.json
# extracted.pkl と extracted.json が生成される
```

### Phase 2-1のテスト
```bash
cd tests/test001
python3 ../../lib/special_processor.py extracted.pkl
# special.pkl と special.json が生成される
```

### Phase 2-2のテスト
```bash
cd tests/test001
python3 ../../lib/reference_resolver.py special.pkl
# reference.pkl と reference.json が生成される
```

### Phase 2-3のテスト
```bash
cd tests/test001
python3 ../../lib/view_converter.py reference.pkl
# view.pkl と view.json が生成される
```

### Phase 3のテスト
```bash
cd tests/test001
python3 ../../lib/file_organizer.py view.pkl html_output
# html_output/ ディレクトリにHTMLが生成される
```

### 全Phase統合テスト
```bash
cd tests/test001
../../bin/tfplan-viewer.py -p plan.json -s schema.json -o html_output
```

## 開発ルール

### 1. インデント
- 2スペース（タブ不可）

### 2. コメント
- ソースコード: 英語
- ドキュメント: 日本語

### 3. git操作
- `git add .` や `git add -A` は禁止
- 個別ファイル指定または `git add -u` を使用
- `git push` は特別な指示がない限り禁止（ユーザーが実行）

### 4. 作業ディレクトリ
- コマンド実行時は必ず`cd`で絶対パスを使用して移動

### 5. pickle形式
- 各Phase間のデータ受け渡しはpickleを使用
- デバッグ用にJSONも同時出力

### 6. エラーハンドリング
- schema.jsonに存在しない属性に対する賢い警告
  - computed-only属性: 警告なし
  - block_types: 警告なし
  - 本当に未定義の属性: 警告を出す

## S3/CloudFrontへのデプロイ

**注意**: デプロイスクリプトはGit管理下に入れるが、出力ファイルは除外する。

デプロイスクリプトの例:
```bash
#!/bin/bash
# sync-s3.sh - HTMLをS3にデプロイ

aws s3 sync html_output/ s3://your-bucket-name/ \
  --delete \
  --exclude "*.pkl" \
  --exclude "*.json" \
  --cache-control "max-age=3600"
```

## 改善提案

詳細は`IMPROVEMENTS.md`を参照。優先度の高い項目：
1. AIによる説明文の自動生成（JSONファイルベース）
2. List型テーブルの実装
3. 変更差分の視覚化（CREATE/UPDATE/DELETE）

## トラブルシューティング

### 警告: "Attribute 'xxx' not found in schema"
- computed-only属性やblock_typesは自動的に除外されるため、この警告は本当に未定義の属性にのみ表示される
- schema.jsonが古い可能性がある場合は`schema_dump.py`で再抽出

### pickleファイルが読めない
- Pythonバージョンの違いによる場合がある
- 同じPhaseを再実行してpickleを作り直す

### HTMLが生成されない
- view.pklが正しく生成されているか確認
- `lib/file_organizer.py view.pkl html_output`で単独テスト

## 参考リンク

- [Terraform JSON Output](https://www.terraform.io/docs/cli/commands/show.html#json-output)
- [GitHub: terraform2sheet](https://github.com/your-repo/terraform2sheet) *(要更新)*
