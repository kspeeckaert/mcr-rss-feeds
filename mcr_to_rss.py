import argparse
import logging
from pathlib import Path
from typing import Any
from datetime import datetime, timezone
import requests
from requests.exceptions import HTTPError
from feedgen.feed import FeedGenerator


BASE_MCR_URL = 'https://mcr.microsoft.com/api/v1/catalog'
BASE_ARTIF_URL = 'https://mcr.microsoft.com/en-us/artifact/mar'


def retrieve_json(url: str) -> Any:
    response = requests.get(url)
    try:
        response.raise_for_status()
    except HTTPError as e:
        logging.error(f'URL returned {e.response.status_code} - {e.response.content}')
        raise
    return response.json()


def generate_feed(repo: str, feed_dir: str) -> None:

    # Get the repository details for the channel
    logging.info('Retrieving repository details...')
    data = retrieve_json(f'{BASE_MCR_URL}/{repo}/details?reg=mar')

    fg = FeedGenerator()
    fg.title(data['name'])
    # Make sure to always have a link, otherwise the RSS file is invalid
    if (link := data.get('projectWebsite')) is None:
        link = f'{BASE_ARTIF_URL}/{repo}/tags'
    fg.link(href=link, rel='alternate')
    fg.description(data.get('shortDescription'))
    fg.lastBuildDate(datetime.now(timezone.utc))
    fg.updated(data.get('lastModifiedDate'))

    for category in data.get('categories', []):
        fg.category(term=category)

    # Get the tag details for the individual items
    logging.info('Retrieving tag details...')
    tag_data = retrieve_json(f'{BASE_MCR_URL}/{repo}/tags?reg=mar')

    logging.debug(f'Found {len(tag_data)} tags.')
    for tag in tag_data:
        fe = fg.add_entry()
        fe.title(tag['name'])
        fe.link(href=f'{BASE_ARTIF_URL}/{repo}/tags')
        fe.published(tag.get('createdDate'))
        fe.updated(tag.get('lastModifiedDate'))
        # Description is the command to pull the container image
        fe.description(f'docker pull mcr.microsoft.com/{repo}:{tag['name']}')
        fe.guid(f'{repo}:{tag['name']}', permalink=False)


    output_file = Path(feed_dir,f'{repo.replace('/', '_')}.xml')
    logging.info(f'Writing to {output_file}...')
    fg.rss_file(output_file)
    logging.info(f'RSS feed saved.')


def process_repo_list(filename:str, feed_dir:str) -> None:
    # Open repositories list file, each line is a separate entry
    with open (filename) as f:
        repos: List[str] = f.read().strip().splitlines()
    logging.info(f'Found {len(repos)} repositories to process.')
    
    # Ensure folder exists
    Path(feed_dir).mkdir(exist_ok=True)

    for repo in repos:
        try:
            logging.info(f'Generating feed for {repo}...')
            generate_feed(repo, feed_dir)
        except Exception as e:
            logging.error(f'Failed to generate feed for {repo}: {e!r}')
    logging.info('Finished generating feeds.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate RSS feeds for MCR repos.')
    parser.add_argument('filename', help='Filename containing list of repositories')
    parser.add_argument('--feed-dir', help='Folder to output the resulting XML files', default='feeds')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()

    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    # Avoid logging from requests
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    # Verify if file exists
    if not Path(args.filename).is_file():
        logging.error(f'File not found: {args.filename}')
        exit(1)
    print(args)
    process_repo_list(args.filename, args.feed_dir)
