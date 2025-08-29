# simple_pdf_filler.py
# Usage:
#   python simple_pdf_filler.py input.pdf output.pdf
#   Edit DATA below OR import and call fill_and_flatten(input, output, data)

from io import BytesIO
from typing import Any, Dict, Iterable, List, Set, Tuple, Union
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import NameObject, TextStringObject, ArrayObject
from reportlab.pdfgen import canvas

FieldValue = Union[str, bool, Iterable[str], Set[str]]

def _to_float_rect(rect):
    return [float(rect[0]), float(rect[1]), float(rect[2]), float(rect[3])]

def _get_field_from_annot(annot):
    return annot.get("/Parent", annot)

def _is_widget(annot) -> bool:
    return annot.get("/Subtype") == "/Widget"

def _ff(field) -> int:
    try:
        return int(field.get("/Ff", 0))
    except Exception:
        return 0

def _is_pushbutton(field) -> bool:
    return bool(_ff(field) & (1 << 16))

def _is_radio(field) -> bool:
    return bool(_ff(field) & (1 << 15))

def _is_text(field) -> bool:
    return field.get("/FT") == "/Tx"

def _is_checkbox(field) -> bool:
    return field.get("/FT") == "/Btn" and not _is_pushbutton(field)

def _is_choice(field) -> bool:
    return field.get("/FT") == "/Ch"

def _choice_is_combo(field) -> bool:
    # Combo flag for /Ch fields
    return bool(_ff(field) & (1 << 17))

def _choice_is_editable(field) -> bool:
    # Edit flag for /Ch fields (editable combo)
    return bool(_ff(field) & (1 << 18))

def _choice_is_multiselect(field) -> bool:
    # Multi-select flag for /Ch fields
    return bool(_ff(field) & (1 << 21))

def _checkbox_on_name(annot) -> NameObject:
    ap = annot.get("/AP")
    if not ap:
        return NameObject("/Yes")
    n = ap.get("/N")
    if not n:
        return NameObject("/Yes")
    for k in n.keys():
        if k != NameObject("/Off"):
            return k
    return NameObject("/Yes")

def _set_checkbox_state(annot, checked: bool):
    on_name = _checkbox_on_name(annot)
    annot.update({NameObject("/AS"): on_name if checked else NameObject("/Off")})

def _set_text_value(field, value: str):
    field.update({NameObject("/V"): TextStringObject(value)})

def _choice_options(field) -> List[Tuple[str, str]]:
    """
    Returns list of (export, display). If only strings are present, export==display.
    """
    opts = field.get("/Opt")
    result: List[Tuple[str, str]] = []
    if not opts:
        return result
    try:
        for it in opts:
            obj = it.get_object() if hasattr(it, "get_object") else it
            if isinstance(obj, list) or getattr(obj, "array", None) is not None:
                # Pair [export, display]
                try:
                    export = str(obj[0])
                    display = str(obj[1])
                except Exception:
                    export = str(obj[0])
                    display = str(obj[0])
                result.append((export, display))
            else:
                s = str(obj)
                result.append((s, s))
    except Exception:
        # Fallback best-effort
        try:
            for it in opts:
                s = str(it)
                result.append((s, s))
        except Exception:
            pass
    return result

def _choice_export_to_display(field, export: str) -> str:
    for ex, disp in _choice_options(field):
        if ex == export:
            return disp
    return export

def _choice_display_to_export(field, display_or_export: str) -> str:
    # If user supplies display label, map to export; if already export, keep as is.
    options = _choice_options(field)
    exports = {ex for ex, _ in options}
    displays = {disp: ex for ex, disp in options}
    if display_or_export in exports:
        return display_or_export
    return displays.get(display_or_export, display_or_export)

def _set_choice_value(field, value: Union[str, Iterable[str]]):
    if isinstance(value, (list, set, tuple)):
        # Multi-select
        exports = [TextStringObject(_choice_display_to_export(field, str(v))) for v in value]
        field.update({NameObject("/V"): ArrayObject(exports)})
    else:
        export = TextStringObject(_choice_display_to_export(field, str(value)))
        field.update({NameObject("/V"): export})

def fill_pdf_fields(reader: PdfReader, data: Dict[str, FieldValue]) -> None:
    """
    Fill text (/Tx), checkbox (/Btn), and choice (/Ch) fields.
    Checkboxes: supports per-widget keys "Name__N", grouped export lists, or single bool.
    Choices: pass a string (single select) or a list/set of strings (multi).
             You may pass display labels or export values; we map to exports.
    """
    name_counts: Dict[str, int] = {}

    for page in reader.pages:
        annots = page.get("/Annots") or []
        for a in annots:
            annot = a.get_object()
            if not _is_widget(annot):
                continue
            field = _get_field_from_annot(annot)
            name = field.get("/T")
            name_str = str(name) if name else None

            # Text
            if _is_text(field):
                if name_str and name_str in data:
                    _set_text_value(field, str(data[name_str]))
                continue

            # Checkboxes
            if _is_checkbox(field) and not _is_radio(field):
                idx = name_counts.get(name_str or "", 0) + 1
                name_counts[name_str or ""] = idx
                checked = None
                if name_str and f"{name_str}__{idx}" in data:
                    checked = bool(data[f"{name_str}__{idx}"])
                elif name_str and name_str in data and isinstance(data[name_str], (list, set, tuple)):
                    on_name = _checkbox_on_name(annot)
                    checked = (on_name[1:] in set(map(str, data[name_str]))) or (on_name in set(data[name_str]))
                elif name_str and name_str in data and isinstance(data[name_str], bool):
                    checked = bool(data[name_str])
                if checked is not None:
                    _set_checkbox_state(annot, checked)
                continue

            # Choice (dropdown/list)
            if _is_choice(field):
                if name_str and name_str in data:
                    _set_choice_value(field, data[name_str])
                continue

    # Help some viewers (we still flatten after)
    root = reader.trailer["/Root"]
    acro = root.get("/AcroForm")
    if acro is not None:
        acro.update({NameObject("/NeedAppearances"): True})

def flatten_to_visible(reader: PdfReader, writer: PdfWriter) -> None:
    """
    Draw field values onto pages and strip widgets so Chrome/Edge display values.
    """
    packet = BytesIO()
    c = canvas.Canvas(packet)

    for page_index, page in enumerate(reader.pages):
        media = page.mediabox
        width = float(media.width)
        height = float(media.height)
        c.setPageSize((width, height))

        annots = page.get("/Annots") or []
        for a in annots:
            annot = a.get_object()
            if not _is_widget(annot):
                continue

            field = _get_field_from_annot(annot)
            rect = _to_float_rect(annot.get("/Rect"))
            x1, y1, x2, y2 = rect
            w, h = (x2 - x1), (y2 - y1)

            if _is_text(field):
                val = field.get("/V")
                if val is None:
                    continue
                text = str(val)
                font_size = max(8, min(12, h * 0.6))
                c.setFont("Helvetica", font_size)
                c.setFillGray(0)
                y_text = y1 + (h - font_size) * 0.5 + 1
                c.drawString(x1 + 2, y_text, text)

            elif _is_checkbox(field) and not _is_radio(field):
                asn = annot.get("/AS", NameObject("/Off"))
                if asn != NameObject("/Off"):
                    c.setLineWidth(max(1, h * 0.12))
                    c.setStrokeGray(0)
                    c.line(x1 + 2, y1 + 2, x2 - 2, y2 - 2)
                    c.line(x1 + 2, y2 - 2, x2 - 2, y1 + 2)

            elif _is_choice(field):
                v = field.get("/V")
                if v is None:
                    continue
                # Normalize to list of display strings
                values: List[str] = []
                if isinstance(v, ArrayObject):
                    for it in v:
                        values.append(_choice_export_to_display(field, str(it)))
                else:
                    values.append(_choice_export_to_display(field, str(v)))

                c.setFont("Helvetica", max(8, min(12, h * 0.6)))
                c.setFillGray(0)
                if len(values) <= 1:
                    text = values[0] if values else ""
                    y_text = y1 + (h - c._fontsize) * 0.5 + 1
                    c.drawString(x1 + 2, y_text, text)
                else:
                    # Multi-line rendering for multi-select
                    line_h = max(8, min(12, h * 0.45))
                    c.setFont("Helvetica", line_h)
                    y = y2 - line_h - 2
                    for val in values:
                        if y < y1 + 2:
                            break
                        c.drawString(x1 + 2, y, val)
                        y -= line_h + 2

        c.showPage()

    c.save()
    overlay_reader = PdfReader(BytesIO(packet.getvalue()))
    for i, page in enumerate(reader.pages):
        overlay_page = overlay_reader.pages[i]
        page.merge_page(overlay_page)
        if "/Annots" in page:
            del page["/Annots"]
        writer.add_page(page)

def fill_and_flatten(input_pdf: str, output_pdf: str, data: Dict[str, FieldValue]):
    reader = PdfReader(input_pdf)
    fill_pdf_fields(reader, data)
    writer = PdfWriter()
    flatten_to_visible(reader, writer)
    with open(output_pdf, "wb") as f:
        writer.write(f)

# Example data; replace with your real field names/values
DATA: Dict[str, FieldValue] = {
    "Name": "Alice",
    "Email": "alice@example.com",
    # Checkboxes examples:
    # "Agree__1": True, "Agree__2": False, "Agree__3": True, "Agree__4": False,
    # Dropdown single:
    # "Country": "United States",  # display or export both accepted
    # Dropdown multi:
    # "Languages": ["English", "French"],  # for multi-select fields
}

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python simple_pdf_filler.py input.pdf output.pdf")
        raise SystemExit(1)
    fill_and_flatten(sys.argv[1], sys.argv[2], DATA)
    print("Saved:", sys.argv[2])
