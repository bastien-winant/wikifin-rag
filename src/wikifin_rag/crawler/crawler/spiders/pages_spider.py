import scrapy
from crawler.items import Batch
from trafilatura import extract_metadata
from bs4 import BeautifulSoup
from datetime import datetime
from hashlib import sha256
from wikifin_rag.db_client import PostgresClient


def has_class(selector, classname):
    selector_classes = selector.attrib["class"].split()
    return classname in selector_classes


def extract_content(html_str, sep=" "):
    soup = BeautifulSoup(html_str, "html.parser")
    return soup.get_text(sep, strip=True)


def generate_id(value):
    return sha256(value.encode()).hexdigest()[:16]


class PagesSpider(scrapy.Spider):
    name = "pages"
    start_urls = ["https://www.wikifin.be/page/sitemap.xml"]


    def __init__(self, batch_size=100, **kwargs):
        super().__init__(**kwargs)

        self.batch_size = int(batch_size)

        self.db_client = PostgresClient()
        self.batch = Batch(
            documents=[],
            size=self.batch_size,
            on_full_callback=self.db_client.insert_batch,
            clear_on_full=True
        )

        drop_tables = getattr(self, "drop_tables", "False").capitalize() == "True"
        self.db_client.open_connection()
        self.db_client.create_tables(drop=drop_tables)


    def parse(self, response):
        response.selector.remove_namespaces()

        language = getattr(self, "language", None)

        urlset = response.xpath("//urlset")

        if language:
            urls = urlset.xpath(f".//url/link[@hreflang='{language.lower()}']")
        else:
            urls = urlset.xpath(".//url/link[@hreflang='fr' or @hreflang='nl']")

        yield from response.follow_all(set(urls), callback=self.parse_content_page)


    def parse_content_page(self, response):
        try:
            page_id = generate_id(response.url)

            language = "fr" if "/fr/" in response.url else "nl"

            # extract metadata
            html = response.text
            metadata = extract_metadata(html).as_dict()

            title = metadata.get('title')
            description = metadata.get('description')

            date_str = metadata.get('date')
            date_format = '%Y-%m-%d'
            date = datetime.strptime(date_str, date_format) if date_str else None

            # isolate the main content
            main = response.css("#main-content")[0]
            node = main.css(".node")[0]

            # Save related link URLs
            related_links = node.css('.related-content a::attr("href")').getall()

            # extract the text from main content
            node_content = node.css(".node__content")[0]
            node_paragraph_container = node_content.css(".node__paragraphs")[0]
            node_paragraphs = node_paragraph_container.css(":scope > .paragraph")


            for paragraph in node_paragraphs:
                # skip table of content
                if has_class(paragraph, "paragraph--type--pt-toc"):
                    continue

                elif has_class(paragraph, "paragraph--type--pt-menu-children"):
                    continue

                elif has_class(paragraph, "paragraph--type--pt-faq-list"):
                    faqs = paragraph.css(".faq")

                    # save each question/pair as a document
                    for faq in faqs:
                        # retrieve the text content
                        section = faq.css(".faq__title::text").get().strip()
                        content_html = faq.css(".faq__content").get()
                        content_text = extract_content(content_html)

                        # add the document to the batch
                        document_id = generate_id(page_id + content_text)
                        self.batch.add_document({
                            "id": document_id,
                            "source_url": response.url,
                            "language": language,
                            "updated_on": date,
                            "title": title,
                            "description": description,
                            "section": section,
                            "html": content_html,
                            "content": content_text,
                            "related_links": related_links
                        })

                elif has_class(paragraph, "paragraph--type--pt-text"):
                    section = title

                    # containers to accumulate document content
                    content_html = []
                    content_text = []

                    # extract all direct children of the .text-content container
                    content_elements = paragraph.css(".text-content > *")

                    # iterate over all html elements
                    for element in content_elements:
                        # if the element is an H2 title
                        if element.root.tag == "h2":
                            # save the current document content
                            if content_html:
                                # add the document to the batch
                                document_id = generate_id(page_id + "\n".join(content_text))
                                self.batch.add_document({
                                    "id": document_id,
                                    "source_url": response.url,
                                    "language": language,
                                    "updated_on": date,
                                    "title": title,
                                    "description": description,
                                    "section": section,
                                    "html": "\n".join(content_html),
                                    "content": "\n".join(content_text),
                                    "related_links": related_links
                                })

                            # set the h2 text as the section title
                            section = element.css("::text").get()

                            # reinitialize the running document containers
                            content_html = []
                            content_text = []

                        # accumulate non-title content into current document
                        else:
                            # get the next html as a string
                            html_str = element.get()

                            # if the element is a list, store strings as CSVs
                            if element.root.tag in ["ul", "ol"]:
                                text_str = extract_content(html_str, sep=", ")
                            # if the element is a header, capitalize and prepend a pound sign
                            elif element.root.tag in ["h3", "h4", "h5", "h6"]:
                                text_str = f"\n\n# {extract_content(html_str).upper()}\n"
                            else:
                                text_str = extract_content(html_str)

                            content_html.append(html_str)
                            content_text.append(text_str)


                    # add the document to the batch
                    document_id = generate_id(page_id + "\n".join(content_text))
                    self.batch.add_document({
                        "id": document_id,
                        "source_url": response.url,
                        "language": language,
                        "updated_on": date,
                        "title": title,
                        "description": description,
                        "section": section,
                        "html": "\n".join(content_html),
                        "content": "\n".join(content_text),
                        "related_links": related_links
                    })

            # Recursively follow links
            links = node.css("a")
            links = set([link for link in links if link.attrib.get('href', "").startswith(f"/{language}") or
                                                link.attrib.get('href', "").startswith(f"https://www.wikifin.be/{language}")])

            yield from response.follow_all(links, self.parse_content_page)
        except Exception as e:
            self.logger.error(f"Unable to parse page content: {e}")


    def closed(self, reason):
        if not self.batch.is_empty():
            self.batch.on_full_callback(self.batch.documents)
            self.batch.clear_documents()

        self.db_client.close_connection()
        self.logger.info(f"Spider closed with reason: {reason}")