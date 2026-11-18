"""Indexed text .bin reader/writer.

Ported from ccc-tl/translation-tools IndexedTextBinFile.kt / TextBinFilePatcher.kt.

Layout: repeating [u32 index][u32 byteLength][CP932 string, NUL padded to 4].
Stops when an index goes backwards (or is 0 after the first entry), or the
declared length is 0. Newlines inside these files are stored as "\\n\\r".
"""
import struct
from fatetext import decode, encode, read_dat_string


# A few files are stored as UTF-8 rather than CP932. The official tools pass an
# explicit charset for these (see MiscTranslationProcessor).
UTF8_FILES = {'interface/cmn/install.bin'}


def parse(data, utf8=False):
    """Return list of (index, text) or None if the file is not indexed text."""
    entries = []
    pos = 0
    n = len(data)
    last_index = 0
    while pos + 8 <= n:
        index = struct.unpack_from('<I', data, pos)[0]
        if index < last_index or (index == 0 and entries):
            break
        length = struct.unpack_from('<I', data, pos + 4)[0]
        if length == 0:
            break
        pos += 8
        if pos + length > n:
            return None
        try:
            raw, consumed = read_dat_string(data, pos)
        except EOFError:
            return None
        if utf8:
            text = raw.decode('utf-8', 'replace').replace('\n\r', '\n')
        else:
            text = decode(raw).replace('\n\r', '\n')
        entries.append((index, text))
        pos += consumed
        last_index += 1
    if not entries:
        return None
    return entries


def looks_like_text(entries):
    """Heuristic: real text files decode to mostly printable characters.

    Binary tables can pass a naive printable check because stray bytes happen
    to decode to letters, so a real entry must also contain an actual run of
    letters - that is what separates a sentence from noise.
    """
    if not entries:
        return False
    total = 0
    bad = 0
    letters = 0
    has_word = False
    for _, t in entries:
        run = 0
        for ch in t:
            total += 1
            o = ord(ch)
            if o < 0x20 and ch not in '\n\r\t':
                bad += 1
            elif ch == '�':
                bad += 1
            if ch.isalpha():
                letters += 1
                run += 1
                if run >= 3:
                    has_word = True
            else:
                run = 0
    if total == 0 or not has_word:
        return False
    return bad / total < 0.05 and letters / total > 0.3


def build(entries, utf8=False):
    """Rebuild the .bin from (index, text) pairs, 16-byte aligned."""
    out = bytearray()
    for index, text in entries:
        body = text.replace('\n', '\n\r')
        payload = body.encode('utf-8') if utf8 else encode(body)
        pad = 4 - (len(payload) % 4)
        out += struct.pack('<II', index, len(payload) + pad)
        out += payload + b'\0' * pad
    while len(out) % 16:
        out += b'\0'
    return bytes(out)
