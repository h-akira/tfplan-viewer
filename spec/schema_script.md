# Schema管理スクリプト仕様書

リソースタイプ別にschemaを分割管理し、差分管理とdescription追加を可能にする仕組みの仕様

---

## 概要

Terraform provider schemaを**リソースタイプ単位**で分割し、バージョン管理可能な形で管理する。
これにより、descriptionを手動で追加した後に新しいリソースタイプが追加されても、既存のdescriptionを保持できる。

---

## 現在の問題点

### 従来の方式（schema_dump.py）

```bash
python bin/schema_dump.py -p plan.json -s schema.json -o schema_extracted.json
```

**問題**:
1. schema_extracted.jsonは複数のリソースタイプを1つのJSONに含む
2. descriptionを手動で追加した後、新しいリソースが追加されると**全体が上書き**される
3. どのリソースタイプにdescriptionを追加したか分かりづらい
4. 差分管理が困難

---

## 新しい設計方針

### ディレクトリ構造

```
schema/
├── d0000/                        # 初回抽出（ベースライン）
│   ├── aws_iam_role.json
│   ├── aws_s3_bucket.json
│   └── aws_vpc.json
├── d0001/                        # 差分のみ（新規追加）
│   └── aws_subnet.json           # 新しく追加されたリソース
└── d0002/                        # 差分のみ（descriptionを追加）
    └── aws_iam_role.json         # descriptionを手動で追加して更新
```

**重要**: `d`は`diff`の頭文字で、`d0001`以降は**差分（新規追加・変更されたリソースタイプ）のみ**を保存する。

### 設計原則

1. **リソースタイプ単位での分割**: 各リソースタイプを独立したJSONファイルとして保存
2. **差分管理**: `d0000`（ベースライン）、`d0001`, ... のディレクトリで差分を管理
   - `d0000`: 初回抽出時の全リソースタイプ
   - `d0001`以降: 前バージョンからの差分（新規追加・変更）のみ
3. **差分検出**: 前バージョンとの差分がある場合のみ新しいディレクトリを作成
4. **マージ読み込み**: メインスクリプトは `schema/d*/*.json` を全て読み込んで統合
   - 同じリソースタイプが複数バージョンにある場合、最新のdXXXXを優先

---

## モジュール構成

### lib/schema_loader.py

**責務**: schema/d*/*.jsonの統合読み込み

**主要関数**:

| 関数 | 入力 | 出力 | 説明 |
|------|------|------|------|
| `load_merged_schema(schema_dir)` | schemaディレクトリパス（str） | Terraform標準形式のschema dict | d*/*.jsonを全て読み込み統合 |

**入力**: schemaディレクトリパス（例: `"schema"`）

**出力**: Terraform標準形式のschema dict
```python
{
  "format_version": "1.0",
  "provider_schemas": {
    "registry.terraform.io/hashicorp/aws": {
      "resource_schemas": {
        "aws_iam_role": { ... },
        "aws_s3_bucket": { ... },
        ...
      }
    }
  }
}
```

**処理**:
1. `schema_dir/d*/`をソート順で走査
2. 各`*.json`ファイルを読み込み、`resource_type`と`provider`をキーにdict構築
3. 同じリソースタイプが複数バージョンにある場合、最新のdXXXXを優先し**警告を表示**
4. Terraform標準形式のschema dictとして返す

**戻り値の形式はdata_extraction.pyが受け取る形式と同一**であるため、data_extraction.pyの変更は不要。

**テスト**: `test()`関数で独立テスト可能（rule.md準拠）

---

### bin/schema_manager.py

**責務**: plan.jsonとschema.jsonからリソースタイプ別schemaを抽出し、schema/d*に差分保存

**内部で`lib/schema_loader.py`の`load_merged_schema()`を使用**して既存schemaを読み込む。

#### コマンドライン引数

```bash
# 基本実行
python bin/schema_manager.py -p plan.json -s schema.json

# 出力ディレクトリ指定
python bin/schema_manager.py -p plan.json -s schema.json -o my_schema

# 強制的に新しいバージョンを作成（差分がなくても）
python bin/schema_manager.py -p plan.json -s schema.json --force
```

| 引数 | 説明 | デフォルト |
|------|------|-----------|
| `-p, --plan` | Terraform plan JSONファイル | - |
| `-s, --schema` | Terraform provider schema JSONファイル | - |
| `-o, --output` | schemaファイル保存ディレクトリ | `schema` |
| `--force` | 差分がなくても強制的に新バージョン作成 | False |

---

## 処理フロー

### 1. schemaの分割保存（bin/schema_manager.py）

```
1. plan.jsonからリソースタイプ抽出
   ↓
2. schema.jsonから対象リソースタイプのschemaを取得
   ↓
3. load_merged_schema()で既存の全リソースタイプを読み込み
   ↓
4. 今回抽出したschemaと既存schemaを比較し、差分を検出
   - 新規追加: 既存に存在しないリソースタイプ
   ↓
5. 差分がある場合のみ新しいバージョンディレクトリを作成
   - schema/d*から最新バージョン番号を取得（例: d0005 → 5）
   - 新しいディレクトリ作成（dXXXX+1）
   ↓
6. 差分のみを新しいディレクトリに保存
   - ファイル名: リソースタイプ名.json（例: aws_iam_role.json）
   - 内容: 該当リソースタイプのschema定義のみ
   - **重要**: 既存のschema/d*に存在するリソースタイプは保存しない
```

### 2. schemaの統合読み込み（lib/schema_loader.py）

```
1. 指定されたディレクトリ配下のd*/から全JSONファイルを読み込み
   （d0000, d0001, ... の順）
   ↓
2. リソースタイプごとに最新のバージョンを選択
   - 同じリソースタイプが複数バージョンにある場合、最新のdXXXXを優先
   - **重要**: 重複が検出された場合は警告を表示
   - 例: d0000/aws_iam_role.json と d0002/aws_iam_role.json がある場合
     → d0002/aws_iam_role.json を採用（descriptionが追加された版）
     → 警告: "WARNING: aws_iam_role found in multiple versions (d0000, d0002), using d0002"
   ↓
3. Terraform標準のschema.json形式で統合schemaを返す
```

**マージ例**:
```
schema/d0000/aws_iam_role.json
schema/d0000/aws_s3_bucket.json
schema/d0000/aws_vpc.json
schema/d0001/aws_subnet.json
schema/d0002/aws_iam_role.json  ← d0000と重複

↓ load_merged_schema('schema')の処理

WARNING: aws_iam_role found in multiple versions (d0000, d0002), using d0002

↓ 戻り値（Terraform標準形式）

- aws_iam_role: d0002版を使用
- aws_s3_bucket: d0000版を使用
- aws_vpc: d0000版を使用
- aws_subnet: d0001版を使用
```

---

## ファイル形式

### リソースタイプ別JSONファイル（例: aws_iam_role.json）

```json
{
  "resource_type": "aws_iam_role",
  "provider": "registry.terraform.io/hashicorp/aws",
  "schema": {
    "version": 0,
    "block": {
      "attributes": {
        "arn": {
          "type": "string",
          "description": "Amazon Resource Name (ARN) of the IAM role",
          "computed": true
        },
        "name": {
          "type": "string",
          "description": "Friendly name of the role",
          "optional": true
        },
        ...
      },
      ...
    }
  }
}
```

---

## 差分検出アルゴリズム

### 新バージョン作成の条件

以下のいずれかに該当する場合、新しいバージョンディレクトリ（dXXXX+1）を作成し、**差分のみ**を保存：

1. **新しいリソースタイプが追加された**
   - 既存のschema/d*に存在しないリソースタイプが今回抽出された
   - 例: d0000に3個、今回4個 → 新しい1個をd0001に保存

2. **--forceオプションが指定された**
   - 差分がなくても強制的に新バージョンを作成
   - すべてのリソースタイプを新しいdXXXXに保存（差分管理の原則を無視）

### 差分がない場合

- 新しいバージョンディレクトリは作成しない
- メッセージを表示: `No changes detected. Schema is up to date.`

### リソースタイプの削除について

- plan.jsonから削除されたリソースタイプは検出しない
- 既存のschema/d*にあるリソースタイプは保持される
- 理由: 過去のリソースタイプ定義も参照可能にするため

---

## メインスクリプトとの統合

### bin/tfplan-viewer.py の変更点

- `-s/--schema`オプションはschemaディレクトリ（`d*/`構造）を受け付ける
- デフォルト（省略時）: `schema/`ディレクトリを使用
- `load_merged_schema()`を使用して統合読み込み
- **data_extraction.pyの変更は不要**: `load_merged_schema()`の戻り値はTerraform標準形式

---

## 使用例

### 初回実行

```bash
# plan.jsonからschemaを抽出してschema/d0000/に保存
$ python bin/schema_manager.py -p plan.json -s schema.json

Found 3 resource types in plan.json:
  - aws_iam_role
  - aws_s3_bucket
  - aws_vpc

✓ Created new version: schema/d0000/
✓ Saved 3 resource type schemas
```

### 新しいリソースを追加後

```bash
# 新しいplan.json（aws_subnetが追加された）
$ python bin/schema_manager.py -p plan.json -s schema.json

Found 4 resource types in plan.json:
  - aws_iam_role
  - aws_s3_bucket
  - aws_vpc
  - aws_subnet (new)

Loading existing schemas from schema/d0000/...
  ✓ Loaded 3 existing resource types

Comparing with existing schemas...
  + aws_subnet (added)

✓ Created new version: schema/d0001/
✓ Saved 1 resource type schema (diff only)
```

### descriptionを手動で追加後

```bash
# schema/d0000/aws_iam_role.jsonを直接編集してdescriptionを追加
$ vim schema/d0000/aws_iam_role.json

# 編集後は特に追加の操作は不要
# 次回のメインスクリプト実行時に、load_merged_schema()が編集後のファイルを読み込む
```

**注**: 手動で編集したファイルはそのまま保持され、次回のメインスクリプト実行時に反映される。schema_manager.pyの実行は不要。

### メインスクリプトでの使用

```bash
# デフォルト（-sを省略すると schema/ を使用）
$ python bin/tfplan-viewer.py -p plan.json

# schemaディレクトリ指定
$ python bin/tfplan-viewer.py -p plan.json -s my_schema
```

---

## エラーハンドリング

### schema/d*が存在しない場合

```
ERROR: Schema directory not found: schema/
Please run schema_manager.py first to create schema files.
```

### schema/d*が空の場合

```
ERROR: No schema files found in schema/d*/
Please run schema_manager.py to extract schemas from plan.json and schema.json.
```

### JSONパースエラー

```
ERROR: Failed to parse schema/d0001/aws_iam_role.json: Invalid JSON format
```

---

## テスト方法

### lib/schema_loader.pyの単体テスト

```bash
# test()関数による独立テスト（rule.md準拠）
cd tests/test001
python3 ../../lib/schema_loader.py schema --output merged.json
```

### bin/schema_manager.pyのテスト

```bash
cd tests/test001

# 初回: schema抽出
../../bin/schema_manager.py -p plan.json -s schema.json

# 確認
ls schema/d0000/

# 差分がない場合の確認
../../bin/schema_manager.py -p plan.json -s schema.json
# → "No changes detected" メッセージが表示される

# 強制的に新バージョン作成
../../bin/schema_manager.py -p plan.json -s schema.json --force
# → schema/d0001/ が作成される
```

### メインスクリプトとの統合テスト

```bash
cd tests/test001

# schemaディレクトリ指定で実行
../../bin/tfplan-viewer.py -p plan.json -s schema -o html_output
```

---

## 参考

- [architecture.md](architecture.md) - アーキテクチャ設計
- [main_script.md](main_script.md) - メインスクリプト仕様
- [rule.md](rule.md) - 開発ルール
