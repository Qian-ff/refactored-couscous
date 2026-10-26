"""Small passive SVG subset; no scripts, styles, external resources or arbitrary XML."""
import hashlib
import math
import re
from dataclasses import dataclass
from xml.parsers import expat
from xml.etree import ElementTree as ET

SVG = "http://www.w3.org/2000/svg"
MAX_BYTES = 262144
TAGS = {"svg", "g", "rect", "circle", "ellipse", "line", "polyline", "polygon", "path", "text", "tspan", "title", "desc"}
NUMERIC = {"x", "y", "x1", "x2", "y1", "y2", "width", "height", "rx", "ry", "r", "cx", "cy",
           "stroke-width", "font-size", "opacity", "fill-opacity", "stroke-opacity"}
ATTRIBUTES = NUMERIC | {"id", "viewBox", "fill", "stroke", "d", "points", "transform", "text-anchor",
                         "font-family", "font-weight", "stroke-linecap", "stroke-linejoin", "role"}
NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
NUMBER_RE = re.compile(NUMBER + r"\Z")
COLORS = re.compile(r"(?:#[0-9a-fA-F]{3}|#[0-9a-fA-F]{6}|#[0-9a-fA-F]{8}|none|transparent|currentColor)\Z")


class UnsafeScene(ValueError):
    def __init__(self):
        super().__init__("UNSAFE_SVG")


@dataclass(frozen=True)
class SafeScene:
    svg: str
    sha256: str
    view_box: tuple[float, float, float, float]


def _number(value):
    if len(value) > 32 or not NUMBER_RE.fullmatch(value):
        raise UnsafeScene()
    number = float(value)
    if not math.isfinite(number) or abs(number) > 1000000:
        raise UnsafeScene()
    return number


def _preflight(raw):
    parser = expat.ParserCreate()
    depth = count = attributes = characters = 0

    def start(_name, attrs):
        nonlocal depth, count, attributes
        depth += 1
        count += 1
        attributes += len(attrs)
        if depth > 24 or count > 2000 or attributes > 16000:
            raise UnsafeScene()

    def end(_name):
        nonlocal depth
        depth -= 1

    def text(value):
        nonlocal characters
        characters += len(value)
        if characters > 131072:
            raise UnsafeScene()

    def forbidden(*_args):
        raise UnsafeScene()

    parser.StartElementHandler, parser.EndElementHandler, parser.CharacterDataHandler = start, end, text
    parser.StartDoctypeDeclHandler = forbidden
    parser.EntityDeclHandler = forbidden
    parser.ExternalEntityRefHandler = forbidden
    parser.ProcessingInstructionHandler = forbidden
    parser.Parse(raw, True)


def validate_svg(value: str) -> SafeScene:
    try:
        raw = value.encode("utf-8")
        if not raw or len(raw) > MAX_BYTES or "\x00" in value:
            raise UnsafeScene()
        _preflight(raw)
        root = ET.fromstring(raw)
        if root.tag != "{" + SVG + "}svg":
            raise UnsafeScene()
        box = root.attrib.get("viewBox", "").replace(",", " ").split()
        if len(box) != 4:
            raise UnsafeScene()
        view_box = tuple(_number(item) for item in box)
        if not 0 < view_box[2] <= 4096 or not 0 < view_box[3] <= 4096:
            raise UnsafeScene()
        ids = set()
        for element in root.iter():
            if not element.tag.startswith("{" + SVG + "}") or element.tag.split("}", 1)[1] not in TAGS:
                raise UnsafeScene()
            if element is not root and element.tag.endswith("}svg"):
                raise UnsafeScene()
            for key, val in element.attrib.items():
                if key not in ATTRIBUTES or len(val) > 65536 or any(ord(c) < 32 for c in val):
                    raise UnsafeScene()
                if key in NUMERIC:
                    number = _number(val)
                    if (key.endswith("opacity") and not 0 <= number <= 1) or (
                            key in {"width", "height", "r", "rx", "ry", "stroke-width", "font-size"} and number < 0):
                        raise UnsafeScene()
                elif key in {"fill", "stroke"} and not COLORS.fullmatch(val):
                    raise UnsafeScene()
                elif key == "id":
                    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", val) or val in ids:
                        raise UnsafeScene()
                    ids.add(val)
                elif key == "viewBox":
                    if element is not root:
                        raise UnsafeScene()
                elif key == "d" and not re.fullmatch(r"[MmZzLlHhVvCcSsQqTtAa0-9eE+.,\s-]*", val):
                    raise UnsafeScene()
                elif key == "points":
                    points = val.replace(",", " ").split()
                    if not points or len(points) > 2048 or len(points) % 2:
                        raise UnsafeScene()
                    for point in points:
                        _number(point)
                elif key == "transform":
                    if not re.fullmatch(r"(?:(?:matrix|translate|scale|rotate|skewX|skewY)\([0-9eE+.,\s-]+\)\s*)+", val):
                        raise UnsafeScene()
                    for number in re.findall(NUMBER, val):
                        _number(number)
                elif key == "text-anchor" and val not in {"start", "middle", "end"}:
                    raise UnsafeScene()
                elif key == "font-weight" and val not in {"normal", "bold", "400", "500", "600", "700"}:
                    raise UnsafeScene()
                elif key == "font-family" and val not in {"sans-serif", "serif", "monospace"}:
                    raise UnsafeScene()
                elif key in {"stroke-linecap", "stroke-linejoin"} and val not in {"butt", "round", "square", "miter", "bevel"}:
                    raise UnsafeScene()
                elif key == "role" and val != "img":
                    raise UnsafeScene()
        ET.register_namespace("", SVG)
        result = ET.tostring(root, encoding="unicode", short_empty_elements=True)
        result_bytes = result.encode("utf-8")
        if len(result_bytes) > MAX_BYTES:
            raise UnsafeScene()
        return SafeScene(result, hashlib.sha256(result_bytes).hexdigest(), view_box)
    except (ET.ParseError, expat.ExpatError, UnicodeError, OverflowError):
        raise UnsafeScene() from None
