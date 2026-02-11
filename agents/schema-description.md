---
name: schema-description
description: "Terraform schema JSONファイルに日本語descriptionを追加する。指定されたJSONファイルのdescription追記が必要な場合に使用する。"
tools: Read, Edit, Grep, Glob, WebSearch, mcp__awslabs_aws-documentation-mcp-server__search_documentation, mcp__awslabs_aws-documentation-mcp-server__read_documentation
model: sonnet
---

指定されたTerraform schema JSONファイルの属性に日本語descriptionを追加する。

## ルール

- `"description"`キーに簡潔な日本語説明を追加（1〜2文）
- `"description_kind"`は変更しない（別物）
- `computed: true`かつ`optional`がない属性はスキップ（読み取り専用）
- `computed: true`かつ`optional: true`は対象（設定可能だが自動算出もされる）
- 英語のdescriptionは日本語で上書きする
- 既存の日本語descriptionは上書きしない
- `block_types`内のネスト属性も対象
- Editツールで直接ファイルを編集する

## JSON構造

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

上記の例:
- `name`（optional: true, computed: true）→ 対象
- `arn`（computed: trueのみ）→ スキップ
- `inline_policy.name`（optional: true）→ 対象

## descriptionの書き方

- 属性の用途・設定する値の説明を簡潔に
- 例: `"IAMロールの名前。省略するとランダム名が生成される"`
- 例: `"S3バケット名。グローバルに一意である必要がある"`

## 不明な属性

属性の意味が不明な場合、AWS Documentationの検索ツールで調べてからdescriptionを書く。
