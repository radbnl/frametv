
import sys
import logging
import os
import random
import json
import requests
import xml.etree.ElementTree as ET

sys.path.append('../')

from samsungtvws import SamsungTVWS

# Set the path to the folder containing the images
folder_path = './images/'

# Rijksmuseum API settings
RIJKSMUSEUM_OAI_URL = "https://data.rijksmuseum.nl/oai"

def fetch_rijksmuseum_artworks(max_items=100):
    """
    Fetch artworks from Rijksmuseum using the OAI-PMH API.
    Returns a list of dicts with 'title', 'creator', 'image_url', 'identifier'.
    """
    artworks = []

    # Build OAI-PMH request
    params = {
        'verb': 'ListRecords',
        'metadataPrefix': 'edm'
    }

    namespaces = {
        'oai': 'http://www.openarchives.org/OAI/2.0/',
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'edm': 'http://www.europeana.eu/schemas/edm/',
        'ore': 'http://www.openarchives.org/ore/terms/',
        'dcterms': 'http://purl.org/dc/terms/'
    }

    resumption_token = None

    while len(artworks) < max_items:
        if resumption_token:
            params = {'verb': 'ListRecords', 'resumptionToken': resumption_token}

        try:
            response = requests.get(RIJKSMUSEUM_OAI_URL, params=params, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            logging.error(f"Failed to fetch from Rijksmuseum API: {e}")
            break

        root = ET.fromstring(response.content)

        # Find all records
        for record in root.findall('.//oai:record', namespaces):
            if len(artworks) >= max_items:
                break

            # Get image URL from edm:isShownBy
            image_url = None
            is_shown_by = record.find('.//edm:isShownBy', namespaces)
            if is_shown_by is not None:
                image_url = is_shown_by.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource')

            if not image_url:
                continue

            # Get title
            title_elem = record.find('.//dc:title', namespaces)
            title = title_elem.text if title_elem is not None and title_elem.text else "Untitled"

            # Get creator
            creator_elem = record.find('.//dc:creator', namespaces)
            if creator_elem is not None:
                creator = creator_elem.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource', 'Unknown')
            else:
                creator = 'Unknown'

            # Get identifier
            identifier_elem = record.find('.//dc:identifier', namespaces)
            identifier = identifier_elem.text if identifier_elem is not None else "unknown"

            artworks.append({
                'title': title,
                'creator': creator,
                'image_url': image_url,
                'identifier': identifier
            })

        # Check for resumption token for pagination
        token_elem = root.find('.//oai:resumptionToken', namespaces)
        if token_elem is not None and token_elem.text:
            resumption_token = token_elem.text
        else:
            break

    return artworks


def download_artwork_image(artwork, target_folder='./images/'):
    """
    Download an artwork image from Rijksmuseum and save it locally.
    Returns the local filename if successful, None otherwise.
    """
    image_url = artwork['image_url']
    identifier = artwork['identifier'].replace('/', '_').replace('\\', '_')

    # Determine file extension from URL
    if '.png' in image_url.lower():
        ext = '.png'
    else:
        ext = '.jpg'

    filename = f"rijks_{identifier}{ext}"
    filepath = os.path.join(target_folder, filename)

    # Skip if already downloaded
    if os.path.exists(filepath):
        logging.info(f"Image already exists: {filename}")
        return filename

    try:
        response = requests.get(image_url, timeout=60)
        response.raise_for_status()

        # Save the image
        os.makedirs(target_folder, exist_ok=True)
        with open(filepath, 'wb') as f:
            f.write(response.content)

        logging.info(f"Downloaded: {filename} - {artwork['title']}")
        return filename
    except requests.RequestException as e:
        logging.error(f"Failed to download {image_url}: {e}")
        return None


def fetch_and_download_random_artwork(target_folder='./images/', max_fetch=50):
    """
    Fetch artworks from Rijksmuseum, pick a random one, and download it.
    Returns the local filename if successful.
    """
    logging.info("Fetching artworks from Rijksmuseum...")
    artworks = fetch_rijksmuseum_artworks(max_items=max_fetch)

    if not artworks:
        logging.warning("No artworks found from Rijksmuseum API")
        return None

    # Pick a random artwork
    artwork = random.choice(artworks)
    logging.info(f"Selected: {artwork['title']}")

    return download_artwork_image(artwork, target_folder)

# Set the path to the file that will store the list of uploaded filenames
upload_list_path = './uploaded_files.json'

# Settings
USE_RIJKSMUSEUM = True  # Set to True to fetch from Rijksmuseum, False to use local images only
RIJKSMUSEUM_FETCH_COUNT = 50  # Number of artworks to fetch when searching


def main():
    # Load the list of uploaded filenames from the file
    if os.path.isfile(upload_list_path):
        with open(upload_list_path, 'r') as f:
            uploaded_files = json.load(f)
    else:
        uploaded_files = []

    # Increase debug level
    logging.basicConfig(level=logging.INFO)

    # Set your TVs local IP address. Highly recommend using a static IP address for your TV.
    tv = SamsungTVWS('192.168.230.68')

    # Checks if the TV supports art mode
    art_mode = tv.art().supported()

    if art_mode == True:
        # Retrieve information about the currently selected art
        current_art = tv.art().get_current()

        # If you are having trouble setting images, uncommenting this will output the current art
        #logging.info(current_art)

        # Option 1: Fetch new artwork from Rijksmuseum
        if USE_RIJKSMUSEUM:
            logging.info("Fetching artwork from Rijksmuseum...")
            new_file = fetch_and_download_random_artwork(folder_path, RIJKSMUSEUM_FETCH_COUNT)
            if new_file:
                logging.info(f"Downloaded new artwork: {new_file}")

        # Get a list of JPG/PNG files in the folder
        files = [f for f in os.listdir(folder_path) if f.endswith('.jpg') or f.endswith('.png')]

        # Remove the filenames of images that have already been uploaded
        files = list(set(files) - set([f['file'] for f in uploaded_files]))

        if len(files) == 0:
            logging.warning('No new images to upload.')
        else:
            # Select a random file from the list of JPEG files
            file = random.choice(files)

            #Test the image is not uploaded again by hard-coding image name
            #file = '0x342fad2ec1f71e948ded12832727175ce05cc0faf5999fa6dfa6e0e156fb1c93.png'

            # Read the contents of the file
            with open(os.path.join(folder_path, file), 'rb') as f:
                data = f.read()

            # Upload the file to the TV and select it as the current art, or select it using the remote filename if it has already been uploaded
            remote_filename = None
            for uploaded_file in uploaded_files:
                if uploaded_file['file'] == file:
                    remote_filename = uploaded_file['remote_filename']
                    logging.warning('Image already uploaded.')
                    break
            if remote_filename is None:
                logging.warning('Uploading new image.')

                if file.endswith('.jpg'):
                    remote_filename = tv.art().upload(data, file_type='JPEG', matte="none")
                elif file.endswith('.png'):
                    remote_filename = tv.art().upload(data, file_type='PNG', matte="none")

                logging.warning('Uploading new image.')

                # Select the uploaded image using the remote file name
                tv.art().select_image(remote_filename, show=True)

                # Add the filename to the list of uploaded filenames
                uploaded_files.append({'file': file, 'remote_filename': remote_filename})
            else:
                logging.warning('Setting existing image, skipping upload')
                # Select the existing image using the saved remote file name from the TV
                tv.art().select_image(remote_filename, show=True)

            # Save the list of uploaded filenames to the file
            with open(upload_list_path, 'w') as f:
                json.dump(uploaded_files, f)
    else:
        logging.warning('Your TV does not support art mode.')


if __name__ == '__main__':
    main()
