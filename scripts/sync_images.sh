#!/bin/bash
# Sync images from WordPress uploads into assets/images/
UP="${1:-$HOME/Downloads/adrianaspmu.com/wp-content/uploads}"
DEST="$(cd "$(dirname "$0")/.." && pwd)/assets/images"

mkdir -p "$DEST"/{services,portfolio,academy,favicon}

cp "$UP/2025/05/hero.webp" "$DEST/hero.webp"
cp "$UP/2025/05/cropped-Favicon-Adrianas-"*.png "$DEST/favicon/" 2>/dev/null || true
mv "$DEST/favicon/cropped-Favicon-Adrianas-192x192.png" "$DEST/favicon/favicon-192.png" 2>/dev/null || true
mv "$DEST/favicon/cropped-Favicon-Adrianas-32x32.png" "$DEST/favicon/favicon-32.png" 2>/dev/null || true
mv "$DEST/favicon/cropped-Favicon-Adrianas-180x180.png" "$DEST/favicon/apple-touch-icon.png" 2>/dev/null || true

declare -A MAP=(
  [nano-brows]="Nanobrows-1.jpg"
  [microblading]="Microblading-1.jpg"
  [powder-brows]="Powder-Brows-9.jpg"
  [lip-blush]="Lip-Blush-1.jpg"
  [dark-lip-neutralization]="Dark-Lip-Neutralization-1.jpg"
  [nano-combo]="Nano-Combo-8.jpg"
  [combination-brows]="Nano-Combo-8.jpg"
  [top-eyeliner]="Top-Eyeliner-Classic-3.jpg"
  [smokey-eyeliner]="Eyeliner-Smokey-Effect-1.jpg"
  [bottom-eyeliner]="Bottom-Eyeliner-4.jpg"
  [eyeliner-combo]="Eyeliner-Combo-1.jpg"
  [eyebrows-lips-combo]="Brows-and-Lips-Combo-1.jpg"
  [yearly-touch-up]="Portfolio-Adriana-Eyebrows-023.jpg"
)

for slug in "${!MAP[@]}"; do
  src="$UP/2025/10/${MAP[$slug]}"
  [[ -f "$src" ]] && cp "$src" "$DEST/services/$slug.jpg"
done

cp "$UP/2025/11/100-hours.jpg" "$DEST/academy/pmu-100h.jpg" 2>/dev/null || true
cp "$UP/2025/11/Apprenticeship-Program.jpg" "$DEST/academy/apprenticeship.jpg" 2>/dev/null || true
cp "$UP/2025/07/Academy-Capa.webp" "$DEST/academy/hero.webp" 2>/dev/null || true
cp "$UP/2025/07/Photo-Adriana-Academy.jpg" "$DEST/academy/adriana.jpg" 2>/dev/null || true
cp "$UP/2025/07/In-Person-Class.jpg" "$DEST/academy/in-person-class.jpg" 2>/dev/null || true
cp "$UP/2025/08/Academy-Classrom.jpg" "$DEST/academy/classroom.jpg" 2>/dev/null || true
cp "$UP/2025/06/SELO-AAM.png" "$DEST/academy/aam-seal.png" 2>/dev/null || true
mkdir -p "$DEST/academy"/{gallery,slides,students}
for f in "$UP/2025/07"/CRRSS-Academy-*.jpg; do
  [[ -f "$f" ]] || continue
  case "$f" in *-*x*) continue ;; esac
  n=$(basename "$f" .jpg | sed 's/CRRSS-Academy-/academy-/')
  cp "$f" "$DEST/academy/gallery/${n}.jpg"
done
for f in "$UP/2025/07/"*SLIDE.jpg; do
  [[ -f "$f" ]] || continue
  case "$f" in *-*x*) continue ;; esac
  num=$(basename "$f" .jpg | sed 's/SLIDE//')
  cp "$f" "$DEST/academy/slides/slide-${num}.jpg"
done
python3 -c "
import shutil
from pathlib import Path
src = Path('$UP') / 'elementor/thumbs'
dest = Path('$DEST/academy/students')
dest.mkdir(parents=True, exist_ok=True)
for i, f in enumerate(sorted(src.glob('Avatar-Aluna-*.jpg'))[:6], 1):
    shutil.copy(f, dest / f'student-{i:02d}.jpg')
" 2>/dev/null || true
cp "$UP/2025/10/Portfolio-Adriana-Eyebrows-023.jpg" "$DEST/about-adriana.jpg" 2>/dev/null || true

find "$UP/2025/10" -maxdepth 1 -name 'Portfolio-*.jpg' ! -name '*-*x*' -exec cp {} "$DEST/portfolio/" \;

SITE_ROOT="$(dirname "$(dirname "$UP")")"
if [[ -f "$SITE_ROOT/index.html" ]]; then
  python3 "$(dirname "$0")/extract_logo.py" "$SITE_ROOT/index.html" "$DEST/logo.svg"
fi

echo "Images synced to $DEST"
