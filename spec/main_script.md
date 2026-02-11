# tfplan-viewer メインスクリプト仕様書

エンドユーザー向けのメインスクリプト `bin/tfplan-viewer.py` の仕様

---

## 概要

`tfplan-viewer.py` は、Terraform plan JSONファイルからHTMLレポートを生成するメインスクリプト。
Phase 1-3の全モジュールを統合し、シンプルなコマンドラインインターフェースを提供する。

---

## 基本使用方法

```bash
# 基本実行（schema/ディレクトリをデフォルトで使用）
python bin/tfplan-viewer.py -p plan.json

# schemaディレクトリ指定
python bin/tfplan-viewer.py -p plan.json -s my_schema

# 出力ディレクトリ指定
python bin/tfplan-viewer.py -p plan.json -o output_dir

# タイトル指定
python bin/tfplan-viewer.py -p plan.json -o output_dir --title "Production Environment"

# 設定ファイル指定
python bin/tfplan-viewer.py -p plan.json -o output_dir \
  --special-config special.json \
  --identifier-config identifiers.json
```

---

## コマンドライン引数

### 必須引数

| 引数 | 説明 |
|------|------|
| `-p, --plan` | Terraform plan JSONファイルのパス |

### オプション引数

| 引数 | 説明 | デフォルト |
|------|------|-----------|
| `-s, --schema` | schemaディレクトリ（`d*/`構造） | `schema` |
| `-o, --output-dir` | HTML出力ディレクトリ | `html_output` |
| `--title` | HTMLレポートのタイトル | "Terraform Plan" |
| `--special-config` | 特殊リソース処理設定ファイル（JSON） | デフォルト設定使用 |
| `--identifier-config` | リソース識別子設定ファイル（JSON） | デフォルト設定使用 |

### 設定ファイル出力

| 引数 | 説明 |
|------|------|
| `--dump-special-config FILE` | デフォルトの特殊リソース設定をJSONで出力 |
| `--dump-identifier-config FILE` | デフォルトのリソース識別子設定をJSONで出力 |

**注**: `--dump-*`オプションを指定した場合、設定ファイルを出力して終了する。

---

## 実行例

### 1. 基本的な実行

```bash
# 基本実行（schema/ディレクトリ、html_output/に出力）
python bin/tfplan-viewer.py -p plan.json

# schemaディレクトリ指定
python bin/tfplan-viewer.py -p plan.json -s my_schema

# 出力ディレクトリ指定
python bin/tfplan-viewer.py -p plan.json -o my_output
```

### 2. カスタム設定での実行

```bash
# デフォルト設定をダンプ
python bin/tfplan-viewer.py --dump-special-config my_special.json
python bin/tfplan-viewer.py --dump-identifier-config my_identifiers.json

# 設定ファイルを編集後、カスタム設定で実行
python bin/tfplan-viewer.py \
  -p plan.json \
  -o html_output \
  --special-config my_special.json \
  --identifier-config my_identifiers.json \
  --title "My Infrastructure"
```

---

## 処理フロー

```
1. コマンドライン引数解析
   ↓
2. 設定ファイル読み込み（指定されている場合）
   ↓
3. schema読み込み
   schema_loader.load_merged_schema()でschemaディレクトリから統合読み込み
   ↓
4. Phase 1: データ抽出
   data_extraction.extract_data()
   ↓
5. Phase 2-1: 特殊リソース処理
   special_processor.process_special_resources()
   ↓
6. Phase 2-2: 参照解決
   reference_resolver.resolve_references()
   ↓
7. Phase 2-3: View変換
   view_converter.convert_to_view_values()
   ↓
8. Phase 3: HTML生成
   file_organizer.organize_html_files()
   ↓
9. 完了メッセージ表示
```

---

## エラーハンドリング

### 入力チェック

- plan.json が存在しない → エラーメッセージ表示、終了
- schemaディレクトリが存在しない → エラーメッセージ表示、終了
- schemaディレクトリ内にd*/が存在しない → エラーメッセージ表示、終了
- JSONパースエラー → エラー詳細表示、終了

### 出力ディレクトリチェック

- 既に存在する場合 → 警告表示、上書き確認（デフォルト: 上書き）
- 作成できない場合 → エラーメッセージ表示、終了

### 設定ファイルエラー

- 設定ファイルが存在しない → 警告表示、デフォルト設定で継続
- JSONパースエラー → 警告表示、デフォルト設定で継続

---

## 中間ファイル

メインスクリプトは中間ファイル（pickle/JSON）を生成しない。
すべてのPhaseをメモリ上で実行し、最終的なHTMLのみを出力する。

---

## 実装方針

### モジュールインポート

```python
from schema_loader import load_merged_schema
from data_extraction import extract_data
from special_processor import process_special_resources
from special_config import load_special_configs, SPECIAL_RESOURCE_TYPES
from reference_resolver import resolve_references
from identifier_config import load_identifier_config, RESOURCE_IDENTIFIER_ATTRIBUTES
from view_converter import convert_to_view_values
from file_organizer import organize_html_files
```

### 関数設計

```python
def main():
  """Main entry point"""
  args = parse_arguments()

  # Handle config dump requests
  if args.dump_special_config:
    dump_special_config(args.dump_special_config)
    return
  if args.dump_identifier_config:
    dump_identifier_config(args.dump_identifier_config)
    return

  # Validate inputs
  validate_inputs(args)

  # Load schema from directory
  schema_json = load_merged_schema(args.schema)

  # Load plan JSON
  with open(args.plan, 'r') as f:
    plan_json = json.load(f)

  # Load configurations
  special_config = load_config_if_specified(args.special_config, 'special')
  identifier_config = load_config_if_specified(args.identifier_config, 'identifier')

  # Execute phases
  print("Phase 1: Extracting data...")
  extracted = extract_data(plan_json, schema_json)

  print("Phase 2-1: Processing special resources...")
  processed = process_special_resources(extracted, special_config)

  print("Phase 2-2: Resolving references...")
  resolved = resolve_references(processed, identifier_config)

  print("Phase 2-3: Converting to view...")
  view_data = convert_to_view_values(resolved)

  print("Phase 3: Generating HTML...")
  organize_html_files(view_data, args.output_dir, args.title)

  print(f"✓ HTML report generated: {args.output_dir}/index.html")
```

---

## 出力メッセージ

### 成功時

```
Loading schema from schema/...
  ✓ Loaded 5 resource type schemas
Phase 1: Extracting data...
  ✓ Extracted 42 resources
Phase 2-1: Processing special resources...
  ✓ Merged 5 special resources
Phase 2-2: Resolving references...
  ✓ Resolved 18 references
Phase 2-3: Converting to view...
  ✓ Converted 37 resources
Phase 3: Generating HTML...
  ✓ Generated 8 HTML files
✓ HTML report generated: html_output/index.html
```

### エラー時

```
ERROR: File not found: plan.json
```

```
ERROR: Schema directory not found: schema/
```

```
ERROR: Failed to parse JSON: Invalid JSON format
```

```
WARNING: Custom config file not found: my_config.json
Using default configuration.
```

---

## テスト方法

```bash
cd tests/test001

# 事前準備: schema_manager.pyでschemaディレクトリ作成
../../bin/schema_manager.py -p plan.json -s schema.json

# テスト実行（schema/ディレクトリを使用）
../../bin/tfplan-viewer.py \
  -p plan.json \
  -o html_output \
  --title "Test001 Terraform Plan"

# schemaディレクトリ指定
../../bin/tfplan-viewer.py \
  -p plan.json \
  -s schema \
  -o html_output

# 出力確認
open html_output/index.html
```

---

## 今後の拡張

- `--verbose` オプション: 詳細ログ出力
- `--quiet` オプション: エラーのみ出力
- `--format` オプション: 出力形式選択（html, markdown, etc.）
- `--resource-config` オプション: HTML生成設定ファイル指定
