#!/usr/bin/env python3
"""
HTML View生成モジュール

整形済みデータからHTMLテーブルを生成する。
- 個別型（individual）: 1リソースを詳細に表示
- 一覧型（list）: 複数リソースを1行ずつ表示
"""

import sys
import json
import re
import argparse
from typing import Any, List, Dict, Tuple
import resource_config
from view_converter import ViewValue


# List型テーブルで表示するリソースタイプ
# リスト型は特殊なオプションであり、基本的にはIAM RoleとS3 Bucketのみ
LIST_TABLE_TYPES = [
  'aws_iam_role',
  'aws_s3_bucket',
]


# HTML CSS スタイル定義
HTML_STYLE = """
<style>
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
        margin: 20px;
        background-color: #f6f8fa;
    }
    h1 {
        color: #24292e;
        border-bottom: 3px solid #0366d6;
        padding-bottom: 10px;
    }
    h2 {
        color: #24292e;
        background-color: #e1e4e8;
        padding: 8px 12px;
        border-left: 4px solid #0366d6;
        margin-top: 30px;
    }
    table {
        border-collapse: collapse;
        width: 100%;
        margin-bottom: 30px;
        background-color: white;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12);
    }
    thead {
        background-color: #0366d6;
        color: white;
    }
    th, td {
        border: 1px solid #d1d5da;
        padding: 8px 12px;
        text-align: left;
        vertical-align: top;
    }
    th {
        font-weight: 600;
    }
    tbody tr:hover {
        background-color: #f6f8fa;
    }
    .index-cell {
        background-color: #f1f8ff;
        font-weight: 600;
        text-align: center;
        color: #0366d6;
        min-width: 50px;
    }
    .param-name {
        font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
        font-size: 0.9em;
        color: #032f62;
    }
    .param-value {
        font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
        font-size: 0.9em;
        word-break: break-all;
    }
    .required-yes {
        color: #d73a49;
        font-weight: 600;
    }
    .required-no {
        color: #6a737d;
    }
    .ref-value {
        color: #0366d6;
        font-weight: 500;
    }
    .null-value {
        color: #6a737d;
        font-style: italic;
    }
    details {
        margin: 4px 0;
    }
    summary {
        cursor: pointer;
        color: #0366d6;
        font-weight: 600;
        padding: 4px 8px;
        border-radius: 3px;
        display: inline-block;
        user-select: none;
    }
    summary:hover {
        background-color: #f1f8ff;
    }
    summary::marker {
        color: #0366d6;
    }
    .collapsible-content {
        background-color: #f6f8fa;
        border: 1px solid #d1d5da;
        border-radius: 3px;
        padding: 8px;
        margin-top: 8px;
        font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
        font-size: 0.85em;
        white-space: pre-wrap;
        word-break: break-all;
        max-height: 400px;
        overflow-y: auto;
    }
    .table-wrapper {
        overflow-x: auto;
        margin-bottom: 30px;
    }
    .table-wrapper table {
        margin-bottom: 0;
    }
    /* Scrollbar styling for webkit browsers (Chrome, Safari, Edge) */
    .table-wrapper::-webkit-scrollbar {
        height: 12px;
    }
    .table-wrapper::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 6px;
    }
    .table-wrapper::-webkit-scrollbar-thumb {
        background: #0366d6;
        border-radius: 6px;
    }
    .table-wrapper::-webkit-scrollbar-thumb:hover {
        background: #0256c4;
    }
    /* Scrollbar styling for Firefox */
    .table-wrapper {
        scrollbar-width: thin;
        scrollbar-color: #0366d6 #f1f1f1;
    }
</style>
"""


def _escape_html(text):
  """HTML特殊文字をエスケープ"""
  if text is None:
    return 'null'
  text = str(text)
  return (text
    .replace('&', '&amp;')
    .replace('<', '&lt;')
    .replace('>', '&gt;')
    .replace('"', '&quot;')
    .replace("'", '&#39;'))


def _format_value(value, resource_type=None, param_name=None):
  """
  値をHTML表示用にフォーマット（個別型テーブル用）

  Args:
    value: ViewValueのvalueフィールドまたはプリミティブ値
    resource_type: リソースタイプ（折りたたみ判定用）
    param_name: パラメータ名（折りたたみ判定用）

  Returns:
    (formatted_html, css_class)のタプル
  """
  if value is None:
    return ('<span class="null-value">null</span>', 'null-value')

  value_str = str(value)

  # (ref) プレフィックスのチェック
  if value_str.startswith('(ref) '):
    ref_text = value_str[6:]  # "(ref) "を除去
    escaped = _escape_html(ref_text)
    return (f'<span class="ref-value">→ {escaped}</span>', 'ref-value')

  # Check if this parameter should be collapsible
  if resource_type and param_name:
    collapse_config = resource_config.should_collapse_parameter(resource_type, param_name)
    if collapse_config and collapse_config['collapsible']:
      # Make it collapsible
      format_json = collapse_config['format_json']
      collapsible_html = resource_config.make_collapsible(param_name, value_str, format_json)
      return (collapsible_html, 'collapsible')

  # 通常の値
  escaped = _escape_html(value_str)
  return (escaped, '')


def _check_nesting_depth(obj, current_depth=0):
  """
  Check the nesting depth of a structure

  Args:
    obj: Object to check
    current_depth: Current depth (used for recursion)

  Returns:
    Maximum depth found
  """
  if isinstance(obj, dict):
    # Skip ViewValue objects - they don't count as nesting
    if 'value' in obj and 'required' in obj and 'description' in obj:
      # Check the nested value
      return _check_nesting_depth(obj['value'], current_depth)
    else:
      # Regular dict - this is 1 level of nesting
      if not obj:
        return current_depth
      max_child_depth = max(
        _check_nesting_depth(v, current_depth + 1) for v in obj.values()
      )
      return max_child_depth
  elif isinstance(obj, list):
    # List - this is 1 level of nesting
    if not obj:
      return current_depth
    max_child_depth = max(
      _check_nesting_depth(item, current_depth + 1) for item in obj
    )
    return max_child_depth
  else:
    # Primitive value
    return current_depth


def _format_dict_as_nested_table(value_dict):
  """
  Format a dictionary as a nested HTML table

  Args:
    value_dict: Dictionary with ViewValue objects as values

  Returns:
    HTML string for nested table
  """
  if not value_dict:
    return '<span class="null-value">-</span>'

  html = ['<table style="margin: 0; border: 1px solid #d1d5da; font-size: 0.9em;">']
  html.append('<tbody>')

  for key, val in sorted(value_dict.items()):
    # Extract value from ViewValue if needed (instance or dictionary)
    if isinstance(val, ViewValue):
      display_value = val.value
    elif isinstance(val, dict) and 'value' in val and 'required' in val:
      display_value = val['value']
    else:
      display_value = val

    # Format the value
    if display_value is None:
      formatted_value = '<span class="null-value">-</span>'
    elif isinstance(display_value, str) and display_value.startswith('(ref) '):
      ref_text = display_value[6:]
      formatted_value = f'<span class="ref-value">→ {_escape_html(ref_text)}</span>'
    else:
      formatted_value = _escape_html(str(display_value))

    html.append(f'<tr><td style="font-weight: 600; padding: 4px 8px;">{_escape_html(key)}</td>')
    html.append(f'<td style="padding: 4px 8px;">{formatted_value}</td></tr>')

  html.append('</tbody>')
  html.append('</table>')

  return '\n'.join(html)


def _format_list_value(value, resource_type=None, param_name=None):
  """
  値をHTML表示用にフォーマット（リスト型テーブル用）
  ネスト構造はJSON展開可能にする

  Args:
    value: ViewValueのvalueフィールドまたはプリミティブ値
    resource_type: リソースタイプ
    param_name: パラメータ名

  Returns:
    formatted_html (文字列)
  """
  if value is None:
    return '<span class="null-value">-</span>'

  # (ref) プレフィックスのチェック
  value_str = str(value)
  if value_str.startswith('(ref) '):
    ref_text = value_str[6:]  # "(ref) "を除去
    escaped = _escape_html(ref_text)
    return f'<span class="ref-value">→ {escaped}</span>'

  # Check nesting depth
  depth = _check_nesting_depth(value)
  if depth > 1:
    # More than 1 level of nesting - this is an error
    import sys
    print(f"ERROR: Parameter '{param_name}' has nesting depth {depth} (max allowed: 1)", file=sys.stderr)
    return f'<span style="color: red; font-weight: bold;">ERROR: Too deeply nested (depth: {depth})</span>'

  # List handling - check if all elements are simple values
  if isinstance(value, list):
    # Check if all elements are simple (string, number, bool, None) or ViewValue with simple value
    all_simple = True
    simple_values = []

    for item in value:
      # Extract value from ViewValue if needed
      if isinstance(item, dict) and 'value' in item and 'required' in item and 'description' in item:
        item_value = item['value']
      else:
        item_value = item

      # Check if the value is simple (not dict/list)
      if isinstance(item_value, (dict, list)):
        all_simple = False
        break

      # Convert to string for display
      if item_value is None:
        simple_values.append('-')
      elif isinstance(item_value, str) and item_value.startswith('(ref) '):
        ref_text = item_value[6:]
        simple_values.append(f'→ {_escape_html(ref_text)}')
      else:
        simple_values.append(_escape_html(str(item_value)))

    # If all elements are simple, display as newline-separated list
    if all_simple:
      return '<br>'.join(simple_values)
    else:
      # 1-level nested list (should not happen based on depth check, but handle gracefully)
      return f'<span style="color: orange;">WARNING: Unexpected list structure in {param_name}</span>'

  # Dict - use nested table for 1-level nesting
  if isinstance(value, dict):
    return _format_dict_as_nested_table(value)

  # JSON文字列かチェック（assume_role_policyなど）
  if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
    import json
    try:
      # Try to parse as JSON
      parsed = json.loads(value)
      pretty_json = json.dumps(parsed, indent=2, ensure_ascii=False)
      return resource_config.make_collapsible(param_name, pretty_json, format_json=True)
    except:
      # Not valid JSON, treat as normal string
      pass

  # 通常の値
  escaped = _escape_html(value_str)
  return escaped


def _flatten_values(values, prefix=''):
  """
  Flatten nested values into a list of attribute paths

  Args:
    values: Nested dictionary or list, or ViewValue objects
    prefix: Current attribute name prefix

  Returns:
    List of {name, value, required, description} dictionaries
  """
  result = []

  if isinstance(values, dict):
    for key, val in values.items():
      new_prefix = f'{prefix}.{key}' if prefix else key

      # ViewValue object (instance of ViewValue class)
      if hasattr(val, 'value') and hasattr(val, 'required') and hasattr(val, 'description'):
        result.append({
          'name': new_prefix,
          'value': val.value,
          'required': val.required,
          'description': val.description
        })
      # ViewValue object (dictionary format - for backward compatibility)
      elif isinstance(val, dict) and 'value' in val and 'required' in val and 'description' in val:
        result.append({
          'name': new_prefix,
          'value': val['value'],
          'required': val['required'],
          'description': val['description']
        })
      # Nested dict (not ViewValue)
      elif isinstance(val, dict) and not ('value' in val and 'required' in val):
        result.extend(_flatten_values(val, new_prefix))
      # List
      elif isinstance(val, list):
        result.extend(_flatten_values(val, new_prefix))

  elif isinstance(values, list):
    for index, item in enumerate(values):
      new_prefix = f'{prefix}[{index}]'

      # ViewValue object (instance of ViewValue class)
      if hasattr(item, 'value') and hasattr(item, 'required') and hasattr(item, 'description'):
        result.append({
          'name': new_prefix,
          'value': item.value,
          'required': item.required,
          'description': item.description
        })
      # ViewValue object (dictionary format - for backward compatibility)
      elif isinstance(item, dict) and 'value' in item and 'required' in item and 'description' in item:
        result.append({
          'name': new_prefix,
          'value': item['value'],
          'required': item['required'],
          'description': item['description']
        })
      # Nested structure
      elif isinstance(item, (dict, list)):
        result.extend(_flatten_values(item, new_prefix))
      else:
        # Primitive value in list (shouldn't happen with ViewValue, but handle it)
        result.append({
          'name': new_prefix,
          'value': item,
          'required': False,
          'description': ''
        })

  return result


def _structure_attributes(flattened_attrs):
  """
  Parse attribute names into structured format with nesting levels

  Args:
    flattened_attrs: List of attribute dictionaries

  Returns:
    List of structured attribute dictionaries with levels
  """
  structured = []

  for attr in flattened_attrs:
    name = attr['name']
    levels = []

    # Parse the name to extract all levels
    # Pattern: name[index].name[index]...
    remaining = name
    while remaining:
      # Match: name[index] or just name
      match = re.match(r'^([^\[\.]*)(?:\[(\d+)\])?\.?', remaining)
      if not match:
        break

      param_name = match.group(1)
      param_index = match.group(2)

      if param_name:  # Skip empty names
        levels.append({
          'name': param_name,
          'index': str(int(param_index) + 1) if param_index else None
        })

      # Move to the next part
      remaining = remaining[match.end():]

    structured.append({
      'levels': levels,
      'attr': attr
    })

  return structured


def _get_max_depth(structured_attrs):
  """
  Get the maximum nesting depth across all attributes

  Args:
    structured_attrs: List of structured attributes

  Returns:
    Maximum depth
  """
  if not structured_attrs:
    return 1
  return max(len(item['levels']) for item in structured_attrs)


def _generate_individual_table(resource):
  """
  個別型テーブルを生成（1リソースを詳細表示）

  Args:
    resource: リソースデータ（resource_type, resource_name, values含む）

  Returns:
    HTML文字列
  """
  resource_type = resource['resource_type']
  resource_name = resource['resource_name']
  values = resource['values']

  html = []
  html.append(f'<h2>{resource_type}.{resource_name}</h2>')

  # Step 1: Flatten nested values
  flattened_attrs = _flatten_values(values)

  # Step 2: Structure attributes with levels
  structured_attrs = _structure_attributes(flattened_attrs)

  # Step 3: Determine max depth
  max_depth = _get_max_depth(structured_attrs)

  # Step 4: Generate HTML table
  html.append('<table>')
  html.append('<thead>')
  html.append('  <tr>')

  # Parameter columns (each level has name + index)
  if max_depth > 0:
    colspan = max_depth * 2
    html.append(f'    <th colspan="{colspan}">パラメータ</th>')

  html.append('    <th>値</th>')
  html.append('    <th>必須</th>')
  html.append('    <th>説明</th>')
  html.append('  </tr>')
  html.append('</thead>')
  html.append('<tbody>')

  # Step 5: Calculate rowspans
  rowspan_counters = {}

  for item in structured_attrs:
    levels = item['levels']

    for depth in range(len(levels)):
      level = levels[depth]

      # Key for the full path including indices (for index cells)
      full_key = tuple((l['name'], l['index']) for l in levels[:depth+1])
      if full_key not in rowspan_counters:
        rowspan_counters[full_key] = 0
      rowspan_counters[full_key] += 1

      # Key for parameter name only (for parameter name cells)
      name_key = tuple((l['name'], l['index']) for l in levels[:depth]) + (level['name'], None)
      if name_key not in rowspan_counters:
        rowspan_counters[name_key] = 0
      rowspan_counters[name_key] += 1

  # Step 6: Render rows
  rendered_cells = {}

  for item in structured_attrs:
    levels = item['levels']
    attr = item['attr']

    row_parts = ['  <tr>']

    # Count occupied columns
    occupied_cols = 0

    # Check if this is a simple attribute (no nesting/array)
    is_simple_attr = len(levels) == 1 and levels[0]['index'] is None
    if is_simple_attr and max_depth > 1:
      # Simple attribute - merge across all parameter/index columns
      level = levels[0]
      key = tuple((l['name'], l['index']) for l in levels)
      should_render = key not in rendered_cells

      if should_render:
        rowspan = rowspan_counters.get(key, 1)
        rendered_cells[key] = True
        colspan = max_depth * 2
        occupied_cols = colspan

        row_parts.append(
          f'    <td class="param-name" rowspan="{rowspan}" colspan="{colspan}">'
          f'{_escape_html(level["name"])}</td>'
        )
      else:
        # Cell is rowspan-merged from previous row
        occupied_cols = max_depth * 2
    else:
      # Nested attributes or arrays - render each level normally
      for depth in range(max_depth):
        if depth < len(levels):
          level = levels[depth]

          # Key for parameter name cell
          name_key = tuple((l['name'], l['index']) for l in levels[:depth]) + (level['name'], None)
          # Key for index cell
          index_key = tuple((l['name'], l['index']) for l in levels[:depth+1])

          # Render parameter name cell
          should_render_name = name_key not in rendered_cells
          if should_render_name:
            name_rowspan = rowspan_counters.get(name_key, 1)
            rendered_cells[name_key] = True
            row_parts.append(
              f'    <td class="param-name" rowspan="{name_rowspan}">'
              f'{_escape_html(level["name"])}</td>'
            )
          occupied_cols += 1

          # Render index cell
          should_render_index = index_key not in rendered_cells
          if should_render_index:
            index_rowspan = rowspan_counters.get(index_key, 1)
            rendered_cells[index_key] = True

            if level['index']:
              row_parts.append(
                f'    <td class="index-cell" rowspan="{index_rowspan}">'
                f'{level["index"]}</td>'
              )
            else:
              row_parts.append(f'    <td rowspan="{index_rowspan}">-</td>')
          occupied_cols += 1

      # Fill remaining columns
      remaining_cols = (max_depth * 2) - occupied_cols
      if remaining_cols > 0:
        row_parts.append(f'    <td colspan="{remaining_cols}"></td>')

    # Value
    value_html, _ = _format_value(attr['value'], resource_type=resource_type, param_name=attr['name'])
    row_parts.append(f'    <td class="param-value">{value_html}</td>')

    # Required
    required = 'Yes' if attr['required'] else 'No'
    required_class = 'required-yes' if attr['required'] else 'required-no'
    row_parts.append(f'    <td class="{required_class}">{required}</td>')

    # Description
    description = _escape_html(attr['description'])
    row_parts.append(f'    <td>{description}</td>')

    row_parts.append('  </tr>')
    html.append('\n'.join(row_parts))

  html.append('</tbody>')
  html.append('</table>')

  return '\n'.join(html)


def _calculate_row_count(attr_value):
  """
  Calculate how many rows an attribute will span

  Args:
    attr_value: Attribute value (ViewValue, dict, list, or primitive)

  Returns:
    Number of rows needed
  """
  if attr_value is None:
    return 1

  # ViewValue object (instance or dictionary)
  if isinstance(attr_value, ViewValue):
    value = attr_value.value
  elif isinstance(attr_value, dict) and 'value' in attr_value and 'required' in attr_value:
    value = attr_value['value']
  else:
    value = attr_value

  # List - count elements (after extracting ViewValue)
  if isinstance(value, list):
    if not value:
      return 1
    # All items count as one row each (ViewValue or not)
    return max(1, len(value))

  # Dict - count keys (after extracting ViewValue)
  if isinstance(value, dict):
    # Check if this is a dict of ViewValues (instance or dictionary)
    if value and all(isinstance(v, ViewValue) or (isinstance(v, dict) and 'value' in v and 'required' in v) for v in value.values()):
      return max(1, len(value))
    else:
      # Not a ViewValue dict, treat as single row
      return 1

  # Primitive value
  return 1


def _render_split_cell(attr_value, resource_type, attr_name, row_index, resource_total_rows):
  """
  Render a cell that may be split across multiple rows

  Args:
    attr_value: Attribute value
    resource_type: Resource type
    attr_name: Attribute name
    row_index: Current row index (0-based)
    resource_total_rows: Total rows for the entire resource (not just this attribute)

  Returns:
    HTML string for the cell, or None if this row should be skipped (rowspan)
  """
  if attr_value is None:
    if row_index == 0:
      if resource_total_rows > 1:
        return f'<td class="null-value" rowspan="{resource_total_rows}">-</td>'
      else:
        return '<td class="null-value">-</td>'
    else:
      return None

  # Extract value from ViewValue (instance or dictionary)
  if isinstance(attr_value, ViewValue):
    value = attr_value.value
  elif isinstance(attr_value, dict) and 'value' in attr_value and 'required' in attr_value:
    value = attr_value['value']
  else:
    value = attr_value

  # List - split across rows
  if isinstance(value, list):
    if not value:
      if row_index == 0:
        if resource_total_rows > 1:
          return f'<td class="null-value" rowspan="{resource_total_rows}">-</td>'
        else:
          return '<td class="null-value">-</td>'
      else:
        return None

    # Check if we're within the list bounds
    if row_index < len(value):
      item = value[row_index]
      # Extract value from ViewValue (instance or dictionary)
      if isinstance(item, ViewValue):
        item_value = item.value
      elif isinstance(item, dict) and 'value' in item and 'required' in item:
        item_value = item['value']
      else:
        item_value = item

      # Format the item
      if item_value is None:
        return '<td class="null-value">-</td>'
      elif isinstance(item_value, str) and item_value.startswith('(ref) '):
        ref_text = item_value[6:]
        return f'<td class="param-value"><span class="ref-value">→ {_escape_html(ref_text)}</span></td>'
      elif isinstance(item_value, dict):
        # Dict inside list - format as key: value pairs
        # Filter out description and required fields
        parts = []
        for k, v in item_value.items():
          # Extract value from ViewValue if needed (instance or dictionary)
          if isinstance(v, ViewValue):
            display_val = v.value
          elif isinstance(v, dict) and 'value' in v and 'required' in v and 'description' in v:
            display_val = v['value']
          else:
            display_val = v

          # Format the value
          if display_val is None:
            formatted_val = '<span class="null-value">-</span>'
          elif isinstance(display_val, str) and display_val.startswith('(ref) '):
            ref_text = display_val[6:]
            formatted_val = f'<span class="ref-value">→ {_escape_html(ref_text)}</span>'
          else:
            formatted_val = _escape_html(str(display_val))

          parts.append(f'<strong>{_escape_html(k)}:</strong> {formatted_val}')

        if parts:
          return f'<td class="param-value">{"<br>".join(parts)}</td>'
        else:
          return '<td class="null-value">-</td>'
      else:
        return f'<td class="param-value">{_escape_html(str(item_value))}</td>'
    else:
      # Beyond list length - this row is for other attributes, skip this cell
      return None

  # Dict - split across rows
  if isinstance(value, dict):
    # Check if this is a dict of ViewValues (instance or dictionary)
    if value and all(isinstance(v, ViewValue) or (isinstance(v, dict) and 'value' in v and 'required' in v) for v in value.values()):
      keys = sorted(value.keys())

      # Check if we're within the dict bounds
      if row_index < len(keys):
        key = keys[row_index]
        val = value[key]
        # Extract value from ViewValue (instance or dictionary)
        if isinstance(val, ViewValue):
          display_value = val.value
        elif isinstance(val, dict) and 'value' in val:
          display_value = val['value']
        else:
          display_value = val

        # Format the value
        if display_value is None:
          formatted_value = '<span class="null-value">-</span>'
        elif isinstance(display_value, str) and display_value.startswith('(ref) '):
          ref_text = display_value[6:]
          formatted_value = f'<span class="ref-value">→ {_escape_html(ref_text)}</span>'
        else:
          formatted_value = _escape_html(str(display_value))

        # Render as key: value in a single cell
        return f'<td class="param-value"><strong>{_escape_html(key)}:</strong> {formatted_value}</td>'
      else:
        # Beyond dict length - this row is for other attributes, skip this cell
        return None
    else:
      # Regular dict, not a ViewValue dict - use nested table (for first row only)
      if row_index == 0:
        nested_table = _format_dict_as_nested_table(value)
        if resource_total_rows > 1:
          return f'<td class="param-value" rowspan="{resource_total_rows}">{nested_table}</td>'
        else:
          return f'<td class="param-value">{nested_table}</td>'
      else:
        return None

  # Primitive value - single row with rowspan if needed
  if row_index == 0:
    if isinstance(value, str) and value.startswith('(ref) '):
      ref_text = value[6:]
      cell_content = f'<span class="ref-value">→ {_escape_html(ref_text)}</span>'
    elif isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
      # JSON string - make it collapsible
      import json
      try:
        parsed = json.loads(value)
        pretty_json = json.dumps(parsed, indent=2, ensure_ascii=False)
        cell_content = resource_config.make_collapsible(attr_name, pretty_json, format_json=True)
      except:
        # Not valid JSON, treat as normal string
        cell_content = _escape_html(str(value))
    else:
      cell_content = _escape_html(str(value))

    if resource_total_rows > 1:
      return f'<td class="param-value" rowspan="{resource_total_rows}">{cell_content}</td>'
    else:
      return f'<td class="param-value">{cell_content}</td>'
  else:
    return None


def _generate_list_table(resources, resource_type):
  """
  一覧型テーブルを生成（複数リソースを1行ずつ表示）

  Args:
    resources: 同じリソースタイプのリソースリスト
    resource_type: リソースタイプ

  Returns:
    HTML文字列
  """
  if not resources:
    return ''

  html = []
  html.append(f'<h2>{resource_type} 一覧</h2>')

  # Step 1: Collect all attribute names from all resources
  all_attr_names = set()
  for resource in resources:
    flattened = _flatten_values(resource['values'])
    for attr in flattened:
      # Only use top-level attribute names (no nesting)
      top_level_name = attr['name'].split('.')[0].split('[')[0]
      all_attr_names.add(top_level_name)

  # Sort attribute names
  sorted_attr_names = sorted(all_attr_names)

  # Get column width configurations
  column_widths = resource_config.get_column_widths(resource_type)

  # Step 2: Generate table header
  html.append('<div class="table-wrapper">')
  html.append('<table>')
  html.append('<thead>')
  html.append('  <tr>')
  html.append('    <th>リソース名</th>')
  for attr_name in sorted_attr_names:
    # Apply column width if configured
    if attr_name in column_widths:
      width = column_widths[attr_name]
      html.append(f'    <th style="min-width: {width}; width: {width};">{_escape_html(attr_name)}</th>')
    else:
      # Default minimum width to fit "None" (4 chars) without wrapping
      html.append(f'    <th style="min-width: 80px;">{_escape_html(attr_name)}</th>')
  html.append('  </tr>')
  html.append('</thead>')
  html.append('<tbody>')

  # Step 3: Generate table rows for each resource
  for resource in resources:
    resource_name = resource['resource_name']
    values = resource['values']

    # Calculate row counts for each attribute
    attr_row_counts = {}
    for attr_name in sorted_attr_names:
      attr_value = values.get(attr_name)
      attr_row_counts[attr_name] = _calculate_row_count(attr_value)

    # Total rows needed for this resource
    total_rows = max(attr_row_counts.values()) if attr_row_counts else 1

    # Generate rows
    for row_index in range(total_rows):
      html.append('  <tr>')

      # Resource name (only on first row)
      if row_index == 0:
        if total_rows > 1:
          html.append(f'    <td class="param-name" rowspan="{total_rows}">{_escape_html(resource_name)}</td>')
        else:
          html.append(f'    <td class="param-name">{_escape_html(resource_name)}</td>')

      # For each attribute column
      for attr_name in sorted_attr_names:
        attr_value = values.get(attr_name)

        cell_html = _render_split_cell(attr_value, resource_type, attr_name, row_index, total_rows)
        if cell_html:
          html.append(f'    {cell_html}')

      html.append('  </tr>')

  html.append('</tbody>')
  html.append('</table>')
  html.append('</div>')

  return '\n'.join(html)


def _get_sort_value(resource, sort_key: str):
  """
  Get sort value from resource

  Args:
    resource: Resource data
    sort_key: Sort key (e.g., "name", "tags.Name")

  Returns:
    Sort value (str)
  """
  if '.' in sort_key:
    # Nested key like "tags.Name"
    parts = sort_key.split('.')
    value = resource.get('values', {})
    for part in parts:
      if isinstance(value, dict):
        value = value.get(part)
        if isinstance(value, ViewValue):
          value = value.value
        elif isinstance(value, dict) and 'value' in value:
          value = value['value']
      else:
        return ''
    return str(value) if value is not None else ''
  else:
    # Simple key like "name"
    value = resource.get('values', {}).get(sort_key)
    if isinstance(value, ViewValue):
      value = value.value
    elif isinstance(value, dict) and 'value' in value:
      value = value['value']
    return str(value) if value is not None else ''


def _group_resources_by_file(formatted_data: list) -> dict:
  """
  Group resources by file path using resource_config

  Args:
    formatted_data: format_data() output

  Returns:
    {
      "aws/iam/role.html": {
        "resources": [resources...],
        "resource_types": {"aws_iam_role": priority}
      },
      ...
    }
  """
  grouped = {}

  for resource in formatted_data:
    resource_type = resource['resource_type']
    file_path = resource_config.get_file_path(resource_type)
    priority = resource_config.get_priority(resource_type)

    if file_path not in grouped:
      grouped[file_path] = {
        "resources": [],
        "resource_types": {}
      }

    grouped[file_path]["resources"].append(resource)
    grouped[file_path]["resource_types"][resource_type] = priority

  # Sort resources within each file
  for file_path, data in grouped.items():
    resources = data["resources"]
    # Sort by: priority first, then sort_key, then resource_name
    resources.sort(key=lambda r: (
      resource_config.get_priority(r['resource_type']),
      _get_sort_value(r, resource_config.get_sort_key(r['resource_type'])),
      r['resource_name']
    ))

  return grouped


def _generate_file_html(resources: list, file_path: str, title: str = "Terraform Plan") -> str:
  """
  Generate HTML for a single file

  Args:
    resources: List of resources for this file (already sorted)
    file_path: File path (e.g., "aws/iam/role.html")
    title: HTML title

  Returns:
    HTML string
  """
  html = []

  # Calculate back link depth
  depth = file_path.count('/')
  back_link = '../' * depth + 'index.html'

  # HTML header
  html.append('<!DOCTYPE html>')
  html.append('<html lang="ja">')
  html.append('<head>')
  html.append('    <meta charset="UTF-8">')
  html.append('    <meta name="viewport" content="width=device-width, initial-scale=1.0">')
  html.append(f'    <title>{_escape_html(title)} - {file_path}</title>')
  html.append(HTML_STYLE)
  html.append('</head>')
  html.append('<body>')
  html.append(f'<h1>{_escape_html(title)} - {file_path.replace(".html", "")}</h1>')
  html.append(f'<p><a href="{back_link}">← 目次に戻る</a></p>')

  # Group by table_type (determine from resource_type)
  individual_resources = []
  list_resources_by_type = {}

  for resource in resources:
    resource_type = resource['resource_type']

    # Determine table type based on resource type
    if resource_type in LIST_TABLE_TYPES:
      if resource_type not in list_resources_by_type:
        list_resources_by_type[resource_type] = []
      list_resources_by_type[resource_type].append(resource)
    else:
      individual_resources.append(resource)

  # Render list tables first
  for resource_type, res_list in sorted(list_resources_by_type.items()):
    html.append(_generate_list_table(res_list, resource_type))

  # Render individual tables
  for resource in individual_resources:
    html.append(_generate_individual_table(resource))

  # HTML footer
  html.append('</body>')
  html.append('</html>')

  return '\n'.join(html)


def _generate_index_html(file_groups: dict, title: str = "Terraform Plan") -> str:
  """
  Generate index.html with table of contents

  Args:
    file_groups: Resources grouped by file path
      {
        "aws/iam/role.html": {
          "resources": [resources...],
          "resource_types": {"aws_iam_role": 1}
        }
      }
    title: HTML title

  Returns:
    HTML string for index page
  """
  html = []

  # HTML header
  html.append('<!DOCTYPE html>')
  html.append('<html lang="ja">')
  html.append('<head>')
  html.append('    <meta charset="UTF-8">')
  html.append('    <meta name="viewport" content="width=device-width, initial-scale=1.0">')
  html.append(f'    <title>{_escape_html(title)}</title>')
  html.append(HTML_STYLE)
  html.append('</head>')
  html.append('<body>')
  html.append(f'<h1>{_escape_html(title)}</h1>')

  # Group files by provider and service (hierarchical structure)
  provider_groups = {}
  for file_path, file_data in file_groups.items():
    parts = file_path.split('/')
    if len(parts) >= 3:  # e.g., ["aws", "iam", "role.html"]
      provider = parts[0]
      service = parts[1]
      page_name = parts[2].replace('.html', '')

      if provider not in provider_groups:
        provider_groups[provider] = {}
      if service not in provider_groups[provider]:
        provider_groups[provider][service] = []

      provider_groups[provider][service].append({
        'file_path': file_path,
        'page_name': page_name,
        'resource_count': len(file_data['resources'])
      })

  # Generate table of contents by provider and service
  for provider in sorted(provider_groups.keys()):
    html.append(f'<h2>{provider}</h2>')
    html.append('<ul>')

    services = provider_groups[provider]
    for service in sorted(services.keys()):
      html.append(f'  <li>{service}')
      html.append('    <ul>')

      pages = services[service]
      for page_data in sorted(pages, key=lambda x: x['page_name']):
        file_path = page_data['file_path']
        page_name = page_data['page_name']
        resource_count = page_data['resource_count']
        html.append(f'      <li><a href="{file_path}">{page_name}</a> ({resource_count} resources)</li>')

      html.append('    </ul>')
      html.append('  </li>')

    html.append('</ul>')

  # HTML footer
  html.append('</body>')
  html.append('</html>')

  return '\n'.join(html)


def generate_html(formatted_data: list, output_dir: str, title: str = "Terraform Plan"):
  """
  整形済みデータからHTMLファイル群を生成（リソース設定に基づくディレクトリ構造）

  Args:
    formatted_data: format_data()の出力
    output_dir: 出力ディレクトリのパス
    title: HTMLのタイトル

  Returns:
    None (ファイルを直接書き込む)
  """
  import os

  # Create output directory
  os.makedirs(output_dir, exist_ok=True)

  # Group resources by file path using resource_config
  file_groups = _group_resources_by_file(formatted_data)

  # Generate HTML files
  for file_path, file_data in file_groups.items():
    resources = file_data['resources']

    # Create directory structure for this file
    full_path = os.path.join(output_dir, file_path)
    file_dir = os.path.dirname(full_path)
    if file_dir:
      os.makedirs(file_dir, exist_ok=True)

    # Generate HTML for this file
    file_html = _generate_file_html(resources, file_path, title)

    with open(full_path, 'w', encoding='utf-8') as f:
      f.write(file_html)

    print(f"Generated: {full_path}", file=sys.stderr)

  # Generate index.html
  index_html = _generate_index_html(file_groups, title)
  index_file = os.path.join(output_dir, 'index.html')

  with open(index_file, 'w', encoding='utf-8') as f:
    f.write(index_html)

  print(f"Generated: {index_file}", file=sys.stderr)


def test():
  """テスト用関数（CLI実行時）"""
  import pickle

  parser = argparse.ArgumentParser(
    description='Generate HTML view from formatted data with directory structure'
  )
  parser.add_argument('input_file', help='Path to formatted data (JSON or pickle file)')
  parser.add_argument('--output', '-o', required=True, help='Output directory path')
  parser.add_argument('--title', '-t', default='Terraform Plan', help='HTML title')
  parser.add_argument('--pickle-load', action='store_true', help='Load input as pickle file (Python objects)')

  args = parser.parse_args()

  # 入力ファイルを読み込み
  if args.pickle_load:
    # Pickle形式で読み込み（ViewValueオブジェクトがそのまま復元される）
    with open(args.input_file, 'rb') as f:
      formatted_data = pickle.load(f)
  else:
    # JSON形式で読み込み
    with open(args.input_file) as f:
      formatted_data = json.load(f)

  # HTML生成（ディレクトリ構造付き）
  generate_html(formatted_data, output_dir=args.output, title=args.title)

  print(f"HTML files generated in {args.output}", file=sys.stderr)


if __name__ == '__main__':
  test()
