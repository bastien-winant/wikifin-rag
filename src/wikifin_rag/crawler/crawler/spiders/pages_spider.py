import scrapy
from crawler.items import Batch
from trafilatura import extract_metadata
from bs4 import BeautifulSoup
from datetime import datetime
from hashlib import sha256


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


    def __init__(self, batch_size=100, chunk_size=2000, **kwargs):
        super().__init__(**kwargs)
        self.batch_size = batch_size
        self.chunk_size = chunk_size
        self.batch = Batch([])


    def parse(self, response):
        response.selector.remove_namespaces()

        language = getattr(self, "language", None)

        urlset = response.xpath("//urlset")

        if language:
            urls = urlset.xpath(f".//url/link[@hreflang='{language.lower()}']")
        else:
            urls = urlset.xpath(".//url/link").getall()

        yield from response.follow_all(set(urls), callback=self.parse_content_page)


    def parse_content_page(self, response):
        document_id = generate_id(response.url)

        language = getattr(self, "language", None)

        # extract metadata
        html = response.text
        metadata = extract_metadata(html).as_dict()

        category = metadata.get('title')
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

                # save each question/pair as a chunk
                for faq in faqs:
                    # retrieve the text content
                    title = faq.css(".faq__title::text").get().strip()
                    content_html = faq.css(".faq__content").get()
                    content_text = extract_content(content_html)

                    # add the chunk to the batch
                    chunk_id = generate_id(document_id + content_text)
                    self.batch.add_item({
                        "chunk_id": chunk_id,
                        "source_url": response.url,
                        "language": language,
                        "updated_on": date,
                        "category": category,
                        "description": description,
                        "title": title,
                        "html": content_html,
                        "content": content_text,
                        "related_links": related_links
                    })

                    if self.batch.length() == self.batch_size:
                        yield self.batch.chunks
                        self.batch.clear_chunks()

            elif has_class(paragraph, "paragraph--type--pt-text"):
                title = category
                content_html = []
                content_text = []

                content_elements = paragraph.css(".text-content > *")

                # save all the paragraph text as chunks
                for element in content_elements:
                    # if there is an h2 title, upload and create a new chunk
                    if element.root.tag == "h2":
                        if content_html:
                            # add the chunk to the batch
                            chunk_id = generate_id(document_id + "\n".join(content_text))
                            self.batch.add_item({
                                "chunk_id": chunk_id,
                                "source_url": response.url,
                                "language": language,
                                "updated_on": date,
                                "category": category,
                                "description": description,
                                "title": title,
                                "html": "\n".join(content_html),
                                "content": "\n".join(content_text),
                                "related_links": related_links
                            })

                            if self.batch.length() == self.batch_size:
                                yield self.batch.chunks
                                self.batch.clear_chunks()

                        # reinitialize the running chunk containers
                        title = element.css("::text").get()
                        content_html = []
                        content_text = []

                    # accumulate non-title text into current chunk
                    else:
                        # get the next html as a string
                        html_str = element.get()

                        # if the element is a list, store strings as CSVs
                        if element.root.tag in ["ul", "ol"]:
                            text_str = extract_content(html_str, sep=", ")
                        # if the element is a header, prepend a pound sign
                        elif element.root.tag in ["h3", "h4", "h5", "h6"]:
                            text_str = f"\n\n# {extract_content(html_str).upper()}\n"
                        else:
                            text_str = extract_content(html_str)

                        content_html.append(html_str)
                        content_text.append(text_str)

                        # length-based chunking
                        if len(" ".join(content_text)) >= self.chunk_size:
                            print("LONG DOCUMENT CHUNKING")
                            chunk_id = generate_id(document_id + "\n".join(content_text))
                            self.batch.add_item({
                                "chunk_id": chunk_id,
                                "source_url": response.url,
                                "language": language,
                                "updated_on": date,
                                "category": category,
                                "description": description,
                                "title": title,
                                "html": "\n".join(content_html),
                                "content": "\n".join(content_text),
                                "related_links": related_links
                            })
            
                            if self.batch.length() == self.batch_size:
                                yield self.batch.chunks
                                self.batch.clear_chunks()

                            content_html = [html_str]
                            content_text = [text_str]


                # add the chunk to the batch
                chunk_id = generate_id(document_id + "\n".join(content_text))
                self.batch.add_item({
                    "chunk_id": chunk_id,
                    "source_url": response.url,
                    "language": language,
                    "updated_on": date,
                    "category": category,
                    "description": description,
                    "title": title,
                    "html": "\n".join(content_html),
                    "content": "\n".join(content_text),
                    "related_links": related_links
                })

                if self.batch.length() == self.batch_size:
                    yield self.batch.chunks
                    self.batch.clear_chunks()

        yield self.batch.chunks
        self.batch.clear_chunks()

        # Recursively follow links
        links = node.css("a")
        links = set([link for link in links if link.attrib.get('href', "").startswith(f"/{language}") or
                                            link.attrib.get('href', "").startswith(f"https://www.wikifin.be/{language}")])

        yield from response.follow_all(links, self.parse_content_page)