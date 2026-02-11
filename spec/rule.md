# tfplan-viewer 開発ルール

本プロジェクトの開発における規約とルールを定義する。

---

## コーディング規約

### モジュール設計原則

#### lib/配下のモジュール

**禁止事項**:
- `main()`関数の定義は禁止

**理由**:
- lib/配下のモジュールは**ライブラリ**として設計される
- エントリーポイントとして実行する場合は`test()`関数を使用する
- `main()`という名前はメインスクリプト（bin/配下）専用

**許可されるもの**:
- モジュール関数（例: `extract_data()`, `process_special_resources()`）
- **テスト・デバッグ用の`test()`関数**
- `if __name__ == '__main__': test()`によるスクリプト実行
- `argparse`によるコマンドライン引数パース（`test()`関数内で使用）
- ヘルパー関数（プライベート関数: `_function_name()`）
- データクラス、定数

**test()関数の用途**:
- モジュール単体のテスト・デバッグ
- 開発時の動作確認
- サンプルデータでの実行確認

**例**:
```python
# lib/data_extraction.py

def extract_data(plan_json, schema_json):
    """Main module function"""
    # 処理...
    pass

def test():
    """Test function for development and debugging"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('plan_file')
    parser.add_argument('schema_file')
    args = parser.parse_args()

    # テスト実行
    with open(args.plan_file) as f:
        plan_json = json.load(f)
    with open(args.schema_file) as f:
        schema_json = json.load(f)

    result = extract_data(plan_json, schema_json)
    print(f"Extracted {len(result)} resources")

if __name__ == '__main__':
    test()
```

---

#### bin/配下のスクリプト

**必須事項**:
- `main()`関数を定義する
- `if __name__ == '__main__': main()`でエントリーポイントを提供
- コマンドライン引数のパースを行う（`argparse`）
- lib/モジュールの関数を組み合わせて処理を実行

**設計方針**:
- エンドユーザー向けのインターフェースを提供
- lib/モジュールを組み合わせて完全な処理フローを実現
- エラーハンドリングとユーザーフレンドリーなメッセージ出力

---

## データフロー規約

### 中間データの永続化

**Pickle vs JSON vs メモリ内**:

| 用途 | フォーマット | 目的 |
|------|-------------|------|
| test()関数でのPhase間データ保存 | **Pickle** | オブジェクト構造を保持（テスト・デバッグ用） |
| 人間による検証・デバッグ | **JSON** | 可読性のため（テスト・デバッグ用） |
| メインスクリプトでのPhase間受け渡し | **メモリ内** | 中間ファイル不要 |

**重要な原則**:
- **メインスクリプト（bin/）では中間ファイルを生成しない** - すべてメモリ内で処理
- **Pickleファイルはテスト用のみ** - Phase別テスト（tests2/）でPhase間のデータ検証に使用
- **JSONファイルもテスト用のみ** - 人間がデータ内容を確認するため
- Phaseモジュールの`test()`関数では、pickleとJSON両方を出力可能にする（テスト・開発用）

---

## Phase間のデータ形式

### Phase 1 → Phase 2-1

- **形式**: Pythonリスト（OriginValueオブジェクトを含む）
- **メインスクリプト**: メモリ内で直接受け渡し
- **テスト（test()関数）**: pickle保存可能

### Phase 2-1 → Phase 2-2

- **形式**: Pythonリスト（OriginValueオブジェクト、特殊リソース処理済み）
- **メインスクリプト**: メモリ内で直接受け渡し
- **テスト（test()関数）**: pickle保存可能

### Phase 2-2 → Phase 2-3

- **形式**: Pythonリスト（OriginValueオブジェクト、参照解決済み）
- **メインスクリプト**: メモリ内で直接受け渡し
- **テスト（test()関数）**: pickle保存可能

### Phase 2-3 → Phase 3

- **形式**: Pythonリスト（ViewValueオブジェクトを含む）
- **メインスクリプト**: メモリ内で直接受け渡し
- **テスト（test()関数）**: pickle保存可能
- **注意**: JSON出力（test()関数）時は`_serialize_for_json()`で辞書に変換されるが、これは人間による検証用のみ

### Phase 3の処理

- **入力**: ViewValueオブジェクトを含むPythonリスト
- **処理**: ViewValueオブジェクトを直接扱う
- **出力**: HTMLファイル群

---

## テストの設計方針

### tests2/（Phase別テスト）

- 各Phaseモジュールを個別にテスト
- 各モジュールの`test()`関数を実行
- 中間データをpickleとJSON両方で出力（検証用）
- 各Phaseのexec_all_tests.shで全サンプルを実行

### tests3/（統合テスト）

- メインスクリプト（bin/tfplan-viewer.py）の統合テスト
- 中間ファイルは生成せず、メモリ内で全Phase実行
- 最終的なHTML出力のみを生成

---

## 命名規約

### 関数名の使い分け

| 関数名 | 用途 | 使用場所 |
|--------|------|----------|
| `main()` | エンドユーザー向けエントリーポイント | bin/配下のみ |
| `test()` | テスト・デバッグ用エントリーポイント | lib/配下のみ |
| `extract_data()` などの具体的な名前 | モジュールの主要機能 | lib/, bin/ 両方 |

---

## 違反例と修正例

### ❌ 違反例: lib/モジュールにmain()を定義

```python
# lib/file_organizer.py (悪い例)
def organize_html_files(view_data, output_dir, title):
    # 処理...
    pass

def main():  # ← 禁止！main()はbin/配下専用
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    organize_html_files(...)

if __name__ == '__main__':
    main()
```

### ✅ 正しい例: test()関数を使用

```python
# lib/file_organizer.py (良い例)
def organize_html_files(view_data, output_dir, title):
    """
    Organize HTML files from view data

    Args:
        view_data: List of resources with ViewValue objects
        output_dir: Output directory path
        title: HTML page title

    Returns:
        Dict with statistics
    """
    # 処理...
    return stats

def test():
    """Test function for development and debugging"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file')
    parser.add_argument('--output-dir', default='test_output')
    args = parser.parse_args()

    # テスト実行
    with open(args.input_file, 'rb') as f:
        view_data = pickle.load(f)

    organize_html_files(view_data, args.output_dir, 'Test')

if __name__ == '__main__':
    test()
```

### ✅ 正しい例: メインスクリプト

```python
# bin/tfplan-viewer.py (良い例)
from lib.file_organizer import organize_html_files

def main():  # ← bin/配下ではmain()を使用
    parser = argparse.ArgumentParser()
    args = parser.parse_args()

    # lib関数を呼び出し
    view_data = load_view_data()
    organize_html_files(view_data, args.output_dir, args.title)

if __name__ == '__main__':
    main()
```

---

## 参考

- [architecture.md](architecture.md) - アーキテクチャ設計
- [main_script.md](main_script.md) - メインスクリプト仕様
