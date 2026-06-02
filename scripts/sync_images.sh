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
cp "$UP/2025/10/Portfolio-Adriana-Eyebrows-023.jpg" "$DEST/about-adriana.jpg" 2>/dev/null || true

find "$UP/2025/10" -maxdepth 1 -name 'Portfolio-*.jpg' ! -name '*-*x*' -exec cp {} "$DEST/portfolio/" \;

echo "Images synced to $DEST"
