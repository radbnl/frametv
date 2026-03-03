# Samsung Frame TV - Rijksmuseum Art Display

Automatisch kunstwerken van het Rijksmuseum ophalen en weergeven op je Samsung Frame TV.

## Wat doet dit?

Dit script haalt kunstwerken op van het [Rijksmuseum](https://www.rijksmuseum.nl/) via hun nieuwe Data Services API en uploadt ze automatisch naar je Samsung Frame TV in Art Mode.

**Features:**
- Zoek kunstwerken op keyword, kunstenaar of type
- Haalt automatisch kunstwerken op van het Rijksmuseum (geen API key nodig!)
- Uploadt afbeeldingen naar je Samsung Frame TV
- Houdt bij welke afbeeldingen al geupload zijn
- Debug script om connectie te testen

## Vereisten

- Python 3.10+
- Samsung Frame TV (of andere Samsung TV met Art Mode)
- TV en computer op hetzelfde netwerk

## Installatie

```bash
# Clone de repository
git clone https://github.com/radbnl/frametv.git
cd frametv

# Maak een virtual environment
python3 -m venv venv
source venv/bin/activate

# Installeer dependencies
pip install requests samsungtvws
```

## Configuratie

Pas het IP-adres van je TV aan in `art.py` (regel 179):

```python
tv = SamsungTVWS('192.168.230.68')  # Vervang met jouw TV IP
```

Je kunt het IP-adres van je TV vinden via:
- TV Instellingen > Netwerk > Netwerkstatus
- Of via je router's apparatenlijst

## Gebruik

### Automatisch kunstwerk ophalen en uploaden

```bash
source venv/bin/activate
python3 art.py
```

Dit zal:
1. Een willekeurig kunstwerk ophalen van het Rijksmuseum
2. De afbeelding downloaden naar `./images/`
3. Uploaden naar je TV
4. Het kunstwerk weergeven in Art Mode

### Alleen testen / debuggen

```bash
source venv/bin/activate
python3 debug_tv.py
```

Dit toont:
- TV connectie status
- Art Mode ondersteuning
- Huidige artwork
- Lijst van geuploadde afbeeldingen
- Optie om een afbeelding te uploaden

### Specifieke afbeelding uploaden

```bash
source venv/bin/activate
python3 debug_tv.py ./images/mijn_afbeelding.jpg
```

### Zoeken op keyword

Gebruik `search.py` om specifieke kunstwerken te zoeken en downloaden:

```bash
source venv/bin/activate

# Zoek op titel/onderwerp
python3 search.py landschap
python3 search.py "nachtwacht"
python3 search.py bloemen --amount 10

# Zoek op kunstenaar
python3 search.py --artist "Rembrandt"
python3 search.py --artist "Vincent van Gogh" --amount 5

# Zoek op type
python3 search.py --type schilderij zee
python3 search.py --type tekening amsterdam

# Alleen tonen zonder downloaden
python3 search.py landschap --list-only
```

**Beschikbare types:** schilderij, tekening, prent, foto, beeld, meubel

## Instellingen

In `art.py` kun je de volgende instellingen aanpassen:

```python
USE_RIJKSMUSEUM = True          # True = ophalen van Rijksmuseum, False = alleen lokale images
RIJKSMUSEUM_FETCH_COUNT = 50    # Aantal kunstwerken om door te zoeken
folder_path = './images/'       # Map met lokale afbeeldingen
```

## Bestandsstructuur

```
frametv/
├── art.py              # Hoofdscript: random artwork ophalen + TV upload
├── search.py           # Zoek kunstwerken op keyword/kunstenaar/type
├── debug_tv.py         # Debug/test script voor TV connectie
├── images/             # Map met gedownloade afbeeldingen
└── venv/               # Python virtual environment (niet in git)
```

## Rijksmuseum API

Dit project gebruikt de nieuwe [Rijksmuseum Data Services](https://data.rijksmuseum.nl/) API:

- **OAI-PMH API** voor metadata harvesting
- **IIIF Image API** voor hoge resolutie afbeeldingen
- Geen API key vereist
- Afbeeldingen zijn vrij te gebruiken (publiek domein)

Documentatie: https://data.rijksmuseum.nl/docs/

## Problemen oplossen

### TV niet bereikbaar
- Controleer of de TV aan staat
- Controleer of TV en computer op hetzelfde netwerk zitten
- Probeer de TV te pingen: `ping 192.168.230.68`

### Art Mode niet ondersteund
- Alleen Samsung Frame TV's en bepaalde QLED modellen ondersteunen Art Mode
- Controleer of je TV Art Mode heeft in de instellingen

### Upload mislukt
- Zorg dat de afbeelding JPEG of PNG is
- Maximale resolutie: 3840x2160 (4K)
- Run `debug_tv.py` voor meer informatie

## Credits

Dit project is gebaseerd op werk van:

- **[marglaur](https://github.com/mmargauxx/frametv)** - Originele repository en eerste Rijksmuseum integratie
- **[Ow](https://github.com/ow/samsung-frame-art)** - Samsung Frame Art Mode++ basis
- **[samsungtvws](https://github.com/xchwarze/samsung-tv-ws-api)** - Samsung TV WebSocket API library

## Licentie

MIT License - Vrij te gebruiken en aan te passen.

De kunstwerken van het Rijksmuseum zijn publiek domein en vrij te gebruiken.