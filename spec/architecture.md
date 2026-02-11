# tfplan-viewer アーキテクチャ仕様書

Terraform plan JSONファイルを人間が読みやすいHTML形式に変換するツール

---

## 本仕様書について

本書は、tfplan-viewerの**モジュール設計**と**Phase構成**を定義する。

- 各Phaseのモジュールは独立して実装され、テスト可能
- 中間データ形式（pickle/JSON）はテスト・デバッグ用
- 実際のエンドユーザー向けメインスクリプトは別途実装予定

---

## アーキテクチャ概要

tfplan-viewerはSchema読み込みと3つのPhaseから構成される:

- **Schema読み込み** - リソースタイプ別に分割されたschemaファイルの統合読み込み
1. **Phase 1: データ抽出** - Terraform plan JSONとschema dictから構造化データを抽出
2. **Phase 2: データ加工** - 特殊リソース処理、参照解決、表示用データ変換
3. **Phase 3: HTML生成** - HTMLテーブルとファイル構造の生成

各モジュールは独立して実装され、テスト可能。

---

## Schema読み込み

### モジュール
- `lib/schema_loader.py`

### 入力
- schemaディレクトリ（`schema/d*/*.json`）

### 出力
- Terraform標準形式のschema dict

### 責任
- `schema/d*/`配下のリソースタイプ別JSONファイルを統合読み込み
- 同じリソースタイプが複数バージョンにある場合、最新のdXXXXを優先（警告表示）
- 詳細は[schema_script.md](schema_script.md)を参照

---

## Phase 1: データ抽出

### モジュール
- `lib/data_extraction.py`

### 入力
- `plan.json` - Terraform planの出力（JSON形式）
- schema dict - `schema_loader.load_merged_schema()`の戻り値（Terraform標準形式）

### 出力
- Pythonリスト（pickleファイル）
- 各リソースは以下の構造:
```python
{
  "module": str | None,           # モジュール名 (例: "module.network")
  "address": str,                 # リソースのフルアドレス
  "type": str,                    # リソースタイプ (例: "aws_iam_role")
  "name": str,                    # リソース名
  "values": dict                  # OriginValueオブジェクトを含む辞書
}
```

### 責任
- schema dictから非computed属性を抽出
- plan.jsonから各リソースの値を取得
- OriginValueオブジェクトの生成（値、参照、description、required情報を保持）
- モジュール変数（`var.xxx`）の解決
- ネスト構造（dict/list）の保持

### OriginValueデータクラス
```python
class OriginValue:
  value: Any           # 実際の値
  reference: str       # 参照先アドレス (例: "aws_iam_policy.xxx")
  description: str     # 属性の説明
  required: bool       # 必須属性かどうか
```

---

## Phase 2: データ加工

Phase 2は3つのサブフェーズに分割される:

### Phase 2-1: 特殊リソース処理

**モジュール**: `lib/special_processor.py`

**入力**: Phase 1の出力（OriginValueオブジェクトを含むリスト）

**出力**: 同じ形式（特殊リソースが親リソースにマージされた状態）

**責任**:
- 従属リソースを親リソースに統合
  - 例1: `aws_iam_role_policy_attachment` → `aws_iam_role`の`attached_policies`配列
  - 例2: `aws_subnet` → `aws_vpc`の`subnets`配列
- 設定ファイル（`lib/special_config.py`）に基づく処理

**設定例**:
```python
{
  "type": "aws_iam_role_policy_attachment",
  "merge_into": {
    "parent_type": "aws_iam_role",
    "parent_key": "attached_policies",
    "match_by": "role",
    "exclude_keys": ["role"]
  }
}
```

---

### Phase 2-2: 参照解決

**モジュール**: `lib/reference_resolver.py`

**入力**: Phase 2-1の出力

**出力**: 同じ形式（OriginValue.referenceが識別子に解決された状態）

**責任**:
- すべての参照を人間が読める識別子に解決
  - 通常参照: `aws_iam_policy.xxx` → ポリシー名
  - モジュール参照: `module.network.vpc_id` → VPC名（tags.Name）
- 解決できない参照はそのまま保持

**識別子の決定ルール**:
- リソースタイプごとの識別子属性を使用（`lib/identifier_config.py`）
- デフォルトは`name`属性
- 例: `aws_vpc`は`tags.Name`、`aws_s3_bucket`は`bucket`
- カスタム設定: `--identifier-config`オプションでJSON設定可能

---

### Phase 2-3: View変換

**モジュール**: `lib/view_converter.py`

**入力**: Phase 2-2の出力

**出力**: Pythonリスト（ViewValueオブジェクトを含む）
```python
{
  "resource_type": str,
  "resource_name": str,
  "values": dict      # ViewValueオブジェクトを含む
}
```

**責任**:
- OriginValue → ViewValue変換
- 参照を "(ref) identifier" 形式に変換
- 除外属性の削除（デフォルト: `tags_all`）
- 内部情報（address, module）の除去

**ViewValueデータクラス**:
```python
class ViewValue:
  value: Any           # 表示用の値（参照は "(ref) xxx" 形式）
  description: str     # 属性の説明
  required: bool       # 必須属性かどうか
```

---

## Phase 3: HTML生成

Phase 3は2つのサブモジュールで構成される:

### Phase 3-1: テーブル生成

**モジュール**: `lib/table_generator.py`

**入力**: Phase 2-3の出力（ViewValueオブジェクトを含むリスト）

**出力**: HTML文字列（テーブルのみ）

**責任**:
- リソースデータからHTMLテーブルを生成
- 2種類のテーブル形式:
  - **individual型**: 1リソースを詳細表示（縦方向のパラメータリスト）
  - **list型**: 複数リソースを一覧表示（横方向の表形式）
- ネスト構造の表現（rowspan/colspan）
- 参照の視覚的表示（`→ identifier`）

---

### Phase 3-2: ファイル配置

**モジュール**: `lib/file_organizer.py`

**入力**: Phase 2-3の出力

**出力**: HTMLファイル群（ディレクトリ構造）

**責任**:
- リソースタイプごとにファイルをグループ化
- ファイルパスの決定（`lib/resource_config.py`の設定に基づく）
- 各HTMLファイルの生成（table_generatorを使用）
- 階層構造のindex.html生成
- ファイルの書き込み

**出力例**:
```
html_output/
├── index.html
├── aws/
│   ├── iam/
│   │   ├── role.html
│   │   └── policy.html
│   ├── s3/
│   │   └── bucket.html
│   └── vpc/
│       └── vpc.html
```

---

## 設定ファイル

### special_config.py
従属リソースの統合設定

- デフォルト設定: モジュール内の`SPECIAL_RESOURCE_TYPES`
- 外部設定: JSON形式（オプション）
- 各設定項目:
  - `type`: 従属リソースタイプ
  - `merge_into.parent_type`: 親リソースタイプ
  - `merge_into.parent_key`: 統合先の属性名
  - `merge_into.match_by`: マッチング条件（親を特定する属性）
  - `merge_into.exclude_keys`: 除外する属性

### identifier_config.py
参照解決時のリソース識別子設定

- デフォルト設定: モジュール内の`RESOURCE_IDENTIFIER_ATTRIBUTES`
- 外部設定: JSON形式（オプション）
- リソースタイプごとの識別子属性を定義（例: `aws_vpc`は`tags.Name`）
- デフォルトは`name`属性

### resource_config.py
HTML生成の設定

- ファイルパス: リソースタイプ → HTMLファイルパスのマッピング
- テーブル形式: individual/list の決定
- 列幅: list型テーブルの列幅設定
- ソートキー: リソースのソート順
- collapsible設定: 折りたたみ可能なパラメータの指定

---

## データフロー

```
schema/d*/*.json
        ↓
   [Schema読み込み]
   schema_loader.py
        ↓ (schema dict)
plan.json + schema dict
        ↓
   [Phase 1: データ抽出]
   data_extraction.py
        ↓ (pickle)
   OriginValueを含むリスト
        ↓
   [Phase 2-1: 特殊リソース処理]
   special_processor.py
        ↓ (pickle)
   統合済みリスト
        ↓
   [Phase 2-2: 参照解決]
   reference_resolver.py
        ↓ (pickle)
   参照解決済みリスト
        ↓
   [Phase 2-3: View変換]
   view_converter.py
        ↓ (JSON)
   ViewValueを含むリスト
        ↓
   [Phase 3-1: テーブル生成]
   table_generator.py
        ↓ (HTML文字列)
   [Phase 3-2: ファイル配置]
   file_organizer.py
        ↓
   HTMLファイル群
```

---

## テスト・検証

### テストスクリプトの使い方

`tests/`ディレクトリに共通テストスクリプトがあり、引数でテストディレクトリを指定する：

```bash
cd tests

# 個別Phaseのテスト
./phase1_test.sh test001
./phase2_1_test.sh test001
./phase2_2_test.sh test001
./phase2_3_test.sh test001
./phase3_test.sh test001

# 1つのテストの全Phase実行
./run_all_phases.sh test001

# 全テスト実行（test001〜test004）
./run_all_tests.sh
```

### 個別Phaseモジュールの直接実行
各モジュールは`test()`関数を持ち、単独で実行可能（テスト・デバッグ用）：

```bash
cd tests/test001

# Phase 1
python3 ../../lib/data_extraction.py plan.json schema.json \
  --pickle-dump extracted.pkl \
  --output extracted.json

# Phase 2-1
python3 ../../lib/special_processor.py extracted.pkl --pickle-load \
  --pickle-dump special.pkl \
  --output special.json

# Phase 2-2
python3 ../../lib/reference_resolver.py special.pkl --pickle-load \
  --pickle-dump reference.pkl \
  --output reference.json

# Phase 2-3
python3 ../../lib/view_converter.py reference.pkl --pickle-load \
  --pickle-dump view.pkl \
  --output view.json

# Phase 3
python3 ../../lib/file_organizer.py view.pkl html_output --pickle-load
```

### 統合テスト（メインスクリプト）
```bash
cd tests/test001
../../bin/tfplan-viewer.py -p plan.json -s schema -o html_output
```

---

## 拡張ポイント

### 新しい特殊リソースの追加
`lib/special_config.py`の`SPECIAL_RESOURCE_TYPES`に設定を追加

### 新しいリソースタイプの識別子
`lib/identifier_config.py`の`RESOURCE_IDENTIFIER_ATTRIBUTES`に追加、またはJSON設定ファイルで指定

### 新しいファイル配置ルール
`lib/resource_config.py`の`FILE_PATH_CONFIG`に追加

### 新しいテーブル形式
`lib/table_generator.py`に生成関数を追加

---

## テストケース

`tests/`ディレクトリに各テストケースのデータを配置:

- `test001/` - 基本的なリソース（IAM Role + S3 Bucket）
- `test002/` - リソース間参照
- `test003/` - モジュール構造
- `test004/` - 複雑な参照

各テストケースにはTerraformの`main.tf`、`plan.json`、`schema.json`が含まれ、全Phaseを通して実行可能。

---

## ライセンス

MIT License
