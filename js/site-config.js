/** Adriana's PMU — site configuration (semantic architecture PDF) */
const SITE = {
  name: "Adriana's Permanent Makeup",
  legalName: "Adriana Beauty Services, Inc.",
  url: "https://adrianaspmu.com",
  logo: "/assets/images/logo.svg",
  lang: "en-US",
  phoneWilmington: "(781) 853-8063",
  phoneSalem: "(978) 223-7496",
  email: "info@adrianaspmu.com",
  fresha: "https://www.fresha.com/a/adrianas-permanent-makeup-wilmington-ma-wilmington-211-lowell-street-jalpqett",
  freshaBookNow:
    "https://www.fresha.com/book-now/adrianas-permanent-makeup-zeaseit5/all-offer?share=true&pId=727586",
  freshaServiceUrls: {
    "yearly-touch-up":
      "https://www.fresha.com/book-now/adrianas-permanent-makeup-zeaseit5/services?oiid=sv%3A18160395&share=true&pId=727586",
    "flash-sale":
      "https://www.fresha.com/book-now/adrianas-permanent-makeup-zeaseit5/services?oiid=sv%3A19707327&share=true&pId=727586",
  },
  freshaReviews:
    "https://www.fresha.com/a/adrianas-permanent-makeup-wilmington-ma-wilmington-211-lowell-street-jalpqett#modal-reviews",
  gbp: "https://maps.app.goo.gl/oJRNewzwwWACAera6",
  googleReviews:
    "https://www.google.com/maps/place/Adriana's+Permanent+Makeup/@42.5388138,-71.1485431,17z/data=!4m8!3m7!1s0x89e30b1334f8bef9:0xe7fa0014b608ddc6!8m2!3d42.5388138!4d-71.1485431!9m1!1b1!16s%2Fg%2F11tm_909cb",
  trustindexLoader: "https://cdn.trustindex.io/loader.js?a8b99d8541280410986623737af",
  facebook: "https://www.facebook.com/adrianaspmu",
  instagram: "https://www.instagram.com/adrianas_pmu/",
  locations: {
    wilmington: {
      name: "Wilmington, MA",
      street: "211 Lowell Street, Suite F",
      city: "Wilmington",
      region: "MA",
      zip: "01887",
      phone: "(781) 853-8063",
      hours: "Mon–Sat 10:00 AM – 6:00 PM; Sun Closed",
      geo: { lat: 42.539192, lng: -71.148805 },
      license: "Town of Wilmington Business Certificate #26-26",
      areaServed:
        "Wilmington, Reading, North Reading, Burlington, Tewksbury, Andover, North Andover, Woburn, Lowell, and the Greater Boston North Shore",
    },
    salem: {
      name: "Salem, NH",
      street: "117A Main Street",
      city: "Salem",
      region: "NH",
      zip: "03079",
      phone: "(978) 223-7496",
      hours: "Mon–Sat 10:00 AM – 6:00 PM; Sun Closed",
      geo: { lat: 42.782612, lng: -71.228213 },
      license: "Compliant with Salem NH Body Art Regulations Chapter 433",
      areaServed:
        "Salem NH, Derry, Windham, Methuen MA, Lawrence MA, Hampstead, Plaistow, and the I-93 corridor",
      tag: "New Location",
    },
    peabody: {
      name: "Peabody, MA",
      street: "39 Cross Street, Suite 206",
      city: "Peabody",
      region: "MA",
      zip: "01960",
      phone: "(781) 853-8063",
      tag: "Academy",
    },
  },
  stats: {
    years: "20+",
    procedures: "5,000+",
    reviews: "1,000+",
    googleRating: "4.9",
    googleCount: "174",
  },
};

const NAV = [
  { label: "Home", href: "/" },
  { label: "Services", href: "/services/" },
  { label: "Portfolio", href: "/portfolio.html" },
  {
    label: "Training",
    href: "/training/",
    children: [
      { label: "100-Hour Fundamental", href: "/academy/pmu-100h-fundamental.html" },
      { label: "Apprenticeship", href: "/academy/pmu-apprenticeship.html" },
      { label: "VIP Masterclass", href: "/academy/vip-masterclass.html" },
    ],
  },
  { label: "About", href: "/about.html" },
  { label: "Contact", href: "/contact.html" },
  { label: "FAQ", href: "/faq.html" },
];

const HERO_SERVICES = [
  {
    slug: "nano-brows",
    category: "eyebrows",
    name: "Nano Brows",
    price: 650,
    desc: "Hyperrealistic hair-like strokes using an ultra-fine needle. Lasts 1–3 years.",
    hero: true,
  },
  {
    slug: "microblading",
    category: "eyebrows",
    name: "Microblading",
    price: 550,
    desc: "Natural hair-stroke eyebrow tattoo. Our most popular brow service.",
    hero: true,
  },
  {
    slug: "powder-brows",
    category: "eyebrows",
    name: "Powder Brows",
    price: 550,
    desc: "Soft ombre shading for defined, makeup-ready brows. Includes microshading.",
    hero: true,
  },
  {
    slug: "lip-blush",
    category: "lips",
    name: "Lip Blush",
    price: 550,
    desc: "Soft natural lip color that lasts 2–3 years. Custom color matching.",
    hero: true,
  },
];

const ALL_SERVICES = [
  ...HERO_SERVICES,
  { slug: "combination-brows", category: "eyebrows", name: "Combination Brows", price: null, desc: "Hair strokes plus soft shading in one session." },
  { slug: "nano-combo", category: "eyebrows", name: "Nano Combo Brows", price: 600, desc: "Nano strokes with soft shading combined." },
  { slug: "dark-lip-neutralization", category: "lips", name: "Dark Lip Neutralization", price: 550, desc: "Color correction for hyperpigmented or dark lips." },
  { slug: "top-eyeliner", category: "eyeliner", name: "Top Eyeliner", price: 350, desc: "Classic definition and cat eye styles." },
  { slug: "smokey-eyeliner", category: "eyeliner", name: "Smokey Eyeliner", price: 400, desc: "Soft diffused shadow effect on the upper lid." },
  { slug: "bottom-eyeliner", category: "eyeliner", name: "Bottom Eyeliner", price: 250, desc: "Subtle lower lash line definition." },
  { slug: "eyeliner-combo", category: "eyeliner", name: "Eyeliner Combo", price: 500, desc: "Top and bottom permanent eyeliner together." },
  { slug: "eyebrows-lips-combo", category: "combos", name: "Brows + Lips Combo", price: 850, desc: "Eyebrow PMU and lip blush in one session." },
  { slug: "yearly-touch-up", category: "touch-ups", name: "Yearly Touch-Up", price: 300, desc: "Color refresh for existing brow clients.", priceNote: "from" },
];
