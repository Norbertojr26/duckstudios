# Satoshi

Tipografia da marca. **Os arquivos `.woff2` não estão versionados** — e isso é de propósito.

## Por que não estão no repositório

A licença do Fontshare (Indian Type Foundry) permite uso pessoal e comercial em qualquer mídia,
inclusive web, mas a cláusula 02 proíbe distribuir os arquivos:

> The Fonts may not […] be distributed, duplicated, loaned, resold or licensed in any way […]
> This includes […] uploading them in a public server or making the fonts available on
> peer-to-peer networks.

Commitar os `.woff2` num repositório público seria exatamente isso. Usar a fonte no site e no app
é permitido; hospedar os arquivos para qualquer um baixar, não.

## Como colocar os arquivos

Baixe **Satoshi** em [fontshare.com/fonts/satoshi](https://www.fontshare.com/fonts/satoshi) e copie
para cá:

```
design/fonts/
├── Satoshi-Variable.woff2   ← a que importa (300–900 num arquivo só)
├── Satoshi-Regular.woff2
├── Satoshi-Medium.woff2
├── Satoshi-Bold.woff2
└── Satoshi-Black.woff2
```

Alternativa que dispensa hospedar: o Fontshare serve a fonte por CDN. Em campo, porém, o app roda
**offline** — então o arquivo local é o caminho certo aqui, e o CDN só serve para o site.

## Pesos em uso

| Uso | Peso |
|---|---|
| Título de seção | 500 (Medium) — o catálogo usa título largo e leve, não bold |
| Corpo | 400 |
| Logotipo / destaque | 700 (Bold) |
| Número grande (código do item na etiqueta) | 900 (Black) |
