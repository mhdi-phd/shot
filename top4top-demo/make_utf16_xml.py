from pathlib import Path

output = Path(__file__).parent / "input" / "kiro-demo.xml"
content = """<?xml version=\"1.0\" encoding=\"UTF-16\"?>
<demo>
  <title>Kiro Web Upload Demonstration</title>
  <purpose>Educational browser automation test</purpose>
  <created>2026-07-22</created>
  <sensitive>false</sensitive>
</demo>
"""
output.write_text(content, encoding="utf-16")
print(output)
