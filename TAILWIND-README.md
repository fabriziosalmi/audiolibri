# Integrazione di Tailwind CSS in Audiolibri.org

## Panoramica

Questo progetto utilizza un approccio ibrido per l'integrazione di Tailwind CSS, mantenendo la compatibilità con il sistema di stile esistente. Invece di una completa migrazione a Tailwind, abbiamo creato un layer di classi Tailwind-like che possono essere utilizzate insieme alle classi CSS esistenti.

## Come utilizzare le classi Tailwind

Tutte le classi Tailwind personalizzate hanno il prefisso `tw-` per evitare conflitti con le classi esistenti. Puoi utilizzare queste classi insieme alle classi esistenti nei tuoi elementi HTML.

Esempio:

```html
<div class="single-card tw-shadow-lg tw-rounded-2xl">
  <h2 class="tw-text-xl tw-font-bold">Titolo</h2>
  <p class="tw-text-base">Contenuto</p>
</div>
```

## Classi disponibili

Abbiamo creato un sottoinsieme di classi Tailwind più comunemente utilizzate:

### Layout
- `tw-container`: Container principale con larghezza massima e padding
- `tw-flex`, `tw-flex-col`: Display flex e direzione colonna
- `tw-items-center`, `tw-justify-center`, `tw-justify-between`: Allineamento flex
- `tw-gap-1`, `tw-gap-2`, `tw-gap-4`, `tw-gap-6`: Spaziatura tra elementi flex
- `tw-grid`, `tw-grid-cols-1/2/3/4`: Layout a griglia

### Componenti
- `tw-card`: Card con bordi arrotondati e ombra
- `tw-header`: Header con stile simile all'header esistente
- `tw-button`: Pulsante con stile simile ai pulsanti esistenti
- `tw-input`: Input con stile simile agli input esistenti

### Tipografia
- `tw-text-center`: Allineamento testo al centro
- `tw-text-sm`, `tw-text-base`, `tw-text-lg`, `tw-text-xl`, `tw-text-2xl`: Dimensioni testo
- `tw-font-medium`, `tw-font-semibold`, `tw-font-bold`: Spessore font

### Spaziatura
- `tw-m-0/1/2/4`: Margin
- `tw-mb-1/2/4/6/8`, `tw-mt-1/2/4/6`: Margin bottom/top
- `tw-p-1/2/4/6/8`: Padding

### Bordi e ombre
- `tw-rounded-md/lg/xl/2xl/full`: Border radius
- `tw-shadow-sm/md/lg`: Box shadow

### Responsive
- `tw-md-grid-cols-2`, `tw-md-flex-col`: Classi per schermi medi (max-width: 800px)
- `tw-sm-grid-cols-1`, `tw-sm-flex-col`, `tw-sm-w-full`: Classi per schermi piccoli (max-width: 600px)

## Tema e colori

Le classi Tailwind utilizzano le variabili CSS esistenti per mantenere la coerenza con il tema dell'applicazione, incluso il supporto per il tema chiaro/scuro.

## Estensione

Per aggiungere nuove classi Tailwind, modifica il file `tailwind-styles.css` aggiungendo le nuove classi con il prefisso `tw-`.

## Migrazione completa (futuro)

In futuro, se desideri migrare completamente a Tailwind CSS, puoi seguire questi passaggi:

1. Configura correttamente l'ambiente di build con PostCSS
2. Utilizza il file `tailwind.config.js` già creato
3. Utilizza il file `tailwind-input.css` come punto di partenza
4. Migra gradualmente le classi CSS esistenti alle classi Tailwind native

Questo approccio ibrido consente di iniziare a utilizzare Tailwind senza interrompere la funzionalità esistente, fornendo un percorso di migrazione graduale.