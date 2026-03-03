#!/usr/bin/env python3
"""
Debug script voor Samsung Frame TV connectie en image upload.
Gebruik: python3 debug_tv.py [image_path]
"""

import sys
import os
import logging

sys.path.append('../')

from samsungtvws import SamsungTVWS

# Configuratie
TV_IP = '192.168.230.68'
DEFAULT_TEST_IMAGE = './images/rijks_RP-P-1906-2564.jpg'

# Verbose logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_connection(tv_ip):
    """Test basis connectie met de TV."""
    logger.info(f"=== Test 1: Connectie met TV ({tv_ip}) ===")
    try:
        tv = SamsungTVWS(tv_ip)
        logger.info("SamsungTVWS object aangemaakt")
        return tv
    except Exception as e:
        logger.error(f"Kon geen verbinding maken: {e}")
        return None


def test_art_mode(tv):
    """Test of Art Mode ondersteund wordt."""
    logger.info("=== Test 2: Art Mode Support ===")
    try:
        art = tv.art()
        supported = art.supported()
        logger.info(f"Art Mode ondersteund: {supported}")
        return supported
    except Exception as e:
        logger.error(f"Fout bij Art Mode check: {e}")
        return False


def get_current_art(tv):
    """Haal huidige artwork info op."""
    logger.info("=== Test 3: Huidige Artwork ===")
    try:
        current = tv.art().get_current()
        logger.info(f"Huidige artwork: {current}")
        return current
    except Exception as e:
        logger.error(f"Fout bij ophalen huidige artwork: {e}")
        return None


def list_uploaded_art(tv):
    """Lijst alle geuploadde artwork."""
    logger.info("=== Test 4: Geuploadde Artwork Lijst ===")
    try:
        art_list = tv.art().available()
        logger.info(f"Aantal items: {len(art_list) if art_list else 0}")
        if art_list:
            for i, item in enumerate(art_list[:5]):  # Eerste 5 tonen
                logger.info(f"  {i+1}. {item}")
            if len(art_list) > 5:
                logger.info(f"  ... en nog {len(art_list) - 5} meer")
        return art_list
    except Exception as e:
        logger.error(f"Fout bij ophalen artwork lijst: {e}")
        return None


def upload_image(tv, image_path):
    """Upload een afbeelding naar de TV."""
    logger.info(f"=== Test 5: Upload Afbeelding ===")
    logger.info(f"Bestand: {image_path}")

    if not os.path.exists(image_path):
        logger.error(f"Bestand bestaat niet: {image_path}")
        return None

    file_size = os.path.getsize(image_path)
    logger.info(f"Bestandsgrootte: {file_size / 1024 / 1024:.2f} MB")

    # Bepaal file type
    if image_path.lower().endswith('.png'):
        file_type = 'PNG'
    else:
        file_type = 'JPEG'
    logger.info(f"File type: {file_type}")

    try:
        with open(image_path, 'rb') as f:
            data = f.read()

        logger.info("Uploaden naar TV...")
        remote_filename = tv.art().upload(data, file_type=file_type, matte="none")
        logger.info(f"Upload succesvol! Remote filename: {remote_filename}")
        return remote_filename
    except Exception as e:
        logger.error(f"Upload mislukt: {e}")
        return None


def select_image(tv, remote_filename):
    """Selecteer een afbeelding als huidige artwork."""
    logger.info(f"=== Test 6: Selecteer Afbeelding ===")
    try:
        tv.art().select_image(remote_filename, show=True)
        logger.info(f"Afbeelding geselecteerd: {remote_filename}")
        return True
    except Exception as e:
        logger.error(f"Selecteren mislukt: {e}")
        return False


def main():
    print("\n" + "="*60)
    print("  Samsung Frame TV Debug Script")
    print("="*60 + "\n")

    # Bepaal test image
    if len(sys.argv) > 1:
        test_image = sys.argv[1]
    else:
        test_image = DEFAULT_TEST_IMAGE

    # Test 1: Connectie
    tv = test_connection(TV_IP)
    if not tv:
        print("\n[FOUT] Kan geen verbinding maken met TV.")
        print(f"       Controleer of de TV aan staat en bereikbaar is op {TV_IP}")
        return 1

    # Test 2: Art Mode
    if not test_art_mode(tv):
        print("\n[FOUT] TV ondersteunt geen Art Mode of is niet bereikbaar.")
        return 1

    # Test 3: Huidige artwork
    get_current_art(tv)

    # Test 4: Lijst artwork
    list_uploaded_art(tv)

    # Test 5 & 6: Upload en selecteer (alleen als bestand bestaat)
    if os.path.exists(test_image):
        print(f"\nWil je '{test_image}' uploaden naar de TV? [j/N] ", end='')
        try:
            answer = input().strip().lower()
        except EOFError:
            answer = 'n'

        if answer == 'j':
            remote_filename = upload_image(tv, test_image)
            if remote_filename:
                select_image(tv, remote_filename)
    else:
        logger.warning(f"Test afbeelding niet gevonden: {test_image}")
        logger.info("Geef een afbeelding op als argument: python3 debug_tv.py /pad/naar/afbeelding.jpg")

    print("\n" + "="*60)
    print("  Debug voltooid")
    print("="*60 + "\n")
    return 0


if __name__ == '__main__':
    sys.exit(main())
