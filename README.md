# sphinx-matlab

## Tokenization

The tokenization engine is based on the [syntax](https://github.com/mathworks/MATLAB-Language-grammar) created by Mathworks for its integration in IDE's such as VSCode. The syntax is a recursive list of regular expressions, normally read by the [TypeScript engine](https://github.com/microsoft/TypeScript-TmLanguage). The work here hopes also to improve the syntax such to improve the MATLAB [extension](https://github.com/mathworks/matlab-extension-for-vscode) for VSCode. The overview of all the scopes in the syntax is listed below. 

- 🔲 No work done
- ⚠️ Issue found
- ⚒️ PR submitted
- ✅ Done

| Scope                     | No issues with regex  | Implemented   | Test  | Comment                                       |
|---------------------------|-----------------------|---------------|-------|-----------------------------------------------|
| rules_before_command_dual | 🔲                     | 🔲             | 🔲     |                                               |
| rules_after_command_dual  | 🔲                     | 🔲             | 🔲     |                                               |
| anonymous_function        | ⚒️                     | ✅             | ✅     |                                               |
| blocks                    | 🔲                     | 🔲             | 🔲     |                                               |
| classdef                  | 🔲                     | 🔲             | 🔲     |                                               |
| command_dual              | 🔲                     | 🔲             | 🔲     |                                               |
| comment_block             | ✅                     | ✅             | ✅     |                                               |
| comments                  | ✅                     | ✅             | ✅     |                                               |
| control_statements        | ✅                     | ✅             | ✅     |                                               |
| function                  | 🔲                     | 🔲             | 🔲     |                                               |
| function_call             | 🔲                     | 🔲             | 🔲     |                                               |
| global_persistent         | ✅                     | ✅             | ✅     |                                               |
| import                    | ✅                     | ✅             | ✅     |                                               |
| indexing_by_expression    | 🔲                     | 🔲             | 🔲     |                                               |
| multiple_assignment       | 🔲                     | 🔲             | 🔲     |                                               |
| parentheses               | 🔲                     | 🔲             | 🔲     |                                               |
| single_assignment         | 🔲                     | 🔲             | 🔲     |                                               |
| square_brackets           | 🔲                     | 🔲             | 🔲     |                                               |
| curly_brackets            | 🔲                     | 🔲             | 🔲     |                                               |
| indexing_curly_brackets   | 🔲                     | 🔲             | 🔲     |                                               |
| line_continuation         | ✅                     | ✅             | ✅     |                                               |
| shell_string              | ✅                     | ✅             | ⚠️     | Requires source.shell                         |
| string_quoted_double      | ✅                     | ✅             | ✅     |                                               |
| string_quoted_single      | ✅                     | ✅             | ✅     |                                               |
| string                    | ✅                     | ✅             | ✅     |                                               |
| superclass_method_call    | 🔲                     | 🔲             | 🔲     |                                               |
| conjugate_transpos        | ✅                     | ✅             | ✅     |                                               |
| transpose                 | ✅                     | ✅             | ✅     |                                               |
| constants                 | ✅                     | ✅             | ✅     |                                               |
| variables                 | ✅                     | ✅             | ✅     |                                               |
| end_in_parentheses        | ✅                     | ✅             | 🚫     | Not required                                  |
| numbers                   | ✅                     | ✅             | ✅     |                                               |
| operators                 | 🔲                     | 🔲             | 🔲     |                                               |
| punctuation               | ✅                     | ✅             | ✅     |                                               |
| validators                | 🔲                     | 🔲             | 🔲     |                                               |
| braced_validator_list     | 🔲                     | 🔲             | 🔲     |                                               |
| validator_strings         | 🔲                     | 🔲             | 🔲     |                                               |
| readwrite_operations      | 🔲                     | 🔲             | 🔲     |                                               |
| property                  | 🔲                     | 🔲             | 🔲     |                                               |
| readwrite_variable        | 🔲                     | 🔲             | 🔲     |                                               |
| property_access           | 🔲                     | 🔲             | 🔲     |                                               |