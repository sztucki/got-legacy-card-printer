from PIL import Image


def remove_footer_band(trim_image: Image.Image, height_fraction: float) -> Image.Image:
    """Flat-fill the bottom band of the image (height_fraction of the total
    height) with its own dominant background color - removes blurry footer
    text (illustrator credit, copyright, card number) that no upscaler can
    make crisp, since the source photo never captured enough real detail in
    that tiny font to begin with.

    The dominant color is the band's most common pixel color: since the band
    is mostly flat background with thin text strokes as a small minority of
    pixels, the mode reliably approximates the true background color without
    any manual color picking or AI call.
    """
    trim_rgb = trim_image.convert("RGB")
    width, height = trim_rgb.size
    band_top = height - round(height * height_fraction)

    band = trim_rgb.crop((0, band_top, width, height))
    dominant_color = max(band.getcolors(maxcolors=band.width * band.height), key=lambda c: c[0])[1]

    cleaned = trim_rgb.copy()
    cleaned.paste(Image.new("RGB", (width, height - band_top), dominant_color), (0, band_top))
    return cleaned
