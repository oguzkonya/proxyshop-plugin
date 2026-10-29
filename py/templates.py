"""
* KarbonatErol Templates
"""

from functools import cached_property

from photoshop.api._artlayer import ArtLayer

import src.helpers as psd
from src import APP, CON
from src.helpers.bounds import get_layer_height
from src.helpers.text import get_font_size, set_text_size_and_leading
from src.enums.layers import LAYERS
from src.enums.mtg import CardTextPatterns
from src.schema.colors import ColorObject, SymbolColorMap
from src.templates import NormalTemplate
from src.text_layers import (
    FormattedTextArea,
    FormattedTextField,
    ScaledTextField,
    TextField,
)
from src.utils.mtg import get_symbol_colors

"""
* Text Layers
"""


class MinSizeTextArea(FormattedTextArea):
    """FormattedTextArea which never scales the font below a minimum size (in pt)
    and keeps the leading to font size ratio of the PSD layer."""

    def execute(self):
        # Read the ratio before any scaling changes the leading
        text_item = self.layer.textItem
        self.leading_ratio = 1.0 if text_item.useAutoLeading else text_item.leading / text_item.size
        super().execute()

    def scale_to_fit(self, font_size: float | None = None) -> None:
        # Scale with leading equal to font size, then reapply the ratio, stepping down if it no longer fits
        super().scale_to_fit(font_size)
        min_size = self.kwargs.get("min_size") or 0
        height = (
            self.reference_dims["height"] - APP.instance.scale_by_dpi(64)
            if self.reference_dims else None
        )
        font_size = max(get_font_size(self.layer), min_size)
        set_text_size_and_leading(self.layer, font_size, font_size * self.leading_ratio)
        while height and font_size > min_size and get_layer_height(self.layer) > height:
            font_size = max(font_size - 0.2, min_size)
            set_text_size_and_leading(self.layer, font_size, font_size * self.leading_ratio)


"""
* Normal Templates
"""


class LcarsTemplate(NormalTemplate):
    """
    * Created by KarbonatErol.
    * Star Trek themed frame based on the LCARS computer interface.
    """

    template_suffix = "LCARS"

    # LCARS uses a single font, so italic and bold text use it as well
    font_lcars = "Antonio-Regular"

    # Rules text is never scaled below this size (pt, as in Photoshop's Character panel)
    rules_text_min_size = 7.2

    # Background layers available in the template
    background_colors = ("W", "U", "B", "R", "G", LAYERS.GOLD, LAYERS.COLORLESS)

    # Mana symbol font, a copy of Proxyglyph where each symbol carries its own ring
    font_mana_lcars = "LCARSGlyph"

    # Mana symbols are a single color, ring and symbol alike
    mana_colors_lcars: dict[str, ColorObject] = {
        "W": (245, 241, 179),
        "U": (101, 180, 226),
        "B": (120, 103, 175),
        "R": (228, 105, 117),
        "G": (132, 187, 130),
    }
    mana_color_generic: ColorObject = (165, 217, 220)

    # Hybrid half glyphs: 1st half (zero width) and 2nd half, drawn on the same spot
    hybrid_first = dict(zip("2WUBRG", "WLMNOP"))
    hybrid_second = dict(zip("WUBRG", "RSTUV"))

    """
    * Symbols
    """

    @cached_property
    def symbol_map_lcars(self) -> dict[str, tuple[str, list[ColorObject]]]:
        """dict: Symbols drawn on the blank circle use one color for all characters, hybrids use
        one glyph per half, other symbols (phyrexian, snow) are colored like Proxyglyph with LCARS colors."""
        colors = {"2": self.mana_color_generic, "C": self.mana_color_generic, **self.mana_colors_lcars}
        color_map = SymbolColorMap(colorless=self.mana_color_generic, colors=colors, hybrid=colors)
        symbol_map: dict[str, tuple[str, list[ColorObject]]] = {}
        for symbol, chars in CON.mana_symbols.items():
            if chars.startswith("o"):
                color = self.mana_colors_lcars.get(symbol.strip("{}"), self.mana_color_generic)
                symbol_map[symbol] = (chars, [color] * len(chars))
            elif hybrid := CardTextPatterns.MANA_HYBRID.match(symbol):
                # Each half is one glyph carrying its half of the ring, colored with its mana color
                first, second = hybrid[1], hybrid[2]
                symbol_map[symbol] = (
                    self.hybrid_first[first] + self.hybrid_second[second],
                    [colors[first], colors[second]],
                )
            else:
                symbol_map[symbol] = (chars, [
                    c if c is not None else self.mana_color_generic
                    for c in get_symbol_colors(symbol, chars, color_map)
                ])
        return symbol_map

    """
    * Frame Details
    """

    @cached_property
    def background(self) -> str:
        """str: No Land, Artifact, Vehicle or hybrid backgrounds, fallback on color identity."""
        if (background := super().background) in self.background_colors:
            return background
        if len(self.identity) == 1:
            return self.identity
        if len(self.identity) > 1:
            return LAYERS.GOLD
        return LAYERS.COLORLESS

    """
    * Frame Layers
    """

    @cached_property
    def twins_layer(self) -> ArtLayer | None:
        return

    @cached_property
    def pinlines_layer(self) -> ArtLayer | None:
        return

    @cached_property
    def pt_layer(self) -> ArtLayer | None:
        return

    @cached_property
    def crown_layer(self) -> ArtLayer | None:
        return

    """
    * Text Layers
    """

    @cached_property
    def text_layer_rules(self) -> ArtLayer | None:
        """ArtLayer: No separate text layer for creatures."""
        return psd.getLayer(LAYERS.RULES_TEXT, self.text_group)

    """
    * Text Layer Methods
    """

    def basic_text_layers(self) -> None:
        """Card name and typeline are written in all caps."""
        if self.text_layer_mana:
            self.text.append(
                FormattedTextField(
                    layer=self.text_layer_mana,
                    contents=self.layout.mana_cost,
                    font_mana=self.font_mana_lcars,
                    symbol_map=self.symbol_map_lcars,
                )
            )
        if self.text_layer_name:
            self.text.append(
                ScaledTextField(
                    layer=self.text_layer_name,
                    contents=self.layout.name.upper(),
                    reference=self.name_reference,
                )
            )
        if self.text_layer_type:
            self.text.append(
                ScaledTextField(
                    layer=self.text_layer_type,
                    contents=self.layout.type_line.upper(),
                    reference=self.type_reference,
                )
            )

    def rules_text_and_pt_layers(self) -> None:
        """Rules text is written in all caps using the LCARS font, no flavor text."""
        if self.text_layer_rules:
            self.text.append(
                MinSizeTextArea(
                    layer=self.text_layer_rules,
                    contents=self.layout.oracle_text.upper(),
                    reference=self.textbox_reference,
                    pt_reference=self.pt_reference,
                    centered=self.is_centered,
                    font_italic=self.font_lcars,
                    font_bold=self.font_lcars,
                    min_size=self.rules_text_min_size,
                )
            )
        if self.text_layer_pt and self.is_creature:
            self.text.append(
                TextField(
                    layer=self.text_layer_pt,
                    contents=f"{self.layout.power}/{self.layout.toughness}",
                )
            )


"""
* Land Templates
"""


class LcarsLandTemplate(LcarsTemplate):
    """
    * Created by KarbonatErol.
    * LCARS frame for dual lands: two color background, name and typeline only.
    """

    template_suffix = "LCARS Land"

    @cached_property
    def background(self) -> str:
        """str: Two color background named after the land's color pair, e.g. WU or GW."""
        return self.identity
