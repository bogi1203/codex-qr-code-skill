#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
import struct
import sys
import zlib
from pathlib import Path


ECC_CODEWORDS_PER_BLOCK = {
    "L": [-1, 7, 10, 15, 20, 26, 18, 20, 24, 30, 18, 20, 24, 26, 30, 22, 24, 28, 30, 28, 28, 28, 28, 30, 30, 26, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30],
    "M": [-1, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26, 30, 22, 22, 24, 24, 28, 28, 26, 26, 26, 26, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28],
    "Q": [-1, 13, 22, 18, 26, 18, 24, 18, 22, 20, 24, 28, 26, 24, 20, 30, 24, 28, 28, 26, 30, 28, 30, 30, 30, 30, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30],
    "H": [-1, 17, 28, 22, 16, 22, 28, 26, 26, 24, 28, 24, 28, 22, 24, 24, 30, 28, 28, 26, 28, 30, 24, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30],
}

NUM_ERROR_CORRECTION_BLOCKS = {
    "L": [-1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 4, 4, 4, 4, 4, 6, 6, 6, 6, 7, 8, 8, 9, 9, 10, 12, 12, 12, 13, 14, 15, 16, 17, 18, 19, 19, 20, 21, 22, 24, 25],
    "M": [-1, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5, 5, 8, 9, 9, 10, 10, 11, 13, 14, 16, 17, 17, 18, 20, 21, 23, 25, 26, 28, 29, 31, 33, 35, 37, 38, 40, 43, 45, 47, 49],
    "Q": [-1, 1, 1, 2, 2, 4, 4, 6, 6, 8, 8, 8, 10, 12, 16, 12, 17, 16, 18, 21, 20, 23, 23, 25, 27, 29, 34, 34, 35, 38, 40, 43, 45, 48, 51, 53, 56, 59, 62, 65, 68],
    "H": [-1, 1, 1, 2, 4, 4, 4, 5, 6, 8, 8, 11, 11, 16, 16, 18, 16, 19, 21, 25, 25, 25, 34, 30, 32, 35, 37, 40, 42, 45, 48, 51, 54, 57, 60, 63, 66, 70, 74, 77, 81],
}

FORMAT_BITS = {"L": 1, "M": 0, "Q": 3, "H": 2}
PAD_BYTES = (0xEC, 0x11)


class BitBuffer:
    def __init__(self) -> None:
        self.bits: list[int] = []

    def append(self, value: int, length: int) -> None:
        if length < 0 or value < 0 or value >= (1 << length):
            raise ValueError("Invalid bit value or length")
        for i in range(length - 1, -1, -1):
            self.bits.append((value >> i) & 1)

    def __len__(self) -> int:
        return len(self.bits)

    def to_codewords(self) -> list[int]:
        if len(self.bits) % 8 != 0:
            raise ValueError("Bit buffer length must be byte-aligned")
        return [
            sum(self.bits[i + j] << (7 - j) for j in range(8))
            for i in range(0, len(self.bits), 8)
        ]


def gf_multiply(x: int, y: int) -> int:
    result = 0
    for _ in range(8):
        if y & 1:
            result ^= x
        y >>= 1
        carry = x & 0x80
        x = (x << 1) & 0xFF
        if carry:
            x ^= 0x1D
    return result


def gf_pow2(power: int) -> int:
    result = 1
    for _ in range(power):
        result = gf_multiply(result, 2)
    return result


def poly_multiply(left: list[int], right: list[int]) -> list[int]:
    result = [0] * (len(left) + len(right) - 1)
    for i, left_coef in enumerate(left):
        for j, right_coef in enumerate(right):
            result[i + j] ^= gf_multiply(left_coef, right_coef)
    return result


def reed_solomon_generator(degree: int) -> list[int]:
    generator = [1]
    for i in range(degree):
        generator = poly_multiply(generator, [1, gf_pow2(i)])
    return generator


def reed_solomon_remainder(data: list[int], degree: int) -> list[int]:
    generator = reed_solomon_generator(degree)
    result = data[:] + [0] * degree
    for i, coefficient in enumerate(data):
        if coefficient == 0:
            continue
        factor = result[i]
        for j, generator_coefficient in enumerate(generator):
            result[i + j] ^= gf_multiply(generator_coefficient, factor)
    return result[-degree:]


def get_num_raw_data_modules(version: int) -> int:
    result = (16 * version + 128) * version + 64
    if version >= 2:
        num_align = version // 7 + 2
        result -= (25 * num_align - 10) * num_align - 55
        if version >= 7:
            result -= 36
    return result


def get_num_data_codewords(version: int, error_correction: str) -> int:
    raw_codewords = get_num_raw_data_modules(version) // 8
    return raw_codewords - (
        ECC_CODEWORDS_PER_BLOCK[error_correction][version]
        * NUM_ERROR_CORRECTION_BLOCKS[error_correction][version]
    )


def choose_version(data: bytes, error_correction: str) -> int:
    for version in range(1, 41):
        count_bits = 8 if version <= 9 else 16
        if len(data) >= (1 << count_bits):
            continue
        needed_bits = 4 + count_bits + len(data) * 8
        if needed_bits <= get_num_data_codewords(version, error_correction) * 8:
            return version
    raise ValueError("Payload is too large for QR Code version 40")


def encode_data_codewords(data: bytes, version: int, error_correction: str) -> list[int]:
    capacity_bits = get_num_data_codewords(version, error_correction) * 8
    count_bits = 8 if version <= 9 else 16

    buffer = BitBuffer()
    buffer.append(0x4, 4)
    buffer.append(len(data), count_bits)
    for byte in data:
        buffer.append(byte, 8)

    terminator = min(4, capacity_bits - len(buffer))
    buffer.append(0, terminator)
    while len(buffer) % 8:
        buffer.append(0, 1)

    pad_index = 0
    while len(buffer) < capacity_bits:
        buffer.append(PAD_BYTES[pad_index % 2], 8)
        pad_index += 1

    return buffer.to_codewords()


def add_ecc_and_interleave(data_codewords: list[int], version: int, error_correction: str) -> list[int]:
    num_blocks = NUM_ERROR_CORRECTION_BLOCKS[error_correction][version]
    block_ecc_len = ECC_CODEWORDS_PER_BLOCK[error_correction][version]
    raw_codewords = get_num_raw_data_modules(version) // 8
    num_short_blocks = num_blocks - raw_codewords % num_blocks
    short_data_len = raw_codewords // num_blocks - block_ecc_len

    data_blocks: list[list[int]] = []
    ecc_blocks: list[list[int]] = []
    offset = 0
    for block_index in range(num_blocks):
        data_len = short_data_len + (0 if block_index < num_short_blocks else 1)
        block = data_codewords[offset : offset + data_len]
        offset += data_len
        data_blocks.append(block)
        ecc_blocks.append(reed_solomon_remainder(block, block_ecc_len))

    if offset != len(data_codewords):
        raise ValueError("Internal QR block sizing error")

    result: list[int] = []
    for i in range(max(len(block) for block in data_blocks)):
        for block in data_blocks:
            if i < len(block):
                result.append(block[i])
    for i in range(block_ecc_len):
        for block in ecc_blocks:
            result.append(block[i])

    if len(result) != raw_codewords:
        raise ValueError("Internal QR interleave error")
    return result


def get_bit(value: int, index: int) -> bool:
    return ((value >> index) & 1) != 0


def alignment_pattern_positions(version: int) -> list[int]:
    if version == 1:
        return []
    size = version * 4 + 17
    num_align = version // 7 + 2
    step = 26 if version == 32 else ((version * 4 + num_align * 2 + 1) // (num_align * 2 - 2)) * 2
    return [6] + sorted(size - 7 - i * step for i in range(num_align - 1))


def mask_condition(mask: int, x: int, y: int) -> bool:
    if mask == 0:
        return (x + y) % 2 == 0
    if mask == 1:
        return y % 2 == 0
    if mask == 2:
        return x % 3 == 0
    if mask == 3:
        return (x + y) % 3 == 0
    if mask == 4:
        return (x // 3 + y // 2) % 2 == 0
    if mask == 5:
        return (x * y) % 2 + (x * y) % 3 == 0
    if mask == 6:
        return ((x * y) % 2 + (x * y) % 3) % 2 == 0
    if mask == 7:
        return ((x + y) % 2 + (x * y) % 3) % 2 == 0
    raise ValueError("Mask must be 0 through 7")


class QrMatrix:
    def __init__(self, version: int) -> None:
        self.version = version
        self.size = version * 4 + 17
        self.modules = [[False] * self.size for _ in range(self.size)]
        self.is_function = [[False] * self.size for _ in range(self.size)]

    def copy(self) -> "QrMatrix":
        other = QrMatrix(self.version)
        other.modules = [row[:] for row in self.modules]
        other.is_function = [row[:] for row in self.is_function]
        return other

    def set_function(self, x: int, y: int, dark: bool) -> None:
        self.modules[y][x] = dark
        self.is_function[y][x] = True

    def draw_finder(self, center_x: int, center_y: int) -> None:
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                x = center_x + dx
                y = center_y + dy
                if 0 <= x < self.size and 0 <= y < self.size:
                    distance = max(abs(dx), abs(dy))
                    self.set_function(x, y, distance != 2 and distance != 4)

    def draw_alignment(self, center_x: int, center_y: int) -> None:
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                self.set_function(
                    center_x + dx,
                    center_y + dy,
                    max(abs(dx), abs(dy)) != 1,
                )

    def draw_function_patterns(self, error_correction: str) -> None:
        self.draw_finder(3, 3)
        self.draw_finder(self.size - 4, 3)
        self.draw_finder(3, self.size - 4)

        for i in range(self.size):
            if not self.is_function[6][i]:
                self.set_function(i, 6, i % 2 == 0)
            if not self.is_function[i][6]:
                self.set_function(6, i, i % 2 == 0)

        positions = alignment_pattern_positions(self.version)
        for y in positions:
            for x in positions:
                if not self.is_function[y][x]:
                    self.draw_alignment(x, y)

        self.draw_format_bits(error_correction, 0)
        if self.version >= 7:
            self.draw_version_bits()

    def draw_format_bits(self, error_correction: str, mask: int) -> None:
        data = (FORMAT_BITS[error_correction] << 3) | mask
        remainder = data
        for _ in range(10):
            remainder = (remainder << 1) ^ ((remainder >> 9) * 0x537)
        bits = ((data << 10) | remainder) ^ 0x5412

        for i in range(6):
            self.set_function(8, i, get_bit(bits, i))
        self.set_function(8, 7, get_bit(bits, 6))
        self.set_function(8, 8, get_bit(bits, 7))
        self.set_function(7, 8, get_bit(bits, 8))
        for i in range(9, 15):
            self.set_function(14 - i, 8, get_bit(bits, i))

        for i in range(8):
            self.set_function(self.size - 1 - i, 8, get_bit(bits, i))
        for i in range(8, 15):
            self.set_function(8, self.size - 15 + i, get_bit(bits, i))
        self.set_function(8, self.size - 8, True)

    def draw_version_bits(self) -> None:
        remainder = self.version
        for _ in range(12):
            remainder = (remainder << 1) ^ ((remainder >> 11) * 0x1F25)
        bits = (self.version << 12) | remainder

        for i in range(18):
            bit = get_bit(bits, i)
            a = self.size - 11 + i % 3
            b = i // 3
            self.set_function(a, b, bit)
            self.set_function(b, a, bit)

    def place_codewords(self, codewords: list[int]) -> None:
        bits = [
            ((codeword >> i) & 1) != 0
            for codeword in codewords
            for i in range(7, -1, -1)
        ]
        bit_index = 0
        right = self.size - 1
        while right >= 1:
            if right == 6:
                right -= 1
            for vertical in range(self.size):
                upward = ((right + 1) & 2) == 0
                y = self.size - 1 - vertical if upward else vertical
                for x in (right, right - 1):
                    if not self.is_function[y][x]:
                        self.modules[y][x] = bits[bit_index] if bit_index < len(bits) else False
                        bit_index += 1
            right -= 2

        if bit_index < len(bits):
            raise ValueError("QR matrix does not have enough data modules")

    def apply_mask(self, mask: int) -> None:
        for y in range(self.size):
            for x in range(self.size):
                if not self.is_function[y][x] and mask_condition(mask, x, y):
                    self.modules[y][x] = not self.modules[y][x]

    def penalty_score(self) -> int:
        penalty = 0

        for row in self.modules:
            penalty += run_penalty(row)
        for x in range(self.size):
            penalty += run_penalty([self.modules[y][x] for y in range(self.size)])

        for y in range(self.size - 1):
            for x in range(self.size - 1):
                color = self.modules[y][x]
                if (
                    color == self.modules[y][x + 1]
                    and color == self.modules[y + 1][x]
                    and color == self.modules[y + 1][x + 1]
                ):
                    penalty += 3

        for row in self.modules:
            penalty += finder_pattern_penalty(row)
        for x in range(self.size):
            penalty += finder_pattern_penalty([self.modules[y][x] for y in range(self.size)])

        dark = sum(1 for row in self.modules for module in row if module)
        total = self.size * self.size
        penalty += (abs(dark * 20 - total * 10) // total) * 10
        return penalty


def run_penalty(line: list[bool]) -> int:
    penalty = 0
    run_color = line[0]
    run_len = 1
    for color in line[1:]:
        if color == run_color:
            run_len += 1
        else:
            if run_len >= 5:
                penalty += 3 + run_len - 5
            run_color = color
            run_len = 1
    if run_len >= 5:
        penalty += 3 + run_len - 5
    return penalty


def finder_pattern_penalty(line: list[bool]) -> int:
    pattern = [True, False, True, True, True, False, True]
    penalty = 0
    for i in range(len(line) - 6):
        if line[i : i + 7] != pattern:
            continue
        before = i >= 4 and not any(line[i - 4 : i])
        after = i + 11 <= len(line) and not any(line[i + 7 : i + 11])
        if before or after:
            penalty += 40
    return penalty


def encode_qr(content: str, error_correction: str) -> tuple[QrMatrix, int, int]:
    data = content.encode("utf-8")
    version = choose_version(data, error_correction)
    data_codewords = encode_data_codewords(data, version, error_correction)
    all_codewords = add_ecc_and_interleave(data_codewords, version, error_correction)

    base = QrMatrix(version)
    base.draw_function_patterns(error_correction)
    base.place_codewords(all_codewords)

    best_matrix: QrMatrix | None = None
    best_mask = -1
    best_penalty = 1 << 30
    for mask in range(8):
        candidate = base.copy()
        candidate.apply_mask(mask)
        candidate.draw_format_bits(error_correction, mask)
        penalty = candidate.penalty_score()
        if penalty < best_penalty:
            best_matrix = candidate
            best_mask = mask
            best_penalty = penalty

    if best_matrix is None:
        raise ValueError("Could not choose QR mask")
    return best_matrix, best_mask, best_penalty


def parse_color(value: str) -> tuple[str, tuple[int, int, int]]:
    if not re.fullmatch(r"#?[0-9a-fA-F]{6}", value):
        raise argparse.ArgumentTypeError("Color must be #RRGGBB")
    normalized = value if value.startswith("#") else f"#{value}"
    rgb = tuple(int(normalized[i : i + 2], 16) for i in (1, 3, 5))
    return normalized.upper(), rgb  # type: ignore[return-value]


def write_png(path: Path, matrix: QrMatrix, scale: int, border: int, dark: tuple[int, int, int], light: tuple[int, int, int]) -> None:
    image_size = (matrix.size + border * 2) * scale

    def chunk(chunk_type: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + chunk_type
            + data
            + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        )

    rows = bytearray()
    for pixel_y in range(image_size):
        module_y = pixel_y // scale - border
        rows.append(0)
        for pixel_x in range(image_size):
            module_x = pixel_x // scale - border
            is_dark = (
                0 <= module_x < matrix.size
                and 0 <= module_y < matrix.size
                and matrix.modules[module_y][module_x]
            )
            rows.extend(dark if is_dark else light)

    png = (
        b"\x89PNG\r\n\x1A\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", image_size, image_size, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(rows), level=9))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)


def write_svg(path: Path, matrix: QrMatrix, border: int, dark: str, light: str, title: str | None) -> None:
    size = matrix.size + border * 2
    commands = []
    for y, row in enumerate(matrix.modules):
        for x, module in enumerate(row):
            if module:
                commands.append(f"M{x + border},{y + border}h1v1h-1z")

    title_node = f"<title>{html.escape(title)}</title>" if title else ""
    path_data = " ".join(commands)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
        f'width="{size}" height="{size}" shape-rendering="crispEdges">'
        f"{title_node}"
        f'<rect width="100%" height="100%" fill="{light}"/>'
        f'<path d="{path_data}" fill="{dark}"/>'
        "</svg>\n"
    )
    path.write_text(svg, encoding="utf-8")


def resolve_output(path_text: str | None, output_format: str) -> tuple[Path, str]:
    path = Path(path_text) if path_text else Path("qrcode.png")
    suffix = path.suffix.lower()

    if output_format == "auto":
        fmt = "svg" if suffix == ".svg" else "png"
    else:
        fmt = output_format

    if path.suffix == "":
        path = path.with_suffix(f".{fmt}")
    return path, fmt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a scannable QR code as PNG or SVG.")
    parser.add_argument("content", nargs="?", help="Text or URL to encode. Use --input-file for multiline content.")
    parser.add_argument("--input-file", help="Read payload text from a UTF-8 file.")
    parser.add_argument("--output", "-o", help="Output path. Extension controls format when --format auto is used.")
    parser.add_argument("--format", choices=["auto", "png", "svg"], default="auto", help="Output format.")
    parser.add_argument("--error-correction", "-e", choices=["L", "M", "Q", "H"], default="M", help="QR error correction level.")
    parser.add_argument("--scale", type=int, default=10, help="PNG pixels per QR module.")
    parser.add_argument("--border", type=int, default=4, help="Quiet-zone modules around the QR code.")
    parser.add_argument("--dark", default="#000000", help="Dark module color as #RRGGBB.")
    parser.add_argument("--light", default="#FFFFFF", help="Light background color as #RRGGBB.")
    parser.add_argument("--title", help="SVG title text for accessibility.")
    parser.add_argument("--print-json", action="store_true", help="Print machine-readable generation metadata.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.scale < 1:
        parser.error("--scale must be at least 1")
    if args.border < 4:
        parser.error("--border must be at least 4 for reliable scanning")
    if args.content is None and args.input_file is None:
        parser.error("Provide content or --input-file")
    if args.content is not None and args.input_file is not None:
        parser.error("Use either content or --input-file, not both")

    if args.input_file:
        content = Path(args.input_file).read_text(encoding="utf-8")
    else:
        content = args.content

    output_path, output_format = resolve_output(args.output, args.format)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    dark_hex, dark_rgb = parse_color(args.dark)
    light_hex, light_rgb = parse_color(args.light)
    matrix, mask, penalty = encode_qr(content, args.error_correction)

    if output_format == "png":
        write_png(output_path, matrix, args.scale, args.border, dark_rgb, light_rgb)
    else:
        write_svg(output_path, matrix, args.border, dark_hex, light_hex, args.title)

    metadata = {
        "output": str(output_path.resolve()),
        "format": output_format,
        "error_correction": args.error_correction,
        "version": matrix.version,
        "modules": matrix.size,
        "mask": mask,
        "penalty": penalty,
        "payload_bytes": len(content.encode("utf-8")),
    }
    if args.print_json:
        print(json.dumps(metadata, ensure_ascii=False, indent=2))
    else:
        print(f"QR code written to {metadata['output']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
