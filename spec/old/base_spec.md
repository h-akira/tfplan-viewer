# tfplan-viewer 基本仕様 (2025-12-16)

## 設計思想

**Phase間のデータ受け渡し**:
- Python関数として使う場合：Pythonオブジェクトを直接受け渡す（推奨）
- CLIとして使う場合：JSONまたはpickleファイルを経由する

**型安全性の確保**:
- OriginValue/ViewValueオブジェクトはPythonクラスとして定義
- Pickle形式を使うことでオブジェクトの型情報を保持
- JSON形式はヒューリスティックで復元（後方互換性のため）

## システム構成

```
plan.json + schema.json
    ↓
[Phase 1] data_extraction.py
    ↓
extracted data (OriginValue objects)
    ├─ output.json    (JSON形式: 後方互換性)
    └─ output.pkl     (Pickle形式: Python objects)
    ↓
[Phase 2] formatting_data.py
    ↓
formatted data (ViewValue objects)
    ├─ formatted.json (JSON形式: 後方互換性)
    └─ formatted.pkl  (Pickle形式: Python objects)
    ↓
[Phase 3] html_view.py
    ↓
HTML出力
```

## 各Phaseの入出力

### [Phase 1] data_extraction.py

**入力**:
- `plan.json`: Terraform plan
- `schema.json`: Provider schema

**出力**:
- **Pythonオブジェクト**: `list[dict]` (OriginValueオブジェクトを含む)
- **JSONファイル**: `output.json` (OriginValueを辞書に変換)
- **Pickleファイル**: `output.pkl` (OriginValueオブジェクトそのまま)

**CLI使用例**:
```bash
# JSON形式（後方互換性）
python lib/data_extraction.py plan.json schema.json --output output.json

# Pickle形式（推奨）
python lib/data_extraction.py plan.json schema.json \
  --output output.json --pickle-dump output.pkl
```

**Python関数として使用**:
```python
from lib.data_extraction import extract_data

result = extract_data(plan_json_dict, schema_json_dict)
# result: list[dict] with OriginValue objects
```

---

### [Phase 2] formatting_data.py

**入力**:
- **Pythonオブジェクト**: Phase 1の出力（OriginValueオブジェクト）
- **JSONファイル**: `output.json` (OriginValueを復元)
- **Pickleファイル**: `output.pkl` (OriginValueオブジェクトを直接ロード)

**出力**:
- **Pythonオブジェクト**: `list[dict]` (ViewValueオブジェクトを含む)
- **JSONファイル**: `formatted.json` (ViewValueを辞書に変換)
- **Pickleファイル**: `formatted.pkl` (ViewValueオブジェクトそのまま)

**CLI使用例**:
```bash
# JSON形式（後方互換性）
python lib/formatting_data.py output.json --output formatted.json

# Pickle形式（推奨）
python lib/formatting_data.py output.pkl --pickle-load \
  --output formatted.json --pickle-dump formatted.pkl
```

**Python関数として使用**:
```python
from lib.formatting_data import format_data

result = format_data(extracted_data)
# result: list[dict] with ViewValue objects
```

---

### [Phase 3] html_view.py

**入力**:
- **Pythonオブジェクト**: Phase 2の出力（ViewValueオブジェクト）
- **JSONファイル**: `formatted.json` (ヒューリスティックで処理)
- **Pickleファイル**: `formatted.pkl` (ViewValueオブジェクトを直接ロード)

**出力**:
- HTMLファイル群（ディレクトリ構造）

**CLI使用例**:
```bash
# JSON形式（後方互換性）
python lib/html_view.py formatted.json --output html_output

# Pickle形式（推奨）
python lib/html_view.py formatted.pkl --pickle-load --output html_output
```

**Python関数として使用**:
```python
from lib.html_view import generate_html

generate_html(formatted_data, output_dir='html_output', title='My Plan')
```

---

## データクラス

### OriginValue

**責任**: plan.jsonから抽出した生データを保持

```python
class OriginValue:
  value: Any          # 実際の値（参照の場合はNone）
  reference: str      # 参照先アドレス（値の場合はNone）
  required: bool      # 必須属性か
  description: str    # schema.jsonのdescription
```

### ViewValue

**責任**: 表示用に整形されたデータを保持

```python
class ViewValue:
  value: Any          # 表示値（参照は "(ref) identifier"）
  description: str    # カスタムdescriptionで上書き可
  required: bool      # 必須属性か
```

---

## Pickle vs JSON

### Pickleモードのメリット

1. **型安全性**: OriginValue/ViewValueオブジェクトの型情報が保持される
2. **確実性**: ヒューリスティックによる誤判定がない
3. **テスト容易性**: Phase間で中間データを確実に保存・再現できる

### JSONモードのメリット

1. **後方互換性**: 既存のテストデータ・スクリプトがそのまま動作
2. **可読性**: JSONファイルをテキストエディタで確認できる
3. **デバッグ**: 中間データの内容を人間が読める

### 推奨される使い方

- **開発・テスト**: Pickleモード（`--pickle`）を使用
- **デバッグ**: JSONファイルも同時に出力（`--output` + `--pickle-dump`）
- **本番環境**: Python関数として直接呼び出し（ファイルI/O不要）

---

## テスト実行方法

### JSON形式でテスト（後方互換性）

```bash
cd tests
./regenerate_all.sh
```

### Pickle形式でテスト（推奨）

```bash
cd tests
./regenerate_all.sh --pickle
```

### 個別Phaseのテスト

```bash
# Phase 1のみ
python lib/data_extraction.py \
  tests/data_extraction/sample001/plan.json \
  tests/data_extraction/sample001/schema.json \
  --pickle-dump /tmp/test_output.pkl

# Phase 2のみ（Phase 1の出力から）
python lib/formatting_data.py /tmp/test_output.pkl \
  --pickle-load --pickle-dump /tmp/test_formatted.pkl

# Phase 3のみ（Phase 2の出力から）
python lib/html_view.py /tmp/test_formatted.pkl \
  --pickle-load --output /tmp/html_output
```

---

## JSON形式の制限事項

### ViewValueの判定ヒューリスティック

JSONから読み込んだデータは、以下のロジックでViewValueかどうかを判定します：

```python
# html_view.pyでの判定例
if isinstance(obj, dict) and 'value' in obj and 'required' in obj:
  # ViewValueとして扱う
  value = obj['value']
```

**問題**:
もし実際のTerraformデータに`{"value": X, "required": Y}`という形式のオブジェクトがあった場合、ViewValueと誤認される可能性があります。

**対策**:
- Pickleモードを使用する（推奨）
- または、実際にそのようなデータが現れた場合に個別に対処

---

## .gitignoreへの追加推奨

```gitignore
# Pickle files (test artifacts)
*.pkl
```

JSONファイルはデバッグ用に残すことを推奨しますが、pickleファイルはバイナリなのでgitに含めない方が良いでしょう。

---

## まとめ

- **開発時**: Pickleモードでテスト実行（`./regenerate_all.sh --pickle`）
- **デバッグ時**: JSONファイルも出力してテキストエディタで確認
- **本番環境**: Python関数として直接呼び出し
- **後方互換性**: JSON形式も引き続きサポート
