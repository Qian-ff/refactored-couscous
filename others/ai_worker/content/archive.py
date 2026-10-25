"""Bounded OOXML inspection before handing the immutable input to an Office parser."""
import stat
from pathlib import PurePosixPath
from xml.parsers import expat
from zipfile import BadZipFile, ZipFile

from content.protocol import ParseError

MAIN_TYPES = {
    "docx": ("word/document.xml", "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"),
    "pptx": ("ppt/presentation.xml", "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"),
}


def inspect_office(path, kind: str) -> set[str]:
    names = set()
    total = 0
    content_types = {}

    def forbidden(*_args):
        raise ParseError("CORRUPT_FILE")

    try:
        with ZipFile(path) as archive:
            entries = archive.infolist()
            if len(entries) > 2000:
                raise ParseError("RESOURCE_LIMIT")
            for entry in entries:
                name = entry.filename
                parts = PurePosixPath(name).parts
                if (not parts or name.startswith("/") or "\\" in name or ":" in name
                        or any(p in {"..", "."} for p in name.split("/")) or name in names
                        or stat.S_ISLNK(entry.external_attr >> 16) or entry.flag_bits & 1):
                    raise ParseError("CORRUPT_FILE")
                names.add(name)
                if (entry.file_size > 32 * 1024 * 1024
                        or entry.file_size > max(1, entry.compress_size) * 100):
                    raise ParseError("RESOURCE_LIMIT")
                parser = None
                if name.endswith((".xml", ".rels")):
                    parser = expat.ParserCreate(namespace_separator="}")
                    parser.StartDoctypeDeclHandler = forbidden
                    parser.ExternalEntityRefHandler = forbidden
                    if name == "[Content_Types].xml":
                        def start(tag, attrs):
                            if tag == "http://schemas.openxmlformats.org/package/2006/content-types}Override":
                                content_types[attrs.get("PartName")] = attrs.get("ContentType")
                        parser.StartElementHandler = start
                actual = 0
                with archive.open(entry) as stream:
                    while piece := stream.read(65536):
                        actual += len(piece)
                        total += len(piece)
                        if actual > 32 * 1024 * 1024 or total > 128 * 1024 * 1024:
                            raise ParseError("RESOURCE_LIMIT")
                        if parser:
                            parser.Parse(piece, False)
                if parser:
                    parser.Parse(b"", True)
                if actual != entry.file_size:
                    raise ParseError("CORRUPT_FILE")
        main, expected = MAIN_TYPES[kind]
        if (main not in names or content_types.get("/" + main) != expected
                or any("macroenabled" in value.lower() for value in content_types.values())
                or any("vbaproject" in name.lower() for name in names)):
            raise ParseError("UNSUPPORTED_TYPE")
        return names
    except (BadZipFile, expat.ExpatError, RuntimeError, KeyError, EOFError) as error:
        raise ParseError("CORRUPT_FILE") from error
