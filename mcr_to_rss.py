import argparse
import datetime
import logging
from pathlib import Path
import requests
from requests.exceptions import HTTPError
from feedgen.feed import FeedGenerator


def generate_feed(repo):

    # Get the repository details for the channel
    logging.info('Retrieving repository details...')
    url = f'https://mcr.microsoft.com/api/v1/catalog/{repo}/details?reg=mar'
    output_file = f'{repo.replace("/", "_")}.xml'

    response = requests.get(url)
    try:
        response.raise_for_status()
    except HTTPError as e:
        logging.error(f'Web service returned {e.response.status_code} - {e.response.content}')
        raise
    data = response.json()

    fg = FeedGenerator()
    fg.title(data['name'])
    # Make sure to always have a link, otherwise the RSS file is invalid
    if (link := data.get('projectWebsite')) is None:
        link = f'https://mcr.microsoft.com/en-us/artifact/mar/{repo}/tags'
    fg.link(href=link, rel='alternate')
    fg.description(data.get('shortDescription'))
    fg.lastBuildDate(datetime.datetime.now(datetime.UTC))
    fg.updated(data.get('lastModifiedDate'))

    for category in data.get('categories', []):
        fg.category(term=category)

    # Get the tag details for the individual items
    logging.info('Retrieving tag details...')
    url = f'https://mcr.microsoft.com/api/v1/catalog/{repo}/tags?reg=mar'
    response = requests.get(url)
    try:
        response.raise_for_status()
    except HTTPError as e:
        logging.error(f'Web service returned {e.response.status_code} - {e.response.content}')
        raise
    tag_data = response.json()

    logging.debug(f'Found {len(tag_data)} tags.')
    for tag in tag_data:
        fe = fg.add_entry()
        fe.title(tag['name'])
        fe.link(href=f'https://mcr.microsoft.com/en-us/artifact/mar/{repo}/tags')
        fe.published(tag.get('createdDate'))
        fe.updated(tag.get('lastModifiedDate'))
        # Description is the command to pull the container image
        fe.description(f'docker pull mcr.microsoft.com/{repo}:{tag['name']}')
        fe.guid(f'{repo}:{tag['name']}', permalink=False)

    filename = f'feeds/{output_file}'
    logging.info(f'Writing to {filename}...')
    fg.rss_file(filename)
    logging.info(f"RSS feed saved.")


def process_repo_list(filename):
    # Open repositories list file, each line is a separate entry
    with open (filename) as f:
        repos = f.read().strip().splitlines()
    logging.info(f'Found {len(repos)} repositories to process.')
    
    # Ensure folder exists
    Path('feeds').mkdir(exist_ok=True)

    for repo in repos:
        try:
            logging.info(f'Generating feed for {repo}...')
            generate_feed(repo)
        except Exception as e:
            logging.error(f'Failed to generate feed for {repo}: {e!r}')
    logging.info('Finished generating feeds.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate RSS feeds for MCR repos.")
    parser.add_argument("filename", help="Filename containing list of repositories")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()

    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    # Avoid logging from requests
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    process_repo_list(args.filename)
