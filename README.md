# Adriana's PMU — Site estático (HTML5 + CSS + JS)

Reconstrução do site **adrianaspmu.com** conforme o documento *adrianas-pmu-semantic-architecture* (arquitetura semântica 2026).

## Estrutura

- **58+ páginas HTML** com hierarquia corrigida (H1 com cidade/estado, H2 como perguntas)
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
