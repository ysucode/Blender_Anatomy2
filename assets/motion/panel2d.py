"""Worked example (replace the maths, keep the rules). Flat 2D content for the glass panel: derivative and
integral of x^2, transparent, at the film's fps.
Identity (content-studio/style-sheet.md): ink #252422, secondary #403D39, grid #CCC5B9, one accent #EB5E28,
IBM Plex Sans Arabic for every glyph. Beat times from ../edit/beats.json (WhisperX word times)."""
import json
from pathlib import Path
from manim import *

config.pixel_width, config.pixel_height = 1200, 1320
config.frame_width, config.frame_height = 10, 11
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "blender"))
from timeline import FPS
config.frame_rate = FPS      # 24: the film's one clock
config.background_opacity = 0.0

B = json.loads((Path(__file__).parent.parent / "edit" / "beats.json").read_text(encoding="utf-8"))
INK, INK2, LINE, ACC = "#252422", "#403D39", "#CCC5B9", "#EB5E28"
FONT = "IBM Plex Sans Arabic"


def T(s, size=60, color=INK, weight=BOLD):
    t = Text(s, font=FONT, weight=weight, font_size=size, color=color)
    assert len(t.submobjects), f"empty glyphs for {s!r}"      # Pango drops some Arabic words silently
    return t


class Panel2D(Scene):
    def construct(self):
        ax = Axes(x_range=[-2.3, 2.3, 1], y_range=[0, 4.6, 1], x_length=8.4, y_length=6.2,
                  axis_config={"color": INK2, "stroke_width": 3, "include_tip": True, "tip_length": .2},
                  ).move_to([0, -.75, 0])
        grid = NumberPlane(x_range=[-2.3, 2.3, .5], y_range=[0, 4.6, .5], x_length=8.4, y_length=6.2,
                           background_line_style={"stroke_color": LINE, "stroke_width": 1.5, "stroke_opacity": .55},
                           axis_config={"stroke_opacity": 0}).move_to(ax)
        f = lambda x: x * x
        curve = ax.plot(f, x_range=[-2.1, 2.1], color=INK, stroke_width=7)

        eq_f = T("f(x) = x²", 76).move_to([0, 4.5, 0])
        eq_d = T("f'(x) = 2x", 76).move_to([0, 4.5, 0])
        eq_i = VGroup(T("∫₀² x² dx =", 76), T("8⁄3", 76, ACC)).arrange(RIGHT, buff=.25).move_to([0, 4.5, 0])

        t0, t1, ta = B["d_start"], B["i_start"], B["a_start"]
        self.add(grid, ax, curve, eq_f)            # identity: the first frame reads fully, no empty panel
        self.wait(t0 - .05)

        # derivative: orange tangent rides the curve, slope readout under the graph
        x = ValueTracker(-1.6)
        dot = always_redraw(lambda: Dot(ax.c2p(x.get_value(), f(x.get_value())), radius=.12, color=ACC))
        def tangent():
            a = x.get_value(); s = 2 * a; h = 1.0 / (1 + s * s) ** .5
            return Line(ax.c2p(a - h, f(a) - s * h), ax.c2p(a + h, f(a) + s * h), color=ACC, stroke_width=7)
        tan = always_redraw(tangent)
        lab = T("ميل المماس", 52, INK2).move_to([1.0, -4.6, 0])
        mk = lambda: T(f"{2 * x.get_value():+.1f}".replace("-", "−"), 58, ACC).next_to(lab, LEFT, buff=.35)
        num = mk(); num.add_updater(lambda m: m.become(mk()))
        self.play(FadeOut(eq_f, shift=UP * .2), FadeIn(eq_d, shift=UP * .2), FadeIn(dot), Create(tan), FadeIn(lab), FadeIn(num), run_time=.45)
        self.play(x.animate.set_value(2.0), run_time=t1 - t0 - .45, rate_func=smooth)

        # integral: rectangles step in, then melt into the exact area
        n = 8; w = 2 / n
        bars = VGroup(*[Rectangle(width=ax.x_length / 4.6 * w, height=ax.y_length / 4.6 * f(i * w + w / 2),
                                  stroke_color=ACC, stroke_width=3, fill_color=ACC, fill_opacity=.45)
                        .move_to(ax.c2p(i * w + w / 2, 0), aligned_edge=DOWN) for i in range(n)])
        area = ax.get_area(curve, x_range=[0, 2]).set_fill(ACC, .45).set_stroke(ACC, 0)
        num.clear_updaters()
        self.play(FadeOut(eq_d, shift=UP * .2), FadeIn(eq_i, shift=UP * .2), FadeOut(lab), FadeOut(num), FadeOut(tan), FadeOut(dot),
                  LaggedStart(*[GrowFromEdge(b, DOWN) for b in bars], lag_ratio=.12), run_time=1.6)
        self.wait(max(0, ta - self.renderer.time))
        self.play(FadeOut(bars), FadeIn(area), run_time=.6)    # crossfade: morphing rects scatters
        self.play(eq_i[1].animate.scale(1.06), run_time=.25)          # identity: 1.06 for 0.25 s, then back
        self.play(eq_i[1].animate.scale(1 / 1.06), run_time=.25)
        self.wait(max(0, 10 - self.renderer.time))
