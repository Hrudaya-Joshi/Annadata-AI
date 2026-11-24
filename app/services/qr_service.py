"""
QR Code Generation Service for ANNADATA AI
Provides high-fidelity, zero-dependency SVG & Base64 Data-URI QR Code Generation.
Also supports `qrcode` library if installed.
"""
import base64
import html


class QRService:
    @staticmethod
    def generate_svg(data: str, size: int = 240, dark_color: str = "#123D32", light_color: str = "#FFFFFF") -> str:
        """
        Generate a valid, scannable QR Code as an SVG string.
        Uses pure Python implementation with Reed-Solomon error correction.
        """
        try:
            import qrcode
            import qrcode.image.svg
            import io
            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)
            factory = qrcode.image.svg.SvgPathImage
            img = qr.make_image(image_factory=factory)
            stream = io.BytesIO()
            img.save(stream)
            svg_str = stream.getvalue().decode('utf-8')
            return svg_str
        except ImportError:
            # Fallback to robust pure-python QR generator
            return QRService._pure_python_qr_svg(data, size, dark_color, light_color)

    @classmethod
    def generate_data_uri(cls, data: str, size: int = 240, dark_color: str = "#123D32", light_color: str = "#FFFFFF") -> str:
        """Generate a base64 encoded data URI for embedding directly in <img src="...">"""
        svg = cls.generate_svg(data, size=size, dark_color=dark_color, light_color=light_color)
        b64 = base64.b64encode(svg.encode('utf-8')).decode('ascii')
        return f"data:image/svg+xml;base64,{b64}"

    @staticmethod
    def _pure_python_qr_svg(text: str, size: int = 240, dark_color: str = "#123D32", light_color: str = "#FFFFFF") -> str:
        """
        Self-contained QR Code Version 2-4 byte-mode generator in pure Python.
        Generates standard QR module matrix with Reed-Solomon ECC and renders crisp SVG.
        """
        matrix = PureQR.encode_to_matrix(text)
        modules = len(matrix)
        viewbox_size = modules + 8  # 4 module quiet zone on each side
        path_segments = []
        for r in range(modules):
            for c in range(modules):
                if matrix[r][c]:
                    x = c + 4
                    y = r + 4
                    path_segments.append(f"M{x},{y}h1v1h-1z")

        path_d = "".join(path_segments)
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {viewbox_size} {viewbox_size}" '
            f'width="{size}" height="{size}" shape-rendering="crispEdges">'
            f'<rect width="{viewbox_size}" height="{viewbox_size}" fill="{light_color}"/>'
            f'<path d="{path_d}" fill="{dark_color}"/>'
            f'</svg>'
        )
        return svg


class PureQR:
    """Minimal, self-contained QR Code Encoder (ISO/IEC 18004) for URL & text payloads."""

    # Precomputed Galois Field GF(2^8) tables
    EXP = [0] * 512
    LOG = [0] * 256
    _initialized = False

    @classmethod
    def _init_gf(cls):
        if cls._initialized:
            return
        x = 1
        for i in range(255):
            cls.EXP[i] = x
            cls.LOG[x] = i
            x <<= 1
            if x & 256:
                x ^= 0x11d
        for i in range(255, 512):
            cls.EXP[i] = cls.EXP[i - 255]
        cls._initialized = True

    @classmethod
    def _gf_mul(cls, x, y):
        if x == 0 or y == 0:
            return 0
        return cls.EXP[cls.LOG[x] + cls.LOG[y]]

    @classmethod
    def _rs_poly(cls, n_ecc):
        # Generate generator polynomial for Reed-Solomon code of length n_ecc
        poly = [1]
        for i in range(n_ecc):
            factor = [1, cls.EXP[i]]
            new_poly = [0] * (len(poly) + 1)
            for j in range(len(poly)):
                new_poly[j] ^= cls._gf_mul(poly[j], factor[0])
                new_poly[j + 1] ^= cls._gf_mul(poly[j], factor[1])
            poly = new_poly
        return poly

    @classmethod
    def _calculate_ecc(cls, data_bytes, n_ecc):
        cls._init_gf()
        gen = cls._rs_poly(n_ecc)
        msg = list(data_bytes) + [0] * n_ecc
        for i in range(len(data_bytes)):
            coef = msg[i]
            if coef != 0:
                for j in range(len(gen)):
                    msg[i + j] ^= cls._gf_mul(gen[j], coef)
        return msg[len(data_bytes):]

    @classmethod
    def encode_to_matrix(cls, text: str):
        cls._init_gf()
        data = text.encode('utf-8')
        length = len(data)

        # Determine version (M-level ECC)
        # V1: 16 data bytes (128 bits), V2: 28 data bytes, V3: 44 data bytes, V4: 64 data bytes, V5: 86 data bytes
        capacity = [(1, 16, 10, 21), (2, 28, 16, 25), (3, 44, 26, 29), (4, 64, 36, 33), (5, 86, 48, 37)]
        chosen = None
        for ver, cap, ecc_len, dim in capacity:
            if length + 3 <= cap:
                chosen = (ver, cap, ecc_len, dim)
                break
        if not chosen:
            # Default to version 5
            chosen = (5, 86, 48, 37)

        ver, data_cap, ecc_count, dim = chosen

        # Build bitstream: Byte Mode Indicator (0100) + Character Count Indicator (8 bits for V1-9) + data + terminator + padding
        bitstream = []

        def add_bits(val, count):
            for i in range(count - 1, -1, -1):
                bitstream.append((val >> i) & 1)

        add_bits(0b0100, 4)  # Byte mode
        add_bits(length, 8)  # Character count
        for byte in data:
            add_bits(byte, 8)

        # Terminator up to 4 zero bits
        needed = data_cap * 8
        rem = needed - len(bitstream)
        for _ in range(min(4, max(0, rem))):
            bitstream.append(0)

        # Pad to multiple of 8
        while len(bitstream) % 8 != 0:
            bitstream.append(0)

        # Pad bytes 0xEC, 0x11
        pad_bytes = [0xEC, 0x11]
        pad_idx = 0
        while len(bitstream) < needed:
            add_bits(pad_bytes[pad_idx % 2], 8)
            pad_idx += 1

        # Convert bitstream to bytes
        data_bytes = []
        for i in range(0, len(bitstream), 8):
            byte = 0
            for b in range(8):
                byte = (byte << 1) | bitstream[i + b]
            data_bytes.append(byte)

        # Compute Reed-Solomon ECC
        ecc_bytes = cls._calculate_ecc(data_bytes[:data_cap], ecc_count)
        all_codewords = data_bytes[:data_cap] + ecc_bytes

        # Initialize matrix: dim x dim
        matrix = [[None] * dim for _ in range(dim)]
        reserved = [[False] * dim for _ in range(dim)]

        def set_module(r, c, val):
            matrix[r][c] = bool(val)
            reserved[r][c] = True

        # 1. Finder patterns (top-left, top-right, bottom-left)
        def draw_finder(top, left):
            for r in range(-1, 8):
                for c in range(-1, 8):
                    nr, nc = top + r, left + c
                    if 0 <= nr < dim and 0 <= nc < dim:
                        if 0 <= r <= 6 and 0 <= c <= 6:
                            if r in (0, 6) or c in (0, 6) or (2 <= r <= 4 and 2 <= c <= 4):
                                set_module(nr, nc, 1)
                            else:
                                set_module(nr, nc, 0)
                        else:
                            set_module(nr, nc, 0)

        draw_finder(0, 0)
        draw_finder(0, dim - 7)
        draw_finder(dim - 7, 0)

        # 2. Timing patterns
        for i in range(8, dim - 8):
            set_module(6, i, 1 if i % 2 == 0 else 0)
            set_module(i, 6, 1 if i % 2 == 0 else 0)

        # 3. Dark module
        set_module(dim - 8, 8, 1)

        # 4. Alignment patterns for V2+
        if ver >= 2:
            align_coords = {2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30]}
            pos = align_coords.get(ver, [6, 30])
            for ar in pos:
                for ac in pos:
                    if reserved[ar][ac]:
                        continue
                    for dr in range(-2, 3):
                        for dc in range(-2, 3):
                            val = 1 if max(abs(dr), abs(dc)) in (0, 2) else 0
                            set_module(ar + dr, ac + dc, val)

        # 5. Format info area reservation
        for i in range(9):
            if not reserved[8][i]:
                reserved[8][i] = True
            if not reserved[i][8]:
                reserved[i][8] = True
        for i in range(dim - 8, dim):
            if not reserved[8][i]:
                reserved[8][i] = True
        for i in range(dim - 8, dim):
            if not reserved[i][8]:
                reserved[i][8] = True

        # 6. Place data codewords
        codeword_bits = []
        for byte in all_codewords:
            for b in range(7, -1, -1):
                codeword_bits.append((byte >> b) & 1)

        bit_idx = 0
        direction = -1  # upwards
        c = dim - 1
        while c > 0:
            if c == 6:  # Skip vertical timing pattern
                c -= 1
            rows = range(dim - 1, -1, -1) if direction == -1 else range(dim)
            for r in rows:
                for col in (c, c - 1):
                    if not reserved[r][col]:
                        val = codeword_bits[bit_idx] if bit_idx < len(codeword_bits) else 0
                        bit_idx += 1
                        # Apply mask 0: (r + c) % 2 == 0
                        mask = ((r + col) % 2 == 0)
                        matrix[r][col] = bool(val ^ mask)
            direction = -direction
            c -= 2

        # 7. Write format info (Format bits for ECC Level M, Mask pattern 0: 0x5412)
        # Format string for Level M, Mask 0 with BCH error correction and mask: 101010000010010 (0x5412)
        fmt_bits = [int(b) for b in "101010000010010"]
        # Top-left around finder pattern
        fmt_coords_1 = [
            (8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7), (8, 8),
            (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8)
        ]
        for idx, (r, col) in enumerate(fmt_coords_1):
            matrix[r][col] = bool(fmt_bits[idx])

        # Bottom-left and Top-right
        fmt_coords_2 = [
            (dim - 1, 8), (dim - 2, 8), (dim - 3, 8), (dim - 4, 8), (dim - 5, 8), (dim - 6, 8), (dim - 7, 8),
            (8, dim - 8), (8, dim - 7), (8, dim - 6), (8, dim - 5), (8, dim - 4), (8, dim - 3), (8, dim - 2), (8, dim - 1)
        ]
        for idx, (r, col) in enumerate(fmt_coords_2):
            matrix[r][col] = bool(fmt_bits[idx])

        return matrix
