import asyncio
import base64
import io
import logging
import os

logger = logging.getLogger(__name__)

SPEC_COLORS = {
    'red':    (220,  50,  50),
    'blue':   ( 50, 100, 220),
    'yellow': (220, 180,   0),
}


def find_emoji_file(class_name: str, emoji_dir: str) -> str | None:
    """Find the image file for a class, tolerating hyphenated filenames."""
    path = os.path.join(emoji_dir, f'{class_name}.png')
    if os.path.exists(path):
        return path
    normalized = class_name.lower()
    for fname in os.listdir(emoji_dir):
        if not fname.lower().endswith(('.png', '.jpg')):
            continue
        stem = os.path.splitext(fname)[0].lower().replace('-', '').replace('_', '')
        if stem == normalized:
            return os.path.join(emoji_dir, fname)
    return None


def _generate_spec_variant(base_path: str, color_rgb: tuple) -> bytes:
    """Overlay a small coloured badge on the bottom-right of the class icon."""
    from PIL import Image, ImageDraw
    img = Image.open(base_path).convert('RGBA').resize((128, 128))
    overlay = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    r, margin = 22, 3
    cx = cy = 128 - r - margin
    draw.ellipse([cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2], fill=(255, 255, 255, 230))
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*color_rgb, 255))
    result = Image.alpha_composite(img, overlay)
    buf = io.BytesIO()
    result.save(buf, 'PNG')
    return buf.getvalue()


def _data_uri(image_bytes: bytes) -> str:
    return 'data:image/png;base64,' + base64.b64encode(image_bytes).decode()


async def _list_app_emojis(bot) -> dict:
    """Returns {name: id} for all existing application emojis."""
    from discord.http import Route
    data = await bot.http.request(
        Route('GET', '/applications/{application_id}/emojis',
              application_id=bot.application_id)
    )
    items = data.get('items', []) if isinstance(data, dict) else data
    return {e['name']: e['id'] for e in items}


async def _create_app_emoji(bot, name: str, image_bytes: bytes) -> str:
    """Creates an application emoji; returns its ID."""
    from discord.http import Route
    data = await bot.http.request(
        Route('POST', '/applications/{application_id}/emojis',
              application_id=bot.application_id),
        json={'name': name, 'image': _data_uri(image_bytes)}
    )
    return data['id']


async def ensure_emojis(bot, class_names: list, emoji_dir: str) -> dict:
    """
    Ensures base class emojis and red/blue/yellow spec variants all exist
    as application emojis. Returns {emoji_name: '<:name:id>'} for every emoji.
    """
    try:
        from PIL import Image  # noqa: F401 — just checking availability
        pil_available = True
    except ImportError:
        pil_available = False
        logger.warning('Pillow not installed; spec variant emojis will be skipped.')

    existing = await _list_app_emojis(bot)
    to_create = {}

    for class_name in class_names:
        base_path = find_emoji_file(class_name, emoji_dir)
        if not base_path:
            logger.warning(f'No image found for {class_name} in {emoji_dir}')
            continue

        if class_name not in existing:
            with open(base_path, 'rb') as f:
                to_create[class_name] = f.read()

        if pil_available:
            for spec, color in SPEC_COLORS.items():
                variant = f'{class_name}_{spec}'
                if variant not in existing:
                    to_create[variant] = _generate_spec_variant(base_path, color)

    for name, image_bytes in to_create.items():
        try:
            emoji_id = await _create_app_emoji(bot, name, image_bytes)
            existing[name] = emoji_id
            logger.info(f'Created application emoji: {name}')
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f'Failed to create emoji {name}: {e}')

    return {name: f'<:{name}:{eid}>' for name, eid in existing.items()}
