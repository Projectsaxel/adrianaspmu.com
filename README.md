# Adriana's PMU — Site estático (HTML5 + CSS + JS)

Reconstrução do site **adrianaspmu.com** conforme o documento *adrianas-pmu-semantic-architecture* (arquitetura semântica 2026).

## Estrutura

- **58+ páginas HTML** com hierarquia corrigida (H1 com cidade/estado, H2 como perguntas)
- **URLs sem extensão `.html`**: toda página é `pasta/index.html` e é servida como `/pasta/`
  (ex.: `/about/`, `/services/eyebrows/microblading/wilmington-ma/`). Links internos, sitemap
  e llms.txt seguem esse formato — não reintroduzir `.html` nas URLs.
- **Inglês (en-US)** exclusivo no site
- **Duas localizações**: Wilmington, MA (matriz) e Salem, NH (filial)
- **Schema.org** JSON-LD (Organization, BeautySalon, Service)
- **llms.txt**, **robots.txt**, **sitemap.xml**

## Como visualizar

```bash
cd "/Users/marceloneves/Projetos GIT/adrianaspmu.com"
python3 -m http.server 8080
```

Abra http://localhost:8080

### GA4 nao mede fora de producao (de proposito)

O `gtag.js` (G-ZSD89WRHYZ) e o `/js/analytics.js` so sao carregados quando
`location.hostname === "adrianaspmu.com"` (o `www` redireciona para o apex).
Em `127.0.0.1`, `localhost`, `*.workers.dev`, preview da Hostinger ou qualquer
outro host, **nenhum hit vai para o Google Analytics** e a decoracao de UTM dos
links do Fresha tambem nao roda. Testar local e ver zero requisicoes para
`google-analytics.com` / `googletagmanager.com` e o comportamento esperado,
nao medicao quebrada. Antes disso, o GA4 somava sessoes de 127.0.0.1 (31),
localhost (12), workers.dev e hostingersite.com.

A trava e injetada no build por `scripts/enrich_pages.py` (`add_analytics`,
constante `GA_HOST`); `window.PMU_PAGE` continua definido em todo host. Para
depurar a medicao, use o DebugView do GA4 no site publicado.

## Imagens

Origem: `wp-content/uploads` do WordPress (copiadas para `assets/images/`).

```bash
# Re-sincronizar do WordPress local
bash scripts/sync_images.sh "/Users/marceloneves/Downloads/adrianaspmu.com/wp-content/uploads"
python3 scripts/generate_pages.py
```

## Regenerar páginas de serviço

```bash
python3 scripts/generate_pages.py
```

## Arquivos principais

| Pasta/arquivo | Função |
|---------------|--------|
| `index.html` | Home (hub semântico) |
| `css/styles.css` | Estilos globais |
| `js/site-config.js` | NAP, navegação, serviços |
| `js/main.js` | Header/footer, FAQ, formulário |
| `services/` | Hubs e páginas de serviço + city combos |
| `locations/` | Wilmington MA e Salem NH |

## Pendências (conforme PDF)

- Fotos reais no portfolio e hero
- LinkedIn URL no schema Person
- Confirmar licença NH OPLC e preços VIP Masterclass
- Publicar em produção com HTTPS e domínio adrianaspmu.com
