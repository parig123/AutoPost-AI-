import re
import markdown

with open('AutoPost_AI_Project_Report.md', 'r', encoding='utf-8') as f:
    text = f.read()

text = re.sub(r'---\s*\[PAGE \d+\]\s*---', '<div class="page-break"></div>', text)
html_content = markdown.markdown(text)

template = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>AutoPost AI Project Report</title>
<style>
  body {{ font-family: Arial, sans-serif; line-height: 1.8; max-width: 900px; margin: 0 auto; padding: 20px; font-size: 15px; }}
  h1 {{ font-size: 2.2em; margin-bottom: 0.5em; page-break-after: avoid; }}
  h2 {{ font-size: 1.8em; margin-top: 1em; page-break-after: avoid; }}
  p {{ margin-bottom: 1.2em; text-align: justify; }}
  ul {{ margin-bottom: 1.2em; }}
  li {{ margin-bottom: 0.5em; }}
  @media print {{
    .page-break {{ page-break-before: always; margin-top: 0; border-top: none; padding-top: 0; }}
  }}
  .page-break {{ margin-top: 50px; border-top: 1px dashed #ccc; padding-top: 50px; }}
</style>
</head>
<body>
{html_content}
</body>
</html>"""

with open('AutoPost_AI_Project_Report.html', 'w', encoding='utf-8') as f:
    f.write(template)
