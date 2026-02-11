# Schema JSONファイル形式

## ファイル構造

```json
{
  "resource_type": "aws_iam_role",
  "provider": "registry.terraform.io/hashicorp/aws",
  "schema": {
    "version": 0,
    "block": {
      "attributes": {
        "name": {
          "type": "string",
          "description": "ここに日本語の説明を追加する",
          "description_kind": "plain",
          "optional": true,
          "computed": true
        },
        "arn": {
          "type": "string",
          "description_kind": "plain",
          "computed": true
        }
      },
      "block_types": {
        "inline_policy": {
          "nesting_mode": "set",
          "block": {
            "attributes": {
              "name": {
                "type": "string",
                "description": "ネストされた属性にも追加",
                "description_kind": "plain",
                "optional": true
              }
            }
          }
        }
      },
      "description_kind": "plain"
    }
  }
}
```

## description追加ルール

- `"description"` キーに日本語テキストを設定する
- `"description_kind"` は既存のまま変更しない（別物）
- `computed: true` かつ `optional` がないもの（読み取り専用）はスキップ
- `computed: true` かつ `optional: true` のもの（設定可能だが自動算出もされる）は対象
- 英語のdescriptionは日本語で上書きする
- 既存の日本語descriptionは上書きしない
- `block_types` 内のネストされた属性も対象

## descriptionの書き方

- 簡潔な日本語（1〜2文）
- 属性の用途・設定する値の説明
- 例: `"description": "IAMロールの名前。省略するとランダム名が生成される"`
