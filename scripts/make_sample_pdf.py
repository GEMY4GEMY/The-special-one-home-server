"""Generate printable sample questions PDF from the bundled JSON using stdlib only."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = root / "samples" / "primary3-example-bank.json"
target = root / "samples" / "THE_SPECIAL_ONE_Sample_Questions.pdf"
bank = json.loads(source.read_text(encoding="utf-8"))
lines = ["THE SPECIAL ONE - Sample English Questions", "Mr. Sameh Abdel Hafeez", "Primary 3 | Units 1 and 2", "Sample only: replace with approved curriculum questions", ""]
for i, question in enumerate(bank["questions"], 1):
    lines.append(str(i) + ". " + question["prompt"])
    lines.append("Answer: " + question["answer"])
    lines.append("")
pages = [lines[i:i+45] for i in range(0, len(lines), 45)]
objects = []
def add(body):
    objects.append(body)
    return len(objects)
catalog = add("")
pages_id = add("")
font_id = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
page_ids = []
for lines in pages:
    commands = ["BT /F1 10 Tf 45 790 Td 14 TL"]
    for line in lines:
        safe = line.encode("ascii", "replace").decode("ascii").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        commands.append("(" + safe + ") Tj T*")
    commands.append("ET")
    stream = "\n".join(commands).encode("ascii")
    content_id = add("<< /Length " + str(len(stream)) + " >>\nstream\n" + stream.decode("ascii") + "\nendstream")
    page_ids.append(add("<< /Type /Page /Parent " + str(pages_id) + " 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 " + str(font_id) + " 0 R >> >> /Contents " + str(content_id) + " 0 R >>"))
objects[catalog-1] = "<< /Type /Catalog /Pages " + str(pages_id) + " 0 R >>"
objects[pages_id-1] = "<< /Type /Pages /Kids [" + " ".join(str(x)+" 0 R" for x in page_ids) + "] /Count " + str(len(page_ids)) + " >>"
data = bytearray(b"%PDF-1.4\n")
offsets = [0]
for i, body in enumerate(objects, 1):
    offsets.append(len(data))
    data.extend((str(i) + " 0 obj\n" + body + "\nendobj\n").encode("ascii"))
xref = len(data)
data.extend(("xref\n0 " + str(len(objects)+1) + "\n0000000000 65535 f \n").encode("ascii"))
for offset in offsets[1:]:
    data.extend(("%010d 00000 n \n" % offset).encode("ascii"))
data.extend(("trailer\n<< /Size " + str(len(objects)+1) + " /Root " + str(catalog) + " 0 R >>\nstartxref\n" + str(xref) + "\n%%EOF\n").encode("ascii"))
target.write_bytes(data)
print(target)
