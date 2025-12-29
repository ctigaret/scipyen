import re

# Sample string with potential Markdown
text = """
# Heading 1
## Heading 2
### Heading 3

This is some *italic* text and some **bold** text.

Here is a [link](http://example.com) and an image: ![alt text](image.jpg).

- Item 1
- Item 2
  - Subitem 2.1

```python
print("Hello, World!")
"""


### Explanation of the Pattern

1. **`(^#{1,6}\s.*$)`**:
   - Matches headings (from `#` to `######`).

2. **`|`**: Acts as an OR operator.

3. **`(^[^\s].*(\*{1,2}|_{1,2}).*$)`**:
   - Matches emphasized text (italic or bold) using single or double asterisks or underscores.

4. **`|`**: Another OR operator.

5. **`(^[\-\+\*]\s.*$)`**:
   - Matches list items that start with `-`, `+`, or `*`.

6. **`|`**: Another OR operator.

7. **`(�LATEXPH2PH�)`**:
   - Matches code blocks enclosed in triple backticks.

8. **`|`**: Another OR operator.

9. **`(!\[.*\]\(.*\))`**:
   - Matches images with the syntax `![alt text](url)`.

10. **`|`**: Another OR operator.

11. **`\[.*\]\(.*\)`**:
    - Matches links with the syntax `[text](url)`.

### Usage

This code will scan the `text` variable for Markdown elements using the defined regex pattern. The matches will be printed out, allowing you to identify the various Markdown features present in the string. You can modify the regex pattern to accommodate additional Markdown elements as needed.


