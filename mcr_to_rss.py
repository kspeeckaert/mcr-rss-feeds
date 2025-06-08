import sys
import requests
import datetime
from feedgen.feed import FeedGenerator

def main(container_image):
    repo = container_image
    url = f'https://mcr.microsoft.com/api/v1/catalog/{repo}/details?reg=mar'
    output_file = f'{repo.replace("/", "_")}.xml'

    response = requests.get(url)
    response.raise_for_status()
    data = response.json()

    fg = FeedGenerator()
    fg.title(data['name'])
    fg.link(href=data['projectWebsite'], rel='alternate')
    fg.description(data['shortDescription'])
    fg.lastBuildDate(datetime.datetime.now(datetime.UTC))

    for category in data.get('categories', []):
        fg.category(term=category)

    url = f'https://mcr.microsoft.com/api/v1/catalog/{repo}/tags?reg=mar'
    response = requests.get(url)
    response.raise_for_status()
    tag_data = response.json()

    for tag in tag_data:
        fe = fg.add_entry()
        fe.title(tag['name'])
        fe.link(href=f'https://mcr.microsoft.com/en-us/artifact/mar/{repo}/tags')
        fe.published = tag.get('createdDate')
        fe.updated  = tag.get('lastModifiedDate')
        fe.description(f'docker pull mcr.microsoft.com/{repo}:{tag['name']}')
        fe.guid(f'{repo}:{tag['name']}', permalink=False)

    fg.rss_file(output_file)
    print(f"RSS feed saved to {output_file}")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python mcr_to_rss.py <container-image>")
        sys.exit(1)
    main(sys.argv[1])
