from __future__ import annotations

from pathlib import Path
from typing import cast

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTextEdit, QComboBox,
    QCheckBox, QSpinBox, QDoubleSpinBox, QMessageBox
)

from PIL import Image
from PIL.ImageQt import ImageQt

from core.metadata import ImageMeta, read_metadata, metadata_to_text
from core.visible_watermark import Position, VisibleParams, apply_visible_watermark
from core.steg_lsb import StegParams, embed_text, extract_text, clean_lsb, capacity_bytes
from core.binary_diff import diff_files


def pil_to_pixmap(im: Image.Image) -> QPixmap:
    return QPixmap.fromImage(ImageQt(im))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vandens ženklai + Steganografija (PySide6)")

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self._init_visible_tab()
        self._init_steg_tab()
        self._init_info_tab()

    # ------------------ TAB 1: Visible watermark ------------------
    def _init_visible_tab(self):
        self.base_meta: ImageMeta | None = None

        w = QWidget()
        root = QVBoxLayout(w)

        # Buttons
        btn_row = QHBoxLayout()
        self.btn_load_base = QPushButton("Load base image")
        self.btn_load_wm = QPushButton("Load watermark image")
        self.btn_save_visible = QPushButton("Save result")
        btn_row.addWidget(self.btn_load_base)
        btn_row.addWidget(self.btn_load_wm)
        btn_row.addWidget(self.btn_save_visible)
        root.addLayout(btn_row)

        # Params
        params_row = QHBoxLayout()

        self.angle = QDoubleSpinBox()
        self.angle.setRange(-180.0, 180.0)
        self.angle.setValue(-25.0)

        self.opacity = QDoubleSpinBox()
        self.opacity.setRange(0.0, 1.0)
        self.opacity.setSingleStep(0.05)
        self.opacity.setValue(0.35)

        self.scale = QDoubleSpinBox()
        self.scale.setRange(0.05, 1.0)
        self.scale.setSingleStep(0.05)
        self.scale.setValue(0.25)

        self.repeat = QCheckBox("Repeat/tile")

        self.spacing = QSpinBox()
        self.spacing.setRange(0, 1000)
        self.spacing.setValue(40)

        self.position_combo = QComboBox()
        self.position_combo.addItems([
            "top_left", "top_center", "top_right",
            "center_left", "center", "center_right",
            "bottom_left", "bottom_center", "bottom_right",
        ])
        self.position_combo.setCurrentText("bottom_right")

        params_row.addWidget(QLabel("Angle"))
        params_row.addWidget(self.angle)
        params_row.addWidget(QLabel("Opacity"))
        params_row.addWidget(self.opacity)
        params_row.addWidget(QLabel("Scale"))
        params_row.addWidget(self.scale)
        params_row.addWidget(self.repeat)
        params_row.addWidget(QLabel("Spacing"))
        params_row.addWidget(self.spacing)
        params_row.addWidget(QLabel("Position"))
        params_row.addWidget(self.position_combo)
        root.addLayout(params_row)

        # Preview + metadata
        img_row = QHBoxLayout()

        self.lbl_preview_visible = QLabel("Preview")
        self.lbl_preview_visible.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview_visible.setMinimumHeight(320)

        meta_col = QVBoxLayout()
        self.meta_before_visible = QTextEdit()
        self.meta_before_visible.setReadOnly(True)
        self.meta_after_visible = QTextEdit()
        self.meta_after_visible.setReadOnly(True)

        meta_col.addWidget(QLabel("Metadata BEFORE"))
        meta_col.addWidget(self.meta_before_visible)
        meta_col.addWidget(QLabel("Metadata AFTER (saved file)"))
        meta_col.addWidget(self.meta_after_visible)

        img_row.addWidget(self.lbl_preview_visible, 2)
        img_row.addLayout(meta_col, 3)
        root.addLayout(img_row)

        self.tabs.addTab(w, "Matomas vandens ženklas")

        # State
        self.base_path: str | None = None
        self.wm_path: str | None = None
        self.visible_result: Image.Image | None = None

        # Signals
        self.btn_load_base.clicked.connect(self._load_base_visible)
        self.btn_load_wm.clicked.connect(self._load_wm_visible)
        self.btn_save_visible.clicked.connect(self._save_visible)

        # Auto re-render on param changes
        self.angle.valueChanged.connect(self._render_visible_preview)
        self.opacity.valueChanged.connect(self._render_visible_preview)
        self.scale.valueChanged.connect(self._render_visible_preview)
        self.repeat.stateChanged.connect(self._render_visible_preview)
        self.spacing.valueChanged.connect(self._render_visible_preview)
        self.position_combo.currentIndexChanged.connect(
            self._render_visible_preview)

    def _render_visible_preview(self) -> None:
        if not self.base_path:
            self.lbl_preview_visible.setText("Preview")
            self.lbl_preview_visible.setPixmap(QPixmap())  # clear
            self.visible_result = None
            return

        base = Image.open(self.base_path)

        # If watermark not chosen, show base only
        if not self.wm_path:
            pix = pil_to_pixmap(base).scaled(
                self.lbl_preview_visible.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.lbl_preview_visible.setPixmap(pix)
            self.visible_result = None
            return

        wm = Image.open(self.wm_path)

        params = VisibleParams(
            angle_deg=float(self.angle.value()),
            opacity=float(self.opacity.value()),
            scale=float(self.scale.value()),
            repeat=bool(self.repeat.isChecked()),
            tile_spacing=int(self.spacing.value()),
            position=cast(Position, self.position_combo.currentText()),
        )

        self.visible_result = apply_visible_watermark(base, wm, params)

        pix = pil_to_pixmap(self.visible_result).scaled(
            self.lbl_preview_visible.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.lbl_preview_visible.setPixmap(pix)

    def _load_base_visible(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select base image", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if not path:
            return

        self.base_path = path
        self.base_meta = read_metadata(path)
        self.meta_before_visible.setPlainText(
            metadata_to_text(self.base_meta))

        # Immediately render preview (base only or with watermark if already chosen)
        self._render_visible_preview()

    def _load_wm_visible(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select watermark image", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if not path:
            return

        self.wm_path = path
        self._render_visible_preview()

    def _save_visible(self):
        if self.visible_result is None or not self.base_meta:
            QMessageBox.warning(
                self, "Nothing", "Load base and watermark images first.")
            return

        default_filter = self._default_save_filter_for_visible()

        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save image",
            "",
            "JPEG (*.jpg *.jpeg);;PNG (*.png);;BMP (*.bmp)",
            default_filter,
        )
        if not path:
            return

        out = self.visible_result

        # Išsprendžiam "JPEG negali turėti alpha"
        # Ir bendrai stengiamės atkartoti originalų mode, jei įmanoma.
        base_fmt = (self.base_meta.format or "").upper()
        base_mode = self.base_meta.mode

        # Nustatom į ką realiai saugom pagal pasirinktą filtrą arba pagal path extension
        # (nes vartotojas gali įrašyti plėtinį ranka)
        lower_path = path.lower()
        saving_jpeg = ("*.jpg" in selected_filter.lower()
                       ) or lower_path.endswith((".jpg", ".jpeg"))
        saving_png = ("*.png" in selected_filter.lower()
                      ) or lower_path.endswith(".png")
        saving_bmp = ("*.bmp" in selected_filter.lower()
                      ) or lower_path.endswith(".bmp")

        if saving_jpeg or (base_fmt in ("JPEG", "JPG") and not (saving_png or saving_bmp)):
            # JPEG: privalomai RGB
            out = out.convert("RGB")
            out.save(path, format="JPEG", quality=95,
                     optimize=True, progressive=True)

        elif saving_png or base_fmt == "PNG":
            # PNG: jei originalas buvo RGB (be alpha) – nenumetame į RGBA be reikalo
            if base_mode == "RGB":
                out = out.convert("RGB")
            out.save(path, format="PNG", optimize=True)

        elif saving_bmp or base_fmt == "BMP":
            # BMP: dažniausiai RGB
            if base_mode in ("RGB", "L"):
                out = out.convert(base_mode)
            else:
                out = out.convert("RGB")
            out.save(path, format="BMP")

        else:
            # Fallback
            out = out.convert("RGB")
            out.save(path)

        self.meta_after_visible.setPlainText(
            metadata_to_text(read_metadata(path)))

    def _default_save_filter_for_visible(self) -> str:
        if not self.base_meta:
            return "PNG (*.png)"

        fmt = (self.base_meta.format or "").upper()
        if fmt in ("JPEG", "JPG"):
            return "JPEG (*.jpg *.jpeg)"
        if fmt == "PNG":
            return "PNG (*.png)"
        if fmt == "BMP":
            return "BMP (*.bmp)"
        return "PNG (*.png)"

    # ------------------ TAB 2: Steganography (LSB) ------------------
    def _init_steg_tab(self):
        w = QWidget()
        root = QVBoxLayout(w)

        # --- Top buttons row ---
        top = QHBoxLayout()

        self.btn_load_steg = QPushButton("Load image")
        self.btn_encode = QPushButton("Encode text")
        self.btn_clean = QPushButton("Clean image")
        self.btn_extract = QPushButton("Extract text")
        self.btn_save_steg = QPushButton("Save image")

        top.addWidget(self.btn_load_steg)
        top.addWidget(self.btn_encode)
        top.addWidget(self.btn_clean)
        top.addWidget(self.btn_extract)
        top.addWidget(self.btn_save_steg)

        top.addSpacing(12)
        top.addWidget(QLabel("Bits/channel"))

        self.bits_per_channel = QSpinBox()
        self.bits_per_channel.setRange(1, 2)
        self.bits_per_channel.setValue(1)
        self.bits_per_channel.setFixedWidth(70)  # make it wider
        top.addWidget(self.bits_per_channel)

        self.lbl_capacity = QLabel("Capacity: -")
        top.addWidget(self.lbl_capacity)

        top.addStretch(1)
        root.addLayout(top)

        # --- Main content: left (text + images) and right (metadata) ---
        main = QHBoxLayout()

        # LEFT column: text, original preview, encoded/processed preview
        left = QVBoxLayout()

        left.addWidget(QLabel("Tekstas"))
        self.steg_text = QTextEdit()
        self.steg_text.setPlaceholderText(
            "Įvesk paslepiamą tekstą (UTF-8)...\n"
            "(Extract metu čia bus parodytas atgautas tekstas)"
        )
        left.addWidget(self.steg_text, 2)

        left.addWidget(QLabel("Originalus vaizdas"))
        self.lbl_steg_original = QLabel("Original image preview")
        self.lbl_steg_original.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_steg_original.setMinimumHeight(220)
        left.addWidget(self.lbl_steg_original, 3)

        left.addWidget(QLabel("Po LSB algoritmo"))
        self.lbl_steg_processed = QLabel("Processed image preview")
        self.lbl_steg_processed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_steg_processed.setMinimumHeight(220)
        left.addWidget(self.lbl_steg_processed, 3)

        # RIGHT column: metadata before/after
        right = QVBoxLayout()

        right.addWidget(QLabel("Metadata BEFORE"))
        self.meta_before_steg = QTextEdit()
        self.meta_before_steg.setReadOnly(True)
        right.addWidget(self.meta_before_steg, 1)

        right.addWidget(QLabel("Metadata AFTER (saved file)"))
        self.meta_after_steg = QTextEdit()
        self.meta_after_steg.setReadOnly(True)
        right.addWidget(self.meta_after_steg, 1)

        main.addLayout(left, 3)
        main.addLayout(right, 2)
        root.addLayout(main)

        self.tabs.addTab(w, "Nematomas tekstas (LSB)")

        # --- State ---
        self.steg_src_path = None
        self.steg_src_image = None

        self.steg_encoded_image = None
        self.steg_clean_image = None

        # "currently selected" image for saving (encoded/clean)
        self.steg_current_image = None
        self.steg_current_kind = None  # "encoded" / "clean"

        # --- Signals ---
        self.btn_load_steg.clicked.connect(self._load_steg_src)
        self.btn_encode.clicked.connect(self._encode_text)
        self.btn_clean.clicked.connect(self._clean_current_or_encoded)
        self.btn_extract.clicked.connect(self._extract_from_loaded_or_pick)
        self.btn_save_steg.clicked.connect(self._save_steg_current)

        self.bits_per_channel.valueChanged.connect(self._update_capacity_label)
        self.steg_text.textChanged.connect(self._update_capacity_label)

    def _load_steg_src(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select image", "", "Images (*.png *.bmp)"
        )
        if not path:
            return
        self._load_steg_src_from_path(path)

    def _load_steg_src_from_path(self, path: str):
        self.steg_src_path = path
        self.steg_src_image = Image.open(path)

        # reset derived images
        self.steg_encoded_image = None
        self.steg_clean_image = None
        self.steg_current_image = None
        self.steg_current_kind = None
        self.lbl_steg_processed.setPixmap(QPixmap())  # clear

        # metadata BEFORE
        self.meta_before_steg.setPlainText(
            metadata_to_text(read_metadata(path)))
        self.meta_after_steg.setPlainText("")

        # show original preview
        pix = pil_to_pixmap(self.steg_src_image).scaled(
            self.lbl_steg_original.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.lbl_steg_original.setPixmap(pix)

        self._update_capacity_label()

    def _update_capacity_label(self):
        if not self.steg_src_path:
            self.lbl_capacity.setText("Capacity: -")
            return

        im = Image.open(self.steg_src_path)
        params = StegParams(bits_per_channel=int(
            self.bits_per_channel.value()))
        cap = capacity_bytes(im, params)
        self.lbl_capacity.setText(
            f"Capacity: { len(self.steg_text.toPlainText())}/{cap} bytes (ASCII chars approx)")

    def _encode_text(self):
        if not self.steg_src_path:
            QMessageBox.warning(
                self, "Missing", "Load an image first (PNG/BMP recommended).")
            return

        text = self.steg_text.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "Missing", "Enter some text to embed.")
            return

        params = StegParams(bits_per_channel=int(
            self.bits_per_channel.value()))
        src = Image.open(self.steg_src_path)

        try:
            out = embed_text(src, text, params)
        except Exception as e:
            QMessageBox.critical(self, "Encode failed", str(e))
            return

        self.steg_encoded_image = out
        self.steg_current_image = out
        self.steg_current_kind = "encoded"

        pix = pil_to_pixmap(out).scaled(
            self.lbl_steg_processed.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.lbl_steg_processed.setPixmap(pix)

    def _clean_current_or_encoded(self):
        # Prefer current image, then encoded, then loaded original (steg_src_image)
        if self.steg_current_image is not None:
            base = self.steg_current_image
        elif self.steg_encoded_image is not None:
            base = self.steg_encoded_image
        elif self.steg_src_path is not None:
            base = Image.open(self.steg_src_path)
            self.steg_current_image = base
            self.steg_current_kind = "loaded_marked"
        else:
            QMessageBox.warning(self, "Missing", "Load an image first.")
            return

        params = StegParams(bits_per_channel=int(
            self.bits_per_channel.value()))
        out = clean_lsb(base, params)

        self.steg_clean_image = out
        self.steg_current_image = out
        self.steg_current_kind = "clean"

        pix = pil_to_pixmap(out).scaled(
            self.lbl_steg_processed.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.lbl_steg_processed.setPixmap(pix)
        self.steg_text.clear()

    def _extract_from_loaded_or_pick(self):
        params = StegParams(bits_per_channel=int(
            self.bits_per_channel.value()))

        # If no image loaded yet, ask user to pick one and load it as ORIGINAL
        if not self.steg_src_path:
            path, _ = QFileDialog.getOpenFileName(
                self, "Select image to extract from", "", "Images (*.png *.bmp)"
            )
            if not path:
                return
            self._load_steg_src_from_path(path)

            # IMPORTANT: set current image to the loaded file so Clean/Save works
            loaded_img = Image.open(path)
            self.steg_current_image = loaded_img
            self.steg_current_kind = "loaded_marked"
            # show it also in processed preview (optional but useful)
            pix = pil_to_pixmap(loaded_img).scaled(
                self.lbl_steg_processed.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.lbl_steg_processed.setPixmap(pix)

        # Extract from the loaded ORIGINAL image
        try:
            img = Image.open(str(self.steg_src_path))
            msg = extract_text(img, params)
        except Exception as e:
            QMessageBox.critical(self, "Extract failed", str(e))
            return

        self.steg_text.setPlainText(msg)

    def _save_steg_current(self):
        if self.steg_current_image is None:
            QMessageBox.warning(
                self, "Nothing", "Nothing to save. Use Encode/Clean first.")
            return

        suggested = "marked.png" if self.steg_current_kind == "encoded" else "clean.png"

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save image", suggested, "PNG (*.png);;BMP (*.bmp)"
        )
        if not save_path:
            return

        self.steg_current_image.save(save_path)
        self.meta_after_steg.setPlainText(
            metadata_to_text(read_metadata(save_path)))

    # ------------------ TAB 4: About / Help ------------------
    def _init_info_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setHtml("""
        <h1>Programos aprašymas</h1>

        <p>
        Ši programa skirta pademonstruoti skaitmeninių vandens ženklų ir steganografijos veikimą
        naudojant paveikslėlius. Programa leidžia uždėti matomą vandens ženklą ant paveikslėlio,
        paslėpti tekstinį pranešimą naudojant LSB metodą, išgauti paslėptą tekstą bei palyginti
        paveikslėlio metaduomenis prieš ir po ženklinimo.
        </p>

        <h2>Programavimo kalba ir aplinka</h2>
        <p>
        Programa sukurta naudojant <b>Python</b> programavimo kalbą.<br>
        Grafinė vartotojo sąsaja realizuota naudojant <b>PySide6 (Qt for Python)</b> biblioteką.
        </p>

        <h2>Naudotos bibliotekos</h2>
        <ul>
        <li><b>PySide6</b> – grafinės vartotojo sąsajos kūrimui (langai, mygtukai, skirtukai, teksto laukai, paveikslėlių peržiūra).</li>
        <li><b>Pillow (PIL)</b> – paveikslėlių nuskaitymui, apdorojimui, vandens ženklo uždėjimui ir išsaugojimui.</li>
        </ul>

        <h2>Pasirinkti ženklinimo metodai</h2>

        <h3>1. Matomas vandens ženklas</h3>
        <p>
        Matomam vandens ženklinimui naudojamas <b>paveikslėlio uždėjimo ant kito paveikslėlio</b> metodas.
        Naudotojas gali pasirinkti pagrindinį paveikslėlį, pasirinkti vandens ženklo paveikslėlį,
        nustatyti pasvirimo kampą, mastelį, permatomumą, poziciją bei pasirinkti, ar vandens ženklas
        bus kartojamas visame paveikslėlyje.
        </p>

        <h3>2. Nematomas vandens ženklas / steganografija (LSB)</h3>
        <p>
        Programoje tekstinis pranešimas pirmiausia paverčiamas baitais, tada šie baitai suskaidomi į bitus.
        Toliau tie bitai įrašomi į paveikslėlio <b>RGB kanalų</b> mažiausiai reikšmingus bitus. Išgavimo metu
        atliekamas atvirkštinis procesas – nuskaitomi mažiausiai reikšmingi bitai, atkuriami baitai ir
        galiausiai atkuriamas tekstinis pranešimas.
        </p>

        <h2>Programos funkcijos</h2>
        <ul>
        <li>Matomo vandens ženklo uždėjimas ant paveikslėlio.</li>
        <li>Tekstinio pranešimo slėpimas paveikslėlyje naudojant LSB metodą.</li>
        <li>Paslėpto tekstinio pranešimo išgavimas.</li>
        <li>Paveikslėlio „išvalymas“ nuo LSB pranešimo.</li>
        <li>Paveikslėlių metaduomenų peržiūra prieš ir po ženklinimo.</li>
        </ul>

        <h2>Kaip naudotis programa</h2>
        <ol>
        <li>Pasirinkti norimą skirtuką: matomas vandens ženklas arba LSB steganografija.</li>
        <li>Įkelti paveikslėlį naudojant mygtuką <b>Load image</b> arba <b>Load base image</b>.</li>
        <li>Matomo vandens ženklo atveju pasirinkti papildomą vandens ženklo paveikslėlį ir nustatyti parametrus.</li>
        <li>LSB atveju įvesti tekstą ir paspausti <b>Encode text</b>.</li>
        <li>Norint atkurti tekstą, naudoti <b>Extract text</b>.</li>
        <li>Norint pašalinti paslėptą pranešimą, naudoti <b>Clean image</b>.</li>
        <li>Galutinį rezultatą išsaugoti naudojant <b>Save image</b>.</li>
        </ol>

        <h2>Autorius</h2>
        <p>
        Projektą sukūrė <b>Justas Kaulakis</b>.<br>
        Grupė: IFB-3<br>
        KTU Informatikos inžinerija.<br>
        2026 m.
        </p>
        """)

        layout.addWidget(info_text)
        self.tabs.addTab(w, "Aprašymas")
