# terraform2sheet 仕様書

## 概要

Terraform plan.json を HTML テーブル形式に変換するツール。3段階のパイプライン処理で実装する。

## システム構成

```
plan.json + schema.json
    ↓
[1] 必要データ抽出 (data_extraction.py)
    ↓
中間データ (Value Class)
    ↓
[2] View用データ整形 (formatting_data.py)
    ↓
整形済みデータ
    ↓
[3] HTML View生成 (html_view.py)
    ↓
HTML出力
```

### 処理フロー

1. **必要データ抽出** (`lib/data_extraction.py`)
   - 入力: `plan.json` (dict), `schema.json` (dict)
   - 処理: schema.json をベースに、computed-onlyでない属性（required/optionalな属性）を抽出
   - 出力: OriginValue インスタンスを含む辞書型データ
   - 警告: schema.json と plan.json の不整合を検出

2. **View用データ整形** (`lib/formatting_data.py`)
   - 入力: OriginValue を含む中間データ、オプション設定
   - 処理: OriginValue → ViewValue 変換、参照解決、description上書き、table_type決定、特殊処理、リソースタイプ検証
   - 特殊処理例: `aws_iam_role_policy_attachment` を IAM Role に統合
   - 出力: ViewValue を含む辞書型データ（table_type含む、address等の内部情報は除去済み）

3. **HTML View生成** (`lib/html_view.py`)
   - 入力: 整形済みデータ
   - 処理: HTML テーブル生成
   - 出力: HTML文字列

## ディレクトリ構成

```
terraform2sheet/
├── spec/
│   ├── spec.md              # 本仕様書
│   └── samples/             # HTML出力サンプル
│       ├── sample_normal.html   # 個別型テーブルサンプル
│       └── sample_list.html     # 一覧型テーブルサンプル
├── lib/
│   ├── data_extraction.py   # [1] 必要データ抽出 + OriginValue Class
│   ├── formatting_data.py   # [2] View用データ整形 + ViewValue Class
│   └── html_view.py         # [3] HTML View生成
├── bin/
│   └── terraform2sheet      # メインエントリポイント
└── tests/
    ├── data_extraction/
    │   ├── sample001/       # テストケース1
    │   │   ├── main.tf
    │   │   ├── plan.json
    │   │   └── schema.json
    │   └── sample002/       # テストケース2
    │       └── ...
    ├── formatting_data/
    │   ├── sample001/
    │   │   └── extracted_data.json
    │   └── sample002/
    │       └── ...
    └── html_view/
        ├── sample001/
        │   └── formatted_data.json
        └── sample002/
            └── ...
```

## Value Class

### OriginValue Class

`lib/data_extraction.py` 内で定義。plan.json と schema.json から取得した生データを保持。

```python
# lib/data_extraction.py 内
class OriginValue:
  value: Any           # 実際の値（参照の場合はNone）
  reference: str       # 参照先アドレス（参照でない場合はNone）
  required: bool       # 必須属性か
  description: str     # schema.jsonから取得したdescription
```

**使い分け**:
- **通常の値**: `value=<actual_value>`, `reference=None`
- **参照**: `value=None`, `reference=<address>`

### ViewValue Class

`lib/formatting_data.py` 内で定義。表示用に加工されたデータを保持。

```python
# lib/formatting_data.py 内
class ViewValue:
  value: Any           # 表示値（参照は "(ref) identifier" 形式）
  description: str     # カスタムdescriptionで上書き済み
  required: bool       # 必須属性かどうか（HTML表示で使用）
```

**特徴**:
- 参照は解決済み（`"(ref) identifier"` 形式の文字列）
- description はカスタム値で上書き済み
- required はそのまま引き継ぎ（HTML表示で必須マークを付けるため）
- address などの内部情報は除去済み

## データフロー詳細

### [1] 必要データ抽出

**入力例**

`plan.json` の一部:
```json
{
  "planned_values": {
    "root_module": {
      "resources": [{
        "address": "aws_iam_role.lambda",
        "values": {"name": "lambda-role", "assume_role_policy": "..."}
      }]
    }
  },
  "configuration": {
    "root_module": {
      "resources": [{
        "expressions": {
          "name": {"constant_value": "lambda-role"},
          "assume_role_policy": {"references": ["data.aws_iam_policy_document.lambda_assume"]}
        }
      }]
    }
  }
}
```

`schema.json` の一部:
```json
{
  "provider_schemas": {
    "registry.terraform.io/hashicorp/aws": {
      "resource_schemas": {
        "aws_iam_role": {
          "block": {
            "attributes": {
              "name": {
                "type": "string",
                "description": "Friendly name of the role",
                "optional": true,
                "computed": true
              },
              "assume_role_policy": {
                "type": "string",
                "required": true
              },
              "arn": {
                "type": "string",
                "computed": true
              }
            }
          }
        }
      }
    }
  }
}
```

**処理内容**:
1. **ベースは `schema.json`**: リソースタイプの属性定義を処理対象とする
2. `computed == true` かつ `required != true` かつ `optional != true` の属性は除外
3. 残った属性について:
   - `planned_values` に値がある場合 → 実際の値を取得
   - `planned_values` に値がないが `configuration` にある場合 → 参照情報を取得
   - `planned_values` にも `configuration` にもない場合 → **警告を発する**
4. **逆方向チェック**: `planned_values` に存在するが `schema.json` に存在しない属性 → **警告を発する**

**出力例**:
```python
[
  {
    "module": "root",
    "address": "aws_iam_role.lambda",
    "type": "aws_iam_role",
    "name": "lambda",
    "values": {
      "name": OriginValue(
        value="lambda-role",
        reference=None,
        required=False,  # optional=true, computed=true
        description="Friendly name of the role"  # schema.jsonから取得
      ),
      "assume_role_policy": OriginValue(
        value="...",
        reference="data.aws_iam_policy_document.lambda_assume",  # configurationから取得
        required=True,
        description=""  # schema.jsonにdescriptionなし
      )
      # "arn"は computed=true のみなので除外される
    }
  }
]
```

**ネスト構造の扱い**:
- `values` 内は複雑にネストされた辞書や配列を含むことがある
- ネスト構造はそのまま保持し、**最末端の値のみ** OriginValue に変換
- 例:
```python
"values": {
  "simple_attr": OriginValue(value="text", ...),
  "nested_object": {
    "inner_attr": OriginValue(value="value", ...)
  },
  "array_attr": [
    {"item": OriginValue(value="item1", ...)}
  ]
}
```

### [2] View用データ整形

**入力**:
- OriginValue を含むデータ
- オプション設定（`exclude_keys`, `custom_descriptions`, `strict_mode` 等）

**処理内容**:
1. OriginValue → ViewValue 変換:
   - 参照解決: `reference` フィールドを使って識別子を解決し `"(ref) identifier"` に変換
   - description上書き: カスタム description を指定された属性に適用
   - required引き継ぎ: OriginValueの`required`をViewValueにコピー（HTML表示で必須マークに使用）
   - 不要データ除去: `address`, `module` などの内部情報を除去
2. テーブル形式決定: リソースタイプに応じて `table_type` (individual/list) を決定
3. 特殊処理: リソースタイプ固有の処理
4. リソースタイプ検証: 動作確認済みリソースタイプのチェック

**特殊処理の例**:
- `aws_iam_role_policy_attachment`: 独立したリソースとして残さず、IAM Role に統合
  - 対象の IAM Role に `attached_policies` 配列を追加
  - ポリシー情報を配列要素として格納
  - 元の `aws_iam_role_policy_attachment` リソースは出力から除外

**リソースタイプ検証**:
- 動作確認済みリソースタイプの配列を定義（例: `VERIFIED_RESOURCE_TYPES`）
- 未検証のリソースタイプに対する動作:
  - `strict_mode=True`: エラーを発して処理を停止
  - `strict_mode=False`: 警告を出力して処理を継続（デフォルト）

**description上書きの仕組み**:
- 必要データ抽出段階では schema.json の description のみ（多くが空）
- View用データ整形で `custom_descriptions` オプションにより上書き可能
- 形式: `{"resource_type.attribute": "カスタム説明", ...}`

**出力例** (特殊処理適用前):
```python
[
  {
    "resource_type": "aws_iam_role",
    "resource_name": "lambda",
    "table_type": "list",  # リソースタイプに応じて決定
    "values": {
      "name": ViewValue(
        value="lambda-role",
        description="IAMロール名",  # カスタムdescriptionで上書き
        required=False
      ),
      "assume_role_policy": ViewValue(
        value="...",
        description="AssumeRoleポリシー",
        required=True
      )
    }
  },
  {
    "resource_type": "aws_iam_role_policy_attachment",
    "resource_name": "attach",
    "table_type": "individual",
    "values": {
      "role": ViewValue(
        value="(ref) lambda-role",  # 参照解決済み
        description="アタッチ先IAMロール",
        required=True
      ),
      "policy_arn": ViewValue(
        value="(ref) s3-policy",
        description="ポリシーARN",
        required=True
      )
    }
  }
]
# address, module などの内部情報は除去済み
```

**出力例** (特殊処理適用後):
```python
[
  {
    "resource_type": "aws_iam_role",
    "resource_name": "lambda",
    "table_type": "list",
    "values": {
      "name": ViewValue(
        value="lambda-role",
        description="IAMロール名",
        required=False
      ),
      "assume_role_policy": ViewValue(
        value="...",
        description="AssumeRoleポリシー",
        required=True
      ),
      "attached_policies": [  # 特殊処理で追加
        ViewValue(
          value="(ref) s3-policy",
          description="アタッチ済みポリシー",
          required=False  # 配列要素なのでrequiredは意味を持たない
        )
      ]
    }
  }
  # aws_iam_role_policy_attachment.attach は統合されたため除外
]
```

### [3] HTML View生成

**入力**: 整形済みデータ

**出力**: HTML テーブル

**テーブル形式**:
- **個別型**: 1リソースを詳細に表示（ネスト構造を rowspan で表現）
- **一覧型**: 複数リソースを1行ずつ表示（列幅固定、長いコンテンツは折りたたみ）

**表示形式の決定**:
- formatting_data の段階で、リソースタイプに応じて `table_type` を決定
- 一覧型 (`table_type="list"`) 対象リソース例: `aws_iam_role`, `aws_iam_policy`, `aws_s3_bucket` 等
- 個別型 (`table_type="individual"`) はそれ以外のリソースタイプ

**共通仕様**:
- 参照は `(ref)` プレフィックスで視覚的に区別
- ViewValue の description を説明列に表示
- ViewValue の required が True の場合、項目名に必須マーク（例: `*`）を表示

**サンプル**:
- [個別型サンプル](samples/sample_normal.html)
- [一覧型サンプル](samples/sample_list.html)

## インターフェース定義

### data_extraction.py

```python
class OriginValue:
    """Data class for original values from plan.json and schema.json"""
    def __init__(self, value=None, reference=None, required=False, description=""):
        self.value = value
        self.reference = reference
        self.required = required
        self.description = description

def extract_data(plan_json: dict, schema_json: dict) -> list:
    """
    Extract non-computed attributes from plan.json using schema.json.

    Returns:
        list: [
          {
            "module": str,
            "address": str,
            "type": str,
            "name": str,
            "values": dict  # Nested structure with OriginValue instances at leaf nodes
          },
          ...
        ]
    """
    pass
```

### formatting_data.py

```python
class ViewValue:
    """Data class for view-ready values with resolved references"""
    def __init__(self, value, description="", required=False):
        self.value = value
        self.description = description
        self.required = required

def format_data(extracted_data: list, options: dict = None) -> list:
    """
    Convert OriginValue to ViewValue with reference resolution and special processing.

    Args:
        extracted_data: Output from extract_data() (list with OriginValue)
        options: Optional settings
            - exclude_keys: List[str] - Keys to exclude from output
            - custom_descriptions: dict - Custom descriptions to override
              Format: {"resource_type.attribute": "description", ...}
              Example: {"aws_iam_role.name": "IAMロール名"}
            - strict_mode: bool - Fail on unverified resource types (default: False)

    Returns:
        list: [
          {
            "resource_type": str,  # "type" from input
            "resource_name": str,  # "name" from input
            "table_type": str,  # "individual" or "list" - table format type
            "values": dict  # ViewValue instances at leaf nodes
          },
          ...
        ]
        # "module" and "address" are removed

    Processing:
        1. OriginValue → ViewValue conversion (resolve references, override descriptions, copy required)
        2. Remove internal metadata (module, address, etc.)
        3. Determine table_type based on resource type
        4. Apply special processing (e.g., merge aws_iam_role_policy_attachment)
        5. Verify resource types

    Special processing:
        - aws_iam_role_policy_attachment: Merged into IAM Role as "attached_policies"
        - (Future resource types can be added)
    """
    pass
```

### html_view.py

```python
def generate_html(formatted_data: list) -> str:
    """
    Generate HTML table from formatted data.

    Args:
        formatted_data: Output from format_data() (list of resources)

    Returns:
        str: HTML string
    """
    pass
```

## 設計原則

1. **単一責任**: 各モジュールは1つの責任のみを持つ
2. **疎結合**: OriginValue / ViewValue を介して各段階を独立させる
3. **明確な責任分離**:
   - OriginValue: 生データの保持（参照アドレス、schema情報）
   - ViewValue: 表示用データの保持（解決済み参照、カスタムdescription）
4. **テスタビリティ**: 各段階を個別にテスト可能
5. **拡張性**: 特殊処理は formatting_data.py に集約し、追加が容易

## テストコード構成

### テストディレクトリ構造

```
tests/
├── data_extraction/
│   ├── sample001/           # IAMロールとポリシーアタッチメント
│   │   ├── main.tf          # Terraformコード
│   │   ├── plan.json        # terraform plan -out=tfplan && terraform show -json tfplan
│   │   └── schema.json      # terraform providers schema -json
│   ├── sample002/           # S3バケットとCORS設定
│   │   └── ...
│   └── sample003/           # VPCとサブネット（モジュール）
│       └── ...
├── formatting_data/
│   ├── sample001/
│   │   └── extracted_data.json  # data_extraction の出力
│   └── sample002/
│       └── ...
└── html_view/
    ├── sample001/
    │   └── formatted_data.json  # formatting_data の出力
    └── sample002/
        └── ...
```

### 各libファイルの構成

各 `lib/*.py` ファイルは以下の構成とする:

```python
# lib/data_extraction.py の例

def extract_data(plan_json: dict, schema_json: dict) -> list:
    """メイン処理"""
    # 実装...
    pass

# ... その他の関数 ...

def test():
    """テスト関数"""
    import argparse
    parser = argparse.ArgumentParser(description='Test data extraction')
    parser.add_argument('plan_json', help='Path to plan.json')
    parser.add_argument('schema_json', help='Path to schema.json')
    parser.add_argument('--output', help='Output file path (optional)')
    args = parser.parse_args()

    # JSONファイル読み込み
    with open(args.plan_json) as f:
        plan_json = json.load(f)
    with open(args.schema_json) as f:
        schema_json = json.load(f)

    # メイン処理実行
    result = extract_data(plan_json, schema_json)

    # 結果出力
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
    else:
        print(json.dumps(result, indent=2))

if __name__ == '__main__':
    test()
```

### テスト実行例

```bash
# data_extraction のテスト
python lib/data_extraction.py \
  tests/data_extraction/sample001/plan.json \
  tests/data_extraction/sample001/schema.json \
  --output tests/data_extraction/sample001/output.json

# formatting_data のテスト
python lib/formatting_data.py \
  tests/formatting_data/sample001/extracted_data.json \
  --output tests/formatting_data/sample001/output.json

# html_view のテスト
python lib/html_view.py \
  tests/html_view/sample001/formatted_data.json \
  --output tests/html_view/sample001/output.html
```

**利点**:
- 各モジュールを個別にテスト可能
- コマンドラインから直接実行可能
- 実装とテストが同じファイルに存在し、メンテナンスが容易
- テストケースごとに独立したディレクトリで管理

## 実装順序

1. `lib/data_extraction.py` - OriginValue Class + データ抽出実装 + test()
   - `tests/data_extraction/sample001/` - テストケース作成
2. `lib/formatting_data.py` - ViewValue Class + データ整形実装 + test()
   - `tests/formatting_data/sample001/` - テストケース作成
3. `lib/html_view.py` - HTML生成実装 + test()
   - `tests/html_view/sample001/` - テストケース作成
4. `bin/terraform2sheet` - エントリポイント
5. 追加テストケース作成（sample002, sample003, ...）

## エラー処理と警告

### データ抽出時の警告

1. **schema.json に存在するが plan.json に存在しない属性**:
   - 警告メッセージ例: `"WARNING: Attribute 'tags' in resource 'aws_iam_role.lambda' defined in schema but missing in plan"`
   - 原因: 属性が設定されていない、または条件によりスキップされた
   - 動作: 警告を出力して処理を継続

2. **plan.json に存在するが schema.json に存在しない属性**:
   - 警告メッセージ例: `"WARNING: Attribute 'unknown_field' in resource 'aws_iam_role.lambda' found in plan but not in schema"`
   - 原因: schema.json のバージョン不一致やプロバイダ定義の欠落
   - 動作: 警告を出力して該当属性をスキップ

### データ整形時の警告/エラー

**未検証のリソースタイプ**:
- `strict_mode=False` (デフォルト):
  - 警告メッセージ例: `"WARNING: Resource type 'aws_unknown_service.resource' is not verified"`
  - 動作: 警告を出力して処理を継続（特殊処理なしで通常処理）
- `strict_mode=True`:
  - エラーメッセージ例: `"ERROR: Resource type 'aws_unknown_service.resource' is not verified (strict mode)"`
  - 動作: エラーを発して処理を停止

## 制約事項

- Terraform 1.0以降を対象
- AWS Provider 5.0以降を想定
- 大規模プラン（1000リソース超）はパフォーマンス検証が必要
- plan.json と schema.json は同じ Terraform 実行で生成されたものを使用すること
