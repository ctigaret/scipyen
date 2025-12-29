import re

# Sample string with LaTeX display environments
text = """
Here is some LaTeX: 
\\begin{equation}
E = mc^2
\\end{equation}
and some text.
\\begin{align}
x + y &= z
\\end{align}
"""

# Regular expression to capture LaTeX display environments
latex_display_pattern = r'\\begin\{[^\}]+\}.*?\\end\{[^\}]+\}'

# Finding all matches
matches = re.findall(latex_display_pattern, text, re.DOTALL)

# Display matches
for match in matches:
    print(match)


# ------------------------
# import re

# Sample string with LaTeX
text = "Here is some LaTeX: $E = mc^2$ and \\begin{equation} x = y + z \\end{equation}."

# Regular expression to capture LaTeX commands
latex_pattern = r'(\$[^\$]*\$|\\(begin|end)\{[^\}]*\}|\\[a-zA-Z]+(?:\{[^\}]*\})?)'

matches = re.findall(latex_pattern, text)

# Display matches
for match in matches:
    print(match[0])  # match[0] contains the full matched LaTeX

# ------------------------
# import re

# Sample string with LaTeX embedded between $$
text = """
Here is some inline LaTeX: $$E = mc^2$$ and here's a display LaTeX: $$\\int_0^1 x^2 \\, dx$$.
More LaTeX here: $$\\frac{a}{b}$$.
"""

# Regular expression to capture LaTeX between $$ and $$
latex_pattern = r'\$\$([^$]*)\$\$'

# Finding all matches
matches = re.findall(latex_pattern, text)

# Display matches
for match in matches:
    print(match.strip())  # strip() to remove leading/trailing whitespace

# ------------------------
# import re

# Sample string containing various LaTeX expressions
text = """
Inline LaTeX: $E = mc^2$, and display LaTeX: $$E = mc^2$$.
Another display environment:
$$\\begin{equation} E = mc^2 \\end{equation}$$.
Yet another one: $$\\frac{a}{b}$$.
And a simple environment: \\begin{align} x + y &= z \\end{align}.
"""

# Combined regular expression to capture all types of LaTeX
latex_combined_pattern = r'(\$\$([^$]*)\$\$|\\begin\{[^\}]+\}.*?\\end\{[^\}]+\}|(\$[^\$]*\$|\\[a-zA-Z]+(?:\{[^\}]*\})?))'

# Finding all matches
matches = re.findall(latex_combined_pattern, text, re.DOTALL)

# Display matches
for match in matches:
    # match[0] contains the complete matched substring
    print(match[0].strip())
