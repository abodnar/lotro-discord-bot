import asyncio
import base64
import io
import logging
import os

logger = logging.getLogger(__name__)

# RGB colours for the three LotRO trait trees
_R = (220,  50,  50, 255)
_B = ( 50, 100, 220, 255)
_Y = (220, 180,   0, 255)

# Each entry maps an emoji name to the ordered list of colour sectors to draw.
# 1 colour → solid circle.  2 → left/right halves.  3 → equal thirds.
SPEC_ICONS = {
    'spec_red':    [_R],
    'spec_blue':   [_B],
    'spec_yellow': [_Y],
    'spec_rb':     [_R, _B],
    'spec_by':     [_B, _Y],
    'spec_ry':     [_R, _Y],
    'spec_all':    [_R, _B, _Y],
}


def find_emoji_file(name: str, directory: str) -> str | None:
    """Return the image path for *name* inside *directory*, tolerating hyphens."""
    exact = os.path.join(directory, f'{name}.png')
    if os.path.exists(exact):
        return exact
    normalized = name.lower()
    for fname in os.listdir(directory):
        if not fname.lower().endswith(('.png', '.jpg')):
            continue
        stem = os.path.splitext(fname)[0].lower().replace('-', '').replace('_', '')
        if stem == normalized:
            return os.path.join(directory, fname)
    return None


def _generate_spec_icon(colours: list) -> bytes:
    """Generate a 128×128 circular spec icon with 1, 2, or 3 colour sectors."""
    from PIL import Image, ImageDraw
    size = 128
    pad = 4
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    box = [pad, pad, size - pad, size - pad]

    n = len(colours)
    if n == 1:
        draw.ellipse(box, fill=colours[0])
    elif n == 2:
        # Left half then right half (split at 12 and 6 o'clock)
        draw.pieslice(box, start=90,  end=270, fill=colours[0])   # left
        draw.pieslice(box, start=270, end=450, fill=colours[1])   # right (450 = 90)
    else:
        # Three 120° sectors; boundary points at 12, 4, and 8 o'clock
        # Pillow: 0°=3 o'clock, clockwise.  12 o'clock = 270°.
        draw.pieslice(box, start=270, end=390, fill=colours[0])   # right sector
        draw.pieslice(box, start=30,  end=150, fill=colours[1])   # bottom sector
        draw.pieslice(box, start=150, end=270, fill=colours[2])   # left sector

    # White border ring
    draw.ellipse(box, outline=(255, 255, 255, 220), width=4)

    buf = io.BytesIO()
    img.save(buf, 'PNG')
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
    """Upload one application emoji; returns its ID."""
    from discord.http import Route
    data = await bot.http.request(
        Route('POST', '/applications/{application_id}/emojis',
              application_id=bot.application_id),
        json={'name': name, 'image': _data_uri(image_bytes)}
    )
    return data['id']


async def ensure_emojis(bot, role_names: list, creep_names: list, emoji_base_dir: str) -> dict:
    """
    Ensures all class icons and the 7 spec icons exist as application emojis.
    - Hero classes are loaded from  emoji_base_dir/freep/
    - Creep classes are loaded from emoji_base_dir/creep/
    - Spec icons are generated with Pillow.
    Returns {emoji_name: '<:name:id>'} for every known emoji.
    """
    try:
        from PIL import Image  # noqa: F401
        pil_available = True
    except ImportError:
        pil_available = False
        logger.warning('Pillow not installed; spec icons will be skipped.')

    existing = await _list_app_emojis(bot)
    to_create: dict[str, bytes] = {}

    freep_dir = os.path.join(emoji_base_dir, 'freep')
    creep_dir = os.path.join(emoji_base_dir, 'creep')

    for name in role_names:
        if name not in existing:
            path = find_emoji_file(name, freep_dir)
            if path:
                with open(path, 'rb') as f:
                    to_create[name] = f.read()
            else:
                logger.warning(f'No image found for {name} in {freep_dir}')

    for name in (creep_names or []):
        if name not in existing:
            path = find_emoji_file(name, creep_dir)
            if path:
                with open(path, 'rb') as f:
                    to_create[name] = f.read()
            else:
                logger.warning(f'No image found for {name} in {creep_dir}')

    if pil_available:
        for emoji_name, colours in SPEC_ICONS.items():
            if emoji_name not in existing:
                to_create[emoji_name] = _generate_spec_icon(colours)

    for name, image_bytes in to_create.items():
        try:
            emoji_id = await _create_app_emoji(bot, name, image_bytes)
            existing[name] = emoji_id
            logger.info(f'Created application emoji: {name}')
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f'Failed to create emoji {name}: {e}')

    return {name: f'<:{name}:{eid}>' for name, eid in existing.items()}
