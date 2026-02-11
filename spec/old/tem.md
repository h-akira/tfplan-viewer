```
[
  {
    "module": "root",
    "address": "aws_hoge.fuga",
    "type": "aws_hoge",
    "name": "hoge",
    "values": {
      "name": Value(value="hoge", ...),
      "hoge": {
        "fuga": Value(...)
      }
    }
  }
]
```

sample002のroleを見ると、attached_policiesの値が辞書型になっているうえにdescription、requiredが残っている。これは、リスト型のViewの仕様で多重のネストに対応していないからなので仕方がないが、phase2-1の従属処理の時にネストが入らないようにすれば良かった可能性はある。SPECIAL_RESOURCE_TYPESで、exclude_keysにidを