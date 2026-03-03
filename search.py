#!/usr/bin/env python3
"""
Rijksmuseum Search Script - Zoek en download kunstwerken op keyword.

Gebruik:
    python3 search.py landschap                    # Zoek op titel
    python3 search.py --artist "Rembrandt"         # Zoek op kunstenaar
    python3 search.py --type schilderij bloemen    # Zoek schilderijen met 'bloemen'
    python3 search.py landschap --amount 10        # Download 10 kunstwerken

Voorbeelden:
    python3 search.py "nachtwacht"
    python3 search.py --artist "Vincent van Gogh"
    python3 search.py --type tekening amsterdam
    python3 search.py zee --amount 20
"""

import argparse
import logging
import os
import requests
import xml.etree.ElementTree as ET
import sys
import re

# Configuratie
RIJKSMUSEUM_OAI_URL = "https://data.rijksmuseum.nl/oai"
RIJKSMUSEUM_SEARCH_URL = "https://data.rijksmuseum.nl/search/collection"
DEFAULT_OUTPUT_DIR = "./images"

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


def search_collection(query=None, artist=None, object_type=None, max_results=100):
    """
    Zoek in de Rijksmuseum collectie via de Search API.
    Retourneert een lijst met object IDs.
    """
    params = {
        'imageAvailable': 'true'
    }

    if query:
        params['title'] = query
    if artist:
        params['creator'] = artist
    if object_type:
        # Vertaal Nederlandse termen naar Engels indien nodig
        type_mapping = {
            'schilderij': 'painting',
            'tekening': 'drawing',
            'prent': 'print',
            'foto': 'photograph',
            'beeld': 'sculpture',
            'meubel': 'furniture',
        }
        params['type'] = type_mapping.get(object_type.lower(), object_type)

    logger.info(f"Zoeken in Rijksmuseum collectie...")
    logger.info(f"Parameters: {params}")

    object_ids = []
    page_token = None

    while len(object_ids) < max_results:
        if page_token:
            params['pageToken'] = page_token

        try:
            response = requests.get(RIJKSMUSEUM_SEARCH_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.error(f"Fout bij zoeken: {e}")
            break
        except ValueError as e:
            logger.error(f"Fout bij parsen response: {e}")
            break

        # Haal object IDs uit de response
        items = data.get('orderedItems', [])
        if not items:
            break

        for item in items:
            if len(object_ids) >= max_results:
                break
            obj_id = item.get('id', '')
            if obj_id:
                # Extract het numerieke ID uit de URL
                # https://id.rijksmuseum.nl/200100988 -> 200100988
                match = re.search(r'/(\d+)$', obj_id)
                if match:
                    object_ids.append(match.group(1))

        # Check voor volgende pagina
        next_page = data.get('next', {})
        if isinstance(next_page, dict):
            next_url = next_page.get('id', '')
            if next_url and 'pageToken=' in next_url:
                page_token = next_url.split('pageToken=')[-1]
            else:
                break
        else:
            break

    logger.info(f"Gevonden: {len(object_ids)} objecten")
    return object_ids


def get_artwork_details_oai(object_ids):
    """
    Haal artwork details op via OAI-PMH API voor een lijst van object IDs.
    """
    artworks = []

    namespaces = {
        'oai': 'http://www.openarchives.org/OAI/2.0/',
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'edm': 'http://www.europeana.eu/schemas/edm/',
    }

    # OAI-PMH ondersteunt geen specifieke ID queries, dus we halen alles op
    # en filteren op de IDs die we willen
    logger.info("Ophalen artwork details via OAI-PMH...")

    params = {
        'verb': 'ListRecords',
        'metadataPrefix': 'edm'
    }

    resumption_token = None
    checked_count = 0

    while len(artworks) < len(object_ids):
        if resumption_token:
            params = {'verb': 'ListRecords', 'resumptionToken': resumption_token}

        try:
            response = requests.get(RIJKSMUSEUM_OAI_URL, params=params, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Fout bij OAI-PMH request: {e}")
            break

        root = ET.fromstring(response.content)

        for record in root.findall('.//oai:record', namespaces):
            checked_count += 1

            # Get identifier
            header = record.find('oai:header', namespaces)
            if header is None:
                continue

            identifier = header.find('oai:identifier', namespaces)
            if identifier is None or identifier.text is None:
                continue

            # Check of dit een van onze gewenste IDs is
            record_id = identifier.text.split('/')[-1]
            if record_id not in object_ids:
                continue

            # Get image URL
            is_shown_by = record.find('.//edm:isShownBy', namespaces)
            if is_shown_by is None:
                continue
            image_url = is_shown_by.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource')
            if not image_url:
                continue

            # Get title
            title_elem = record.find('.//dc:title', namespaces)
            title = title_elem.text if title_elem is not None and title_elem.text else "Untitled"

            # Get creator
            creator_elem = record.find('.//dc:creator', namespaces)
            if creator_elem is not None:
                creator = creator_elem.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource', '')
                creator = creator.split('/')[-1] if creator else 'Unknown'
            else:
                creator = 'Unknown'

            # Get object number
            dc_identifier = record.find('.//dc:identifier', namespaces)
            obj_number = dc_identifier.text if dc_identifier is not None else record_id

            artworks.append({
                'id': record_id,
                'title': title,
                'creator': creator,
                'image_url': image_url,
                'identifier': obj_number
            })

            logger.info(f"  [{len(artworks)}/{len(object_ids)}] {title[:50]}...")

            if len(artworks) >= len(object_ids):
                break

        # Check for resumption token
        token_elem = root.find('.//oai:resumptionToken', namespaces)
        if token_elem is not None and token_elem.text:
            resumption_token = token_elem.text
        else:
            break

        # Stop als we te veel records hebben gecheckt zonder resultaat
        if checked_count > 10000 and len(artworks) == 0:
            logger.warning("Geen matches gevonden in eerste 10000 records")
            break

    return artworks


def search_via_oai(query=None, artist=None, object_type=None, max_results=10):
    """
    Alternatieve zoekfunctie die direct via OAI-PMH zoekt.
    Langzamer maar betrouwbaarder voor het krijgen van image URLs.
    """
    artworks = []

    namespaces = {
        'oai': 'http://www.openarchives.org/OAI/2.0/',
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'edm': 'http://www.europeana.eu/schemas/edm/',
    }

    logger.info(f"Zoeken via OAI-PMH (dit kan even duren)...")
    if query:
        logger.info(f"  Zoekterm: {query}")
    if artist:
        logger.info(f"  Kunstenaar: {artist}")
    if object_type:
        logger.info(f"  Type: {object_type}")

    params = {
        'verb': 'ListRecords',
        'metadataPrefix': 'edm'
    }

    resumption_token = None
    checked_count = 0

    # Maak zoektermen lowercase voor matching
    query_lower = query.lower() if query else None
    artist_lower = artist.lower() if artist else None

    while len(artworks) < max_results:
        if resumption_token:
            params = {'verb': 'ListRecords', 'resumptionToken': resumption_token}

        try:
            response = requests.get(RIJKSMUSEUM_OAI_URL, params=params, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Fout bij OAI-PMH request: {e}")
            break

        root = ET.fromstring(response.content)

        for record in root.findall('.//oai:record', namespaces):
            checked_count += 1

            if checked_count % 500 == 0:
                logger.info(f"  Doorzocht: {checked_count} records, gevonden: {len(artworks)}")

            # Get image URL first (skip if no image)
            is_shown_by = record.find('.//edm:isShownBy', namespaces)
            if is_shown_by is None:
                continue
            image_url = is_shown_by.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource')
            if not image_url:
                continue

            # Get title
            title_elem = record.find('.//dc:title', namespaces)
            title = title_elem.text if title_elem is not None and title_elem.text else ""

            # Get description
            desc_elem = record.find('.//dc:description', namespaces)
            description = desc_elem.text if desc_elem is not None and desc_elem.text else ""

            # Get creator
            creator_elem = record.find('.//dc:creator', namespaces)
            if creator_elem is not None:
                creator_ref = creator_elem.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource', '')
                creator = creator_ref.split('/')[-1] if creator_ref else 'Unknown'
            else:
                creator = 'Unknown'

            # Check query match (in title or description)
            if query_lower:
                if query_lower not in title.lower() and query_lower not in description.lower():
                    continue

            # Check artist match
            if artist_lower:
                if artist_lower not in creator.lower():
                    continue

            # Get identifier
            header = record.find('oai:header', namespaces)
            identifier_elem = header.find('oai:identifier', namespaces) if header is not None else None
            record_id = identifier_elem.text.split('/')[-1] if identifier_elem is not None and identifier_elem.text else "unknown"

            dc_identifier = record.find('.//dc:identifier', namespaces)
            obj_number = dc_identifier.text if dc_identifier is not None else record_id

            artworks.append({
                'id': record_id,
                'title': title or "Untitled",
                'creator': creator,
                'image_url': image_url,
                'identifier': obj_number
            })

            logger.info(f"  Gevonden: {title[:50]}..." if title else f"  Gevonden: {obj_number}")

            if len(artworks) >= max_results:
                break

        # Check for resumption token
        token_elem = root.find('.//oai:resumptionToken', namespaces)
        if token_elem is not None and token_elem.text:
            resumption_token = token_elem.text
        else:
            break

    logger.info(f"Totaal gevonden: {len(artworks)} kunstwerken (doorzocht: {checked_count} records)")
    return artworks


def download_artwork(artwork, output_dir):
    """Download een artwork afbeelding."""
    image_url = artwork['image_url']
    identifier = artwork['identifier'].replace('/', '_').replace('\\', '_').replace(' ', '_')

    # Bepaal extensie
    ext = '.png' if '.png' in image_url.lower() else '.jpg'
    filename = f"rijks_{identifier}{ext}"
    filepath = os.path.join(output_dir, filename)

    # Skip als al gedownload
    if os.path.exists(filepath):
        logger.info(f"  Bestaat al: {filename}")
        return filepath

    try:
        response = requests.get(image_url, timeout=60)
        response.raise_for_status()

        os.makedirs(output_dir, exist_ok=True)
        with open(filepath, 'wb') as f:
            f.write(response.content)

        size_mb = len(response.content) / 1024 / 1024
        logger.info(f"  Gedownload: {filename} ({size_mb:.1f} MB)")
        return filepath
    except requests.RequestException as e:
        logger.error(f"  Download mislukt: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description='Zoek en download kunstwerken van het Rijksmuseum',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Voorbeelden:
  %(prog)s landschap                     Zoek 'landschap' in titels
  %(prog)s --artist "Rembrandt"          Zoek werken van Rembrandt
  %(prog)s --type schilderij bloemen     Zoek schilderijen met 'bloemen'
  %(prog)s zee --amount 20               Download 20 zeegezichten
  %(prog)s --artist "Vermeer" --amount 5 Download 5 werken van Vermeer

Types: schilderij, tekening, prent, foto, beeld, meubel
        """
    )

    parser.add_argument('query', nargs='?', help='Zoekterm (zoekt in titel)')
    parser.add_argument('--artist', '-a', help='Zoek op kunstenaar')
    parser.add_argument('--type', '-t', dest='object_type', help='Type object (schilderij, tekening, etc.)')
    parser.add_argument('--amount', '-n', type=int, default=5, help='Aantal te downloaden (default: 5)')
    parser.add_argument('--output', '-o', default=DEFAULT_OUTPUT_DIR, help='Output directory (default: ./images)')
    parser.add_argument('--list-only', '-l', action='store_true', help='Alleen tonen, niet downloaden')

    args = parser.parse_args()

    if not args.query and not args.artist and not args.object_type:
        parser.print_help()
        print("\nFout: Geef minimaal een zoekterm, kunstenaar of type op.")
        sys.exit(1)

    print()
    print("=" * 60)
    print("  Rijksmuseum Kunstwerk Zoeker")
    print("=" * 60)
    print()

    # Zoek kunstwerken
    artworks = search_via_oai(
        query=args.query,
        artist=args.artist,
        object_type=args.object_type,
        max_results=args.amount
    )

    if not artworks:
        logger.warning("Geen kunstwerken gevonden met deze zoekcriteria.")
        sys.exit(0)

    print()
    print("-" * 60)
    print(f"Gevonden kunstwerken ({len(artworks)}):")
    print("-" * 60)

    for i, art in enumerate(artworks, 1):
        print(f"{i}. {art['title']}")
        print(f"   Kunstenaar: {art['creator']}")
        print(f"   ID: {art['identifier']}")
        print()

    if args.list_only:
        print("(--list-only: geen downloads)")
        sys.exit(0)

    print("-" * 60)
    print(f"Downloaden naar: {args.output}")
    print("-" * 60)

    downloaded = 0
    for art in artworks:
        result = download_artwork(art, args.output)
        if result:
            downloaded += 1

    print()
    print("=" * 60)
    print(f"  Klaar! {downloaded} afbeeldingen gedownload naar {args.output}")
    print("=" * 60)
    print()


if __name__ == '__main__':
    main()
