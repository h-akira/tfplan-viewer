# 完了した作業

## 1. lib/data_extraction.py の実装

### 実装内容

#### 1. OriginValue Class
- plan.jsonとschema.jsonから取得した生データを保持するデータクラス
- フィールド:
  - `value`: 実際の値（参照の場合はNone）
  - `reference`: 参照先アドレス（参照でない場合はNone）
  - `required`: 必須属性かどうか
  - `description`: schema.jsonから取得したdescription
- `to_dict()`: JSON シリアライズ用メソッド

#### 2. extract_data() 関数
主要な処理関数。以下の機能を実装:

**入力**:
- `plan_json`: Terraform plan JSON (dict)
- `schema_json`: Terraform provider schema JSON (dict)

**処理フロー**:
1. schema.jsonをベースに処理対象の属性を特定
2. computed-only属性を除外（`computed=true かつ required!=true かつ optional!=true`）
3. plan.jsonのplanned_valuesとconfigurationから値と参照を取得
4. ネスト構造を保持し、最末端の値のみOriginValueに変換

**出力**:
```python
[
  {
    "module": str,      # モジュール名（rootの場合はNone）
    "address": str,     # リソースフルアドレス
    "type": str,        # リソースタイプ
    "name": str,        # リソース名
    "values": dict      # OriginValueインスタンスを含むネスト構造
  },
  ...
]
```

**主要機能**:
- モジュール対応（root_moduleとchild_modules）
- 参照の抽出（リソース参照のみ、var/data/local等は除外）
- ネスト構造の保持（dict/listはそのまま、最末端のみOriginValue化）
- 警告システム

#### 3. 警告システム
以下のケースで標準エラー出力に警告を表示:
- schema.jsonに存在しないがplan.jsonに存在する属性
- required属性がschema.jsonに定義されているがplan.jsonに存在しない場合

#### 4. ヘルパー関数
- `_collect_resources_from_plan()`: planned_valuesからリソース収集
- `_build_module_variable_map()`: モジュール変数のマッピング構築（var → 参照元）
- `_extract_config_expressions()`: configurationから参照情報抽出
- `_get_resource_schema()`: リソースタイプのschema取得
- `_get_non_computed_attributes()`: computed-only属性の除外
- `_extract_values()`: 属性値の抽出とOriginValue化
- `_extract_resource_address()`: 参照からリソースアドレス抽出、モジュール変数解決
- `_process_value()`: 再帰的な値処理（ネスト対応）
- `_serialize_for_json()`: JSON出力用のシリアライズ

#### 5. test() 関数
argparseを使用したCLIテスト機能:
```bash
python lib/data_extraction.py <plan.json> <schema.json> [--output <file>]
```

### テストケース

#### tests/data_extraction/sample001/
**内容**: 基本的なリソース
- IAM Role, IAM Policy, S3 Bucket
- ネスト構造（tags）のテスト

**テスト結果**: ✅ 正常動作

#### tests/data_extraction/sample002/
**内容**: リソース間参照のテスト
- IAM Role, IAM Policy（複数）, IAM Role Policy Attachment
- 参照例: `aws_iam_role.lambda_role`, `aws_iam_policy.s3_access_policy.arn`

**テスト結果**: ✅ 正常動作

## 2. lib/formatting_data.py の実装

### 実装内容

#### 1. ViewValue Class
- 表示用に整形されたデータを保持するデータクラス
- フィールド:
  - `value`: 表示用の値（参照は "(ref) identifier" 形式）
  - `description`: 説明文
  - `required`: 必須属性かどうか
- `to_dict()`: JSON シリアライズ用メソッド

#### 2. format_data() 関数
OriginValueからViewValueへの変換を実行:

**入力**: `extracted_data` (data_extraction.pyの出力)

**処理フロー**:
1. 特殊処理対象リソースの分離（aws_iam_role_policy_attachment）
2. 特殊処理の実行（IAM Roleへの統合）
3. OriginValue → ViewValue 変換（参照解決）
4. table_type決定
5. JSON出力用データ作成

**出力**:
```python
[
  {
    "resource_type": str,
    "resource_name": str,
    "table_type": str,      # "individual" or "list"
    "values": dict          # ViewValueインスタンスを含むネスト構造
  },
  ...
]
```

#### 3. 参照解決機能

**RESOURCE_IDENTIFIER_ATTRIBUTES**:
リソースタイプごとに識別子となる属性を定義:
- `aws_iam_role`: name
- `aws_iam_policy`: name
- `aws_s3_bucket`: bucket
- `aws_vpc`: tags.Name
- `aws_subnet`: tags.Name
- `aws_instance`: tags.Name

**_resolve_reference() 関数**:
Terraform参照を実際のリソース名に変換:
```
aws_iam_policy.example → (ref) example-policy-name
```

**_get_resource_identifier() 関数**:
ネスト属性（tags.Name等）に対応した識別子取得

#### 4. 特殊処理: aws_iam_role_policy_attachment

**処理内容**:
- IAM Role Policy Attachmentを独立したリソースとして出力せず、IAM Roleに統合
- IAM Roleの `attached_policies` 配列に policy_arn を追加

**実装**: `_process_special_aws_iam_role_policy_attachment()`
- roleフィールドから参照先IAM Roleを特定（参照/値の両方に対応）
- policy_arnをViewValueとして配列に追加

#### 5. table_type決定

**TABLE_TYPE_LIST リスト**:
一覧表示が望ましいリソースタイプを定義（現在は未実装、全て individual）

**_determine_table_type() 関数**:
リソースタイプから表示形式を決定

### テスト結果

- ✅ 参照解決が正常動作（aws_iam_policy.example → example-policy-name）
- ✅ ネスト属性参照の解決（tags.Name）
- ✅ aws_iam_role_policy_attachmentの統合処理
- ✅ ViewValue変換
- ✅ JSON出力

## 3. lib/html_view.py の実装（基本版）

### 実装内容

#### 1. Individual型テーブル生成

**_generate_individual_table() 関数**:
1リソースを詳細に表示するテーブル生成

**主要機能**:
- ネスト構造の展開（dict/list）
- 配列インデックスの1始まり表示
- rowspanによるセル結合
- 参照値の特殊表示（`(ref) xxx` → 青色矢印）
- null値の特殊表示（グレー斜体）

**処理ステップ**:
1. `_flatten_values()`: ネスト構造をフラット化
2. `_structure_attributes()`: 属性名をレベル構造に解析
3. `_get_max_depth()`: 最大ネスト深度を計算
4. rowspan計算とHTML生成

#### 2. HTML/CSSスタイル

**デザイン**: GitHub風
- モノスペースフォント（コード表示用）
- ホバー効果
- カラーコーディング（必須=赤、参照=青、null=グレー）

### テスト結果

- ✅ ネスト構造の正しい表示
- ✅ 配列インデックスの表示（1, 2, 3...）
- ✅ rowspanによるセル結合
- ✅ 参照値の特殊表示
- ✅ sample001, sample002で動作確認

## 4. リソース設定システムの実装（2025-12-15）

### lib/resource_config.py の実装

#### 1. RESOURCE_CONFIGS リスト
リソースタイプごとの設定を定義:
- **resource_types**: 対象リソースタイプ（複数指定可）
- **file_path**: 出力先HTMLファイル（例: "aws/iam/role.html"）
- **priority**: 同一ファイル内での優先順位（低い方が先）
- **sort_by**: ソートキー（"name", "tags.Name", "bucket"など）
- **special_parameters**: 展開可能パラメータの設定

#### 2. 展開可能パラメータ機能

**make_collapsible() 関数**:
大きなJSON値を折りたたみ表示に変換:
- HTML5の `<details>`/`<summary>` 要素を使用
- JSON値は自動整形（indent=2）
- JavaScriptなしで動作

**対応パラメータ**:
- aws_iam_role: assume_role_policy, inline_policy
- aws_iam_policy: policy
- aws_s3_bucket_policy: policy
- aws_lambda_function: environment
- aws_instance: user_data

#### 3. ヘルパー関数

- `get_resource_config()`: リソースタイプから設定取得
- `get_file_path()`: ファイルパス取得
- `get_sort_key()`: ソートキー取得
- `get_priority()`: 優先度取得
- `get_special_parameters()`: 特殊パラメータ設定取得
- `should_collapse_parameter()`: 折りたたみ判定

#### 4. 設定済みリソースタイプ

- **AWS IAM**: role, policy, user, group, inline_policy
- **AWS S3**: bucket, bucket_policy, bucket_versioning, bucket_encryption
- **AWS Lambda**: function, permission
- **AWS VPC**: vpc, subnet, internet_gateway, nat_gateway, route_table
- **AWS EC2**: instance, security_group, security_group_rule, key_pair
- **AWS RDS**: db_instance, db_subnet_group, db_parameter_group
- **AWS CloudWatch**: log_group, metric_alarm

### lib/html_view.py の拡張

#### 1. リソース設定システムとの統合

**_group_resources_by_file() 関数**:
- resource_config.pyを使用してリソースをファイル別にグループ化
- ファイル内でのソート（priority → sort_key → resource_name）

**_generate_file_html() 関数**:
- 個別HTMLファイルの生成
- ネストされたディレクトリに対応した戻りリンク生成

**_generate_index_html() 関数**:
- プロバイダー別の目次ページ生成
- リソース数の表示

#### 2. 展開可能パラメータの実装

**_format_value() 関数の拡張**:
- resource_typeとparam_nameを受け取る
- resource_config.should_collapse_parameter()で判定
- 該当する場合はdetails/summary要素で出力

**CSSの追加**:
- details/summary要素のスタイリング
- .collapsible-contentのスタイル（max-height: 400px、スクロール）

#### 3. ディレクトリ構造生成

**generate_html() 関数の改修**:
- ネストされたディレクトリの自動作成
- 相対パスによる戻りリンク（`../../index.html`）

### 出力構造

```
output/
├── index.html                    # 目次ページ
└── aws/
    ├── iam/
    │   ├── role.html
    │   ├── policy.html
    │   ├── user_group.html
    │   └── inline_policy.html
    ├── s3/
    │   ├── bucket.html
    │   ├── bucket_policy.html
    │   └── bucket_config.html
    ├── lambda/
    │   ├── function.html
    │   └── permission.html
    └── ...
```

### テスト結果

- ✅ ファイル配置が設定通り（aws/iam/role.html など）
- ✅ 展開可能パラメータが動作（assume_role_policy, policy）
- ✅ JSON整形が正しく動作
- ✅ ソート順が正しい（cloudwatch_logs_policy → s3_access_policy）
- ✅ 戻りリンクが正しい（../../index.html）
- ✅ 目次ページのリソース数表示
- ✅ sample001, sample002で正常動作確認

## 5. ドキュメント整備（2025-12-15）

### spec/spec_20251215.md の作成

包括的な仕様書を作成:

#### 主要セクション
1. **概要**: 3ステージパイプラインの説明
2. **アーキテクチャ**: データ構造の変換フロー
3. **リソース設定システム**: 設定項目と例
4. **展開可能パラメータ**: 実装方法と設定
5. **リソースのソート**: 3段階ソートの仕様
6. **参照解決**: 識別子マッピングとネスト属性対応
7. **特殊処理**: aws_iam_role_policy_attachmentの統合
8. **HTMLテーブル形式**: Individual型の詳細仕様
9. **HTMLスタイル**: CSS設計とカラーコード
10. **ディレクトリ構造**: 生成されるファイル構造
11. **使用方法**: コマンドライン実行例
12. **カスタマイズ方法**: 新規リソースタイプの追加手順
13. **制限事項**: 現在の制限と今後の拡張予定

### done.md の更新

完了した作業を時系列で記録:
- lib/data_extraction.py の実装
- lib/formatting_data.py の実装
- lib/html_view.py の実装
- リソース設定システムの実装
- ドキュメント整備

## 検証済み機能の全体像

### データ抽出（data_extraction.py）
✅ schema.jsonベースの属性抽出
✅ computed-only属性の除外
✅ optional+computed属性の常時出力
✅ OriginValueでの値と参照の保持
✅ ネスト構造の保持
✅ モジュール対応
✅ リソース間参照の抽出
✅ モジュール変数参照の解決
✅ モジュールoutput参照の保持

### データ整形（formatting_data.py）
✅ OriginValue → ViewValue 変換
✅ 参照解決（Terraform参照 → リソース名）
✅ ネスト属性参照の解決（tags.Name）
✅ aws_iam_role_policy_attachmentの統合処理
✅ table_type決定
✅ JSON出力

### HTML生成（html_view.py）
✅ Individual型テーブル生成
✅ ネスト構造の展開表示
✅ 配列インデックスの1始まり表示
✅ rowspanによるセル結合
✅ 参照値の特殊表示
✅ リソース設定システムの統合
✅ 展開可能パラメータ（details/summary）
✅ 階層的ディレクトリ構造
✅ リソースのソート（priority → sort_key → name）
✅ 目次ページ生成
✅ 相対パスの戻りリンク
✅ GitHub風デザイン

### リソース設定（resource_config.py）
✅ リソースタイプ別のファイル配置
✅ 優先度とソート設定
✅ 展開可能パラメータの設定
✅ AWS主要サービスの設定（IAM, S3, Lambda, VPC, EC2, RDS, CloudWatch）
✅ ヘルパー関数の実装

## ファイル構成

```
terraform2sheet/
├── lib/
│   ├── data_extraction.py      # ✅ 実装完了
│   ├── formatting_data.py      # ✅ 実装完了
│   ├── html_view.py            # ✅ 実装完了
│   ├── resource_config.py      # ✅ 実装完了（2025-12-15）
│   └── tem.py                  # 実装検討用（不要）
├── spec/
│   ├── spec_20251215.md        # ✅ 作成完了（2025-12-15）
│   └── tem.md                  # 旧仕様（参考）
├── done.md                     # ✅ 更新完了（2025-12-15）
└── tests/
    └── data_extraction/
        ├── sample001/          # ✅ 基本テスト
        ├── sample002/          # ✅ 参照テスト
        ├── sample003/          # ✅ モジュールテスト
        ├── sample004/          # ✅ モジュール参照引数テスト
        └── sample005/          # ✅ モジュールoutput引数テスト
```

## 実装の特徴

### 1. 3ステージパイプライン
各ステージが独立しており、中間JSON出力で検証可能:
- Stage 1: 生データ抽出（OriginValue）
- Stage 2: 表示用整形（ViewValue、参照解決）
- Stage 3: HTML生成（設定ベースのファイル配置）

### 2. 柔軟な設定システム
resource_config.pyで集中管理:
- ファイル配置の自由度
- 複数リソースタイプの同一ファイル配置
- パラメータ単位の表示制御

### 3. 参照解決の高度化
リソースタイプ別の識別子設定:
- 単純属性（name, bucket）
- ネスト属性（tags.Name）
- モジュールoutput（module.xxx.yyy）

### 4. HTML5ネイティブ機能の活用
JavaScriptなしで展開可能パラメータを実現:
- details/summary要素
- CSS:hoverによるインタラクション

### 5. スケーラビリティ
新しいリソースタイプの追加が容易:
- resource_config.pyに設定追加
- RESOURCE_IDENTIFIER_ATTRIBUTESに識別子追加

## 次のステップ（今後の拡張予定）

### 優先度: 高
1. **List型テーブルの実装**
   - 複数リソースを1行ずつ表示
   - _generate_list_table()の実装

2. **差分表示機能**
   - create/update/delete の視覚化
   - plan.jsonのresource_changesを利用

### 優先度: 中
3. **カスタムdescriptionの対応**
   - リソースタイプ別の説明文オーバーライド
   - 日本語説明の追加

4. **フィルタリング・検索機能**
   - JavaScriptによるクライアントサイド検索
   - リソースタイプフィルター

### 優先度: 低
5. **エクスポート機能**
   - CSV出力
   - Excel出力

6. **他クラウドプロバイダー対応**
   - GCP, Azure, etc.

## 注意事項

### computed-only属性の扱い
- `computed=true` かつ `required!=true` かつ `optional!=true` の属性は出力されない
- これは仕様通りの動作

### optional+computed属性の扱い
- `optional=true` かつ `computed=true` の属性は常に出力される
- 値がない場合は `value=None, reference=None`
- 例: id, name_prefix, arn（リソースによる）

### モジュールoutput参照
- `module.xxx.yyy` 形式はそのまま保持される
- 解決は行わない（モジュール内部情報が必要なため）

### 特殊処理の拡張
今後、他のリソースタイプでも特殊処理が必要になる可能性:
- formatting_data.pyのSPECIAL_RESOURCE_TYPESに追加
- 処理関数を実装
