import os
from collections import namedtuple
import datetime
import os
import uuid
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient, ContentSettings
from markdown import markdown
from collections import namedtuple
import sys


print(f"### Args: {sys.argv}")
DRY_RUN = False if (len(sys.argv) >= 2 and sys.argv[1].strip() == '--deploy') else True

print("### DRY RUN ###" if DRY_RUN else "### DEPLOY ###")


# HTML Template
HEAD = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Met Office Informatics Lab COVID-19 environmental data</title>
</head>
<body>
"""
FOOT = '</body></html>'


# Define a list of blobs to upload
BlobEntry = namedtuple("Blob", ['path', 'content', 'mime'])
blobs = []


# set up blob access

SIGNED_URL = os.environ['SIGNED_URL']


CONTAINER = SIGNED_URL.split('/')[3].split('?')[0]
ACCOUNT = SIGNED_URL.split('/')[2]
CREDS = SIGNED_URL.split('?', 1)[1]


# Create the BlobServiceClient object which will be used to create a container client
blob_service_client = BlobServiceClient(f"https://{ACCOUNT}/?{CREDS}")
container_client = blob_service_client.get_container_client(CONTAINER)


print("\nListing blobs...")
# List the blobs in the container
blob_list = container_client.list_blobs()
all_blobs = [blob.name for blob in blob_list]  # if blob.name[0] != '.' and blob.name.find('/.') == -1]
print(f"found {len(all_blobs)} blobs")


# filter out 'hidden' files
clean_blobs = []
for blob in all_blobs:
    if blob[0] == '.' or blob.find('/.') >= 0:
        continue
    clean_blobs.append(blob)
print(f"got {len(clean_blobs)} non hidden blobs")


# Build Index

base = "<NOT A BASE>"
html = """
    <h1>Met Office Informatics Lab COVID-19 environmental data index</h1>
    <p>This is a very simple index of the files in this container/bucket.<p>
    <p>For information on this dataset see
    <a href="https://medium.com/informatics-lab/met-office-and-partners-offer-data-and-compute-platform-for-covid-19-researchers-83848ac55f5f">the related blog post</a>
    and the <a href="README.md">README.md</a>.
    </p>
    <p>For downloading numerous files we suggest using <a href="https://docs.microsoft.com/en-us/azure/storage/common/storage-use-azcopy-v10">AzCopy</a> or other tools rather than this page.</p>
"""


def sorter(item):
    return (len(item.split('/')), item)


for i, blob in enumerate(sorted(clean_blobs, key=sorter)):
    fbase = blob.rsplit('/', 1)[0] if blob.find('/') >= 0 else ''
    name = blob.rsplit('/', 1)[1] if blob.find('/') >= 0 else blob

    if not fbase == base:
        base = fbase

#         if len(base) >0 and base.split('/')[-1][0] == '.':
#             continue

        jsid = "base-" + base.replace('/', '--')
        htmlstr = "" if i == 0 else "</ul>"
        htmlstr += f"\n\n<h3>{base}/<a style='font-size:50%' href='#' onclick='$(\"#{jsid}\").toggle();false'>[show/hide]</a></h3>\n"
        htmlstr += f"<ul id='{jsid}'>"
        html += htmlstr

#     if f.name[0].strip()[0] == "." or (fbase and fbase.split('/')[-1][0] == '.'):
#         continue
    htmlstr = f'\t<li><a title="{name}" href="{blob}">{name}</a></li>'
    html += htmlstr
html += f"""</ul>
<script type="text/javascript" src="https://code.jquery.com/jquery-3.4.1.slim.min.js"></script>
<p style="font-size:50%">Created at {datetime.datetime.now()}</p>"""

blobs.append(BlobEntry('index.html', HEAD+html+FOOT, 'text/html'))


# Convert markdown files to HTML
for path_local in ('./README_data.md', './README_data_air_quality.md'):
    name = os.path.splitext(os.path.basename(path_local))[0]

    with open(path_local) as fp:
        markdown_readme = fp.read()

    # markdown_readme = blob_service_client.get_blob_client(container=COUNTAINER, blob=README_MD_PATH).download_blob().readall().decode('utf-8')

    print(f'Markdown from {path_local}:\n')
    print(markdown_readme)
    print('\n'*3)

    # Add raw markdown
    blobs.append(BlobEntry(f'{name}.md', markdown_readme, 'text/markdown'))

    # Add HTML
    html = markdown(markdown_readme)
    blobs.append(BlobEntry(f'{name}.html', HEAD+html+FOOT, 'text/html'))


# Add technical docs
TECHNICAL_DOCS_PATH = 'README_data_processing.pdf'
with open(TECHNICAL_DOCS_PATH, 'rb') as fp:
    technical_docs_data = fp.read()
blobs.append(BlobEntry(TECHNICAL_DOCS_PATH, technical_docs_data, 'application/pdf'))


# Upload to the blob store
if(DRY_RUN):
    print("*** DRY RUN ***")
    for blob_entry in blobs:
        print(f"""

---------------------------------------------------
{blob_entry.path} {blob_entry.mime}
""")
else:
    for blob_entry in blobs:
        print(f'upload {blob_entry.path}...')
        blob_client = blob_service_client.get_blob_client(container=CONTAINER, blob=blob_entry.path)
        blob_client.upload_blob(
            blob_entry.content,
            overwrite=True,
            content_settings=ContentSettings(content_type=blob_entry.mime))
        print('uploaded')
